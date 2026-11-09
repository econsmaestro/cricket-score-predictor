"""Reproducible, offline chronological experiments; no production imports at startup."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gc
import hashlib
import json
from pathlib import Path
import csv
import statistics
import time

import numpy as np
from .data import FORMATS, load_archive, snapshot, replay, wicket_bucket
from .legacy import make_module, bind_priors, predict as legacy_predict
from .priors import PriorStore, select_alpha
from .simulator import LEVELS, predict as joint_predict, seed_for

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "generated-artifacts/wicket-phase2"
VARIANTS = ("baseline", "no_0_6", "no_floor", "no_0_6_no_floor", *LEVELS)


def protected_hashes():
    files = [ROOT / n for n in ("prediction.py", "backtest.py", "backtest_data.py",
                                "backtest_reports.py", "routes.py", "learning_engine.py", "ipl_stats.py")]
    files += sorted((ROOT / "fielding_intelligence").glob("*.py"))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def metrics(rows):
    if not rows:
        return None
    w = np.array([r["predicted_wickets"] - r["actual_wickets"] for r in rows])
    s = np.array([r["predicted_score"] - r["actual_score"] for r in rows])
    return {
        "n": len(rows), "matches": len({r["match_id"] for r in rows}),
        "wicket_mae": float(np.mean(abs(w))), "wicket_bias": float(w.mean()),
        "exact_pct": float(100 * np.mean(w == 0)), "wicket_rmse": float(np.sqrt(np.mean(w*w))),
        "score_mae": float(np.mean(abs(s))), "score_bias": float(s.mean()),
        "score_rmse": float(np.sqrt(np.mean(s*s))),
        "coverage_pct": float(100 * np.mean([r["low"] <= r["actual_score"] <= r["high"] for r in rows])),
        "range_width": float(np.mean([r["high"] - r["low"] for r in rows])),
    }


def breakdown(rows):
    result = {"overall": metrics(rows),
              "configured_only": metrics([r for r in rows if r["checkpoint"] != 0])}
    for key in ("checkpoint", "phase", "actual_wicket_bucket"):
        groups = defaultdict(list)
        for row in rows:
            groups[str(row[key])].append(row)
        result[key] = {k: metrics(v) for k, v in sorted(groups.items())}
    return result


def uncertainty(rows, repetitions=2000):
    by_variant = defaultdict(lambda: defaultdict(list))
    for row in rows:
        by_variant[row["variant"]][row["match_id"]].append(row)
    ids = sorted(by_variant["baseline"])
    rng = np.random.default_rng(20261105)
    samples = rng.integers(0, len(ids), (repetitions, len(ids)))
    sizes = np.array([len(by_variant["baseline"][mid]) for mid in ids])
    denominator = sizes[samples].sum(axis=1)
    result = {}
    for name, grouped in by_variant.items():
        if name == "baseline":
            continue
        result[name] = {}
        for target in ("wickets", "score"):
            delta = np.array([
                sum(abs(r["predicted_" + target] - r["actual_" + target]) for r in grouped[mid])
                - sum(abs(r["predicted_" + target] - r["actual_" + target])
                      for r in by_variant["baseline"][mid]) for mid in ids])
            resampled = delta[samples].sum(axis=1) / denominator
            low, high = np.quantile(resampled, (.025, .975))
            result[name][target] = {"delta_mae": float(delta.sum() / sizes.sum()),
                                    "ci_low": float(low), "ci_high": float(high)}
    return result


def split(matches):
    """Latest100 eligible older, unused first innings; preceding50 validation."""
    if len(matches) < 200:
        raise ValueError("At least 200 earlier completed first innings required")
    test = matches[-100:]
    test_cutoff = min(m["date"] for m in test)
    older = [m for m in matches[:-100] if m["completed_before"] <= test_cutoff]
    validation = older[-50:]
    validation_cutoff = min(m["date"] for m in validation)
    train = [m for m in older[:-50] if m["completed_before"] <= validation_cutoff]
    assert train and validation and len(test) == 100
    assert max(m["completed_before"] for m in train) <= validation_cutoff
    assert max(m["completed_before"] for m in validation) <= test_cutoff
    assert not ({m["id"] for m in test} & {m["id"] for m in train + validation})
    return train, validation, test


def death_table(matches):
    groups = defaultdict(lambda: [0, 0, 0])
    for match in matches:
        for state, e in replay(match):
            key = (state["phase"], wicket_bucket(state["wickets"]), state["rate_bucket"],
                   int(state["recent"] >= 1))
            groups[key][0] += e["wicket"]
            groups[key][1] += e["legal"]
            groups[key][2] += 1
    return [{"phase": k[0], "wickets_bucket": k[1], "run_rate_bucket": k[2],
             "recent_wicket_in_12_balls": k[3], "wickets": v[0],
             "legal_balls": v[1], "deliveries": v[2],
             "wickets_per_over": 6*v[0]/v[1] if v[1] else None}
            for k, v in sorted(groups.items())]


def run(paths=128):
    OUT.mkdir(parents=True, exist_ok=True)
    before = protected_hashes()
    prior_audit = json.loads((ROOT / "generated-artifacts/wicket-audit/ablations.json").read_text())
    first_seen = datetime.now(timezone.utc).isoformat()
    modules = {name: make_module(name, "no_0_6" in name, "no_floor" in name)
               for name in VARIANTS if not name.startswith("joint_")}
    specification = {
        "registered_before_evaluation": first_seen, "paths": paths, "variants": list(VARIANTS),
        "joint_levels": LEVELS, "alpha_grid": [1, 10, 100, 1000],
        "selection": "Completed standard first innings, including early all-outs; no minimum-over filter.",
        "checkpoints": {f: config[4] for f, config in FORMATS.items()},
        "holdout": "100 latest eligible innings strictly preceding every fixture examined in phase1.",
        "primary_weighting": "Each eligible active checkpoint, including innings start. No padded terminal forecasts.",
        "date_only_embargo_days": 2,
        "output_decision": "Rounded predictive mean; joint central 80% empirical interval.",
        "empirical_availability": "event-time reconstruction; strict first-seen mode separately assessed",
        "frozen_legacy_input_policy": "Dated stable-ID batting SR and venue means; neutral unsupported labels/fielding; DB offsets zero.",
        "legacy_sources": {name: m.source_hash for name, m in modules.items()},
        "protected_hashes": before,
    }
    (OUT / "preregistered-specification.json").write_text(json.dumps(specification, indent=2))
    all_results = {}
    output = (OUT / "predictions.csv").open("w", newline="")
    writer = None
    for fmt in FORMATS:
        start = time.monotonic()
        prior_ids = [m for group in prior_audit["manifest"][fmt].values() for m in group]
        before_date = min(m["date"] for m in prior_ids)
        matches, excluded, source_sha = load_archive(ROOT, fmt, first_seen, end_before=before_date)
        training, validation, test = split(matches)
        assert not ({m["id"] for m in test} & {m["id"] for m in prior_ids})
        tune = PriorStore(training, min(m["date"] for m in validation),
                          OUT / "priors", source_sha)
        learned = {name: select_alpha(tune, validation, level) for name, level in LEVELS.items()}
        frozen = PriorStore(training + validation, min(m["date"] for m in test),
                            OUT / "priors", source_sha)
        for module in modules.values():
            bind_priors(module, frozen)
        try:
            PriorStore(training + validation, min(m["date"] for m in test),
                       OUT / "priors", source_sha, mode="verified_availability")
            strict_available = True
        except ValueError:
            strict_available = False
        print(fmt, "train", len(training), "validation", len(validation), "holdout", len(test),
              "selected concentrations", {k: v[0] for k, v in learned.items()}, flush=True)
        rows, eligibility = [], Counter()
        target_checks = pair_checks = 0
        for index, match in enumerate(test):
            assert sum(e["runs"] for e in match["events"]) == match["actual_score"]
            assert sum(e["wicket"] for e in match["events"]) == match["actual_wickets"]
            target_checks += 1
            for cp in FORMATS[fmt][4]:
                state = snapshot(match, cp)
                if state is None:
                    eligibility[f"ended_before_or_at_{cp}"] += 1
                    continue
                eligibility[f"active_at_{cp}"] += 1
                frozen.assert_as_of(state["as_of"])
                predictions = {name: legacy_predict(module, state, frozen) for name, module in modules.items()}
                for name in ("no_0_6", "no_floor", "no_0_6_no_floor"):
                    assert predictions[name]["score"] == predictions["baseline"]["score"]
                    assert predictions[name]["low"] == predictions["baseline"]["low"]
                    assert predictions[name]["high"] == predictions["baseline"]["high"]
                    pair_checks += 1
                for name in LEVELS:
                    predictions[name] = joint_predict(
                        state, frozen, name, learned[name][0],
                        seed_for(fmt, match["id"], cp), paths)
                for name, predicted in predictions.items():
                    row = {
                        "format": fmt, "match_id": match["id"], "date": match["date"],
                        "checkpoint": cp, "phase": int(np.searchsorted(
                            [10, 30, 40] if fmt.endswith("odi") else [6, 14, 17], cp, side="right")),
                        "variant": name, "wickets_at_cp": state["wickets"], "score_at_cp": state["score"],
                        "predicted_wickets": predicted["wickets"], "actual_wickets": match["actual_wickets"],
                        "predicted_score": predicted["score"], "actual_score": match["actual_score"],
                        "actual_wicket_bucket": "0–3" if match["actual_wickets"] <= 3
                            else "4–6" if match["actual_wickets"] <= 6 else "7–10",
                        "low": predicted["low"], "high": predicted["high"],
                        "allout_probability": predicted.get("allout_probability"),
                        "score_mc_se": predicted.get("score_mc_se"),
                        "wicket_mc_se": predicted.get("wicket_mc_se"),
                        "prior_sha256": frozen.digest, "prior_cutoff": frozen.cutoff,
                    }
                    assert state["wickets"] <= row["predicted_wickets"] <= 10
                    assert row["predicted_score"] >= state["score"]
                    rows.append(row)
                    if writer is None:
                        writer = csv.DictWriter(output, fieldnames=list(row))
                        writer.writeheader()
                    writer.writerow(row)
            if (index + 1) % 20 == 0:
                output.flush()
                print(fmt, index + 1, "holdout fixtures completed", flush=True)
        by_variant = {name: breakdown([r for r in rows if r["variant"] == name]) for name in VARIANTS}
        manifest = {
            key: [{"id": m["id"], "date": m["date"], "completed_before": m["completed_before"],
                   "sha256": m["sha256"]} for m in group]
            for key, group in (("training", training), ("validation", validation), ("holdout", test))
        }
        all_results[fmt] = {
            "metrics": by_variant, "paired_uncertainty": uncertainty(rows), "manifest": manifest,
            "eligibility": dict(eligibility), "exclusions": excluded, "source_sha256": source_sha,
            "prior_snapshot_sha256": frozen.digest, "prior_cutoff": frozen.cutoff,
            "tuning": {name: {"selected_alpha": values[0], "validation_scores": values[1]}
                       for name, values in learned.items()},
            "strict_available_history": strict_available,
            "early_allout_fixtures": sum(m["actual_wickets"] == 10 and
                m["legal_balls"] <= max(FORMATS[fmt][4]) * 6 for m in test),
            "allout_fixtures": sum(m["actual_wickets"] == 10 for m in test),
            "training_hazards": death_table(training + validation),
            "checks": {"target_checks": target_checks, "unchanged_legacy_score_checks": pair_checks},
            "seconds": time.monotonic() - start,
        }
        (OUT / "results.json").write_text(json.dumps(all_results, indent=2))
        print(fmt, {name: tuple(round(by_variant[name]["overall"][k], 3)
                               for k in ("wicket_mae", "wicket_bias", "score_mae")) for name in VARIANTS}, flush=True)
        del matches, training, validation, test, frozen, tune, rows
        gc.collect()
    output.close()
    assert before == protected_hashes(), "Protected production or fielding source changed"
    (OUT / "verification.json").write_text(json.dumps({
        "protected_sources_unchanged": True, "formats": 4,
        "historical_availability_certified": False, "first_seen_at": first_seen,
        "certification_blocker": "Current ZIPs have no verifiable historical revision publication ledger.",
        "paths": paths, "code_hashes": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob("*.py")},
    }, indent=2))
    print("All experiments complete; production and Fielding Intelligence unchanged.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--paths", type=int, default=128)
    args = parser.parse_args()
    if args.paths < 2:
        parser.error("--paths must be >=2")
    run(args.paths)
