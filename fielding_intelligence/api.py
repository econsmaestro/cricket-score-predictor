"""Read-only research status and component estimates, not a live FQR promise."""
from datetime import date

from flask import Blueprint, jsonify, request
from sqlalchemy import func, select

from app import db
from .models import FieldingMatch, FieldingPerson, FieldingTrial
from .ratings import fielding_quality
from .service import trial_records
from .sources import ATTRIBUTION

blueprint = Blueprint("fielding_intelligence", __name__, url_prefix="/api/fielding")
FORMATS = {"mens_t20": ("T20", "male"), "womens_t20": ("T20", "female"),
           "mens_odi": ("ODI", "male"), "womens_odi": ("ODI", "female"),
           "mens_test": ("Test", "male"), "womens_test": ("Test", "female")}


@blueprint.get("/status")
def status():
    counts = db.session.execute(select(
        FieldingMatch.match_format, FieldingMatch.gender, func.count(),
        func.min(FieldingMatch.start_date), func.max(FieldingMatch.end_date)
    ).group_by(FieldingMatch.match_format, FieldingMatch.gender)).all()
    return jsonify({
        "mode": "shadow_only", "live_predictions_modified": False,
        "people_including_officials": db.session.scalar(select(func.count()).select_from(FieldingPerson)),
        "imported_event_records": db.session.scalar(select(func.count()).select_from(FieldingTrial)),
        "labelled_opportunity_trials": db.session.scalar(select(func.count()).select_from(FieldingTrial).where(
            FieldingTrial.kind.in_(("catch", "run_out")), FieldingTrial.opportunity.is_not(None))),
        "complete_delivery_opportunity_records": db.session.scalar(
            select(func.count()).select_from(FieldingTrial).where(
                FieldingTrial.kind.in_(("catch", "run_out")),
                FieldingTrial.exhaustive_delivery_coverage.is_(True),
                FieldingTrial.opportunity.is_not(None))),
        "coverage": [{"format": f, "gender": g, "matches": n, "first": str(a), "last": str(b)}
                     for f, g, n, a, b in counts],
        "overall_fqr": None, "pressure_multiplier": None, "attribution": ATTRIBUTION,
    })


@blueprint.get("/players/<person_id>")
def player_quality(person_id):
    requested_format = request.args.get("format", "mens_t20")
    if requested_format not in FORMATS:
        return jsonify(error="Unsupported fielding research format"), 400
    try:
        cutoff = date.fromisoformat(request.args.get("as_of", str(date.today())))
    except ValueError:
        return jsonify(error="as_of must be YYYY-MM-DD; only earlier completed days are included"), 400
    if cutoff > date.today():
        return jsonify(error="Future evidence cutoffs are not supported"), 400
    person = db.session.get(FieldingPerson, person_id)
    if not person:
        return jsonify(error="Unknown stable player/person ID"), 404
    raw_format, gender = FORMATS[requested_format]
    rows = trial_records(db.session, cutoff, raw_format, gender)
    rating = fielding_quality(rows, person_id=person_id, as_of=cutoff,
                             match_format=raw_format, gender=gender)
    return jsonify(name=person.name, rating=rating, applied_to_live_predictions=False,
                   attribution=ATTRIBUTION)
