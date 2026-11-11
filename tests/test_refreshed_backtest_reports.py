"""Committed first-innings reports and downloadable CSVs must stay in sync."""
import csv
import io
import json
from pathlib import Path

import pytest

import prediction
from backtest import compute_metrics, generate_summary
from backtest_data import FORMATS
from backtest_reports import load_report
from research.refresh_first_innings_reports import CSV_FIELDS, NOTE


@pytest.mark.parametrize("fmt", FORMATS)
def test_refreshed_reports_match_csv_and_served_download(client, fmt):
    report = load_report(fmt)
    assert report["methodology"].endswith(" " + NOTE)
    assert report["methodology"].count(NOTE) == 1
    assert report["metrics"] == json.loads(json.dumps(compute_metrics(report["results"])))
    assert report["summary"] == generate_summary(report["metrics"])
    assert prediction.FIELDING_EFFECT_STRENGTH == 1.0
    paths = list(Path("attached_assets").glob(f"backtest_{fmt}_100_matches_*.csv"))
    assert len(paths) == 1
    with paths[0].open(newline="") as stream:
        stored = list(csv.DictReader(stream))
    response = client.get(f"/backtest/export.csv?format={fmt}&innings=1")
    assert response.status_code == 200
    served = list(csv.DictReader(io.StringIO(response.data.decode())))
    expected = [
        {key: str(row[key]) if key in row else "" for key in CSV_FIELDS}
        for row in report["results"]
    ]
    assert stored == served == expected
    response = client.get(f"/backtest/report/{fmt}?innings=1")
    assert response.status_code == 200
    assert response.get_json() == report
