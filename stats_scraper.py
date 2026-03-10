"""
Stats Scraper Module
Scrapes player statistics from ESPNCricinfo to keep predictions up-to-date
"""
import re
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
from datetime import datetime, timedelta

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

PLAYER_ID_MAP = {
    "Virat Kohli": "253802",
    "Rohit Sharma": "34102",
    "Suryakumar Yadav": "446507",
    "KL Rahul": "422108",
    "Rishabh Pant": "931581",
    "Hardik Pandya": "625371",
    "Ravindra Jadeja": "234675",
    "Jasprit Bumrah": "625383",
    "Yuzvendra Chahal": "430246",
    "Mohammed Shami": "481896",
    "Bhuvneshwar Kumar": "326016",
    "MS Dhoni": "28081",
    "Shubman Gill": "1070173",
    "Yashasvi Jaiswal": "1151270",
    "Babar Azam": "348144",
    "Mohammad Rizwan": "323389",
    "Shaheen Afridi": "1072405",
    "Jos Buttler": "308967",
    "Ben Stokes": "311158",
    "Jofra Archer": "669855",
    "David Warner": "219889",
    "Steve Smith": "267192",
    "Glenn Maxwell": "325026",
    "Pat Cummins": "489889",
    "Mitchell Starc": "311592",
    "Kane Williamson": "277906",
    "Trent Boult": "277912",
    "Quinton de Kock": "379143",
    "Kagiso Rabada": "550215",
    "Rashid Khan": "793463",
    "Andre Russell": "276298",
    "Sunil Narine": "230558",
    "Nicholas Pooran": "550261",
    "Wanindu Hasaranga": "903619",
    "Faf du Plessis": "44828",
}

stats_cache = {}
CACHE_DURATION = timedelta(hours=24)

def get_player_espn_id(player_name: str) -> Optional[str]:
    return PLAYER_ID_MAP.get(player_name)

def scrape_player_t20_stats(player_name: str) -> Optional[Dict]:
    espn_id = get_player_espn_id(player_name)
    if not espn_id:
        logger.debug(f"No ESPN ID found for {player_name}")
        return None
    
    cache_key = f"{player_name}_t20"
    if cache_key in stats_cache:
        cached_data, cached_time = stats_cache[cache_key]
        if datetime.now() - cached_time < CACHE_DURATION:
            logger.debug(f"Using cached stats for {player_name}")
            return cached_data
    
    try:
        url = f"https://www.espncricinfo.com/cricketers/{player_name.lower().replace(' ', '-')}-{espn_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.error(f"Failed to fetch stats for {player_name}: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        stats = {
            'name': player_name,
            'espn_id': espn_id,
            'batting': {},
            'bowling': {},
            'updated_at': datetime.now().isoformat()
        }
        
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    format_cell = cells[0].get_text(strip=True)
                    if 'T20' in format_cell or 't20' in format_cell.lower():
                        try:
                            stats_values = [cell.get_text(strip=True) for cell in cells[1:]]
                            if len(stats_values) >= 4:
                                stats['batting'] = {
                                    'matches': stats_values[0] if stats_values[0].isdigit() else '0',
                                    'runs': stats_values[2] if len(stats_values) > 2 and stats_values[2].isdigit() else '0',
                                    'average': stats_values[4] if len(stats_values) > 4 else '0',
                                    'strike_rate': stats_values[6] if len(stats_values) > 6 else '0',
                                }
                        except (IndexError, ValueError) as e:
                            logger.debug(f"Error parsing stats: {e}")
        
        stats_cache[cache_key] = (stats, datetime.now())
        return stats
        
    except Exception as e:
        logger.error(f"Error scraping stats for {player_name}: {e}")
        return None

def get_ipl_player_stats(player_name: str) -> Optional[Dict]:
    try:
        search_name = player_name.lower().replace(' ', '+')
        url = f"https://www.iplt20.com/stats/all-time/most-runs"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        player_rows = soup.find_all('tr')
        for row in player_rows:
            cells = row.find_all('td')
            if cells:
                name_cell = cells[0].get_text(strip=True) if cells else ''
                if player_name.lower() in name_cell.lower():
                    try:
                        return {
                            'name': player_name,
                            'matches': cells[1].get_text(strip=True) if len(cells) > 1 else '0',
                            'runs': cells[2].get_text(strip=True) if len(cells) > 2 else '0',
                            'average': cells[4].get_text(strip=True) if len(cells) > 4 else '0',
                            'strike_rate': cells[5].get_text(strip=True) if len(cells) > 5 else '0',
                            'fifties': cells[7].get_text(strip=True) if len(cells) > 7 else '0',
                            'hundreds': cells[8].get_text(strip=True) if len(cells) > 8 else '0',
                        }
                    except (IndexError, ValueError):
                        pass
        
        return None
        
    except Exception as e:
        logger.error(f"Error fetching IPL stats for {player_name}: {e}")
        return None

def update_player_stats_batch(player_names: list) -> Dict[str, Dict]:
    results = {}
    for name in player_names:
        stats = scrape_player_t20_stats(name)
        if stats:
            results[name] = stats
    return results

