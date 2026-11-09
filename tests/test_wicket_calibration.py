"""Offline phase-2 experiments; no Flask app or database required."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import zipfile

import pytest

from research.wicket_calibration.data import snapshot, iso_next_day, replay, load_archive
from research.wicket_calibration.priors import PriorStore
from research.wicket_calibration.legacy import make_module, bind_priors, predict as legacy_predict
from research.wicket_calibration.simulator import predict, seed_for
from research.wicket_calibration.evaluation import metrics, uncertainty, split


def match(day="2020-01-01", runs=1, wicket=0, count=12, available="2026-11-05"):
    events = [{
        "batter": "p0", "non_striker": "p1", "bowler": "b0",
        "runs": runs, "bat_runs": runs, "legal": 1, "faced": 1,
        "bowler_runs": runs, "bowler_wicket": wicket,
        "wicket": wicket, "out": "p0" if wicket else None,
        "unavailable": ["p0"] if wicket else [], "rotation": runs % 2,
    } for _ in range(count)]
    return {
        "id": day, "date": day, "completed_before": iso_next_day(day), "available_at": available,
        "format": "mens_t20", "venue": "Test venue", "fielding_team": "Test opponents",
        "players": [f"p{i}" for i in range(11)], "names": {f"p{i}": f"Name{i}" for i in range(11)},
        "events": events, "actual_score": runs*count, "actual_wickets": wicket*count,
        "legal_balls": count, "max_balls": 120, "sha256": "test-only-fixture",
    }


def priors(tmp_path, fixtures=None, cutoff="2020-02-01", mode="event_time"):
    return PriorStore(fixtures or [match()], cutoff, tmp_path, "test-archive", mode)


def test_two_day_date_only_embargo():
    assert iso_next_day("2020-02-28") == "2020-03-01"
    assert iso_next_day("2020-12-31") == "2021-01-02"


def test_early_collapse_has_start_but_no_padded_checkpoint():
    m = match(wicket=1, count=10)
    assert snapshot(m, 0)["score"] == 0
    assert snapshot(m, 6) is None
    assert snapshot(m, 20) is None


def test_snapshot_at_terminal_time_is_not_forecast():
    assert snapshot(match(count=6), 1) is None


def test_snapshot_does_not_see_future_delivery():
    m = match(count=12)
    initial = snapshot(m, 1)
    m["events"][7]["runs"] = 10000
    m["events"][7]["batter"] = "future_player"
    assert snapshot(m, 1) == initial


def test_zero_checkpoint_does_not_peek_at_openers():
    m = match()
    assert snapshot(m, 0)["active"] == [None, None]
    assert not snapshot(m, 0)["seen"]


def test_pending_batter_not_filled_from_next_over():
    m = match(runs=0)
    m["events"][5].update(wicket=1, out="p0", unavailable=["p0"])
    m["events"][6]["batter"] = "p2"
    s = snapshot(m, 1)
    assert None in s["active"]
    assert "p2" not in s["seen"]


def test_snapshot_keeps_nonstriker_without_facing_ball():
    m = match(runs=0)
    s = snapshot(m, 1)
    assert set(s["active"]) == {"p0", "p1"}
    assert s["faced"]["p1"] == [0, 0]


def test_actual_score_and_wickets_reconstruct():
    m = match(runs=2)
    s = snapshot(m, 1)
    assert (s["score"], s["wickets"], s["balls"]) == (12, 0, 6)


def test_future_completed_fixture_is_excluded(tmp_path):
    store = priors(tmp_path, [match(), match("2020-03-01", runs=999)])
    assert len(store.matches) == 1
    assert store.bat["p0"][0] == 12


def test_same_day_information_is_embargoed(tmp_path):
    with pytest.raises(ValueError, match="No historical"):
        priors(tmp_path, [match("2020-01-31")])


def test_verified_first_seen_rejects_historical_reconstruction(tmp_path):
    with pytest.raises(ValueError, match="provably available"):
        priors(tmp_path, mode="verified_availability")


def test_verified_first_seen_accepts_previously_observed_data(tmp_path):
    store = priors(tmp_path, [match(available="2020-01-20")], mode="verified_availability")
    assert store.mode == "verified_availability"


def test_prior_snapshot_is_content_addressed_and_repeatable(tmp_path):
    first = priors(tmp_path)
    second = priors(tmp_path)
    assert first.digest == second.digest
    assert first.path == second.path


def test_prior_rejects_prediction_before_snapshot_cutoff(tmp_path):
    store = priors(tmp_path)
    with pytest.raises(ValueError, match="future information"):
        store.assert_as_of("2020-01-20")


def test_unobserved_player_has_no_fabricated_history(tmp_path):
    store = priors(tmp_path)
    assert "p10" not in store.bat
    p = store.distribution(3, 2, 2, 1, "unknown", "full", 100)
    assert p.sum() == pytest.approx(1)


def test_simulation_without_dismissal_events_never_invents_wickets(tmp_path):
    store = priors(tmp_path)
    state = snapshot(match("2020-03-01"), 0)
    result = predict(state, store, "joint_full", 100, 1, paths=32)
    assert result["wickets"] == 0
    assert result["score"] == 120
    assert result["low"] == result["high"] == 120


def test_joint_outcomes_stop_runs_at_allout(tmp_path):
    store = priors(tmp_path, [match(runs=4, wicket=1, count=10)])
    state = snapshot(match("2020-03-01"), 0)
    result = predict(state, store, "joint_full", 100, 1, paths=32)
    assert result["wickets"] == 10
    assert result["score"] == 40
    assert result["mean_legal_balls_remaining"] == 10
    assert result["allout_probability"] == 1


def test_simulation_seed_reproducible(tmp_path):
    store = priors(tmp_path)
    state = snapshot(match("2020-03-01"), 0)
    assert predict(state, store, "joint_state", 10, 123, paths=16) == predict(
        state, store, "joint_state", 10, 123, paths=16)
    assert seed_for("mens_t20", "a", 6) != seed_for("mens_t20", "a", 10)


def test_completed_state_is_absorbing(tmp_path):
    store = priors(tmp_path)
    state = snapshot(match("2020-03-01"), 0)
    state.update(wickets=10, score=99)
    result = predict(state, store, "joint_phase", 100, 1, paths=16)
    assert result["wickets"] == 10 and result["score"] == 99
    assert result["allout_probability"] == 1


def test_no_floor_allows_zero_additional_wickets(tmp_path):
    store = priors(tmp_path)
    state = snapshot(match("2020-03-01", count=120), 19)
    state["wickets"] = 3
    base = make_module("unit_base")
    changed = make_module("unit_no_floor", no_floor=True)
    for module in (base, changed):
        bind_priors(module, store)
    before = legacy_predict(base, state, store)
    after = legacy_predict(changed, state, store)
    assert before["wickets"] == 4
    assert after["wickets"] == 3
    assert before["score"] == after["score"]


def test_factor_removal_does_not_modify_scores(tmp_path):
    store = priors(tmp_path)
    state = snapshot(match("2020-03-01", count=120), 6)
    base, changed = make_module("unit_factor_base"), make_module("unit_factor", no_factor=True)
    for module in (base, changed):
        bind_priors(module, store)
    before, after = legacy_predict(base, state, store), legacy_predict(changed, state, store)
    assert before["score"] == after["score"]
    assert before["low"] == after["low"] and before["high"] == after["high"]
    assert after["wickets"] >= before["wickets"]


def test_rounding_metrics_have_correct_error_sign():
    row = {"match_id": "a", "predicted_wickets": 5, "actual_wickets": 8,
           "predicted_score": 200, "actual_score": 210, "low": 180, "high": 220}
    values = metrics([row])
    assert values["wicket_mae"] == 3 and values["wicket_bias"] == -3
    assert values["score_mae"] == 10 and values["score_bias"] == -10
    assert values["coverage_pct"] == 100


def test_import_keeps_early_allout_and_flags_ambiguous_timing(tmp_path):
    cache = tmp_path / "backtest_cache"
    cache.mkdir()
    registry = {f"P{i}": f"p{i}" for i in range(11)}
    registry["Bowler"] = "b0"
    deliveries = [{
        "batter": f"P{i}", "non_striker": "P10", "bowler": "Bowler",
        "runs": {"batter": 0, "total": 0},
        "wickets": [{"player_out": f"P{i}", "kind": "bowled"}],
    } for i in range(10)]
    raw = {"meta": {"created": "2020-02-01", "revision": 1},
           "info": {"gender": "male", "match_type": "T20", "overs": 20,
                    "dates": ["2020-01-01"], "teams": ["A", "B"], "venue": "Test",
                    "players": {"A": list(registry)[:11]}, "registry": {"people": registry}},
           "innings": [{"team": "A", "overs": [{"over": 0, "deliveries": deliveries[:6]},
                                               {"over": 1, "deliveries": deliveries[6:]}]}]}
    bad = deepcopy(raw)
    bad["innings"][0]["overs"][0]["deliveries"][0]["wickets"].append(
        {"player_out": "P10", "kind": "retired out"})
    with zipfile.ZipFile(cache / "t20s_male_json.zip", "w") as archive:
        archive.writestr("valid.json", json.dumps(raw))
        archive.writestr("ambiguous.json", json.dumps(bad))
    loaded, excluded, digest = load_archive(tmp_path, "mens_t20", "2026-11-05")
    assert len(loaded) == 1 and loaded[0]["actual_wickets"] == 10
    assert loaded[0]["legal_balls"] == 10
    assert excluded["ambiguous_multiple_wicket_timing_requires_review"] == 1
    assert len(digest) == 64
