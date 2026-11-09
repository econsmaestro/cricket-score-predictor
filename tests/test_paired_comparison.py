"""Checks for shared observations and the promotion evidence calculations."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from research.wicket_calibration.paired_comparison import (
    NAMES, assessment, current_input_prediction, paired_rows,
)


def rows():
    return [
        {"variant": variant, "match_id": "one", "checkpoint": 10,
         "actual_score": 200, "actual_wickets": 8, "score_at_cp": 50,
         "wickets_at_cp": 2, "state_hash": "same-state"}
        for variant in NAMES
    ]


def test_paired_observations_require_all_arms():
    assert paired_rows(rows()) == 1
    with pytest.raises(AssertionError):
        paired_rows(rows()[:-1])


@pytest.mark.parametrize("field", [
    "actual_score", "actual_wickets", "score_at_cp", "wickets_at_cp", "state_hash",
])
def test_different_states_or_targets_are_rejected(field):
    data = rows()
    data[-1][field] = "different"
    with pytest.raises(AssertionError):
        paired_rows(data)


def test_both_outcomes_must_improve():
    b = {"score_mae": 40, "wicket_mae": 3}
    e = {"score_mae": 30, "wicket_mae": 2}
    ci = {"score": {"ci_high": -1}, "wickets": {"ci_high": -0.1}}
    result = assessment(b, e, ci)
    assert result["both_mae_lower"]
    assert result["both_paired_95ci_below_zero"]
    assert result["run_mae_reduction_pct"] == 25
    assert result["wicket_mae_reduction_pct"] == pytest.approx(100 / 3)
    assert not assessment(b, {**e, "score_mae": 41}, ci)["both_mae_lower"]
    assert not assessment(b, e, {**ci, "score": {"ci_high": 1}})["both_paired_95ci_below_zero"]


def test_current_input_adapter_preserves_observed_state():
    module = SimpleNamespace(
        MatchState=lambda **kwargs: SimpleNamespace(**kwargs),
        Batsman=lambda **kwargs: SimpleNamespace(**kwargs),
        Bowler=lambda **kwargs: SimpleNamespace(**kwargs),
        predict_score=Mock(return_value=SimpleNamespace(
            predicted_final_score=200, predicted_wickets=7, score_range=(180, 220))),
    )
    state = {
        "names": {"p": "Player", "b": "Bowler", "next": "Next"},
        "score": 50, "wickets": 2, "balls": 60, "venue": "Test ground",
        "active": ["p", None], "faced": {"p": [10, 15]}, "bowled": {"b": [12, 10, 1]},
        "max_balls": 300, "players": ["p", "next"], "seen": {"p"},
        "format": "mens_odi", "fielding_team": "Opponents",
    }
    before = deepcopy(state)
    result = current_input_prediction(module, state)
    ms = module.predict_score.call_args.args[0]
    assert (ms.current_score, ms.wickets_fallen, ms.overs_completed) == (50, 2, 10)
    assert ms.batsmen[0].name == "Player"
    assert ms.batsmen[0].balls_faced == 15
    assert ms.batsmen_to_come == ["Next"]
    assert ms.bowlers[0].overs_remaining == 8
    assert ms.innings == 1 and ms.target == 0
    assert result == {"score": 200, "wickets": 7, "low": 180, "high": 220}
    assert state == before
