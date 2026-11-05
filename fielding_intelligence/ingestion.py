"""Cricsheet JSON ingestion: observed events, missingness and source provenance."""
from collections import Counter
from datetime import date
import hashlib
import json
import logging
import zipfile

from .models import FieldingAlias, FieldingMatch, FieldingPerson, FieldingTrial
from .registry import normalize_name, upsert

logger = logging.getLogger(__name__)
PARSER_VERSION = 1
UNAVAILABLE = ["catch_opportunities", "dropped_catches", "catch_difficulty", "fielding_positions",
               "run_out_opportunities", "direct_hits", "misfields", "runs_saved", "catch_assists"]


def parse_match(raw, match_id):
    """Retain successful-dismissal evidence, never infer failed opportunities."""
    info = raw["info"]
    dates = sorted(date.fromisoformat(str(d)) for d in info["dates"])
    registry = info["registry"]["people"]
    innings_facts = []
    for number, innings in enumerate(raw.get("innings", []), 1):
        batting_team = innings["team"]
        fielding_team = next((t for t in info["teams"] if t != batting_team), None)
        roster = [registry[n] for n in info.get("players", {}).get(fielding_team, []) if n in registry]
        players = {person_id: Counter() for person_id in roster}
        totals = Counter()
        totals["runs"] = sum(innings.get("penalty_runs", {}).values())
        for over in innings.get("overs", []):
            for delivery in over["deliveries"]:
                totals["deliveries"] += 1
                if not any(k in delivery.get("extras", {}) for k in ("wides", "noballs")):
                    totals["legal_deliveries"] += 1
                totals["runs"] += delivery["runs"]["total"]
                for wicket in delivery.get("wickets", []):
                    kind = wicket["kind"]
                    if kind not in {"retired hurt", "retired not out"}:
                        totals["wickets"] += 1
                    fielders = wicket.get("fielders", [])
                    ids = []
                    for fielder in fielders:
                        name = fielder.get("name")
                        if name in registry:
                            ids.append(registry[name])
                        else:
                            totals["unresolved_fielder_events"] += 1
                    if kind == "caught and bowled":
                        ids = [registry[delivery["bowler"]]]
                    for person_id in set(ids):
                        stats = players.setdefault(person_id, Counter())
                        if kind in {"caught", "caught and bowled"}:
                            stats["catch_involvements"] += 1
                            # Multiple names do not tell us who completed the catch.
                            if len(set(ids)) == 1:
                                stats["catches"] += 1
                        elif kind == "run out":
                            stats["run_out_involvements"] += 1
                            if len(set(ids)) > 1:
                                stats["multi_fielder_run_out_involvements"] += 1
                        elif kind == "stumped":
                            stats["stumpings"] += 1
                    if kind in {"caught", "caught and bowled"}:
                        totals["catch_dismissals"] += 1
                    elif kind == "run out":
                        totals["run_out_dismissals"] += 1
                    elif kind == "stumped":
                        totals["stumpings"] += 1
        # XI membership is exposure, not proof of a fielding opportunity.
        # Substitutions mean exact individual on-field delivery exposure is unknown.
        innings_facts.append({
            "innings": number, "batting_team": batting_team, "fielding_team": fielding_team,
            "xi": roster, "players": {p: dict(v) for p, v in players.items()},
            "observed": dict(totals), "individual_delivery_exposure": None,
        })
    return {
        "id": "cricsheet:" + match_id,
        "start_date": dates[0], "end_date": dates[-1],
        "source_created": date.fromisoformat(raw["meta"]["created"]),
        "match_format": info["match_type"], "gender": info["gender"],
        "competition": info.get("event", {}).get("name") or info.get("team_type", "unknown"),
        "source": "cricsheet", "revision": raw["meta"]["revision"],
        "source_sha256": hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest(),
        "facts": {"innings": innings_facts, "unavailable": UNAVAILABLE,
                  "registry": registry, "venue": info.get("venue"),
                  "source_license": "ODC-By 1.0", "data_version": raw["meta"]["data_version"],
                  "parser_version": PARSER_VERSION},
    }


