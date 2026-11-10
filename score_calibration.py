"""Leakage-free post-hoc calibration of first-innings score predictions.

``prediction.py`` is frozen, so this layer learns a ridge correction on top of
its output from historical backtest rows, plus split-conformal prediction
intervals. Training is strictly temporal: the ridge is fit on the oldest rows,
interval widths are calibrated on the newer rows, and evaluation uses matches
newer than both. Artifacts are plain JSON (no pickle) in data/calibration/.
"""
import json
import math
from pathlib import Path

import numpy as np

CALIBRATION_DIR = Path(__file__).parent / "data" / "calibration"
TARGET_COVERAGE = 0.80
RIDGE_ALPHA = 10.0
_FEATURES = ("predicted", "score", "wickets", "projected_remaining", "wk_x_remaining", "overs")


def features(predicted, score, wickets, overs):
    remaining = predicted - score
    return np.array([predicted, score, wickets, remaining, wickets * remaining, overs], dtype=float)


def _row_features(row):
    return features(row["predicted"], row["score_at_cp"], row["wickets_at_cp"], row["checkpoint"])


def _scale(predicted, score):
    return max(predicted - score, 20.0)


def fit(rows, interval_fraction=0.25, alpha=RIDGE_ALPHA, coverage=TARGET_COVERAGE):
    """Fit on backtest rows (dicts from backtest.run_backtest), oldest first by date.

    The newest ``interval_fraction`` of *matches* is held out of the ridge fit and
    used only to calibrate the interval width.
    """
    order = sorted({(r["date"], r["match_id"]) for r in rows})
    if len(order) < 40:
        raise ValueError("Need at least 40 matches to calibrate")
    cut = int(len(order) * (1 - interval_fraction))
    early = {m for _, m in order[:cut]}
    fit_rows = [r for r in rows if r["match_id"] in early]
    cal_rows = [r for r in rows if r["match_id"] not in early]

    X = np.array([_row_features(r) for r in fit_rows])
    y = np.array([r["actual"] - r["predicted"] for r in fit_rows], dtype=float)
    mean, std = X.mean(0), X.std(0)
    std[std == 0] = 1.0
    Z = (X - mean) / std
    y_mean = y.mean()
    coef = np.linalg.solve(Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ (y - y_mean))
    model = {"mean": mean.tolist(), "std": std.tolist(), "coef": coef.tolist(),
             "intercept": float(y_mean), "features": list(_FEATURES)}

    scores = []
    for r in cal_rows:
        p = _apply(model, r["predicted"], r["score_at_cp"], r["wickets_at_cp"], r["checkpoint"])
        scores.append(abs(r["actual"] - p) / _scale(p, r["score_at_cp"]))
    n = len(scores)
    k = min(n - 1, math.ceil((n + 1) * coverage) - 1)
    model["interval_q"] = float(np.sort(scores)[k])
    model["coverage"] = coverage
    model["n_fit_rows"], model["n_calibration_rows"] = len(fit_rows), n
    return model


def _apply(model, predicted, score, wickets, overs):
    z = (features(predicted, score, wickets, overs) - np.array(model["mean"])) / np.array(model["std"])
    return predicted + model["intercept"] + float(z @ np.array(model["coef"]))


def calibrate(model, predicted, score, wickets, overs):
    """Return (calibrated_score, low, high); never below the current score."""
    p = max(_apply(model, predicted, score, wickets, overs), float(score))
    half = model["interval_q"] * _scale(p, score)
    return round(p), round(max(score, p - half)), round(p + half)


def save(model, match_format, directory=CALIBRATION_DIR):
    Path(directory).mkdir(parents=True, exist_ok=True)
    (Path(directory) / f"{match_format}.json").write_text(json.dumps(model, indent=1))


def load(match_format, directory=CALIBRATION_DIR):
    path = Path(directory) / f"{match_format}.json"
    return json.loads(path.read_text()) if path.exists() else None


def evaluate(model, rows):
    """MAE/RMSE/bias/coverage/width of calibrated vs raw predictions on rows."""
    out = {}
    for label, getp in (("raw", None), ("calibrated", model)):
        errs, hits, widths = [], [], []
        for r in rows:
            if getp is None:
                p, lo, hi = r["predicted"], r["pred_low"], r["pred_high"]
            else:
                p, lo, hi = calibrate(model, r["predicted"], r["score_at_cp"], r["wickets_at_cp"], r["checkpoint"])
            errs.append(p - r["actual"]); hits.append(lo <= r["actual"] <= hi); widths.append(hi - lo)
        e = np.array(errs, dtype=float)
        out[label] = {"n": len(e), "mae": round(float(np.abs(e).mean()), 2), "rmse": round(float(np.sqrt((e ** 2).mean())), 2),
                      "bias": round(float(e.mean()), 2), "hit_rate": round(100 * float(np.mean(hits)), 1),
                      "avg_width": round(float(np.mean(widths)), 1)}
    return out
