"""Never confuse historical over separators with current batting state."""
import copy
import json
from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup

from live_batting import current_batting_snapshot, disruption_notice
from live_match_scraper import extract_batsmen, get_cricbuzz_match_details


def mini():
    return {
        "inningsId": 1, "batTeam": {"teamId": 13, "teamScore": 112, "teamWkts": 6},
        "overs": 35, "responseLastUpdated": 1794030000,
        "batsmanStriker": {"id": 1, "name": "Kyle Jamieson", "runs": 0, "balls": 0},
        "batsmanNonStriker": {"id": 2, "name": "Mitchell Santner", "runs": 25, "balls": 33},
        "matchScoreDetails": {"matchId": 161256, "state": "In Progress",
                             "inningsScoreList": [{"inningsId": 1, "batTeamId": 13,
                                                   "score": 112, "wickets": 6, "overs": 35}]},
    }


def html(snapshot, title="NZ vs IND, 2nd ODI", extra=None):
    payload = json.dumps({
        "commentary": {"batStrikerObj": {"playerName": "Daryl Mitchell", "playerScore": "55(104)"},
                       "batNonStrikerObj": {"playerName": "Mitchell Santner", "playerScore": "25(33)"}},
        "miniscore": snapshot, **(extra or {}),
    })
    return (f"<title>{title}</title><div id='miniscore-branding-container'>NZ 111/5 (34.2)</div>"
            f"<script>self.__next_f.push({json.dumps([1, payload])})</script>")


def parse(snapshot):
    return current_batting_snapshot(BeautifulSoup(html(snapshot), "html.parser"), "161256")


@pytest.mark.parametrize("title", [
    "NZ vs IND, 2nd ODI", "NZ Women vs IND Women, 2nd ODI",
    "NZ vs IND, T20I", "NZ Women vs IND Women, T20I",
    "A vs B, IPL", "A vs B, Women's Big Bash League",
])
def test_autofill_uses_current_pair_and_same_score_snapshot(title):
    page = html(mini(), title)

    def response(url, **kwargs):
        return Mock(status_code=404, text="") if ("scorecard" in url or "squads" in url) else Mock(status_code=200, text=page)

    with patch("live_match_scraper.requests.get", side_effect=response):
        result = get_cricbuzz_match_details("161256")
    assert [b["name"] for b in result["batsmen"]] == ["Kyle Jamieson", "Mitchell Santner"]
    assert result["batsmen"][0]["runs"] == result["batsmen"][0]["balls"] == 0
    assert (result["current_score"], result["wickets"], result["overs"]) == (112, 6, 35)
    assert result["batsmen_verified"] is True
    assert "batsmen" in result["loaded_fields"]


def test_historical_over_objects_alone_are_never_used():
    page = html(None)
    with patch("live_match_scraper.requests.get", return_value=Mock(status_code=200, text=page)):
        result = get_cricbuzz_match_details("161256")
    assert result["batsmen"] == []
    assert result["partial"] is True
    assert "batsmen" not in result["loaded_fields"]


@pytest.mark.parametrize("field,value", [("overs", 34.2), ("wickets", 5), ("score", 111)])
def test_score_record_must_agree(field, value):
    s = mini()
    s["matchScoreDetails"]["inningsScoreList"][0][field] = value
    assert parse(s) is None


def test_wrong_match_and_innings_rejected():
    s = mini()
    s["matchScoreDetails"]["matchId"] = 999
    assert parse(s) is None
    s = mini()
    s["inningsId"] = 2
    assert parse(s) is None


@pytest.mark.parametrize("change", ["dismissed", "duplicate", "missing", "negative", "excess"])
def test_unreliable_pair_withheld(change):
    s = mini()
    if change == "dismissed":
        s["lastWicket"] = "Kyle Jamieson  c Rahul b Brar 0(1)"
    elif change == "duplicate":
        s["batsmanNonStriker"]["id"] = 1
    elif change == "missing":
        del s["batsmanStriker"]
    elif change == "negative":
        s["batsmanStriker"]["balls"] = -1
    else:
        s["batsmanStriker"]["runs"] = 120
    assert parse(s)["batsmen"] == []
    assert not parse(s)["batsmen_verified"]


@pytest.mark.parametrize("state", ["Complete", "Innings Break", "Stumps"])
def test_non_live_states_do_not_supply_active_batters(state):
    s = mini()
    s["matchScoreDetails"]["state"] = state
    assert parse(s)["batsmen"] == []


def test_all_out_withholds_old_pair():
    s = mini()
    s["batTeam"]["teamWkts"] = 10
    s["matchScoreDetails"]["inningsScoreList"][0]["wickets"] = 10
    assert parse(s)["batsmen"] == []


