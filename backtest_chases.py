"""Second-innings replay, isolated from production and legacy first-innings sampling."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from datetime import datetime, timezone

from backtest_data import FORMATS, _parse_innings, counts_as_team_wicket, download_data
from backtest import build_state_at_over, compute_metrics, generate_summary
from backtest_reports import REPORT_DIR


def totals(overs):
    deliveries = [d for o in overs for d in o["deliveries"]]
    return (
        sum(d["runs_total"] for d in deliveries),
        sum(counts_as_team_wicket(w) for d in deliveries for w in d["wickets"]),
        sum(not ("wides" in d["extras"] or "noballs" in d["extras"]) for d in deliveries),
    )


def chase_matches(fmt, archive, limit=100):
    """Keep early chases/all-outs; exclude reduced, incomplete and super-over games."""
    config = FORMATS[fmt]
    selected = []
    with zipfile.ZipFile(archive) as zf:
        for name in sorted(zf.namelist()):
            if not name.endswith(".json"):
                continue
            data = json.loads(zf.read(name))
            info, innings = data.get("info", {}), data.get("innings", [])
            outcome = info.get("outcome", {})
            if (info.get("gender") != config["gender"] or info.get("match_type") != config["type"]
                    or info.get("overs") != config["overs"] or info.get("balls_per_over", 6) != 6
                    or outcome.get("method") or outcome.get("result") in {"no result", "abandoned"}
                    or len(innings) != 2 or any(i.get("super_over") for i in innings)):
                continue
            first, second = map(_parse_innings, innings)
            first_runs, first_wickets, first_balls = totals(first)
            runs, wickets, balls = totals(second)
            target = innings[1].get("target", {})
            if (target.get("overs", config["overs"]) != config["overs"]
                    or target.get("runs") != first_runs + 1
                    or not first or not second
                    or (first_balls < config["overs"] * 6 and first_wickets != 10)
                    or (runs < target["runs"] and wickets != 10 and balls < config["overs"] * 6)):
                continue
            team = innings[1]["team"]
            selected.append({
                "match_id": name.removesuffix(".json"), "date": str(info["dates"][0]),
                "venue": info.get("venue", ""), "players": info.get("players", {}),
                "batting_team": team, "fielding_team": innings[0]["team"],
                "match_format": fmt, "overs": second, "innings": 2,
                "target": target["runs"], "actual_final_score": runs,
                "actual_wickets": wickets, "legal_balls": balls,
                "chase_won": runs >= target["runs"],
                "source_sha256": hashlib.sha256(zf.read(name)).hexdigest(),
                # Non-striker is observed at each delivery, not inferred from
                # future batting order. The legacy runner ignores this field.
                "raw_overs": innings[1]["overs"],
            })
            selected.sort(key=lambda m: (m["date"], m["match_id"]), reverse=True)
            del selected[limit:]
    if len(selected) != limit:
        raise ValueError(f"{fmt}: only {len(selected)} eligible chases; {limit} required")
    return selected


def chase_state(match, checkpoint):
    """Set chase context and recover both active batters from observed deliveries."""
    from prediction import Batsman
    state = build_state_at_over(match, checkpoint)
    state.innings, state.target = 2, match["target"]
    observed, active, dismissed = {}, [], set()
    for over in match["raw_overs"]:
        if over["over"] >= checkpoint:
            break
        for d in over["deliveries"]:
            active = [d["batter"], d["non_striker"]]
            for player in active:
                observed.setdefault(player, [0, 0])
            observed[d["batter"]][0] += d["runs"]["batter"]
            observed[d["batter"]][1] += int("wides" not in d.get("extras", {}))
            for w in d.get("wickets", []):
                dismissed.add(w["player_out"])
                active = [p for p in active if p != w["player_out"]]
    state.batsmen = [Batsman(name=p, runs=observed[p][0], balls_faced=observed[p][1])
                     for p in active if p not in dismissed]
    # A squad list is not an established batting order.
    state.batsmen_to_come = []
    return state


def generate_chase_report(fmt):
    from prediction import predict_score
    archive = download_data(match_format=fmt)
    matches = chase_matches(fmt, archive)
    checkpoints = [0] + FORMATS[fmt]["checkpoints"]
    rows = []
    skipped = 0
    for match in matches:
        for cp in checkpoints:
            # Never create perfect predictions after the innings has ended.
            if cp * 6 >= match["legal_balls"]:
                skipped += 1
                continue
            state = chase_state(match, cp)
            if state.wickets_fallen >= 10 or state.current_score >= state.target:
                skipped += 1
                continue
            pred = predict_score(state)
            low, high = pred.score_range
            error = pred.predicted_final_score - match["actual_final_score"]
            wicket_error = pred.predicted_wickets - match["actual_wickets"]
            rows.append({
                **{k: match[k] for k in ("match_id", "date", "venue", "batting_team",
                   "fielding_team", "match_format", "target", "chase_won", "source_sha256")},
                "innings": 2, "checkpoint": cp, "score_at_cp": state.current_score,
                "wickets_at_cp": state.wickets_fallen, "predicted": pred.predicted_final_score,
                "pred_low": low, "pred_high": high, "actual": match["actual_final_score"],
                "error": error, "abs_error": abs(error),
                "predicted_wickets": pred.predicted_wickets, "actual_wickets": match["actual_wickets"],
                "wicket_error": wicket_error, "wicket_abs_error": abs(wicket_error),
                "in_range": low <= match["actual_final_score"] <= high, "range_width": high - low,
            })
    assert len({r["match_id"] for r in rows}) == 100
    metrics = compute_metrics(rows)
    with open(archive, "rb") as stream:
        archive_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    report = {
        "schema_version": 2, "success": True, "format": fmt, "innings": 2,
        "label": FORMATS[fmt]["label"] + " · 2nd innings",
        "requested_matches": 100, "match_count": 100, "prediction_count": len(rows),
        "checkpoints": checkpoints, "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Cricsheet", "source_url": "https://cricsheet.org/downloads/" + FORMATS[fmt]["archive"],
        "source_archive_sha256": archive_hash,
        "model_fingerprint": hashlib.sha256(Path("prediction.py").read_bytes()).hexdigest(),
        "date_from": min(m["date"] for m in matches), "date_to": max(m["date"] for m in matches),
        "skipped_terminal_checkpoints": skipped,
        "methodology": (
            "100 most recent eligible completed second innings in the downloaded international archive. "
            "Separate cohort from first innings. Full-length six-ball-over fixtures only; DLS/reduced, "
            "incomplete, no-result and super-over matches excluded. Early all-outs and successful short "
            "chases retained through an innings-start checkpoint; later checkpoints only while active. "
            "Actual targets are known from the completed first innings. Final runs and wickets are "
            "measured at chase termination, not a hypothetical full innings. Winning boundary overshoots "
            "are retained. The unchanged model caps its run forecast at the target but does not fully "
            "model wickets until chase termination; interpret wicket errors accordingly. "
            "No future batting order supplied; at innings start openers are unknown. Current player/"
            "venue priors and learned adjustments may contain historical information. This is a "
            "retrospective replay, not leakage-free holdout validation or a test of live scraping."
        ),
        "metrics": metrics, "summary": generate_summary(metrics), "results": rows,
        "metrics_by_chase_outcome": {
            "won": compute_metrics([r for r in rows if r["chase_won"]]),
            "not_won": compute_metrics([r for r in rows if not r["chase_won"]]),
        },
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "match_manifest": [
            {k: m[k] for k in ("match_id", "date", "source_sha256", "legal_balls")}
            for m in matches
        ],
    }
    path = REPORT_DIR / f"{fmt}_innings2.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, allow_nan=False))
    temporary.replace(path)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=list(FORMATS))
    args = parser.parse_args()
    from app import app
    import logging
    logging.getLogger().setLevel(logging.WARNING)
    with app.app_context():
        for fmt in ([args.format] if args.format else FORMATS):
            report = generate_chase_report(fmt)
            print(fmt, report["prediction_count"], report["metrics"]["overall"], flush=True)