def ingest_archive(session, path, limit=None):
    """Transaction belongs to caller. Read ZIP members without extracting paths."""
    matches, seen, revisions = [], set(), 0
    with zipfile.ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if not name.endswith(".json"):
                continue
            member = archive.getinfo(name)
            if member.file_size > 20_000_000:
                raise ValueError("Oversized match member")
            raw = json.loads(archive.read(name))
            match_id = name.rsplit("/", 1)[-1].removesuffix(".json")
            if match_id in seen:
                raise ValueError("Duplicate fixture ID in archive")
            seen.add(match_id)
            parsed = parse_match(raw, match_id)
            people = [{"id": person_id, "name": person_name}
                      for person_name, person_id in raw["info"]["registry"]["people"].items()]
            upsert(session, FieldingPerson, people, ["id"])
            upsert(session, FieldingAlias, [
                {"person_id": p["id"], "name": p["name"], "normalized_name": normalize_name(p["name"])}
                for p in people], ["person_id", "name"])
            old = session.get(FieldingMatch, parsed["id"])
            if (old and old.source_sha256 == parsed["source_sha256"]
                    and old.facts.get("parser_version") == PARSER_VERSION):
                continue
            if old and old.revision > parsed["revision"]:
                raise ValueError("Refusing to downgrade a source revision")
            upsert(session, FieldingMatch, [parsed], ["id"], list(set(parsed) - {"id"}))
            matches.append(parsed["id"])
            revisions += int(old is not None)
            if limit is not None and len(seen) >= limit:
                break
    return {"changed_matches": len(matches), "examined_matches": len(seen), "revisions": revisions}


def import_trials(session, records):
    """Explicit adapter contract for legally obtained, annotated event data.

    The caller must have a licence. No provider subscription or remote request
    is created here. Incomplete feeds must not claim exhaustive coverage.
    """
    rows = []
    for record in records:
        row = dict(record)
        required = {"source", "event_id", "kind", "match_id", "event_date", "available_date",
                    "match_format", "gender", "provenance"}
        if not required <= row.keys():
            raise ValueError("Trial record is missing required identity/availability/provenance fields")
        if row["kind"] not in {"catch", "run_out", "ground"}:
            raise ValueError("Unknown fielding trial kind")
        if not row.get("provenance") or row.get("source") == "cricsheet":
            raise ValueError("Detailed trials need explicit non-Cricsheet event provenance")
        for key in ("opportunity", "success", "direct_hit", "exhaustive_delivery_coverage"):
            if row.get(key) is not None and type(row[key]) is not bool:
                raise ValueError(f"{key} must be boolean or null")
        if row.get("success") is not None and row.get("opportunity") is not True:
            raise ValueError("Conversion outcome requires an observed opportunity")
        if row.get("direct_hit") is not None and row["kind"] != "run_out":
            raise ValueError("Only run-outs can carry a direct-hit label")
        if row.get("person_id") and not session.get(FieldingPerson, row["person_id"]):
            raise ValueError("Unknown stable player ID")
        row["event_date"] = date.fromisoformat(str(row["event_date"]))
        row["available_date"] = date.fromisoformat(str(row["available_date"]))
        if row["available_date"] < row["event_date"]:
            raise ValueError("Event cannot be available before it occurred")
        row.setdefault("context", {})
        if not isinstance(row["context"], dict):
            raise ValueError("Context must be an object")
        row.setdefault("exhaustive_delivery_coverage", False)
        for key in ("person_id", "opportunity", "success", "direct_hit", "runs_saved"):
            row.setdefault(key, None)
        if row["exhaustive_delivery_coverage"] and row["kind"] in {"catch", "run_out"} and row["opportunity"] is None:
            raise ValueError("Complete opportunity coverage cannot carry an unknown opportunity label")
        if row["opportunity"] is False and row["direct_hit"] is True:
            raise ValueError("A direct hit cannot be labelled as no run-out opportunity")
        if row["runs_saved"] is not None:
            import math
            if type(row["runs_saved"]) not in (int, float) or not math.isfinite(row["runs_saved"]):
                raise ValueError("Runs saved must be a finite number or null")
        existing = session.get(FieldingTrial, (row["source"], row["event_id"], row["kind"]))
        if existing and any(getattr(existing, key) != value for key, value in row.items()):
            raise ValueError("Conflicting event revision needs explicit availability-aware reconciliation")
        for earlier in rows:
            if all(earlier[k] == row[k] for k in ("source", "event_id", "kind")) and earlier != row:
                raise ValueError("Conflicting duplicate event in import batch")
        rows.append(row)
    upsert(session, FieldingTrial, rows, ["source", "event_id", "kind"])
    return len(rows)
