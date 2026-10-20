"""Download and parse format-separated Cricsheet international match archives."""
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
FORMATS = {
    "mens_t20": {"label": "Men's T20", "archive": "t20s_male_json.zip", "gender": "male", "type": "T20", "overs": 20, "checkpoints": [6, 10, 11, 15, 16]},
    "womens_t20": {"label": "Women's T20", "archive": "t20s_female_json.zip", "gender": "female", "type": "T20", "overs": 20, "checkpoints": [6, 10, 11, 15, 16]},
    "mens_odi": {"label": "Men's ODI", "archive": "odis_male_json.zip", "gender": "male", "type": "ODI", "overs": 50, "checkpoints": [10, 20, 30, 40]},
    "womens_odi": {"label": "Women's ODI", "archive": "odis_female_json.zip", "gender": "female", "type": "ODI", "overs": 50, "checkpoints": [10, 20, 30, 40]},
}


def format_config(match_format):
    if match_format not in FORMATS:
        raise ValueError("Choose mens_odi, mens_t20, womens_odi or womens_t20")
    return FORMATS[match_format]


def counts_as_team_wicket(wicket):
    return wicket.get("kind") not in {"retired hurt", "retired not out"}


def download_data(force=False, match_format="mens_t20"):
    """Download Cricsheet T20I JSON zip if not already cached."""
    CACHE_DIR.mkdir(exist_ok=True)
    config = format_config(match_format)
    destination = CACHE_DIR / config["archive"]
    if destination.exists() and not force:
        return destination
    import requests
    logger.info("Downloading Cricsheet T20I data...")
    resp = requests.get("https://cricsheet.org/downloads/" + config["archive"], stream=True, timeout=180,
                        headers={"User-Agent": "cricket-backtest/1.0"})
    resp.raise_for_status()
    temporary = destination.with_suffix(".zip.part")
    with open(temporary, "wb") as f:
        for chunk in resp.iter_content(65536):
            f.write(chunk)
    temporary.replace(destination)
    logger.info("Download complete: %s", destination)
    return destination


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


def parse_matches(force=False, match_format="mens_t20", max_matches=None):
    """Return list of parsed first-innings match dicts, downloading if needed."""
    config = format_config(match_format)
    archive = download_data(force=force, match_format=match_format)
    matches = []

    with zipfile.ZipFile(archive) as zf:
        names = [n for n in zf.namelist() if n.endswith(".json")]
        logger.info("Parsing %d JSON files...", len(names))
        for name in names:
            try:
                with zf.open(name) as f:
                    data = json.load(f)
            except Exception:
                continue

            info = data.get("info", {})
            if info.get("match_type") != config["type"]:
                continue
            if info.get("gender") != config["gender"]:
                continue
            if (info.get("overs") != config["overs"] or info.get("balls_per_over", 6) != 6
                    or info.get("outcome", {}).get("result") in {"no result", "abandoned"}
                    or info.get("outcome", {}).get("method")
                    or any(
                        innings.get("target", {}).get("overs", config["overs"]) != config["overs"]
                        for innings in data.get("innings", [])
                    )):
                continue

            innings_list = data.get("innings", [])
            if not innings_list:
                continue

            first = innings_list[0]
            overs = _parse_innings(first)

            if len(overs) <= max(config["checkpoints"]):
                continue

            total_wickets = sum(
                counts_as_team_wicket(w) for o in overs for d in o["deliveries"]
                for w in d["wickets"]
            )
            legal_balls = sum(
                not ("wides" in d["extras"] or "noballs" in d["extras"])
                for o in overs for d in o["deliveries"]
            )
            if legal_balls < config["overs"] * 6 and total_wickets < 10:
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
                "match_format": match_format,
            })
            # Retain only the most recent requested fixtures, not every
            # delivery from the entire archive in memory.
            if max_matches is not None and len(matches) > max_matches:
                matches.sort(key=lambda m: (m["date"], m["match_id"]), reverse=True)
                matches.pop()

    matches.sort(key=lambda m: (m["date"], m["match_id"]), reverse=True)
    logger.info("Parsed %d valid matches", len(matches))

    return matches[:max_matches] if max_matches is not None else matches


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
