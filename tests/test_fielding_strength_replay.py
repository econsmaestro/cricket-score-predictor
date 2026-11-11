"""Integrity checks for the offline replay and shared user-facing labelling."""
from types import SimpleNamespace

import pytest
import prediction
from research.fielding_strength_replay import chronological_split, metrics, replay_cohort


def fixtures():
    return [
        {"match_id": uid, "date": date, "overs": [], "players": {},
         "batting_team": "Other", "fielding_team": "India",
         "venue": "Unknown", "match_format": "womens_odi",
         "committed_rows": [{"checkpoint": 0, "score_at_cp": 0, "wickets_at_cp": 0,
                             "actual": 100, "actual_wickets": 4}]}
        for uid, date in [("a", "2025-01-01"), ("b", "2025-02-01")]
    ]


def test_split_does_not_separate_matches_on_same_date():
    matches = [
        {"match_id": str(i), "date": date}
        for i, date in enumerate(["2025-01-01", "2025-01-01", "2025-02-01", "2025-02-01"])
    ]
    early, late = chronological_split(matches)
    assert early == {"0", "1"}
    assert late == {"2", "3"}


def test_split_rejects_no_chronological_boundary():
    with pytest.raises(ValueError, match="at least two fixture dates"):
        chronological_split([{"match_id": "a", "date": "2025-01-01"}])


def test_signed_metrics():
    rows = [
        {"match_id": "a", "predicted_runs": 10, "actual_runs": 12,
         "predicted_wickets": 2, "actual_wickets": 4},
        {"match_id": "b", "predicted_runs": 16, "actual_runs": 12,
         "predicted_wickets": 5, "actual_wickets": 4},
    ]
    assert metrics(rows) == {
        "n": 2, "matches": 2, "run_mae": 3, "wicket_mae": 1.5,
        "run_bias": 1, "wicket_bias": -0.5,
    }


def test_replay_uses_identical_states_and_earlier_selection(monkeypatch):
    monkeypatch.setattr(prediction, "FIELDING_EFFECT_STRENGTH", 1.0)
    monkeypatch.setattr(prediction, "predict_score", lambda state: SimpleNamespace(
        predicted_final_score=100 + int(20 * prediction.FIELDING_EFFECT_STRENGTH),
        predicted_wickets=4 + int(2 * prediction.FIELDING_EFFECT_STRENGTH),
    ))
    rows, summary, split = replay_cohort("womens_odi", fixtures())
    assert len(rows) == 8
    assert len(summary) == 12
    assert split["selected_strength"] == 0.0
    assert split["fit_match_ids"] == ["a"]
    assert split["test_match_ids"] == ["b"]
    for match_id in ("a", "b"):
        paired = [r for r in rows if r["match_id"] == match_id]
        assert len({r["state_sha256"] for r in paired}) == 1
        assert {r["fielding_rating_key"] for r in paired} == {"India W"}
    assert prediction.FIELDING_EFFECT_STRENGTH == 1.0


def test_replay_restores_strength_on_failure(monkeypatch):
    monkeypatch.setattr(prediction, "FIELDING_EFFECT_STRENGTH", 0.5)

    def failed_prediction(state):
        raise RuntimeError("Synthetic model failure")

    monkeypatch.setattr(prediction, "predict_score", failed_prediction)
    with pytest.raises(RuntimeError, match="Synthetic model failure"):
        replay_cohort("womens_odi", fixtures())
    assert prediction.FIELDING_EFFECT_STRENGTH == 0.5


def test_demo_retains_number_with_honest_label(client, monkeypatch):
    import random
    monkeypatch.setattr(random, "choice", lambda choices: choices[0])
    response = client.get("/demo")
    assert response.status_code == 200
    assert b"Fielding rating (analyst estimate): 94%" in response.data
    assert b'Hand-assigned, not a measured statistic.' in response.data
    assert b"Australia fielding 94%" not in response.data
