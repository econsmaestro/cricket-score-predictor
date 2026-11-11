"""Historical rating keys, without changing live autofill or saved reports."""
import pytest
from backtest import build_state_at_over
from backtest_chases import chase_state
from backtest_data import fielding_rating_key
from prediction import get_fielding_modifier


@pytest.mark.parametrize("fmt,raw,expected", [
    ("womens_odi", "India", "India W"),
    ("womens_t20", "IND", "India W"),
    ("womens_odi", "India Women", "India W"),
    ("womens_t20", "India W", "India W"),
    ("mens_odi", "India", "India"),
    ("mens_t20", "IND", "India"),
    ("womens_odi", "Unlisted XI", "Unlisted XI"),
])
def test_historical_fielding_key_in_both_innings(fmt, raw, expected):
    assert fielding_rating_key(raw, fmt) == expected
    match = {"overs": [], "raw_overs": [], "players": {}, "batting_team": "Other",
             "fielding_team": raw, "match_format": fmt, "venue": "Unknown", "target": 150}
    assert build_state_at_over(match, 0).fielding_team == expected
    assert chase_state(match, 0).fielding_team == expected
    if raw == "Unlisted XI":
        assert get_fielding_modifier(expected)["efficiency"] == 0.85
