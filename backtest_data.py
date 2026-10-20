"""Download, cache, and parse Cricsheet Men's T20I ball-by-ball data."""
import json
import zipfile
import pickle
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = Path("backtest_cache")
DATA_ZIP = CACHE_DIR / "t20s_male_json.zip"
PARSED_CACHE = CACHE_DIR / "parsed_matches.pkl"
CRICSHEET_URL = "https://cricsheet.org/downloads/t20s_male_json.zip"

MIN_CHECKPOINT_OVER = 16


def download_data(force=False):
    """Download Cricsheet T20I JSON zip if not already cached."""
    CACHE_DIR.mkdir(exist_ok=True)
    if DATA_ZIP.exists() and not force:
        return
    import requests
    logger.info("Downloading Cricsheet T20I data...")
    resp = requests.get(CRICSHEET_URL, stream=True, timeout=180,
                        headers={"User-Agent": "cricket-backtest/1.0"})
    resp.raise_for_status()
    with open(DATA_ZIP, "wb") as f:
        for chunk in resp.iter_content(65536):
            f.write(chunk)
    logger.info("Download complete: %s", DATA_ZIP)


def _parse_innings(innings_data):
    overs = []
    for over_data in innings_data.get("overs", []):
        deliveries = []
        for d in over_data["deliveries"]:
            deliveries.append({
                "batter": d["batter"],
                "bowler": d["bowler"],
                "runs_batter": d["runs"]["batter"],
                "runs_total": d["runs"]["total"],
                "wickets": d.get("wickets", []),
                "extras": d.get("extras", {}),
            })
        overs.append({"over": over_data["over"], "deliveries": deliveries})
    return overs


def parse_matches(force=False):
    """Return list of parsed first-innings match dicts, downloading if needed."""
    if PARSED_CACHE.exists() and not force:
        with open(PARSED_CACHE, "rb") as f:
            return pickle.load(f)

    download_data()
    matches = []

    with zipfile.ZipFile(DATA_ZIP) as zf:
        names = [n for n in zf.namelist() if n.endswith(".json")]
        logger.info("Parsing %d JSON files...", len(names))
        for name in names:
            try:
                with zf.open(name) as f:
                    data = json.load(f)
            except Exception:
                continue

            info = data.get("info", {})
            if info.get("match_type") != "T20":
                continue
            if info.get("gender") != "male":
                continue

            innings_list = data.get("innings", [])
            if not innings_list:
                continue

            first = innings_list[0]
            overs = _parse_innings(first)

            if len(overs) < MIN_CHECKPOINT_OVER:
                continue

            total_wickets = sum(len(d["wickets"]) for o in overs for d in o["deliveries"])
            if len(overs) < 20 and total_wickets < 10:
                continue

            total_runs = sum(d["runs_total"] for o in overs for d in o["deliveries"])
            teams = info.get("teams", [])
            batting_team = first.get("team", "")
            fielding_team = next((t for t in teams if t != batting_team), "")

            matches.append({
                "match_id": name.replace(".json", ""),
                "date": info.get("dates", [""])[0],
                "venue": info.get("venue", ""),
                "batting_team": batting_team,
                "fielding_team": fielding_team,
                "players": info.get("players", {}),
                "overs": overs,
                "actual_final_score": total_runs,
                "actual_wickets": total_wickets,
            })

    matches.sort(key=lambda m: m["date"], reverse=True)
    logger.info("Parsed %d valid matches", len(matches))

    with open(PARSED_CACHE, "wb") as f:
        pickle.dump(matches, f)

    return matches


def get_data_info():
    """Return dict with cache status and match count."""
    if PARSED_CACHE.exists():
        try:
            with open(PARSED_CACHE, "rb") as f:
                matches = pickle.load(f)
            return {"cached": True, "count": len(matches)}
        except Exception:
            pass
    return {"cached": False, "count": 0}
