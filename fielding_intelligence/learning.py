"""Optional supervised residual learning; never assigns component weights by hand.

Requires legally obtained opportunity-adjusted features. Not trained by counts
of catches in Cricsheet and never used automatically by the production engine.
"""
from datetime import date

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ("catch_conversion", "run_out_conversion", "runs_saved_per_ground_event",
            "overs_remaining", "wickets_in_hand", "baseline_score", "baseline_wickets")


def fit_residual_model(records, *, training_cutoff):
    cutoff = date.fromisoformat(str(training_cutoff))
    rows = sorted(records, key=lambda r: (r["date"], r["match_id"]))
    if len({(r["format"], r["gender"]) for r in rows}) != 1:
        raise ValueError("Train a separate artifact for each format and gender")
    for row in rows:
        fixture_date = date.fromisoformat(str(row["date"]))
        if date.fromisoformat(str(row["label_available_date"])) < fixture_date:
            raise ValueError("Outcome cannot be available before the fixture")
        if fixture_date >= cutoff or date.fromisoformat(str(row["label_available_date"])) >= cutoff:
            raise ValueError("Training targets must be available before the cutoff")
        if date.fromisoformat(str(row["latest_feature_evidence_date"])) >= fixture_date:
            raise ValueError("Feature leakage: evidence must precede this fixture")
        if not row.get("opportunity_data_validated"):
            raise ValueError("Observed opportunities and coverage must be validated")
        if any(row["features"].get(key) is None for key in FEATURES):
            raise ValueError("Missing components cannot be replaced with invented features")
    dates = sorted({str(row["date"]) for row in rows})
    if len(dates) < 4:
        raise ValueError("At least four distinct dates needed for chronological cross-validation")
    x = np.array([[row["features"][key] for key in FEATURES] for row in rows], dtype=float)
    y = np.array([[row["actual_score"] - row["features"]["baseline_score"],
                   row["actual_wickets"] - row["features"]["baseline_wickets"]]
                  for row in rows], dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Training data must be finite")
    # Split whole dates: a fixture's checkpoints can never cross fold boundaries.
    folds = []
    for train_dates, valid_dates in TimeSeriesSplit(n_splits=min(3, len(dates)-1)).split(dates):
        train = [i for i, row in enumerate(rows) if str(row["date"]) in {dates[j] for j in train_dates}]
        valid = [i for i, row in enumerate(rows) if str(row["date"]) in {dates[j] for j in valid_dates}]
        folds.append((train, valid))
    # Scaling is inside the pipeline so each fold learns it from past data only.
    learner = GridSearchCV(make_pipeline(StandardScaler(), Ridge()),
                           {"ridge__alpha": np.logspace(-4, 4, 17)},
                           cv=folds, scoring="neg_mean_squared_error")
    learner.fit(x, y)
    return {
        "model": learner.best_estimator_, "features": FEATURES,
        "training_cutoff": str(cutoff), "training_matches": len({r["match_id"] for r in rows}),
        "training_format": rows[0]["format"], "training_gender": rows[0]["gender"],
        "regularization": float(learner.best_params_["ridge__alpha"]),
        "activation_allowed": False,
        "reason": "Training is not independent validation; no held-out score/interval/wicket/win approval",
    }


def shadow_residual(artifact, features):
    if any(features.get(key) is None for key in FEATURES):
        raise ValueError("Cannot predict an effect with missing fielding components")
    values = artifact["model"].predict([[features[key] for key in FEATURES]])[0]
    return {"score_residual": float(values[0]), "wicket_residual": float(values[1]),
            "applied": False, "interpretation": "Predictive residual, not a causal fielding effect"}
