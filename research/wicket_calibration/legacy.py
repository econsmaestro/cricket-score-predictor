"""Unchanged production equations, isolated and supplied only dated empirical inputs."""
from collections import defaultdict
from contextlib import contextmanager
import hashlib
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[2]


def make_module(name, no_factor=False, no_floor=False):
    source = (ROOT / "prediction.py").read_text()
    if no_factor:
        assert source.count("expected_additional_wickets = expected_additional_wickets * 0.6") == 1
        source = source.replace("expected_additional_wickets = expected_additional_wickets * 0.6",
                                "expected_additional_wickets = expected_additional_wickets * 1.0")
    if no_floor:
        assert source.count("expected_additional_wickets = max(1, min(expected_additional_wickets, 6))") == 1
        source = source.replace("expected_additional_wickets = max(1, min(expected_additional_wickets, 6))",
                                "expected_additional_wickets = max(0, min(expected_additional_wickets, 6))")
    module = types.ModuleType("phase2_" + name)
    sys.modules[module.__name__] = module
    exec(compile(source, "<isolated-phase2-" + name + ">", "exec"), module.__dict__)
    module.source_hash = hashlib.sha256(source.encode()).hexdigest()
    return module


@contextmanager
def no_database_offsets():
    import learning_engine
    old_venue, old_phase = learning_engine.get_venue_adjustment, learning_engine.get_phase_adjustment
    learning_engine.get_venue_adjustment = lambda venue: 0.
    learning_engine.get_phase_adjustment = lambda over, fmt: 0.
    try:
        yield
    finally:
        learning_engine.get_venue_adjustment, learning_engine.get_phase_adjustment = old_venue, old_phase


def bind_priors(module, priors):
    values = {v: {"avg_1st_innings": sum(scores) / len(scores)}
              for v, scores in priors.venues.items()}
    global_avg = sum(m["actual_score"] for m in priors.matches) / len(priors.matches)
    module.VENUE_HISTORICAL_STATS = values
    module.get_venue_stats = lambda venue: values.get(venue, {"avg_1st_innings": global_avg})
    module.get_comprehensive_batting_stats = lambda name: (
        {"sr": 100 * priors.bat[name][0] / priors.bat[name][1]}
        if name in priors.bat and priors.bat[name][1] else None)
    # Empirical priors are keyed by stable ID; MatchState Batsman names use the
    # stable ID too. Unknown style/phase labels are neutral, never future lookups.
    module.get_comprehensive_bowling_stats = lambda name: None
    module.get_player_by_name = lambda name: None
    module.get_batting_phase_modifier = lambda name, ph: 1.
    module.get_bowling_phase_modifier = lambda name, ph: 1.
    original_fielding = module.get_fielding_modifier
    module.get_fielding_modifier = lambda team: original_fielding("")


def predict(module, state, priors):
    priors.assert_as_of(state["as_of"])
    max_overs = state["max_balls"] / 6
    bowlers = [module.Bowler(
        name=name, overs_bowled=s[0] / 6, runs_conceded=s[1], wickets=s[2],
        overs_remaining=max(0, max_overs / 5 - s[0] / 6))
        for name, s in state["bowled"].items()]
    match_state = module.MatchState(
        current_score=state["score"], wickets_fallen=state["wickets"],
        overs_completed=state["balls"] / 6, venue=state["venue"],
        batsmen=[module.Batsman(name=p, runs=state["faced"].get(p, [0, 0])[0],
                               balls_faced=state["faced"].get(p, [0, 0])[1])
                 for p in state["active"] if p],
        bowlers=bowlers, batsmen_to_come=[p for p in state["players"] if p not in state["seen"]],
        match_format=state["format"], innings=1, target=0,
        fielding_team=state["fielding_team"])
    with no_database_offsets():
        result = module.predict_score(match_state)
    return {"score": result.predicted_final_score, "wickets": result.predicted_wickets,
            "low": result.score_range[0], "high": result.score_range[1]}
