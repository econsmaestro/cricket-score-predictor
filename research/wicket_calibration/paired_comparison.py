"""Paired recent-fixture comparison; never installs a production replacement."""
import argparse
import copy
import csv
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path

import numpy as np

from .data import FORMATS, load_archive, snapshot
from .evaluation import ROOT, breakdown, metrics, protected_hashes, uncertainty
from .legacy import bind_priors, make_module, predict as controlled_predict
from .priors import PriorStore
from .simulator import predict as joint_predict, seed_for

NAMES = {
    "production_inputs": "Current equations + current inputs",
    "baseline": "Current equations + historical controls",
    "joint_full": "Experimental joint model + historical controls",
}


def current_input_prediction(module, state):
    """Same reconstructed checkpoint, with normal name-based production providers."""
    from backtest import _resolve_venue
    names = state["names"]
    ms = module.MatchState(
        current_score=state["score"], wickets_fallen=state["wickets"],
        overs_completed=state["balls"] / 6, venue=_resolve_venue(state["venue"]),
        batsmen=[module.Batsman(name=names[p], runs=state["faced"].get(p, [0, 0])[0],
                               balls_faced=state["faced"].get(p, [0, 0])[1])
                 for p in state["active"] if p],
        bowlers=[module.Bowler(name=names[p], overs_bowled=s[0] / 6,
                               runs_conceded=s[1], wickets=s[2],
                               overs_remaining=max(0, state["max_balls"] / 30 - s[0] / 6))
                 for p, s in state["bowled"].items()],
        batsmen_to_come=[names[p] for p in state["players"] if p not in state["seen"]],
        match_format=state["format"], innings=1, target=0, fielding_team=state["fielding_team"],
    )
    result = module.predict_score(ms)
    return {"score": result.predicted_final_score, "wickets": result.predicted_wickets,
            "low": result.score_range[0], "high": result.score_range[1]}


def paired_rows(rows):
    """Require identical targets, states and observation keys in every arm."""
    groups = {}
    for r in rows:
        key = r["match_id"], r["checkpoint"]
        groups.setdefault(key, {})[r["variant"]] = r
    for variants in groups.values():
        assert set(variants) == set(NAMES)
        for field in ("actual_score", "actual_wickets", "score_at_cp", "wickets_at_cp", "state_hash"):
            assert len({v[field] for v in variants.values()}) == 1, field
    return len(groups)


def assessment(baseline, experimental, intervals):
    return {
        "run_mae_reduction_pct": 100 * (baseline["score_mae"] - experimental["score_mae"]) / baseline["score_mae"],
        "wicket_mae_reduction_pct": 100 * (baseline["wicket_mae"] - experimental["wicket_mae"]) / baseline["wicket_mae"],
        "both_mae_lower": experimental["score_mae"] < baseline["score_mae"] and
                          experimental["wicket_mae"] < baseline["wicket_mae"],
        "both_paired_95ci_below_zero": all(intervals[k]["ci_high"] < 0 for k in ("score", "wickets")),
    }


