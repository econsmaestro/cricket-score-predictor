"""Historical evidence lookups and revision-aware database caching."""
from collections import Counter
from datetime import date
import hashlib
import json
import logging

from sqlalchemy import select

from .models import FieldingCache, FieldingMatch, FieldingTrial
from .ratings import fielding_quality
from .registry import upsert

logger = logging.getLogger(__name__)
TRIAL_FIELDS = ("source", "event_id", "kind", "match_id", "event_date", "available_date",
                "match_format", "gender", "person_id", "opportunity", "success",
                "direct_hit", "runs_saved", "context", "exhaustive_delivery_coverage")


def trial_records(session, as_of, match_format, gender):
    cutoff = date.fromisoformat(str(as_of))
    objects = session.scalars(select(FieldingTrial).where(
        FieldingTrial.event_date < cutoff, FieldingTrial.available_date < cutoff,
        FieldingTrial.match_format == match_format, FieldingTrial.gender == gender
    ).order_by(FieldingTrial.source, FieldingTrial.event_id, FieldingTrial.kind))
    return [{key: getattr(row, key) for key in TRIAL_FIELDS} for row in objects]


def cached_quality(session, person_id, as_of, match_format, gender):
    rows = trial_records(session, as_of, match_format, gender)
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()
    key = f"quality:v1:{person_id}:{match_format}:{gender}:{as_of}"
    old = session.get(FieldingCache, key)
    if old and old.source_digest == digest:
        return old.payload
    payload = fielding_quality(rows, person_id=person_id, as_of=as_of,
                              match_format=match_format, gender=gender)
    upsert(session, FieldingCache, [{"cache_key": key, "source_digest": digest, "payload": payload}],
           ["cache_key"], ["source_digest", "payload"])
    return payload


def history_before(session, as_of, match_format, gender):
    cutoff = date.fromisoformat(str(as_of))
    return list(session.scalars(select(FieldingMatch).where(
        FieldingMatch.end_date < cutoff, FieldingMatch.source_created < cutoff,
        FieldingMatch.match_format == match_format, FieldingMatch.gender == gender
    ).order_by(FieldingMatch.end_date, FieldingMatch.id)))


def observed_history(matches):
    totals, players = Counter(), {}
    for match in matches:
        for innings in match.facts["innings"]:
            totals.update(innings["observed"])
            for person_id, counts in innings["players"].items():
                players.setdefault(person_id, Counter()).update(counts)
    denominator = totals["deliveries"]
    return {
        "matches": len(matches), "observed": dict(totals),
        "players": {p: dict(v) for p, v in players.items()},
        "observed_catch_dismissals_per_delivery": (
            totals["catch_dismissals"] / denominator if denominator else None),
        "observed_run_out_dismissals_per_delivery": (
            totals["run_out_dismissals"] / denominator if denominator else None),
        "interpretation": "Dismissal incidence, not opportunity occurrence or player conversion ability",
    }


def shadow_evidence(session, as_of, match_format, gender, xi_ids):
    history = observed_history(history_before(session, as_of, match_format, gender))
    known = [p for p in xi_ids if p in history["players"]]
    if len(known) != len(xi_ids) or not xi_ids:
        logger.info("Fielding coverage incomplete: %d/%d XI identities have historical evidence",
                    len(known), len(xi_ids))
    return {
        "mode": "shadow", "applied": False, "fqr": None,
        "reason": "No validated opportunity-adjusted replacement; legacy prediction preserved",
        "historical_matches": history["matches"],
        "xi_players": len(xi_ids), "xi_with_dismissal_records": len(known),
        "catch_opportunity_probability": None, "catch_conversion_probability": None,
        "run_out_opportunity_probability": None, "run_out_conversion_probability": None,
        "fpi": None,
    }
