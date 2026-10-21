"""ODI acceleration corrections and frozen pre-change T20 outputs."""
import pytest

import learning_engine
import prediction
from prediction import Batsman, Bowler, MatchState, predict_score


@pytest.fixture(autouse=True)
def fixed_learned_adjustments(monkeypatch):
    # Keep these structural tests independent of the development database.
    monkeypatch.setattr(learning_engine, "get_venue_adjustment", lambda *a: 0)
    monkeypatch.setattr(learning_engine, "get_phase_adjustment", lambda *a: 0)


def state(fmt, score, wickets, overs):
    return MatchState(
        current_score=score, wickets_fallen=wickets, overs_completed=overs,
        venue="Regression test ground",
        batsmen=[Batsman("Test opener", 35, 25), Batsman("Test partner", 15, 12)],
        bowlers=[Bowler("Test bowler", 2, 15, 1, 2)], match_format=fmt,
    )


@pytest.mark.parametrize("fmt", ["mens_t20", "womens_t20"])
@pytest.mark.parametrize("score,wickets,overs,expected", [
    (50, 1, 6, (179, (153, 205), 5, 7, 0.385, 1, 2, 3)),
    (90, 3, 10, (168, (143, 193), 5, 5, 0.385, 1, 2, 3)),
    (140, 5, 16, (163, (150, 176), 6, 6, 0.55, 2, 2, 2)),
    (155, 8, 18, (159, (147, 171), 9, 3, 0.55, 2, 1, 3)),
])
def test_t20_matches_pre_change_outputs(monkeypatch, fmt, score, wickets, overs, expected):
    def odi_must_not_run(*args):
        raise AssertionError("ODI acceleration used for T20")
    monkeypatch.setattr(prediction, "_odi_acceleration_boost", odi_must_not_run)
    p = predict_score(state(fmt, score, wickets, overs))
    assert (p.predicted_final_score, p.score_range, p.predicted_wickets,
            p.predicted_next_over_runs, p.wicket_probability, p.boundary_count,
            p.dot_ball_count, p.singles_doubles_count) == expected


@pytest.mark.parametrize("fmt", ["mens_odi", "womens_odi"])
@pytest.mark.parametrize("overs,score", [(10, 50), (30, 160), (40, 240)])
def test_odi_reserves_boost_future_death_even_after_30(monkeypatch, fmt, overs, score):
    match = state(fmt, score, 2, overs)
    boosted = predict_score(match).predicted_final_score
    monkeypatch.setattr(prediction, "_odi_acceleration_boost", lambda *a: 1.0)
    assert boosted > predict_score(match).predicted_final_score


def test_acceleration_requires_resources_and_is_bounded():
    boost = prediction._odi_acceleration_boost
    assert boost(4, 9.0) == 1.0
    assert 1.0 < boost(5, 5.0) < boost(8, 5.0)
    assert boost(8, 8.0) > boost(8, 5.0)
    assert boost(10, 20.0) <= 1.25


@pytest.mark.parametrize("fmt", ["mens_odi", "womens_odi"])
def test_modern_death_rate_improves_early_projection(monkeypatch, fmt):
    assert prediction.ODI_PHASE_RUN_RATES["death"]["avg_runs_per_over"] == 10.0
    match = state(fmt, 55, 2, 10)
    modern = predict_score(match).predicted_final_score
    monkeypatch.setitem(prediction.ODI_PHASE_RUN_RATES["death"], "avg_runs_per_over", 7.5)
    assert modern > predict_score(match).predicted_final_score


@pytest.mark.parametrize("overs,fraction", [
    (10, 0.15), (20, 0.15), (25, 0.15), (30, 0.12), (40, 0.08),
])
def test_odi_range_uses_innings_progress_not_t20_cutoffs(overs, fraction):
    p = predict_score(state("mens_odi", overs * 5, 2, overs))
    half_width = int(p.predicted_final_score * fraction)
    assert p.score_range == (p.predicted_final_score - half_width,
                             p.predicted_final_score + half_width)


def test_high_scoring_odi_can_project_above_old_death_cap(monkeypatch):
    monkeypatch.setattr(prediction, "calculate_smoothed_batsman_sr", lambda *a: 180.0)
    p = predict_score(state("mens_odi", 320, 2, 40))
    assert p.predicted_final_score > 320 + 10 * 12
    assert p.predicted_final_score <= 320 + 10 * 15


def test_odi_collapse_still_restricts_scoring():
    assert (predict_score(state("mens_odi", 180, 8, 30)).predicted_final_score
            < predict_score(state("mens_odi", 180, 2, 30)).predicted_final_score)
