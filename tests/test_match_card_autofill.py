"""Regression checks for selecting a fixture directly from the home-page cards."""
import shutil
import subprocess
from pathlib import Path

import pytest
from unittest.mock import Mock, patch


def test_match_card_autofill_handlers():
    if not shutil.which("node"):
        pytest.skip("Node is required to exercise the browser JavaScript handlers")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["node", "tests/match_card_autofill.cjs"],
        cwd=root, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("title,expected", [
    ("New Zealand vs India, 1st ODI, Live Cricket Score", "mens_odi"),
    ("India Women vs England Women, 2nd ODI, Live Cricket Score", "womens_odi"),
    ("New Zealand vs India, 1st T20I, Live Cricket Score", "mens_t20"),
    ("India Women vs England Women, 2nd T20I, Live Cricket Score", "womens_t20"),
])
def test_numbered_international_format_detection(title, expected):
    from live_match_scraper import get_cricbuzz_match_details

    response = Mock(status_code=200, text=f"<html><head><title>{title}</title></head><body></body></html>")
    with patch("live_match_scraper.requests.get", return_value=response):
        match = get_cricbuzz_match_details("123")
    assert match["format"] == expected
