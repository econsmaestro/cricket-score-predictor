"""Train/evaluate the score calibration layer with a temporal holdout.

    python calibrate_scores.py [--holdout 150] [--train-matches 1000] [--save]
"""
import argparse
import json

import backtest
import score_calibration as sc
from backtest_data import FORMATS

MAX_TRAIN = {"womens_odi": 480}


def run(match_format, holdout, train_matches, save):
    rows = backtest.run_backtest(min(train_matches, MAX_TRAIN.get(match_format, train_matches)), match_format)
    order = sorted({(r["date"], r["match_id"]) for r in rows})
    test_ids = {m for _, m in order[-holdout:]}
    train = [r for r in rows if r["match_id"] not in test_ids]
    test = [r for r in rows if r["match_id"] in test_ids]
    model = sc.fit(train)
    result = sc.evaluate(model, test)
    if save:  # refit on everything so production uses the newest data
        sc.save(sc.fit(rows), match_format)
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", type=int, default=150)
    ap.add_argument("--train-matches", type=int, default=1000)
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()
    print(json.dumps({f: run(f, a.holdout, a.train_matches, a.save) for f in FORMATS}, indent=1))
