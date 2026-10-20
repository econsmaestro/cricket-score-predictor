import csv
import io
import json
import zipfile

import pytest

import backtest
import backtest_data
from backtest_data import FORMATS
from backtest_reports import load_report


@pytest.mark.parametrize("name", list(FORMATS))
def test_real_reports_contain_exactly_100_unique_matches(name):
    report = load_report(name)
    rows = report["results"]
    checkpoints = FORMATS[name]["checkpoints"]
    assert report["match_count"] == 100
    assert report["prediction_count"] == len(rows) == 100 * len(checkpoints)
    assert len({row["match_id"] for row in rows}) == 100
    assert {row["match_format"] for row in rows} == {name}
    for match_id in {row["match_id"] for row in rows}:
        match_rows = [row for row in rows if row["match_id"] == match_id]
        assert sorted(row["checkpoint"] for row in match_rows) == checkpoints
        assert len({row["actual"] for row in match_rows}) == 1
    assert report["metrics"] == json.loads(json.dumps(backtest.compute_metrics(rows)))
    assert "not an out-of-time training holdout" in report["methodology"]


@pytest.mark.parametrize("name", list(FORMATS))
def test_format_specific_api_and_csv(client, name):
    response = client.get(f"/backtest/report/{name}")
    assert response.status_code == 200
    report = response.json
    assert report["format"] == name
    response = client.get(f"/backtest/export.csv?format={name}")
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.data.decode())))
    assert len(rows) == report["prediction_count"]
    assert len({row["match_id"] for row in rows}) == 100
    assert {row["match_format"] for row in rows} == {name}


def test_page_and_availability(client):
    response = client.get("/backtest")
    assert response.status_code == 200
    assert b"Backtesting" in response.data
    status = client.get("/backtest/status").json
    assert {row["format"] for row in status["formats"]} == set(FORMATS)
    assert all(row["match_count"] == 100 and row["available"] for row in status["formats"])
    assert client.get("/backtest/report/invalid").status_code == 400
    assert client.get("/backtest/export.csv?format=invalid").status_code == 400


def test_missing_report_not_faked(client, monkeypatch, tmp_path):
    import backtest_reports
    monkeypatch.setattr(backtest_reports, "REPORT_DIR", tmp_path)
    status = client.get("/backtest/status").json
    assert all(not row["available"] and row["match_count"] == 0 for row in status["formats"])
    assert client.get("/backtest/report/mens_odi").status_code == 404


@pytest.mark.parametrize("name", list(FORMATS))
def test_loader_filters_gender_type_and_shortened_matches(monkeypatch, tmp_path, name):
    config = FORMATS[name]
    overs = [
        {"over": over, "deliveries": [
            {"batter": "A", "bowler": "B", "runs": {"batter": 1, "total": 1}}
            for _ in range(6)
        ]} for over in range(config["overs"])
    ]
    base = {
        "info": {"gender": config["gender"], "match_type": config["type"],
                 "overs": config["overs"], "teams": ["A", "B"], "dates": ["2026-01-01"]},
        "innings": [{"team": "A", "overs": overs},
                    {"team": "B", "overs": [], "target": {"runs": 121, "overs": config["overs"]}}],
    }
    archive = tmp_path / "matches.zip"
    with zipfile.ZipFile(archive, "w") as file:
        file.writestr("valid.json", json.dumps(base))
        for field, value in [("gender", "other"), ("match_type", "Test"), ("overs", 5)]:
            changed = json.loads(json.dumps(base))
            changed["info"][field] = value
            file.writestr(field + ".json", json.dumps(changed))
        rain = json.loads(json.dumps(base))
        rain["info"]["outcome"] = {"method": "D/L"}
        file.writestr("rain.json", json.dumps(rain))
    monkeypatch.setattr(backtest_data, "download_data", lambda **kwargs: archive)
    matches = backtest_data.parse_matches(match_format=name, max_matches=100)
    assert len(matches) == 1
    assert matches[0]["match_id"] == "valid"
    assert matches[0]["actual_final_score"] == config["overs"] * 6
    assert matches[0]["match_format"] == name


def test_checkpoint_has_no_future_deliveries_and_odi_quotas():
    match = {
        "match_format": "womens_odi", "venue": "Test ground",
        "batting_team": "A", "fielding_team": "B", "players": {"A": ["A", "C"]},
        "overs": [
            {"over": 0, "deliveries": [
                {"batter": "A", "bowler": "B", "runs_total": 2, "runs_batter": 0,
                 "extras": {"byes": 2}, "wickets": [{"kind": "run out", "player_out": "A"}]},
                {"batter": "C", "bowler": "B", "runs_total": 1, "runs_batter": 1,
                 "extras": {}, "wickets": []},
            ]},
            {"over": 1, "deliveries": [
                {"batter": "C", "bowler": "B", "runs_total": 6, "runs_batter": 6,
                 "extras": {}, "wickets": []},
            ]},
        ],
    }
    state = backtest.build_state_at_over(match, 1)
    assert state.current_score == 3
    assert state.wickets_fallen == 1
    assert state.match_format == "womens_odi"
    assert state.bowlers[0].runs_conceded == 1
    assert state.bowlers[0].wickets == 0
    assert state.bowlers[0].overs_remaining == pytest.approx(10 - 2 / 6)


def test_backtest_does_not_silently_return_fewer_than_requested(monkeypatch):
    monkeypatch.setattr(backtest_data, "parse_matches", lambda **kwargs: [])
    with pytest.raises(ValueError, match="100 required"):
        backtest.run_backtest(match_format="mens_odi")


def test_metrics_bucket_computation():
    rows = [{
        "error": 10, "abs_error": 10, "in_range": True, "range_width": 40,
        "actual": 150, "checkpoint": 10,
    }]
    metrics = backtest.compute_metrics(rows)
    assert metrics["overall"]["bucket_mae"]["under_160"] == 10
    assert metrics["overall"]["hit_rate"] == 100
