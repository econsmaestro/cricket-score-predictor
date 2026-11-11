"""Real-engine, exact-committed-cohort fielding ablation; never writes reports in data/.

Run: python -m research.fielding_strength_replay
All fielding modifiers are scaled together, unlike the imported run-only
approximation. This is a current-model replay, NOT an out-of-time holdout.
"""
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

import prediction
from backtest import build_state_at_over
from backtest_data import CACHE_DIR, FORMATS, _parse_innings

STRENGTHS = (0.0, 0.25, 0.5, 1.0)
OUT = Path("generated-artifacts/fielding-strength")
LIMITATIONS = (
    "Replay of the current model, not an out-of-time holdout. Strength is selected "
    "on earlier fixtures and evaluated on later fixtures, but underlying player, "
    "venue and model priors are not timestamp-frozen. Earlier ODI revisions were "
    "evaluated on this same cohort. First innings only; committed checkpoint "
    "eligibility and selection biases are preserved. No improvement is claimed "
    "as an isolated causal fielding effect. All three effects change together."
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(rows):
    if not rows:
        raise ValueError("Cannot evaluate an empty split")
    n = len(rows)
    runs = [r["predicted_runs"] - r["actual_runs"] for r in rows]
    wickets = [r["predicted_wickets"] - r["actual_wickets"] for r in rows]
    return {
        "n": n, "matches": len({r["match_id"] for r in rows}),
        "run_mae": sum(map(abs, runs)) / n, "wicket_mae": sum(map(abs, wickets)) / n,
        "run_bias": sum(runs) / n, "wicket_bias": sum(wickets) / n,
    }


def chronological_split(matches):
    """Closest to half by match count, without splitting a fixture date."""
    ordered = sorted(matches, key=lambda m: (m["date"], m["match_id"]))
    boundaries = [i for i in range(1, len(ordered))
                  if ordered[i - 1]["date"] < ordered[i]["date"]]
    if not boundaries:
        raise ValueError("A strict chronological split needs at least two fixture dates")
    boundary = min(boundaries, key=lambda i: (abs(i - len(ordered) / 2), i))
    return {m["match_id"] for m in ordered[:boundary]}, {
        m["match_id"] for m in ordered[boundary:]
    }


def load_cohort(fmt):
    """Use exact IDs/checkpoints from committed reports, not latest-match selection."""
    report_path = Path("data/backtests") / f"{fmt}.json"
    report = json.loads(report_path.read_text())
    archive = CACHE_DIR / FORMATS[fmt]["archive"]
    archive_hash = digest(archive)
    if archive_hash != report["source_archive_sha256"]:
        raise ValueError(f"{fmt}: cached archive differs from committed provenance")
    by_match = {}
    for row in report["results"]:
        key = (row["match_id"], row["checkpoint"])
        if any(r["checkpoint"] == row["checkpoint"] for r in by_match.get(key[0], [])):
            raise ValueError(f"Duplicate checkpoint: {key}")
        by_match.setdefault(row["match_id"], []).append(row)
    matches, fixture_hashes = [], {}
    with zipfile.ZipFile(archive) as zf:
        for match_id, rows in sorted(by_match.items()):
            raw = zf.read(f"{match_id}.json")
            source = json.loads(raw)
            info, innings = source["info"], source["innings"][0]
            if (info["gender"] != FORMATS[fmt]["gender"]
                    or info["match_type"] != FORMATS[fmt]["type"]):
                raise ValueError(f"{fmt}: source classification mismatch")
            match = {
                "match_id": match_id, "date": str(info["dates"][0]),
                "venue": info["venue"], "batting_team": innings["team"],
                "fielding_team": next(t for t in info["teams"] if t != innings["team"]),
                "players": info.get("players", {}), "overs": _parse_innings(innings),
                "match_format": fmt, "committed_rows": rows,
            }
            if any(row["date"] != match["date"] for row in rows):
                raise ValueError(f"{fmt}: fixture date mismatch")
            actual_runs = sum(d["runs_total"] for o in match["overs"] for d in o["deliveries"])
            from backtest_data import counts_as_team_wicket
            actual_wickets = sum(counts_as_team_wicket(w) for o in match["overs"]
                                 for d in o["deliveries"] for w in d["wickets"])
            if any(row["actual"] != actual_runs or row["actual_wickets"] != actual_wickets
                   for row in rows):
                raise ValueError(f"{fmt}: committed evaluation target mismatch")
            matches.append(match)
            fixture_hashes[match_id] = hashlib.sha256(raw).hexdigest()
    if len(matches) != report["match_count"]:
        raise ValueError(f"{fmt}: committed match count mismatch")
    return matches, {
        "report_sha256": digest(report_path), "archive_sha256": archive_hash,
        "fixture_sha256": fixture_hashes, "committed_predictions": report["prediction_count"],
    }


def replay_cohort(fmt, matches):
    train_ids, test_ids = chronological_split(matches)
    rows = []
    original_strength = prediction.FIELDING_EFFECT_STRENGTH
    try:
        for match in matches:
            for source_row in match["committed_rows"]:
                cp = source_row["checkpoint"]
                state = build_state_at_over(match, cp)
                if (state.current_score != source_row["score_at_cp"]
                        or state.wickets_fallen != source_row["wickets_at_cp"]):
                    raise ValueError(f"{fmt}/{match['match_id']}/{cp}: checkpoint mismatch")
                state_snapshot = asdict(state)
                state_hash = hashlib.sha256(
                    json.dumps(state_snapshot, sort_keys=True).encode()
                ).hexdigest()
                for strength in STRENGTHS:
                    prediction.FIELDING_EFFECT_STRENGTH = strength
                    # Independent state per arm, even if a future engine mutates it.
                    result = prediction.predict_score(build_state_at_over(match, cp))
                    rows.append({
                        "format": fmt, "match_id": match["match_id"], "date": match["date"],
                        "checkpoint": cp, "strength": strength,
                        "split": "fit" if match["match_id"] in train_ids else "test",
                        "batting_team": match["batting_team"],
                        "raw_fielding_team": match["fielding_team"],
                        "fielding_rating_key": state.fielding_team,
                        "state_sha256": state_hash,
                        "predicted_runs": result.predicted_final_score,
                        "predicted_wickets": result.predicted_wickets,
                        "actual_runs": source_row["actual"],
                        "actual_wickets": source_row["actual_wickets"],
                    })
    finally:
        prediction.FIELDING_EFFECT_STRENGTH = original_strength
    # Run MAE first; wicket MAE breaks ties; favour the unchanged baseline on exact ties.
    chosen = min(STRENGTHS, key=lambda k: (
        metrics([r for r in rows if r["strength"] == k and r["split"] == "fit"])["run_mae"],
        metrics([r for r in rows if r["strength"] == k and r["split"] == "fit"])["wicket_mae"],
        -k,
    ))
    summaries = [
        {"format": fmt, "strength": strength, "split": split,
         **metrics([r for r in rows if r["strength"] == strength
                    and (split == "all" or r["split"] == split)])}
        for split in ("all", "fit", "test") for strength in STRENGTHS
    ]
    return rows, summaries, {
        "format": fmt, "selected_strength": chosen,
        "fit_match_ids": sorted(train_ids), "test_match_ids": sorted(test_ids),
        "fit_last_date": max(m["date"] for m in matches if m["match_id"] in train_ids),
        "test_first_date": min(m["date"] for m in matches if m["match_id"] in test_ids),
    }


def write_csv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows):
    lines = [
        "| Format | Split | k | Matches / rows | Run MAE | Wicket MAE | Run bias | Wicket bias |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['format']} | {r['split']} | {r['strength']:g} | "
            f"{r['matches']} / {r['n']} | {r['run_mae']:.2f} | {r['wicket_mae']:.2f} | "
            f"{r['run_bias']:+.2f} | {r['wicket_bias']:+.2f} |"
        )
    return "\n".join(lines)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows, summaries, splits, provenance = [], [], [], {}
    for fmt in FORMATS:
        matches, source = load_cohort(fmt)
        arm_rows, summary, split = replay_cohort(fmt, matches)
        if len(arm_rows) != source["committed_predictions"] * len(STRENGTHS):
            raise ValueError(f"{fmt}: replay row count mismatch")
        rows.extend(arm_rows)
        summaries.extend(summary)
        splits.append(split)
        provenance[fmt] = source
        print(f"{fmt}: {len(matches)} fixtures, {len(arm_rows)} paired-arm rows", flush=True)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_files": {name: digest(Path(name)) for name in (
            "prediction.py", "backtest.py", "backtest_data.py",
            "research/fielding_strength_replay.py", "ipl_stats.py", "player_data.py",
        )},
        "strengths": STRENGTHS, "default_strength": prediction.FIELDING_EFFECT_STRENGTH,
        "selection_rule": "Earlier-fixture run MAE, then wicket MAE, then larger k on exact ties",
        "split_rule": "Nearest half by fixture count at a strict date boundary",
        "limitations": LIMITATIONS, "cohorts": provenance, "splits": splits,
    }
    write_csv(OUT / "predictions.csv", rows)
    write_csv(OUT / "metrics.csv", summaries)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (OUT / "metrics.json").write_text(json.dumps(summaries, indent=2) + "\n")
    report = "# Real-model fielding-strength replay\n\n" + LIMITATIONS + "\n\n"
    report += "Signed bias = predicted minus actual. No default or rating values changed.\n\n"
    report += markdown_table([r for r in summaries if r["split"] == "all"])
    report += "\n\n## Chronological later-fixture results (all candidate strengths)\n\n"
    report += markdown_table([r for r in summaries if r["split"] == "test"])
    report += "\n\n## Strength selection using earlier fixtures only\n\n"
    for split in splits:
        report += (
            f"- {split['format']}: selected k={split['selected_strength']:g}; "
            f"{len(split['fit_match_ids'])} fit fixtures through {split['fit_last_date']}; "
            f"{len(split['test_match_ids'])} test fixtures from {split['test_first_date']}.\n"
        )
    (OUT / "report.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