def test_ambiguous_snapshots_rejected():
    other = copy.deepcopy(mini())
    other["batsmanStriker"]["balls"] = 1
    page = html(mini(), extra={"other": {"miniscore": other}})
    assert current_batting_snapshot(BeautifulSoup(page, "html.parser"), "161256") is None


def test_identical_ssr_and_hydration_state_with_different_fetch_times():
    other = copy.deepcopy(mini())
    other["responseLastUpdated"] += 1
    page = html(mini(), extra={"other": {"miniscore": other}})
    result = current_batting_snapshot(BeautifulSoup(page, "html.parser"), "161256")
    assert result["batsmen_verified"]
    assert result["batting_snapshot_timestamp"] == other["responseLastUpdated"]


def test_chase_uses_its_own_active_pair_and_target():
    s = mini()
    s["inningsId"] = 2
    s["matchScoreDetails"]["inningsScoreList"][0]["inningsId"] = 2
    s["target"] = 200
    result = parse(s)
    assert result["innings"] == 2
    assert result["target"] == 200
    assert result["batsmen_verified"]


@pytest.mark.parametrize("innings", [1, 2])
def test_rain_interruption_retains_verified_current_pair(innings):
    s = mini()
    s["inningsId"] = innings
    s["matchScoreDetails"]["inningsScoreList"][0]["inningsId"] = innings
    s["matchScoreDetails"]["state"] = "Rain"
    s["batsmanStriker"].update(name="KL Rahul", id=8733, runs=26, balls=38)
    s["batsmanNonStriker"].update(name="Auqib Nabi", id=14179, runs=1, balls=1)
    if innings == 2:
        s["target"] = 135
    result = parse(s)
    assert result["batsmen_verified"]
    assert [p["name"] for p in result["batsmen"]] == ["KL Rahul", "Auqib Nabi"]
    assert result["innings"] == innings
    assert result["target"] == (135 if innings == 2 else 0)
    assert result["game_disrupted"]
    assert result["disruption_reason"] == "Rain"


@pytest.mark.parametrize("state,status,expected,reason", [
    ("Rain", "Rain stops play - India need 22 runs", True, "Rain stops play - India need 22 runs"),
    ("Delayed", "Wet outfield delays start", True, "Wet outfield delays start"),
    ("Suspended", "", True, ""),
    ("In Progress", "Play suspended due to bad light", True, "Play suspended due to bad light"),
    ("In Progress", "India need 22 runs", False, ""),
    ("Innings Break", "Innings break", False, ""),
    ("Complete", "India won by 3 wickets", False, ""),
])
def test_provider_disruption_notices(state, status, expected, reason):
    assert disruption_notice({"status": status, "matchScoreDetails": {"state": state}}) == {
        "game_disrupted": expected, "disruption_reason": reason,
    }


def test_disruption_reason_uses_custom_status_when_available():
    assert disruption_notice({"matchScoreDetails": {
        "state": "Delayed", "customStatus": "Start delayed due to wet outfield",
    }})["disruption_reason"] == "Start delayed due to wet outfield"


@pytest.mark.parametrize("invalid", ["dismissed", "all_out", "mismatched_score"])
def test_rain_does_not_bypass_batting_validation(invalid):
    s = mini()
    s["matchScoreDetails"]["state"] = "Rain"
    if invalid == "dismissed":
        s["lastWicket"] = "Kyle Jamieson c Rahul b Brar 0(1)"
    elif invalid == "all_out":
        s["batTeam"]["teamWkts"] = 10
        s["matchScoreDetails"]["inningsScoreList"][0]["wickets"] = 10
    else:
        s["matchScoreDetails"]["inningsScoreList"][0]["score"] += 1
    result = parse(s)
    assert result is None or not result["batsmen_verified"]


def test_generic_scraper_does_not_guess_from_commentary_or_stars():
    soup = BeautifulSoup("<article>Daryl Mitchell 55 (104) Santner 25 (33)</article>"
                         "<table><tr><td>Daryl Mitchell*</td><td>c Rahul b Brar</td>"
                         "<td>55</td><td>104</td></tr></table>", "html.parser")
    assert extract_batsmen(soup) == []


def test_generic_zero_runs_parsed_by_column():
    table = ("<table><tr><td>Player One</td><td>not out</td><td>0</td><td>3</td></tr>"
             "<tr><td>Player Two</td><td>batting</td><td>5</td><td>6</td></tr></table>")
    assert extract_batsmen(BeautifulSoup(table, "html.parser"))[0] == {
        "name": "Player One", "runs": 0, "balls": 3,
    }
    assert extract_batsmen(BeautifulSoup(table + table, "html.parser")) == []
