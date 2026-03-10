"""
CricketData.org API integration for live player statistics.
Free tier: 100,000 requests/hour
Documentation: https://cricketdata.org/
"""

import os
import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from functools import lru_cache

logger = logging.getLogger(__name__)

CRICKET_API_KEY = os.environ.get("CRICKET_API_KEY")
BASE_URL = "https://api.cricketdata.org/v1"

stats_cache = {}
CACHE_DURATION = timedelta(hours=6)
DB_CACHE_HOURS = 24  # Database cache lasts 24 hours

def is_api_configured() -> bool:
    return bool(CRICKET_API_KEY)

def _get_db_cache(cache_key: str) -> Optional[dict]:
    """Try to get from database cache"""
    try:
        from models import PlayerStatsCache
        return PlayerStatsCache.get_cached(cache_key)
    except Exception as e:
        logger.debug(f"DB cache read failed: {e}")
        return None

def _set_db_cache(cache_key: str, player_name: str, cache_type: str, data, hours: int = DB_CACHE_HOURS):
    """Store in database cache"""
    try:
        from models import PlayerStatsCache
        PlayerStatsCache.set_cached(cache_key, player_name, cache_type, data, hours)
    except Exception as e:
        logger.debug(f"DB cache write failed: {e}")

def _make_request(endpoint: str, params: Optional[dict] = None) -> Optional[dict]:
    if not CRICKET_API_KEY:
        logger.warning("Cricket API key not configured")
        return None
    
    headers = {"apikey": CRICKET_API_KEY}
    url = f"{BASE_URL}/{endpoint}"
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            logger.error("Invalid Cricket API key")
        elif response.status_code == 429:
            logger.warning("Cricket API rate limit exceeded")
        else:
            logger.error(f"Cricket API error: {response.status_code}")
        return None
    except requests.RequestException as e:
        logger.error(f"Cricket API request failed: {e}")
        return None

def search_players(query: str, limit: int = 20) -> List[Dict]:
    cache_key = f"search_{query.lower()}"
    
    if cache_key in stats_cache:
        cached_data, cached_time = stats_cache[cache_key]
        if datetime.now() - cached_time < CACHE_DURATION:
            logger.debug(f"Memory cache hit for search: {query}")
            return cached_data
    
    db_cached = _get_db_cache(cache_key)
    if db_cached:
        logger.debug(f"DB cache hit for search: {query}")
        stats_cache[cache_key] = (db_cached, datetime.now())
        return db_cached
    
    data = _make_request("players", {"search": query})
    if not data or "data" not in data:
        return []
    
    players = []
    for player in data.get("data", [])[:limit]:
        players.append({
            "id": player.get("id"),
            "name": player.get("name"),
            "country": player.get("country"),
            "role": player.get("role", "Player"),
            "dateOfBirth": player.get("dateOfBirth"),
            "source": "cricketdata"
        })
    
    stats_cache[cache_key] = (players, datetime.now())
    _set_db_cache(cache_key, query, "search", players)
    return players

def get_player_info(player_id: str) -> Optional[Dict]:
    cache_key = f"player_info_{player_id}"
    
    if cache_key in stats_cache:
        cached_data, cached_time = stats_cache[cache_key]
        if datetime.now() - cached_time < CACHE_DURATION:
            logger.debug(f"Memory cache hit for player info: {player_id}")
            return cached_data
    
    db_cached = _get_db_cache(cache_key)
    if db_cached:
        logger.debug(f"DB cache hit for player info: {player_id}")
        stats_cache[cache_key] = (db_cached, datetime.now())
        return db_cached
    
    data = _make_request(f"players_info", {"id": player_id})
    if not data or "data" not in data:
        return None
    
    player_info = data.get("data")
    stats_cache[cache_key] = (player_info, datetime.now())
    _set_db_cache(cache_key, str(player_id), "player_info", player_info)
    return player_info

def get_current_matches() -> List[Dict]:
    cache_key = "current_matches"
    if cache_key in stats_cache:
        cached_data, cached_time = stats_cache[cache_key]
        if datetime.now() - cached_time < timedelta(minutes=2):
            return cached_data
    
    data = _make_request("currentMatches")
    if not data or "data" not in data:
        return []
    
    matches = []
    for match in data.get("data", []):
        match_type = match.get("matchType", "").upper()
        if match_type in ["T20", "ODI", "T20I"]:
            matches.append({
                "id": match.get("id"),
                "name": match.get("name"),
                "matchType": match_type,
                "status": match.get("status"),
                "venue": match.get("venue"),
                "teams": match.get("teams", []),
                "score": match.get("score", []),
                "date": match.get("date")
            })
    
    stats_cache[cache_key] = (matches, datetime.now())
    return matches

