"""Download, cache, and parse Cricsheet ball-by-ball data for all four formats."""
import json
import zipfile
import pickle
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = Path("backtest_cache")

FORMATS = {
    "mens_t20": {
        "url": "https://cricsheet.org/downloads/t20s_male_json.zip",
        "zip_name": "t20s_male_json.zip",
        "match_type": "T20",
        "gender": "male",
        "max_overs": 20,
        "min_checkpoint_over": 16,
    },
    "womens_t20": {
        "url": "https://cricsheet.org/downloads/t20s_female_json.zip",
        "zip_name": "t20s_female_json.zip",
        "match_type": "T20",
        "gender": "female",
        "max_overs": 20,
        "min_checkpoint_over": 16,
    },
    "mens_odi": {
        "url": "https://cricsheet.org/downloads/odis_male_json.zip",
        "zip_name": "odis_male_json.zip",
        "match_type": "ODI",
        "gender": "male",
        "max_overs": 50,
        "min_checkpoint_over": 45,
    },
    "womens_odi": {
        "url": "https://cricsheet.org/downloads/odis_female_json.zip",
        "zip_name": "odis_female_json.zip",
        "match_type": "ODI",
        "gender": "female",
        "max_overs": 50,
        "min_checkpoint_over": 45,
    },
}


def _zip_path(fmt):
    return CACHE_DIR / FORMATS[fmt]["zip_name"]


def _cache_path(fmt):
    return CACHE_DIR / f"parsed_{fmt}.pkl"


def download_data(fmt, force=False):
    """Download Cricsheet zip for the given format if not already cached."""
    CACHE_DIR.mkdir(exist_ok=True)
    zp = _zip_path(fmt)
    if zp.exists() and not force:
        return
    import requests
    url = FORMATS[fmt]["url"]
    logger.info("Downloading %s data from %s ...", fmt, url)
    resp = requests.get(url, stream=True, timeout=300,
                        headers={"User-Agent": "cricket-backtest/1.0"})
    resp.raise_for_status()
    with open(zp, "wb") as f:
        for chunk in resp.iter_content(65536):
            f.write(chunk)
    logger.info("Download complete: %s", zp)


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


def parse_matches(fmt="mens_t20", force=False):
    """Return list of parsed first-innings match dicts for the given format."""
    cp = _cache_path(fmt)
    if cp.exists() and not force:
        with open(cp, "rb") as f:
            return pickle.load(f)

    download_data(fmt)
    cfg = FORMATS[fmt]
    matches = []

    with zipfile.ZipFile(_zip_path(fmt)) as zf:
        names = [n for n in zf.namelist() if n.endswith(".json")]
        logger.info("Parsing %d JSON files for %s...", len(names), fmt)
        for name in names:
            try:
                with zf.open(name) as f:
                    data = json.load(f)
            except Exception:
                continue

            info = data.get("info", {})
            if info.get("match_type") != cfg["match_type"]:
                continue
            if info.get("gender") != cfg["gender"]:
                continue

            innings_list = data.get("innings", [])
            if not innings_list:
                continue

            first = innings_list[0]
            overs = _parse_innings(first)

            if len(overs) < cfg["min_checkpoint_over"]:
                continue

            total_wickets = sum(len(d["wickets"]) for o in overs for d in o["deliveries"])
            if len(overs) < cfg["max_overs"] and total_wickets < 10:
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
                "format": fmt,
            })

    matches.sort(key=lambda m: m["date"], reverse=True)
    logger.info("Parsed %d valid matches for %s", len(matches), fmt)

    with open(cp, "wb") as f:
        pickle.dump(matches, f)

    return matches


def get_data_info():
    """Return cache status for all formats."""
    result = {}
    for fmt in FORMATS:
        cp = _cache_path(fmt)
        if cp.exists():
            try:
                with open(cp, "rb") as f:
                    m = pickle.load(f)
                result[fmt] = {"cached": True, "count": len(m)}
                continue
            except Exception:
                pass
        result[fmt] = {"cached": False, "count": 0}
    return result
