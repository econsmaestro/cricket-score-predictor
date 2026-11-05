"""Stable IDs and deliberately conservative name resolution."""
import csv
import io
import logging
import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .models import FieldingAlias, FieldingIdentifier, FieldingPerson

logger = logging.getLogger(__name__)


def normalize_name(name):
    return " ".join(unicodedata.normalize("NFKC", name).casefold().split())


def upsert(session, model, rows, keys, update=()):
    """Atomic idempotent insert batches; supports isolated SQLite tests too."""
    if not rows:
        return
    constructor = pg_insert if session.get_bind().dialect.name == "postgresql" else sqlite_insert
    # Repeated aliases in a single batch must not hit the same conflict twice.
    rows = list({tuple(row[k] for k in keys): row for row in rows}.values())
    for start in range(0, len(rows), 500):
        stmt = constructor(model).values(rows[start:start + 500])
        if update:
            stmt = stmt.on_conflict_do_update(
                index_elements=keys, set_={key: getattr(stmt.excluded, key) for key in update})
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=keys)
        session.execute(stmt)


def ingest_registry(session, people_csv, names_csv):
    """Provider mappings and variant names, including duplicate-name people."""
    people, identifiers, aliases = [], [], []
    for row in csv.DictReader(io.StringIO(people_csv)):
        person_id = row["identifier"]
        if not re.fullmatch(r"[0-9a-f]{8}", person_id):
            raise ValueError("Invalid Cricsheet person identifier")
        people.append({"id": person_id, "name": row["name"]})
        identifiers.append({"source": "cricsheet", "external_id": person_id, "person_id": person_id})
        for key, value in row.items():
            if key.startswith("key_") and value:
                identifiers.append({"source": key[4:], "external_id": value, "person_id": person_id})
        for name in {row["name"], row.get("unique_name")} - {None, ""}:
            aliases.append({"person_id": person_id, "name": name, "normalized_name": normalize_name(name)})
    known = {row["id"] for row in people}
    existing_ids = {(source, external): person for source, external, person in session.execute(
        select(FieldingIdentifier.source, FieldingIdentifier.external_id, FieldingIdentifier.person_id))}
    for mapping in identifiers:
        key = (mapping["source"], mapping["external_id"])
        if key in existing_ids and existing_ids[key] != mapping["person_id"]:
            raise ValueError("Conflicting provider identity requires manual reconciliation")
        existing_ids[key] = mapping["person_id"]
    for row in csv.DictReader(io.StringIO(names_csv)):
        if row["identifier"] not in known:
            raise ValueError("Alias references an absent registry person")
        aliases.append({"person_id": row["identifier"], "name": row["name"],
                        "normalized_name": normalize_name(row["name"])})
    upsert(session, FieldingPerson, people, ["id"], ["name"])
    upsert(session, FieldingIdentifier, identifiers, ["source", "external_id"])
    upsert(session, FieldingAlias, aliases, ["person_id", "name"])
    # Reuse existing ESPN identities; a duplicate display name is not evidence.
    from models import DiscoveredPlayer
    existing = dict(session.execute(select(DiscoveredPlayer.espn_id, DiscoveredPlayer.id)).all())
    for mapping in identifiers:
        if mapping["source"] == "cricinfo" and mapping["external_id"] in existing:
            session.get(FieldingPerson, mapping["person_id"]).discovered_player_id = existing[mapping["external_id"]]
    return {"people": len(people), "provider_identifiers": len(identifiers),
            "aliases": len({(a["person_id"], a["name"]) for a in aliases})}


def resolve_person(session, *, source=None, external_id=None, name=None, roster_ids=None):
    if source and external_id:
        identity = session.get(FieldingIdentifier, (source, str(external_id)))
        return identity.person_id if identity else None
    if not name:
        return None
    candidates = set(session.scalars(select(FieldingAlias.person_id).where(
        FieldingAlias.normalized_name == normalize_name(name))))
    if roster_ids is not None:
        candidates &= set(roster_ids)
    if len(candidates) != 1:
        logger.info("Fielding identity unresolved: %d candidates; no name-based merge", len(candidates))
        return None
    return candidates.pop()
