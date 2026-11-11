"""Frozen production outputs captured before adding effect-strength scaling."""
from dataclasses import asdict
import hashlib
import json

import pytest
import prediction


def fixed_states():
    for fmt, score, wickets, over, innings, target in [
        ("mens_t20", 45, 1, 6.0, 1, 0),
        ("womens_t20", 90, 4, 15.0, 2, 150),
        ("mens_odi", 120, 3, 25.0, 1, 0),
        ("womens_odi", 185, 7, 42.0, 2, 240),
    ]:
        for team in ("India", "Australia W", "Bangladesh", "Unlisted XI"):
            yield prediction.MatchState(
                current_score=score, wickets_fallen=wickets, overs_completed=over,
                venue="Wankhede Stadium, Mumbai", batsmen=[
                    prediction.Batsman(name="Fixture Batter A", runs=20, balls_faced=18),
                    prediction.Batsman(name="Fixture Batter B", runs=12, balls_faced=14),
                ], bowlers=[], match_format=fmt, fielding_team=team,
                innings=innings, target=target,
            )


def output_digest(result):
    return hashlib.sha256(json.dumps(asdict(result), sort_keys=True).encode()).hexdigest()


# Captured from the unchanged engine before the strength parameter existed.
EXPECTED = [
    "4a069dfddeeac0a43791b7861898f37a249bfa453c943383c5d8b8e931b585de",  # 140/5
    "29a870d0a6ef5299d18a8d536feefe9d6060981da710927a5c3b044ad40eb836",  # 140/5
    "9f7b6fd842a8cca5c40e81278a05a75e5cba42ff07d00c14a2abbdb93ffab4e5",  # 162/4
    "46c5d32f45865333ce5230ab11f6b6873267d33ad27ca03fdebe0ac80704c4d6",  # 151/5
    "bc90cdee28cd73abaedcbcfce490648062bf6ad647361ecba087e68df339202a",  # 115/5
    "8d2f79a5c78ee19b9250fe83568128f8bb5b07d079f67d16051e9e52e36b4374",  # 115/5
    "ee986e95f1bb0214c900d48fbcecd6e8284f3fc47f94d97c2855bde9b6b0bde5",  # 121/5
    "28b81025982e50b51b41f10b7e2a8702aa4b57b75fabec5534f381eff1a74175",  # 118/5
    "072dc805c1a312631a9d164ab37380f3d1ae590e5c3fed071ad8b7eb5412858d",  # 242/5
    "65ba037e73becda26ded3377700e7a5d2c9efab17ff35879e3185909676f1161",  # 242/5
    "f11a72a27114679dc85b5af6f98944160d8ecf641a50d4311463a3c995727f2d",  # 270/5
    "e023f4fc4726d12a65a8f57039190691a80c606aa3c9156262a233857a0b771d",  # 256/5
    "d65c8d099e36d37e51ac55634b7cddbeb4d058922dcf5c2a9ff951d3f331240c",  # 206/9
    "1cba63ab4f12a7f76f13a37a27e75d3faebb1d99ec0a2a18f493517fe8e23267",  # 206/9
    "acda46bf202cb532567dfa13a52e5bde0094785bd0c1729e7a44ea102493c4d2",  # 206/9
    "75053cdc07f05691bf516d606fb2ca15d3db3e70ba63ec3302c7c2d357cd42b6",  # 206/9
]


def test_strength_one_matches_frozen_production_outputs(monkeypatch):
    monkeypatch.setattr(prediction, "FIELDING_EFFECT_STRENGTH", 1.0)
    actual = [output_digest(prediction.predict_score(state)) for state in fixed_states()]
    assert actual == EXPECTED


@pytest.mark.parametrize("team", ["India", "Australia W", "Bangladesh", "Uganda", "Unlisted XI"])
def test_zero_strength_is_neutral(monkeypatch, team):
    monkeypatch.setattr(prediction, "FIELDING_EFFECT_STRENGTH", 0.0)
    modifiers = prediction.get_fielding_modifier(team)
    for key in ("run_modifier", "wicket_modifier", "boundary_modifier"):
        assert modifiers[key] == 1.0


@pytest.mark.parametrize("team", list(prediction.TEAM_FIELDING_EFFICIENCY) + ["Unlisted XI"])
def test_strength_one_preserves_every_raw_modifier(monkeypatch, team):
    monkeypatch.setattr(prediction, "FIELDING_EFFECT_STRENGTH", 1.0)
    value = prediction.TEAM_FIELDING_EFFICIENCY.get(team, 0.85)
    modifiers = prediction.get_fielding_modifier(team)
    assert modifiers["run_modifier"] == max(0.9, min(1.15, 1 + (0.15 - (1 - value)) * -2))
    assert modifiers["wicket_modifier"] == max(0.7, min(1.3, 1 + (value - 0.85) * 1.5))
    assert modifiers["boundary_modifier"] == max(0.85, min(1.15, 1 - (value - 0.85) * 0.8))