def get_match_scorecard(match_id: str) -> Optional[Dict]:
    data = _make_request("match_scorecard", {"id": match_id})
    if not data or "data" not in data:
        return None
    return data.get("data")

def get_player_batting_stats(player_name: str) -> Optional[Dict]:
    cache_key = f"batting_{player_name.lower()}"
    
    if cache_key in stats_cache:
        cached_data, cached_time = stats_cache[cache_key]
        if datetime.now() - cached_time < CACHE_DURATION:
            logger.debug(f"Memory cache hit for {player_name} batting stats")
            return cached_data
    
    db_cached = _get_db_cache(cache_key)
    if db_cached:
        logger.debug(f"DB cache hit for {player_name} batting stats")
        stats_cache[cache_key] = (db_cached, datetime.now())
        return db_cached
    
    players = search_players(player_name, limit=5)
    if not players:
        return None
    
    exact_match = None
    for p in players:
        if p["name"].lower() == player_name.lower():
            exact_match = p
            break
    
    if not exact_match:
        exact_match = players[0]
    
    player_info = get_player_info(exact_match["id"])
    if not player_info:
        return None
    
    stats = player_info.get("stats", [])
    t20_batting = None
    
    for stat in stats:
        if stat.get("fn") == "batting" and stat.get("matchtype") in ["t20", "t20i"]:
            t20_batting = stat
            break
    
    if not t20_batting:
        return None
    
    result = {
        "matches": int(t20_batting.get("mat", 0)),
        "runs": int(t20_batting.get("runs", 0)),
        "avg": float(t20_batting.get("avg", 0) or 0),
        "sr": float(t20_batting.get("sr", 0) or 0),
        "fifties": int(t20_batting.get("50s", 0)),
        "hundreds": int(t20_batting.get("100s", 0)),
        "balls_faced": int(t20_batting.get("bf", 0))
    }
    
    stats_cache[cache_key] = (result, datetime.now())
    _set_db_cache(cache_key, player_name, "batting", result)
    
    return result

def get_player_bowling_stats(player_name: str) -> Optional[Dict]:
    cache_key = f"bowling_{player_name.lower()}"
    
    if cache_key in stats_cache:
        cached_data, cached_time = stats_cache[cache_key]
        if datetime.now() - cached_time < CACHE_DURATION:
            logger.debug(f"Memory cache hit for {player_name} bowling stats")
            return cached_data
    
    db_cached = _get_db_cache(cache_key)
    if db_cached:
        logger.debug(f"DB cache hit for {player_name} bowling stats")
        stats_cache[cache_key] = (db_cached, datetime.now())
        return db_cached
    
    players = search_players(player_name, limit=5)
    if not players:
        return None
    
    exact_match = None
    for p in players:
        if p["name"].lower() == player_name.lower():
            exact_match = p
            break
    
    if not exact_match:
        exact_match = players[0]
    
    player_info = get_player_info(exact_match["id"])
    if not player_info:
        return None
    
    stats = player_info.get("stats", [])
    t20_bowling = None
    
    for stat in stats:
        if stat.get("fn") == "bowling" and stat.get("matchtype") in ["t20", "t20i"]:
            t20_bowling = stat
            break
    
    if not t20_bowling:
        return None
    
    result = {
        "matches": int(t20_bowling.get("mat", 0)),
        "wickets": int(t20_bowling.get("wkts", 0)),
        "avg": float(t20_bowling.get("avg", 0) or 0),
        "econ": float(t20_bowling.get("econ", 0) or 0),
        "overs": float(t20_bowling.get("overs", 0) or 0),
        "best": t20_bowling.get("bbm", "0/0")
    }
    
    stats_cache[cache_key] = (result, datetime.now())
    _set_db_cache(cache_key, player_name, "bowling", result)
    
    return result

def clear_cache():
    stats_cache.clear()
    logger.info("Cricket API cache cleared")