def run(output, paths=512):
    output.mkdir(parents=True, exist_ok=True)
    before = protected_hashes()
    research_hashes = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in Path(__file__).parent.glob("*.py")
    }
    previous_path = ROOT / "generated-artifacts/wicket-phase2/results.json"
    previous = json.loads(previous_path.read_text())
    now = datetime.now(timezone.utc).isoformat()
    alphas = {fmt: previous[fmt]["tuning"]["joint_full"]["selected_alpha"] for fmt in FORMATS}
    specification = {
        "written_before_evaluation": now, "paths": paths,
        "selection": "Latest 100 eligible first innings per format in the refreshed archives; early all-outs retained.",
        "primary": "Configured active checkpoints only. Innings-start forecasts reported separately.",
        "shared_input_policy": "Identical reconstructed state/targets. Baseline and joint use identical pre-cohort priors.",
        "current_inputs_arm": "Context only: current input providers may contain future information relative to fixtures.",
        "prior_policy": "Up to 750 recent eligible fixtures; exclude all whose completion+2d is after first test date.",
        "alpha_policy": "Freeze previously selected Phase2 alpha; no retuning on this sample.",
        "alpha": alphas,
        "uncertainty": "2000 paired fixture-cluster bootstrap draws; candidate minus baseline MAE.",
        "decision": "Report both MAEs and checkpoint regressions; no automatic promotion.",
        "validation_status": "Historical replay, not proven source-availability or untouched model-development holdout.",
        "second_innings": "Not evaluated: current experimental simulator is first-innings only.",
        "production_hashes": before, "research_hashes": research_hashes,
        "previous_configuration_sha256": hashlib.sha256(previous_path.read_bytes()).hexdigest(),
    }
    (output / "specification.json").write_text(json.dumps(specification, indent=2))
    current, baseline = make_module("paired_current"), make_module("paired_baseline")
    all_rows, results = [], {}
    for fmt in FORMATS:
        matches, exclusions, source_hash = load_archive(ROOT, fmt, now, limit=750)
        test = matches[-100:]
        assert len(test) == 100
        cutoff = min(m["date"] for m in test)
        train = [m for m in matches[:-100] if m["completed_before"] <= cutoff]
        priors = PriorStore(train, cutoff, output / "priors", source_hash)
        assert not ({m["id"] for m in train} & {m["id"] for m in test})
        bind_priors(baseline, priors)
        rows, skips = [], {}
        for index, match in enumerate(test):
            for cp in FORMATS[fmt][4]:
                state = snapshot(match, cp)
                if state is None:
                    skips[str(cp)] = skips.get(str(cp), 0) + 1
                    continue
                priors.assert_as_of(state["as_of"])
                canonical = json.dumps(
                    {k: sorted(v) if isinstance(v, set) else v for k, v in state.items()},
                    sort_keys=True, separators=(",", ":"),
                )
                state_hash = hashlib.sha256(canonical.encode()).hexdigest()
                untouched = copy.deepcopy(state)
                preds = {
                    "production_inputs": current_input_prediction(current, state),
                    "baseline": controlled_predict(baseline, state, priors),
                    "joint_full": joint_predict(state, priors, "joint_full", alphas[fmt],
                                               seed_for(fmt, match["id"], cp), paths),
                }
                assert state == untouched, "Predictor mutated shared checkpoint"
                for name, pred in preds.items():
                    rows.append({
                        "format": fmt, "match_id": match["id"], "date": match["date"],
                        "checkpoint": cp, "variant": name,
                        "phase": int(np.searchsorted([10, 30, 40] if fmt.endswith("odi") else [6, 14, 17], cp, side="right")),
                        "actual_wicket_bucket": "0–3" if match["actual_wickets"] <= 3 else
                            "4–6" if match["actual_wickets"] <= 6 else "7–10",
                        "score_at_cp": state["score"], "wickets_at_cp": state["wickets"],
                        "predicted_score": pred["score"], "predicted_wickets": pred["wickets"],
                        "actual_score": match["actual_score"], "actual_wickets": match["actual_wickets"],
                        "low": pred["low"], "high": pred["high"],
                        "state_hash": state_hash, "prior_cutoff": cutoff, "prior_sha256": priors.digest,
                    })
            if (index + 1) % 20 == 0:
                print(fmt, index + 1, "/100 paired fixtures", flush=True)
        observations = paired_rows(rows)
        primary = [r for r in rows if r["checkpoint"] != 0]
        ci = uncertainty(primary)
        arm_metrics = {name: breakdown([r for r in rows if r["variant"] == name]) for name in NAMES}
        regressions = []
        for cp in FORMATS[fmt][4]:
            if not cp:
                continue
            b = arm_metrics["baseline"]["checkpoint"].get(str(cp))
            e = arm_metrics["joint_full"]["checkpoint"].get(str(cp))
            if b and e:
                for metric in ("score_mae", "wicket_mae"):
                    if e[metric] > b[metric]:
                        regressions.append({"checkpoint": cp, "metric": metric,
                                            "baseline": b[metric], "experimental": e[metric]})
        results[fmt] = {
            "matches": 100, "paired_observations_including_start": observations,
            "primary_observations_per_arm": len(primary) // len(NAMES), "metrics": arm_metrics,
            "paired_uncertainty": ci, "checkpoint_regressions": regressions,
            "assessment": assessment(arm_metrics["baseline"]["configured_only"],
                                     arm_metrics["joint_full"]["configured_only"], ci["joint_full"]),
            "date_from": test[0]["date"], "date_to": test[-1]["date"],
            "training_fixtures": len(train), "training_max_completed_before": priors.maximum_source_time,
            "prior_cutoff": cutoff, "source_sha256": source_hash,
            "archive_exclusions": exclusions, "terminal_checkpoints_skipped": skips,
            "manifest": {key: [{k: m[k] for k in ("id", "date", "completed_before", "sha256")}
                               for m in ms] for key, ms in (("training", train), ("test", test))},
        }
        all_rows.extend(rows)
        (output / "results.json").write_text(json.dumps(results, indent=2))
        print(fmt, results[fmt]["assessment"], flush=True)
    with (output / "predictions.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    with (output / "comparison.csv").open("w", newline="") as f:
        flattened = [{"format": fmt, "variant": name, **data["metrics"][name]["configured_only"]}
                     for fmt, data in results.items() for name in NAMES]
        writer = csv.DictWriter(f, fieldnames=list(flattened[0]))
        writer.writeheader()
        writer.writerows(flattened)
    assert before == protected_hashes(), "Production or fielding sources changed"
    (output / "verification.json").write_text(json.dumps({
        "production_and_fielding_unchanged": True, "matched_states_targets_and_keys": True,
        "paired_fixture_count": 400, "source_availability_certified": False,
        "second_innings_validated": False,
    }, indent=2))
    write_report(output, results)


def write_report(output, results):
    def table(headers, rows):
        return "<div class='scroll'><table><thead><tr>" + "".join(
            "<th>" + html.escape(str(h)) + "</th>" for h in headers
        ) + "</tr></thead><tbody>" + "".join(
            "<tr>" + "".join("<td>" + html.escape(str(v)) + "</td>" for v in row) + "</tr>"
            for row in rows
        ) + "</tbody></table></div>"

    sections = []
    for fmt, r in results.items():
        rows = []
        for variant, label in NAMES.items():
            m = r["metrics"][variant]["configured_only"]
            rows.append([label, m["n"], f'{m["score_mae"]:.2f}', f'{m["score_bias"]:+.2f}',
                         f'{m["score_rmse"]:.2f}', f'{m["wicket_mae"]:.2f}',
                         f'{m["wicket_bias"]:+.2f}', f'{m["exact_pct"]:.1f}%',
                         f'{m["coverage_pct"]:.1f}%', f'{m["range_width"]:.1f}'])
        section = f"<section><h2>{html.escape(fmt)}</h2><p>100 paired fixtures, {r['date_from']} to {r['date_to']}. " \
                  f"{r['training_fixtures']} training fixtures, frozen before {r['prior_cutoff']}.</p>"
        section += table(["Model/input policy", "Forecasts", "Run MAE", "Run bias", "Run RMSE",
                          "Wicket MAE", "Wicket bias", "Exact wickets", "Interval coverage", "Width (runs)"], rows)
        delta = r["paired_uncertainty"]["joint_full"]
        section += "<h3>Paired MAE differences: experimental minus controlled baseline</h3>"
        section += table(["Outcome", "Difference", "95% fixture-bootstrap interval"], [
            [k, f'{delta[k]["delta_mae"]:+.2f}',
             f'[{delta[k]["ci_low"]:+.2f}, {delta[k]["ci_high"]:+.2f}]'] for k in ("score", "wickets")])
        cp_rows = []
        for cp, b in r["metrics"]["baseline"]["checkpoint"].items():
            e = r["metrics"]["joint_full"]["checkpoint"][cp]
            cp_rows.append([cp, b["n"], f'{b["score_mae"]:.2f}', f'{e["score_mae"]:.2f}',
                            f'{b["wicket_mae"]:.2f}', f'{e["wicket_mae"]:.2f}'])
        section += "<h3>Checkpoint comparison (innings start shown separately as over 0)</h3>"
        section += table(["Over", "Forecasts/arm", "Baseline run MAE", "Experimental run MAE",
                          "Baseline wicket MAE", "Experimental wicket MAE"], cp_rows)
        section += "<h3>Regressions at configured checkpoints</h3>"
        section += table(["Over", "Metric", "Baseline", "Experimental"], [
            [x["checkpoint"], x["metric"], f'{x["baseline"]:.2f}', f'{x["experimental"]:.2f}']
            for x in r["checkpoint_regressions"]]) if r["checkpoint_regressions"] else "<p>None observed.</p>"
        sections.append(section + "</section>")
    page = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>CricPredict paired model comparison</title>
<style>body{font:16px/1.6 system-ui;background:#eff6f5;color:#193449;margin:0;padding:24px}
main{max-width:1240px;margin:auto}h1,h2{color:#164e52}section{background:white;border:1px solid #cbdedb;
border-radius:12px;padding:24px;margin:24px 0}.notice{background:#fff3cf;padding:20px;border-left:5px solid #b48725}
.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px;border-bottom:1px solid #d6e3e1;text-align:right;white-space:nowrap}
th{background:#e3efed}th:first-child,td:first-child{text-align:left}h3{margin-top:28px}
</style><main><h1>CricPredict: directly paired model comparison</h1>
<p>400 first innings; 100 recent eligible fixtures per format. Every model uses exactly the same
checkpoint states and targets. Primary metrics exclude over 0 and include only active configured checkpoints.</p>
<div class="notice"><strong>Not a deployment approval.</strong> The controlled baseline and joint model share
historical priors frozen before the test cohort, neutral unsupported fielding/style labels and zero undated DB offsets.
The current-input arm is context, not a pure algorithm comparison; its unversioned providers may contain future knowledge.
These are current archived historical reconstructions, not proven historical publication versions.
Previous parameter-development/tuning provenance is not independently certified. A chronological split
does not turn this into untouched validation. 95% intervals quantify fixture sampling, not those risks.</div>
<p>Parameters: previously selected shrinkage concentration 1000, fixed seeds, 512 simulation paths per prediction.
No tuning on this cohort. Primary weighting is by active checkpoint; innings-start results are supplementary.
Samples can differ from the webpage's first-innings cohort because early all-outs are retained and
stable player IDs, timed penalties and roster validity are required. The experimental score interval is central
80%; baseline interval has no guaranteed coverage label, so coverage is descriptive, not a like-for-like calibration target.</p>
<p><strong>Second innings excluded:</strong> the existing experimental simulator does not model target-based stopping.
Do not promote this as a validated chase-model replacement. Production and Fielding Intelligence remain unchanged.</p>"""
    (output / "report.html").write_text(page + "".join(sections) + "</main></html>")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "generated-artifacts/paired-current")
    parser.add_argument("--paths", type=int, default=512)
    args = parser.parse_args()
    if args.paths != 512:
        parser.error("This fixed comparison specification requires 512 paths")
    from app import app
    import logging
    logging.getLogger().setLevel(logging.WARNING)
    with app.app_context():
        run(args.output, args.paths)
