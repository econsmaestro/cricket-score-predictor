"""Durable, auditable backtest reports; no downloads inside web requests."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from backtest_data import FORMATS, format_config

REPORT_DIR = Path(__file__).parent / "data" / "backtests"
MATCH_COUNT = 100


def load_report(match_format):
    format_config(match_format)
    path = REPORT_DIR / f"{match_format}.json"
    if not path.exists():
        raise FileNotFoundError("Report unavailable. Generate it with python backtest_reports.py")
    with path.open() as stream:
        report = json.load(stream)
    if (report["format"] != match_format or report["match_count"] != MATCH_COUNT
            or len({row["match_id"] for row in report["results"]}) != MATCH_COUNT):
        raise ValueError("Stored report did not pass match-count/format validation")
    return report


def report_status():
    formats = []
    for name, config in FORMATS.items():
        entry = dict(format=name, label=config["label"], requested_matches=MATCH_COUNT,
                     available=False, match_count=0, prediction_count=0, generated_at=None)
        try:
            report = load_report(name)
            entry.update(available=True, match_count=report["match_count"],
                         prediction_count=report["prediction_count"],
                         generated_at=report["generated_at"])
        except (FileNotFoundError, ValueError, KeyError):
            pass
        formats.append(entry)
    return {"formats": formats}


def generate_report(match_format):
    from backtest import run_backtest, compute_metrics, generate_summary

    config = format_config(match_format)
    results = run_backtest(max_matches=MATCH_COUNT, match_format=match_format)
    match_count = len({row["match_id"] for row in results})
    if match_count != MATCH_COUNT or len(results) != MATCH_COUNT * len(config["checkpoints"]):
        raise ValueError(f"Expected exactly 100 complete match replays for {match_format}")
    metrics = compute_metrics(results)
    model_files = ["prediction.py", "backtest.py", "backtest_data.py", "ipl_stats.py", "learning_engine.py"]
    fingerprint = hashlib.sha256()
    for filename in model_files:
        fingerprint.update(Path(filename).read_bytes())
    report = {
        "success": True, "format": match_format, "label": config["label"],
        "requested_matches": MATCH_COUNT, "match_count": match_count,
        "prediction_count": len(results), "checkpoints": config["checkpoints"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_fingerprint": fingerprint.hexdigest(),
        "source": "Cricsheet", "source_url": "https://cricsheet.org/downloads/" + config["archive"],
        "date_from": min(row["date"] for row in results),
        "date_to": max(row["date"] for row in results),
        "methodology": (
            "The 100 most recent eligible international matches in the downloaded archive. "
            "First innings only, replayed at completed-over checkpoints using only deliveries "
            "available at that checkpoint. Full-length six-ball-over matches, including all-out "
            "innings that reached all checkpoints; rain-adjusted and no-result matches excluded. "
            "Historical replay of the current model, not an out-of-time training holdout. "
            "Existing model priors and learned adjustments may incorporate historical information. "
            "Eligibility favours longer innings; this is not a random sample of all matches."
        ),
        "metrics": metrics, "summary": generate_summary(metrics), "results": results,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"{match_format}.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
    temporary.replace(path)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate four real 100-match backtest reports")
    parser.add_argument("--format", choices=list(FORMATS))
    args = parser.parse_args()
    # Use the same configured app/DB context as production predictions.
    from app import app
    import logging
    logging.getLogger().setLevel(logging.WARNING)
    with app.app_context():
        for name in ([args.format] if args.format else FORMATS):
            print(f"Generating {name}: 100 matches", flush=True)
            report = generate_report(name)
            print(f"{name}: {report['match_count']} matches, {report['prediction_count']} predictions, MAE {report['metrics']['overall']['mae']}", flush=True)
