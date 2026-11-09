"""Chase eligibility, timestamp boundaries, active pairs and public report wiring."""
import copy
import csv
import io
import json
import zipfile

import pytest

from backtest_chases import chase_matches, chase_state
from backtest_data import FORMATS
from backtest_reports import load_report


def delivery(batter="A", non_striker="C", runs=1, wickets=None):
    return {"batter": batter, "non_striker": non_striker, "bowler": "B",
            "runs": {"batter": runs, "total": runs}, "wickets": wickets or []}


def fixture():
    return {
        "info": {"gender": "male", "match_type": "T20", "overs": 20,
                 "teams": ["X", "Y"], "players": {"Y": ["A", "C", "D"]},
                 "dates": ["2026-01-01"], "outcome": {"winner": "Y"}},
        "innings": [
            {"team": "X", "overs": [
                {"over": o, "deliveries": [delivery() for _ in range(6)]} for o in range(20)
            ]},
            {"team": "Y", "target": {"runs": 121, "overs": 20},
             "overs": [{"over": 0, "deliveries": [delivery(runs=121)]}]},
        ],
    }


def test_short_chase_kept_and_invalid_fixtures_excluded(tmp_path):
    valid = fixture()
    path = tmp_path / "matches.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("valid.json", json.dumps(valid))
        for change in ["target", "dls", "incomplete", "format", "super_over"]:
            bad = copy.deepcopy(valid)
            if change == "target":
                bad["innings"][1]["target"]["runs"] = 150
            elif change == "dls":
                bad["info"]["outcome"]["method"] = "D/L"
            elif change == "incomplete":
                bad["innings"][1]["overs"][0]["deliveries"][0]["runs"] = {"batter": 1, "total": 1}
            elif change == "format":
                bad["info"]["gender"] = "female"
            else:
                bad["innings"][1]["super_over"] = True
            zf.writestr(change + ".json", json.dumps(bad))
    matches = chase_matches("mens_t20", path, limit=1)
    assert matches[0]["match_id"] == "valid"
    assert matches[0]["legal_balls"] == 1
    assert matches[0]["target"] == 121
    with pytest.raises(ValueError, match="only 1 eligible"):
        chase_matches("mens_t20", path, limit=2)


def test_early_allout_kept(tmp_path):
    data = fixture()
    data["innings"][1]["overs"][0]["deliveries"] = [
        delivery(runs=0, wickets=[{"kind": "bowled", "player_out": str(i)}])
        for i in range(10)
    ]
    path = tmp_path / "allout.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("collapse.json", json.dumps(data))
    matches = chase_matches("mens_t20", path, limit=1)
    assert matches[0]["actual_wickets"] == 10
    assert not matches[0]["chase_won"]


def test_state_has_observed_nonstriker_and_no_future_order():
    from backtest_data import _parse_innings
    raw = [
        {"over": 0, "deliveries": [delivery(runs=2) for _ in range(6)]},
        {"over": 1, "deliveries": [delivery(batter="D", runs=6)]},
    ]
    match = {"match_format": "mens_t20", "venue": "Test", "batting_team": "Y",
             "fielding_team": "X", "players": {"Y": ["A", "C", "D"]},
             "overs": _parse_innings({"overs": raw}), "raw_overs": raw, "target": 121}
    state = chase_state(match, 1)
    assert state.innings == 2 and state.target == 121
    assert state.current_score == 12
    assert [(b.name, b.runs, b.balls_faced) for b in state.batsmen] == [("A", 12, 6), ("C", 0, 0)]
    assert state.batsmen_to_come == []
    assert chase_state(match, 0).batsmen == []


@pytest.mark.parametrize("fmt", list(FORMATS))
def test_real_chase_reports_and_export(client, fmt):
    report = load_report(fmt, innings=2)
    rows = report["results"]
    assert len({r["match_id"] for r in rows}) == 100
    assert len([r for r in rows if r["checkpoint"] == 0]) == 100
    ends = {m["match_id"]: m["legal_balls"] for m in report["match_manifest"]}
    assert all(r["innings"] == 2 and r["checkpoint"] * 6 < ends[r["match_id"]] for r in rows)
    assert all(r["score_at_cp"] < r["target"] and r["wickets_at_cp"] < 10 for r in rows)
    assert all(r["wicket_error"] == r["predicted_wickets"] - r["actual_wickets"] for r in rows)
    response = client.get(f"/backtest/report/{fmt}?innings=2")
    assert response.status_code == 200
    assert response.json["innings"] == 2
    export = client.get(f"/backtest/export.csv?format={fmt}&innings=2")
    exported = list(csv.DictReader(io.StringIO(export.data.decode())))
    assert len(exported) == len(rows)
    assert {r["innings"] for r in exported} == {"2"}


def test_innings_query_validation_and_status(client):
    assert all(r["available"] for r in client.get("/backtest/status?innings=2").json["formats"])
    for path in ["/backtest/status", "/backtest/report/mens_odi", "/backtest/export.csv"]:
        assert client.get(path + "?innings=3").status_code == 400
    assert b'inningsSelect' in client.get("/backtest").data
