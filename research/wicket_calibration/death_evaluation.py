"""Supplementary late checkpoints; never mixed into preregistered primary metrics."""
import csv
import json

from .data import FORMATS, load_archive, snapshot
from .evaluation import OUT, ROOT, VARIANTS, metrics, protected_hashes
from .legacy import make_module, bind_priors, predict as legacy_predict
from .priors import PriorStore
from .simulator import LEVELS, predict as joint_predict, seed_for


def run():
    initial = protected_hashes()
    results = json.loads((OUT / "results.json").read_text())
    spec = json.loads((OUT / "preregistered-specification.json").read_text())
    old = json.loads((ROOT / "generated-artifacts/wicket-audit/ablations.json").read_text())
    rows, summary = [], {}
    for fmt, result in results.items():
        end_before = min(m["date"] for group in old["manifest"][fmt].values() for m in group)
        matches, _, archive_sha = load_archive(
            ROOT, fmt, spec["registered_before_evaluation"], end_before=end_before)
        history_ids = {m["id"] for key in ("training", "validation") for m in result["manifest"][key]}
        test_ids = {m["id"] for m in result["manifest"]["holdout"]}
        frozen = PriorStore([m for m in matches if m["id"] in history_ids],
                            result["prior_cutoff"], OUT / "priors", archive_sha)
        assert frozen.digest == result["prior_snapshot_sha256"], "Do not change late-checkpoint priors"
        modules = {name: make_module("late_" + name, "no_0_6" in name, "no_floor" in name)
                   for name in VARIANTS if not name.startswith("joint_")}
        for module in modules.values():
            bind_priors(module, frozen)
        checkpoints = (45, 48, 49) if fmt.endswith("odi") else (17, 18, 19)
        eligible = {}
        for cp in checkpoints:
            start = len(rows)
            for match in matches:
                if match["id"] not in test_ids:
                    continue
                state = snapshot(match, cp)
                if state is None:
                    continue
                predictions = {name: legacy_predict(module, state, frozen) for name, module in modules.items()}
                for name in LEVELS:
                    predictions[name] = joint_predict(state, frozen, name,
                        result["tuning"][name]["selected_alpha"], seed_for(fmt, match["id"], cp), spec["paths"])
                for name, predicted in predictions.items():
                    rows.append({
                        "format": fmt, "match_id": match["id"], "checkpoint": cp, "variant": name,
                        "predicted_wickets": predicted["wickets"], "actual_wickets": match["actual_wickets"],
                        "predicted_score": predicted["score"], "actual_score": match["actual_score"],
                        "low": predicted["low"], "high": predicted["high"],
                    })
            current = rows[start:]
            eligible[str(cp)] = {name: metrics([r for r in current if r["variant"] == name]) for name in VARIANTS}
        summary[fmt] = eligible
        print(fmt, "supplementary death checkpoints complete", flush=True)
    (OUT / "death-checkpoints.json").write_text(json.dumps(summary, indent=2))
    with (OUT / "death-checkpoints.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    assert initial == protected_hashes()


if __name__ == "__main__":
    run()