def get_cached_stats(player_name: str) -> Optional[Dict]:
    cache_key = f"{player_name}_t20"
    if cache_key in stats_cache:
        cached_data, cached_time = stats_cache[cache_key]
        return cached_data
    return None

discovered_players_cache = {}
DISCOVERED_CACHE_DURATION = timedelta(hours=6)

def search_espncricinfo_players(query: str, limit: int = 20) -> list:
    """
    Search for players. Currently returns empty list as ESPNcricinfo blocks direct scraping.
    The local database already contains 400+ T20 players including most international cricketers.
    """
    cache_key = f"search_{query.lower()}"
    if cache_key in discovered_players_cache:
        cached_data, cached_time = discovered_players_cache[cache_key]
        if datetime.now() - cached_time < DISCOVERED_CACHE_DURATION:
            return cached_data
    
    logger.debug(f"External search for {query} - ESPNcricinfo blocks direct access, using local database")
    discovered_players_cache[cache_key] = ([], datetime.now())
    return []

def fetch_player_details_from_espncricinfo(espn_id: str) -> Optional[Dict]:
    """
    Fetch detailed player information from ESPNcricinfo using their player ID.
    Returns player details including country, role, batting/bowling style.
    """
    cache_key = f"player_details_{espn_id}"
    if cache_key in stats_cache:
        cached_data, cached_time = stats_cache[cache_key]
        if datetime.now() - cached_time < CACHE_DURATION:
            return cached_data
    
    try:
        url = f"https://www.espncricinfo.com/cricketers/player-{espn_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        if response.status_code != 200:
            logger.error(f"Failed to fetch player {espn_id}: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        player_info = {
            'espn_id': espn_id,
            'name': '',
            'country': 'Unknown',
            'role': 'Player',
            'batting_style': 'Unknown',
            'bowling_style': 'Unknown',
            't20_stats': {}
        }
        
        title_tag = soup.find('h1')
        if title_tag:
            player_info['name'] = title_tag.get_text(strip=True)
        
        page_text = soup.get_text()
        
        countries = ['India', 'Australia', 'England', 'Pakistan', 'South Africa', 
                     'New Zealand', 'Sri Lanka', 'Bangladesh', 'West Indies', 
                     'Afghanistan', 'Zimbabwe', 'Ireland', 'Scotland', 'Netherlands',
                     'Namibia', 'Nepal', 'UAE', 'Oman', 'PNG', 'USA', 'Canada']
        for country in countries:
            if country in page_text:
                player_info['country'] = country
                break
        
        if 'Right-hand bat' in page_text:
            player_info['batting_style'] = 'Right-hand bat'
        elif 'Left-hand bat' in page_text:
            player_info['batting_style'] = 'Left-hand bat'
        
        if 'Left-arm fast' in page_text:
            player_info['bowling_style'] = 'Left-arm fast'
        elif 'Right-arm fast' in page_text:
            player_info['bowling_style'] = 'Right-arm fast'
        elif 'Right-arm medium' in page_text:
            player_info['bowling_style'] = 'Right-arm medium'
        elif 'Left-arm medium' in page_text:
            player_info['bowling_style'] = 'Left-arm medium'
        elif 'Leg-break' in page_text or 'Legbreak' in page_text:
            player_info['bowling_style'] = 'Leg-break googly'
        elif 'Right-arm offbreak' in page_text or 'Off-break' in page_text:
            player_info['bowling_style'] = 'Right-arm offbreak'
        elif 'Slow left-arm' in page_text:
            player_info['bowling_style'] = 'Slow left-arm orthodox'
        
        if 'Batsman' in page_text or 'Batter' in page_text:
            if 'Wicketkeeper' in page_text:
                player_info['role'] = 'Wicketkeeper Batsman'
            else:
                player_info['role'] = 'Batsman'
        elif 'Allrounder' in page_text or 'All-rounder' in page_text:
            player_info['role'] = 'All-rounder'
        elif 'Bowler' in page_text:
            player_info['role'] = 'Bowler'
        
        stats_cache[cache_key] = (player_info, datetime.now())
        return player_info
        
    except Exception as e:
        logger.error(f"Error fetching player details for {espn_id}: {e}")
        return None

def get_or_discover_player(player_name: str) -> Optional[Dict]:
    """
    Try to find player in local database first, then search ESPNcricinfo if not found.
    Returns player data dictionary or None.
    """
    if player_name in PLAYER_ID_MAP:
        espn_id = PLAYER_ID_MAP[player_name]
        return {
            'name': player_name,
            'espn_id': espn_id,
            'source': 'local'
        }
    
    search_results = search_espncricinfo_players(player_name, limit=5)
    
    for player in search_results:
        if player['name'].lower() == player_name.lower():
            PLAYER_ID_MAP[player['name']] = player['espn_id']
            return {**player, 'source': 'espncricinfo'}
    
    if search_results:
        player = search_results[0]
        PLAYER_ID_MAP[player['name']] = player['espn_id']
        return {**player, 'source': 'espncricinfo'}
    
    return None
