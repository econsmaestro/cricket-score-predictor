"""Chase state must come from the selected match, not page-wide commentary."""
from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup

from live_match_scraper import extract_cricbuzz_innings_state, get_cricbuzz_match_details


def state(header, outside="", overs=50):
    soup = BeautifulSoup(
        f'<div id="miniscore-branding-container">{header}</div><aside>{outside}</aside>',
        "html.parser",
    )
    return extract_cricbuzz_innings_state(soup, overs)


@pytest.mark.parametrize("outside", [
    "They could set a target 270 in the 2nd innings.",
    "AUS 269/8 (50) ENG 116/7 (29) England need 154 runs.",
    "Last match India won by 6 wickets. CRR 4.0 REQ 8.0",
    "Chasing 270. Require 154 runs. Trail by 100.",
])
def test_first_innings_ignores_other_match_and_commentary(outside):
    result = state("NZ 116 - 7 (29) CRR: 4.0 India opt to bowl", outside)
    assert result == {
        "innings": 1, "target": 0, "current_score": 116, "wickets": 7, "overs": 29.0,
    }


@pytest.mark.parametrize("overs,score", [(20, "19.5"), (50, "49.5")])
def test_repeated_mobile_desktop_scores_are_not_two_innings(overs, score):
    result = state(f"NZ 269/7 ({score}) NZ 269/7 ({score})", overs=overs)
    assert result["innings"] == 1
    assert result["target"] == 0


@pytest.mark.parametrize("overs", [20, 50])
def test_target_requires_complete_first_innings_and_distinct_team(overs):
    result = state(f"NZ 269/7 ({overs}) IND 0/0 (0)", overs=overs)
    assert result["innings"] == 2
    assert result["target"] == 270
    assert result["current_score"] == 0


def test_all_out_first_innings_establishes_chase():
    result = state("NZ 269 (43.3) IND 10/0 (1.2)")
    assert result["innings"] == 2
    assert result["target"] == 270
    assert result["overs"] == 1.2


def test_odi_at_29_overs_is_not_complete():
    result = state("NZ 269/7 (29) IND 10/0 (1)")
    assert result["innings"] == 1
    assert result["target"] == 0


@pytest.mark.parametrize("status,expected", [
    ("Target: 270", 270),
    ("DLS revised target 201", 201),
    ("India need 154 runs in 21 overs", 270),
    ("India require 154 more runs", 270),
])
def test_official_scoreboard_chase_and_revised_targets(status, expected):
    result = state(f"IND 116/7 (29) {status}")
    assert result["innings"] == 2
    assert result["target"] == expected


def test_unknown_layout_does_not_guess_from_commentary():
    soup = BeautifulSoup("<article>Target: 270. NZ need 154 runs.</article>", "html.parser")
    assert extract_cricbuzz_innings_state(soup, 50) == {"innings": 1, "target": 0}


@pytest.mark.parametrize("title", [
    "New Zealand vs India, 1st ODI",
    "New Zealand Women vs India Women, 1st ODI",
    "New Zealand vs India, 1st T20I",
    "New Zealand Women vs India Women, 1st T20I",
])
def test_full_scraper_does_not_take_target_270_from_commentary(title):
    html = f"""
      <title>{title}</title>
      <div id="miniscore-branding-container">NZ 116 - 7 (15) India opt to bowl</div>
      <article>Another game: AUS 269/7 (50) ENG 116/7 (29).
      A target 270 would be competitive. 2nd innings. England need 154 runs.</article>
    """
    def response(url, **kwargs):
        if "scorecard" in url or "squads" in url:
            return Mock(status_code=404, text="")
        return Mock(status_code=200, text=html)

    with patch("live_match_scraper.requests.get", side_effect=response):
        match = get_cricbuzz_match_details("1")
    assert match["innings"] == 1
    assert match["target"] == 0
    assert match["current_score"] == 116
    assert match["overs"] == 15
    assert "target" not in match["loaded_fields"]
