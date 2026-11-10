import numpy as np
import pytest

import score_calibration as sc


def _rows(n_matches=120, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_matches):
        actual = int(rng.normal(165, 25))
        for cp in (6, 10, 15):
            score = int(actual * cp / 20 * rng.uniform(0.8, 1.1))
            pred = int(actual * 0.85 + rng.normal(0, 10))  # systematically low
            rows.append({"match_id": f"m{i}", "date": f"2020-01-{1 + i % 28:02d}", "predicted": pred,
                         "score_at_cp": score, "wickets_at_cp": int(rng.integers(0, 6)),
                         "checkpoint": cp, "actual": actual, "pred_low": pred - 15, "pred_high": pred + 15})
    return rows


def test_calibration_reduces_error_on_holdout():
    rows = _rows()
    train, test = rows[:-60 * 3], rows[-60 * 3:]
    model = sc.fit(train)
    result = sc.evaluate(model, test)
    assert result["calibrated"]["mae"] < result["raw"]["mae"]
    assert 65 <= result["calibrated"]["hit_rate"] <= 95


def test_calibrated_never_below_current_score_and_ordered():
    model = sc.fit(_rows())
    p, lo, hi = sc.calibrate(model, 50, 140, 8, 18)
    assert p >= 140 and 140 <= lo <= p <= hi


def test_interval_set_uses_newer_matches_than_ridge_fit():
    rows = _rows()
    model = sc.fit(rows, interval_fraction=0.25)
    assert model["n_calibration_rows"] == 30 * 3
    assert model["n_fit_rows"] == 90 * 3


def test_fit_requires_enough_matches_and_roundtrips(tmp_path):
    with pytest.raises(ValueError):
        sc.fit(_rows(10))
    model = sc.fit(_rows())
    sc.save(model, "mens_t20", tmp_path)
    assert sc.load("mens_t20", tmp_path) == model
    assert sc.load("womens_odi", tmp_path) is None
