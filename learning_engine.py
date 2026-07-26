"""
Learning engine: records match outcomes, compares them to predictions,
and learns adjustment factors that are applied at prediction time.

Two adjustment types are learned:
  - 'venue'  → additive score offset (e.g. Wankhede consistently scores 9 runs higher than predicted)
  - 'phase'  → fractional multiplier on projected runs (e.g. T20 death-over predictions run 4% low)

Adjustments only activate once MIN_SAMPLES data points have been collected for a key.
New observations are blended with the stored value via an Exponential Moving Average (EMA).
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

EMA_ALPHA = 0.3      # weight given to the newest batch of data
MIN_SAMPLES = 5      # samples required before an adjustment is applied to live predictions


# ---------------------------------------------------------------------------
# Outcome recording
# ---------------------------------------------------------------------------

def record_match_outcome(match_id: str, venue: str, match_format: str,
                         final_score: int, wickets: int, source: str = 'auto'):
    """
    Save a confirmed match outcome and backfill any Prediction rows
    that carry this match_id. Triggers a learning cycle afterwards.

    Args:
        match_id:     Scraper match identifier (e.g. Cricbuzz ID).
        venue:        Canonical venue name (as stored in Prediction.venue).
        match_format: Match format string, e.g. 'mens_t20', 'mens_odi'.
        final_score:  Actual final innings score.
        wickets:      Actual wickets fallen at end of innings.
        source:       'auto' (scraper) or 'manual' (admin override).

    Returns:
        The MatchOutcome instance, or None on failure.
    """
    try:
        from app import db
        from models import MatchOutcome, Prediction

        # Avoid duplicates
        existing = MatchOutcome.query.filter_by(match_id=match_id).first()
        if existing:
            logger.debug(f"Outcome for match {match_id} already recorded — skipping.")
            return existing

        outcome = MatchOutcome(
            match_id=match_id,
            venue=venue,
            match_format=match_format,
            final_score=final_score,
            wickets=wickets,
            confirmed_at=datetime.utcnow(),
            source=source,
        )
        db.session.add(outcome)

        # Backfill predictions that were tagged with this match_id
        predictions = Prediction.query.filter_by(
            match_id=match_id,
            actual_final_score=None,
        ).all()

        for pred in predictions:
            pred.actual_final_score = final_score
            pred.actual_wickets = wickets

        db.session.commit()
        logger.info(
            f"Recorded outcome for match {match_id}: "
            f"{final_score}/{wickets} at {venue}. "
            f"Backfilled {len(predictions)} prediction(s)."
        )

        # Trigger a learning update now that we have new data
        run_learning_cycle()
        return outcome

    except Exception as exc:
        logger.error(f"record_match_outcome failed: {exc}")
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
        return None


# ---------------------------------------------------------------------------
# Learning cycle
# ---------------------------------------------------------------------------

def run_learning_cycle():
    """
    Read all predictions that have confirmed actual scores, compute per-venue
    and per-phase errors, and write updated ModelAdjustment rows.
    """
    try:
        from app import db
        from models import Prediction, ModelAdjustment

        cutoff = datetime.utcnow() - timedelta(days=730)
        resolved = Prediction.query.filter(
            Prediction.actual_final_score.isnot(None),
            Prediction.created_at >= cutoff,
        ).all()

        if len(resolved) < MIN_SAMPLES:
            logger.info(
                f"Learning cycle skipped — only {len(resolved)} resolved "
                f"prediction(s), need {MIN_SAMPLES}."
            )
            return

        # --- Venue adjustments (additive, in runs) ---
        venue_errors: dict[str, list[float]] = {}
        for pred in resolved:
            if not pred.venue:
                continue
            err = pred.actual_final_score - pred.predicted_final_score
            venue_errors.setdefault(pred.venue, []).append(err)

        for venue, errs in venue_errors.items():
            if len(errs) < MIN_SAMPLES:
                continue
            mean_err = sum(errs) / len(errs)
            _upsert_adjustment(db, ModelAdjustment, 'venue', venue, mean_err, len(errs))

        # --- Phase adjustments (fractional multiplier on projected runs) ---
        phase_groups: dict[str, list] = {}
        for pred in resolved:
            key = _phase_key(pred.overs_remaining, pred.match_format)
            phase_groups.setdefault(key, []).append(pred)

        for phase_key, preds in phase_groups.items():
            if len(preds) < MIN_SAMPLES:
                continue
            errors = [p.actual_final_score - p.predicted_final_score for p in preds]
            avg_predicted = sum(p.predicted_final_score for p in preds) / len(preds)
            if avg_predicted > 0:
                frac_err = (sum(errors) / len(errors)) / avg_predicted
            else:
                frac_err = 0.0
            _upsert_adjustment(db, ModelAdjustment, 'phase', phase_key, frac_err, len(preds))

        db.session.commit()
        logger.info(
            f"Learning cycle complete. "
            f"Venues processed: {len(venue_errors)}. "
            f"Phases processed: {len(phase_groups)}."
        )

    except Exception as exc:
        logger.error(f"run_learning_cycle failed: {exc}")
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass


def _upsert_adjustment(db, ModelAdjustment, adj_type: str, key: str,
                       new_value: float, sample_count: int):
    """Create or EMA-blend a ModelAdjustment row (does NOT commit — caller commits)."""
    existing = ModelAdjustment.query.filter_by(
        adjustment_type=adj_type, key=key
    ).first()

    if existing:
        existing.offset = existing.offset * (1.0 - EMA_ALPHA) + new_value * EMA_ALPHA
        existing.sample_count = sample_count
        existing.last_updated = datetime.utcnow()
    else:
        db.session.add(ModelAdjustment(
            adjustment_type=adj_type,
            key=key,
            offset=new_value,
            sample_count=sample_count,
            last_updated=datetime.utcnow(),
        ))


# ---------------------------------------------------------------------------
# Adjustment getters (called from prediction.py)
# ---------------------------------------------------------------------------

def get_venue_adjustment(venue: str) -> float:
    """
    Return the learned additive score offset for a venue (runs).
    Returns 0.0 when insufficient data exists.
    """
    try:
        from models import ModelAdjustment
        adj = ModelAdjustment.query.filter_by(
            adjustment_type='venue', key=venue
        ).first()
        if adj and adj.sample_count >= MIN_SAMPLES:
            # Cap at ±25 runs to prevent runaway corrections
            return max(-25.0, min(25.0, adj.offset))
    except Exception:
        pass
    return 0.0


def get_phase_adjustment(overs_remaining: float, match_format: str) -> float:
    """
    Return the learned fractional multiplier offset for the current match phase.
    A return value of 0.05 means predicted runs should be scaled by 1.05.
    Returns 0.0 when insufficient data exists.
    """
    try:
        from models import ModelAdjustment
        key = _phase_key(overs_remaining, match_format)
        adj = ModelAdjustment.query.filter_by(
            adjustment_type='phase', key=key
        ).first()
        if adj and adj.sample_count >= MIN_SAMPLES:
            # Cap at ±15% to prevent runaway corrections
            return max(-0.15, min(0.15, adj.offset))
    except Exception:
        pass
    return 0.0


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def get_accuracy_stats() -> dict:
    """
    Return a dict of accuracy statistics for the admin dashboard.
    """
    try:
        from models import Prediction, ModelAdjustment, MatchOutcome

        resolved = Prediction.query.filter(
            Prediction.actual_final_score.isnot(None)
        ).all()

        if not resolved:
            return {
                'total_resolved': 0,
                'avg_error': None,
                'avg_abs_error': None,
                'within_10': None,
                'by_venue': [],
                'adjustments': [],
                'outcomes': [],
            }

        errors = [p.actual_final_score - p.predicted_final_score for p in resolved]
        abs_errors = [abs(e) for e in errors]
        within_10 = sum(1 for e in abs_errors if e <= 10) / len(abs_errors) * 100

        # Per-venue breakdown
        venue_data: dict[str, list[float]] = {}
        for p in resolved:
            v = p.venue or 'Unknown'
            venue_data.setdefault(v, []).append(abs(p.actual_final_score - p.predicted_final_score))

        by_venue = sorted(
            [
                {
                    'venue': v,
                    'count': len(errs),
                    'avg_abs_error': round(sum(errs) / len(errs), 1),
                    'bias': round(
                        sum(
                            p.actual_final_score - p.predicted_final_score
                            for p in resolved if (p.venue or 'Unknown') == v
                        ) / len(errs),
                        1,
                    ),
                }
                for v, errs in venue_data.items()
            ],
            key=lambda x: -x['count'],
        )

        adjustments = [
            {
                'type': a.adjustment_type,
                'key': a.key,
                'offset': round(a.offset, 2),
                'samples': a.sample_count,
                'updated': a.last_updated.strftime('%d %b %Y') if a.last_updated else 'N/A',
            }
            for a in ModelAdjustment.query.order_by(
                ModelAdjustment.adjustment_type, ModelAdjustment.key
            ).all()
        ]

        outcomes = [
            {
                'id': o.id,
                'match_id': o.match_id,
                'venue': o.venue,
                'format': o.match_format,
                'score': o.final_score,
                'wickets': o.wickets,
                'confirmed': o.confirmed_at.strftime('%d %b %Y %H:%M') if o.confirmed_at else 'N/A',
                'source': o.source,
            }
            for o in MatchOutcome.query.order_by(
                MatchOutcome.confirmed_at.desc()
            ).limit(30).all()
        ]

        return {
            'total_resolved': len(resolved),
            'avg_error': round(sum(errors) / len(errors), 1),
            'avg_abs_error': round(sum(abs_errors) / len(abs_errors), 1),
            'within_10': round(within_10, 1),
            'by_venue': by_venue,
            'adjustments': adjustments,
            'outcomes': outcomes,
        }

    except Exception as exc:
        logger.error(f"get_accuracy_stats failed: {exc}")
        return {'error': str(exc)}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _phase_key(overs_remaining: float, match_format: str) -> str:
    """
    Map overs_remaining + format to a stable phase identifier string.
    This is the key used in ModelAdjustment.key for phase rows.
    """
    fmt = (match_format or 'mens_t20').lower()
    is_odi = 'odi' in fmt

    if is_odi:
        if overs_remaining > 30:
            phase = 'powerplay'
        elif overs_remaining > 15:
            phase = 'middle1'
        elif overs_remaining > 5:
            phase = 'middle2'
        else:
            phase = 'death'
        return f'odi_{phase}'
    else:
        if overs_remaining > 14:
            phase = 'powerplay'
        elif overs_remaining > 6:
            phase = 'consolidation'
        elif overs_remaining > 3:
            phase = 'acceleration'
        else:
            phase = 'death'
        return f't20_{phase}'
