"""Chronological fielding comparison using CricPredict's existing replay engine."""
from collections import defaultdict
from dataclasses import asdict
from datetime import date
import math
from statistics import mean

from sqlalchemy import func, select

from .adapter import attach_shadow
from .models import FieldingMatch


def metrics(rows):
    if not rows:
        raise ValueError("No predictions to evaluate")
    se = [r["predicted_score"] - r["actual_score"] for r in rows]
    we = [r["predicted_wickets"] - r["actual_wickets"] for r in rows]
    win_rows = [r for r in rows if r.get("win_probability") is not None
                and r.get("actual_win") is not None]
    if any(not 0 <= r["win_probability"] <= 1 or r["actual_win"] not in (0, 1)
           for r in win_rows):
        raise ValueError("Win calibration needs valid probabilities and binary outcomes")
    return {
        "matches": len({r["match_id"] for r in rows}), "predictions": len(rows),
        "score_mae": mean(abs(e) for e in se), "score_bias": mean(se),
        "wicket_mae": mean(abs(e) for e in we), "wicket_bias": mean(we),
        "exact_wicket_accuracy": mean(e == 0 for e in we),
        "interval_coverage": mean(r["low"] <= r["actual_score"] <= r["high"] for r in rows),
        "mean_interval_width": mean(r["high"] - r["low"] for r in rows),
        "win_brier": (mean((r["win_probability"]-r["actual_win"])**2 for r in win_rows)
                      if win_rows else None),
        "win_log_loss": (mean(-r["actual_win"] * math.log(max(1e-15, r["win_probability"]))
                             -(1-r["actual_win"])*math.log(max(1e-15, 1-r["win_probability"]))
                             for r in win_rows) if win_rows else None),
        "win_calibration_bins": [
            {"low": i/10, "high": (i+1)/10,
             "n": len(group), "predicted": mean(r["win_probability"] for r in group),
             "observed": mean(r["actual_win"] for r in group)}
            for i in range(10)
            if (group := [r for r in win_rows if min(int(r["win_probability"]*10), 9) == i])
        ],
    }


def activation_check(baseline, candidate, *, has_opportunity_data,
                     independent_holdout, interval_calibrated, win_validated=False):
    """No equal-metric/no-op candidate can claim to be an improvement."""
    reasons = []
    if not has_opportunity_data:
        reasons.append("Missing complete opportunity labels")
    if not independent_holdout:
        reasons.append("Independent, untouched holdout not established")
    if candidate["score_mae"] >= baseline["score_mae"]:
        reasons.append("No score MAE improvement")
    if candidate["wicket_mae"] > baseline["wicket_mae"]:
        reasons.append("Wicket MAE regression")
    if abs(candidate["score_bias"]) > abs(baseline["score_bias"]):
        reasons.append("Score bias regression")
    if abs(candidate["wicket_bias"]) > abs(baseline["wicket_bias"]):
        reasons.append("Wicket bias regression")
    if candidate["exact_wicket_accuracy"] < baseline["exact_wicket_accuracy"]:
        reasons.append("Exact wicket accuracy regression")
    if not interval_calibrated:
        reasons.append("Interval calibration not independently validated")
    if not win_validated:
        reasons.append("Win-probability changes not approved")
    return {"approved": not reasons, "reasons": reasons}


def compare(session, match_format, max_matches=100, archive_path=None):
    from backtest import build_state_at_over
    from backtest_data import parse_matches, format_config
    from prediction import predict_score

    config = format_config(match_format)
    # One extra fixture establishes an older training/history partition.
    matches = parse_matches(match_format=match_format, max_matches=max_matches + 1,
                            archive_path=archive_path)
    if len(matches) < max_matches + 1:
        raise ValueError("Insufficient fixtures for chronological evaluation")
    matches = sorted(matches, key=lambda m: (m["date"], m["match_id"]))[-max_matches:]
    raw_format, gender = config["type"], config["gender"]
    baseline_rows, candidate_rows, audits = [], [], []
    for match in matches:
        cutoff = date.fromisoformat(match["date"])
        training_count = session.scalar(select(func.count()).select_from(FieldingMatch).where(
            FieldingMatch.match_format == raw_format, FieldingMatch.gender == gender,
            FieldingMatch.end_date < cutoff, FieldingMatch.source_created < cutoff))
        history_end = session.scalar(select(func.max(FieldingMatch.end_date)).where(
            FieldingMatch.match_format == raw_format, FieldingMatch.gender == gender,
            FieldingMatch.end_date < cutoff, FieldingMatch.source_created < cutoff))
        if history_end is not None and history_end >= cutoff:
            raise ValueError("Chronological leakage detected")
        fixture = session.get(FieldingMatch, "cricsheet:" + match["match_id"])
        xi = (fixture.facts["innings"][0]["xi"] if fixture and fixture.facts["innings"] else [])
        audits.append({"match_id": match["match_id"], "prediction_date": str(cutoff),
                       "eligible_historical_matches": training_count,
                       "latest_history_end": str(history_end) if history_end else None,
                       "xi_ids_available": len(xi)})
        diagnostics = {
            "mode": "shadow", "applied": False, "historical_matches": training_count,
            "xi_players": len(xi), "fqr": None, "fpi": None,
            "reason": "Complete fielding opportunities unavailable; no replacement activated",
        }
        for checkpoint in config["checkpoints"]:
            state = build_state_at_over(match, checkpoint)
            if state.wickets_fallen >= 10:
                raise ValueError("Cannot forecast an already completed innings")
            baseline = predict_score(state)
            comparison = attach_shadow(baseline, diagnostics)
            candidate = comparison.candidate
            b, c = asdict(baseline), asdict(candidate)
            if b != c:
                raise AssertionError("Shadow mode changed a baseline prediction")
            for prediction, output in [(baseline, baseline_rows), (candidate, candidate_rows)]:
                output.append({
                    "match_id": match["match_id"], "date": match["date"],
                    "competition": fixture.competition if fixture else "unknown",
                    "checkpoint": checkpoint,
                    "predicted_score": prediction.predicted_final_score,
                    "actual_score": match["actual_final_score"],
                    "predicted_wickets": prediction.predicted_wickets,
                    "actual_wickets": match["actual_wickets"],
                    "low": prediction.score_range[0], "high": prediction.score_range[1],
                    # First-innings replay has no calibrated chase probability.
                    "win_probability": None, "actual_win": None,
                })
    bm, cm = metrics(baseline_rows), metrics(candidate_rows)
    competition_groups = defaultdict(list)
    for row in candidate_rows:
        competition_groups[row["competition"]].append(row)
    return {
        "format": match_format, "baseline": bm, "fielding_shadow": cm,
        "activation": activation_check(bm, cm, has_opportunity_data=False,
                                       independent_holdout=False, interval_calibrated=False),
        "delta_score_mae": cm["score_mae"] - bm["score_mae"],
        "delta_wicket_mae": cm["wicket_mae"] - bm["wicket_mae"],
        "competition_breakdown": {k: metrics(v) for k, v in competition_groups.items()},
        "chronological_audit": audits,
        "limitations": [
            "No independently validated enhanced fielding predictor is available",
            "Shadow equality is compatibility evidence, not prediction improvement",
            "New history excludes the test fixture, same-day fixtures and later completions",
            "Source-created dates are checked, but historical availability of corrected revisions is unknown",
            "Existing engine priors may reflect later data; this is not clean out-of-time validation of the whole engine",
            "First-innings ODI/T20 replay cannot establish Test or chase win-probability improvements",
            "Latest fixtures have been used in earlier calibration; independent untouched holdout still required",
        ],
        "rows": candidate_rows,
    }
