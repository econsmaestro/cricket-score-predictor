"""Regenerate exact committed cohorts at unchanged strength; never access a DB.

Run from the repository root: python -m research.refresh_first_innings_reports
Archives, targets, checkpoints and methodology are preserved. Only predictions,
derived metrics, provenance timestamps and the explicit mapping note change.
"""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import prediction
from backtest import build_state_at_over, compute_metrics, generate_summary
from backtest_data import FORMATS
from research.fielding_strength_replay import load_cohort

NOTE = "Women's fixtures now use the women's fielding rating keys."
CSV_FIELDS = [
    "match_id", "date", "venue", "batting_team", "fielding_team", "match_format",
    "checkpoint", "score_at_cp", "wickets_at_cp", "predicted", "pred_low",
    "pred_high", "actual", "error", "abs_error", "predicted_wickets",
    "actual_wickets", "wicket_error", "wicket_abs_error", "in_range",
    "range_width", "innings", "target", "chase_won",
]


def refreshed_report(fmt, original):
    if prediction.FIELDING_EFFECT_STRENGTH != 1.0:
        raise ValueError("Report refresh requires the unchanged default strength 1.0")
    matches, _ = load_cohort(fmt)
    states = {m["match_id"]: m for m in matches}
    rows = []
    for source in original["results"]:
        state = build_state_at_over(states[source["match_id"]], source["checkpoint"])
        if (state.current_score, state.wickets_fallen) != (
                source["score_at_cp"], source["wickets_at_cp"]):
            raise ValueError("Checkpoint state changed")
        result = prediction.predict_score(state)
        row = dict(source)
        low, high = result.score_range
        error = result.predicted_final_score - source["actual"]
        wicket_error = result.predicted_wickets - source["actual_wickets"]
        row.update(
            predicted=result.predicted_final_score, pred_low=low, pred_high=high,
            error=error, abs_error=abs(error), predicted_wickets=result.predicted_wickets,
            wicket_error=wicket_error, wicket_abs_error=abs(wicket_error),
            in_range=low <= source["actual"] <= high, range_width=high - low,
        )
        rows.append(row)
    if len(states) != 100 or len(rows) != original["prediction_count"]:
        raise ValueError("Cohort or checkpoint count changed")
    report = dict(original)
    fingerprint = hashlib.sha256()
    for name in ("prediction.py", "backtest.py", "backtest_data.py",
                 "ipl_stats.py", "learning_engine.py"):
        fingerprint.update(Path(name).read_bytes())
    report.update(
        results=rows, metrics=compute_metrics(rows),
        generated_at=datetime.now(timezone.utc).isoformat(),
        model_fingerprint=fingerprint.hexdigest(),
    )
    report["summary"] = generate_summary(report["metrics"])
    if NOTE not in original["methodology"]:
        report["methodology"] = original["methodology"] + " " + NOTE
    return report


def main():
    # Complete every replay before changing any committed report.
    pending = []
    for fmt in FORMATS:
        path = Path("data/backtests") / f"{fmt}.json"
        original = json.loads(path.read_text())
        matches = list(Path("attached_assets").glob(f"backtest_{fmt}_100_matches_*.csv"))
        if len(matches) != 1:
            raise ValueError(f"{fmt}: expected exactly one matching committed CSV")
        report = refreshed_report(fmt, original)
        pending.append((path, matches[0], report))
        print(fmt, "BEFORE", original["metrics"]["overall"],
              "AFTER", report["metrics"]["overall"], flush=True)
    for path, csv_path, report in pending:
        path.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":"),
                                   allow_nan=False))
        with csv_path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, extrasaction="ignore",
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerows(report["results"])


if __name__ == "__main__":
    main()
