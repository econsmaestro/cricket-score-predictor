"""
Live Match Scraper Module
Scrapes live T20 match data from ESPNCricinfo
"""
import re
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'close',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
}

live_matches_cache = {}
CACHE_DURATION_SECONDS = 60


def normalize_team_name(name: str) -> str:
    """Normalize team name for deduplication"""
    name = name.lower().strip()
    # Remove common suffixes/prefixes (including attached ones like "rsau19")
    name = re.sub(r'(u19|u-19|under-?19|women|men|xi|a team|live)$', '', name)
    name = re.sub(r'\s*(u19|u-19|under-?19|women|men|xi|a team|live)\s*', ' ', name)
    name = name.strip()
    
    # Common abbreviations - check for both standalone and attached (e.g., "rsau19" -> "rsa")
    abbrevs = {
        'rsa': 'south africa', 'aus': 'australia', 'ind': 'india',
        'eng': 'england', 'pak': 'pakistan', 'nz': 'new zealand',
        'wi': 'west indies', 'sl': 'sri lanka', 'ban': 'bangladesh',
        'afg': 'afghanistan', 'zim': 'zimbabwe', 'ire': 'ireland',
        'sco': 'scotland', 'ned': 'netherlands', 'nam': 'namibia',
        'usa': 'united states', 'uae': 'emirates', 'nep': 'nepal',
        'sa': 'south africa', 'nzl': 'new zealand', 'windies': 'west indies'
    }
    
    # Try exact match first
    if name in abbrevs:
        return abbrevs[name]
    
    # Try prefix match (e.g., "aus " or "rsa ")
    for abbr, full in abbrevs.items():
        if name.startswith(abbr + ' '):
            name = full + name[len(abbr):]
            break
        # Also handle "south africa" -> normalize consistently
        if name.startswith(full):
            name = full + name[len(full):]
            break
    
    # Remove any remaining numbers and extra spaces
    name = re.sub(r'\d+', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def get_match_key(match: Dict) -> str:
    """Generate a unique key for a match based on teams"""
    teams = match.get('teams', [])
    if len(teams) >= 2:
        team1 = normalize_team_name(teams[0])
        team2 = normalize_team_name(teams[1])
        # Sort teams alphabetically to ensure consistent key
        sorted_teams = sorted([team1, team2])
        return f"{sorted_teams[0]}|{sorted_teams[1]}|{match.get('format', 't20')}"
    # Fallback to display text
    display = match.get('display_text', '').lower()
    return display

def extract_overs_from_text(text: str) -> Optional[float]:
    """Extract current overs from match display text"""
    overs_match = re.search(r'\((\d+\.?\d*)\s*(?:ov|overs?)\)', text)
    if overs_match:
        return float(overs_match.group(1))
    return None


def extract_tournament_name(href: str) -> str:
    """Extract tournament name from Cricbuzz/ESPN URL slug"""
    parts = href.rstrip('/').split('/')
    slug = parts[-1] if parts else ''
    cleaned = re.sub(r'^[a-z]+-vs-[a-z]+-', '', slug)
    cleaned = re.sub(
        r'^\d+(st|nd|rd|th)-'
        r'(?:match-group-[a-z]\d?-|match-|odi-|t20i?-|'
        r'quarter-final[^-]*-|semi-final[^-]*-|final-|'
        r'eliminator-|qualifier[^-]*-)',
        '', cleaned
    )
    cleaned = re.sub(r'-\d{4}(-\d{2})?$', '', cleaned)
    name = cleaned.replace('-', ' ').strip()
    if not name:
        return ''
    upper_words = {'icc', 'ipl', 't20', 'odi', 'bbl', 'cpl', 'psl', 'wpl',
                   'sa20', 'bpl', 'cwc', 'wbbl', 'u19', 'uae'}
    words = name.split()
    result = []
    for w in words:
        if w.lower() in upper_words:
            result.append(w.upper())
        else:
            result.append(w.capitalize())
    return ' '.join(result)


EXCLUDED_FORMAT_KEYWORDS = [
    'first class', 'first-class', 'firstclass',
    'test match', 'test series',
    'list a', 'list-a',
    'ranji', 'sheffield shield', 'county championship',
    'plunket shield', 'four day', 'four-day', '4-day', '4 day',
    'duleep trophy', 'irani cup', 'irani trophy',
    'currie cup', 'logan cup', 'quaid-e-azam',
    'national championship', 'fc match', 'multi-day',
    'unofficial test', 'tour match', 'warm-up match',
    'practice match', 'three day', 'three-day', '3-day',
    'vijay hazare', 'marsh cup', 'ford trophy', 'royal london',
    'deodhar trophy', 'momentum cup',
]

def is_excluded_format(text: str) -> bool:
    """Return True if the match text indicates a non-T20/ODI format (Test, first-class, etc.)."""
    text_lower = text.lower()
    if any(keyword in text_lower for keyword in EXCLUDED_FORMAT_KEYWORDS):
        logger.info(f"Filtered out non-T20/ODI match: {text[:80]}")
        return True
    if re.search(r'\btest\b', text_lower) and 'contest' not in text_lower and 't20' not in text_lower:
        logger.info(f"Filtered out Test match: {text[:80]}")
        return True
    return False


FORMAT_OVER_LIMITS = {
    'T20': 20.0,
    'ODI': 50.0,
}


def is_valid_format_overs(match: Dict) -> bool:
    """Check if a match's overs are within the format limit.
    If overs exceed the format max, the match is likely mis-categorized."""
    match_format = match.get('format', 'T20')
    max_overs = FORMAT_OVER_LIMITS.get(match_format, 50.0)
    
    display_text = match.get('display_text', '')
    overs = extract_overs_from_text(display_text)
    
    if overs is not None and overs > max_overs:
        logger.info(f"Filtered out match (overs {overs} > {max_overs} for {match_format}): {display_text}")
        return False
    
    score_text = match.get('score_text', '')
    if score_text:
        overs = extract_overs_from_text(score_text)
        if overs is not None and overs > max_overs:
            logger.info(f"Filtered out match (overs {overs} > {max_overs} for {match_format}): {display_text}")
            return False
    
    return True


def deduplicate_matches(matches: List[Dict]) -> List[Dict]:
    """Remove duplicate matches and filter out format-overs mismatches and first-class games"""
    seen_keys = set()
    seen_ids = set()
    unique_matches = []
    for match in matches:
        display = match.get('display_text', '')
        if is_excluded_format(display):
            continue
        if not is_valid_format_overs(match):
            continue
        match_id = match.get('id', '')
        if match_id and match_id in seen_ids:
            logger.debug(f"Duplicate ID removed: {display}")
            continue
        key = get_match_key(match)
        logger.debug(f"Match key: {key} for: {display}")
        if key not in seen_keys:
            seen_keys.add(key)
            if match_id:
                seen_ids.add(match_id)
            unique_matches.append(match)
        else:
            logger.debug(f"Duplicate removed: {display}")
    logger.info(f"Deduplicated {len(matches)} matches to {len(unique_matches)}")
    return unique_matches

def get_live_matches() -> List[Dict]:
    """Fetch list of live cricket matches (T20, ODI, Men's and Women's)"""
    matches = []
    
    matches = try_cricbuzz_api()
    if matches:
        return deduplicate_matches(matches)
    
    matches = try_espn_api()
    if matches:
        return deduplicate_matches(matches)
    
    return deduplicate_matches(try_espn_scrape())


def try_cricbuzz_api() -> List[Dict]:
    """Try Cricbuzz live scores page for live matches"""
    try:
        url = "https://www.cricbuzz.com/cricket-match/live-scores"
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        if response.status_code != 200:
            logger.debug(f"Cricbuzz live page failed: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        matches = []
        
        match_links = soup.find_all('a', href=re.compile(r'/live-cricket-scores/'))
        seen = set()
        
        for link in match_links:
            href = link.get('href', '')
            if href in seen:
                continue
            seen.add(href)
            
            text = link.get_text(separator=' ', strip=True)
            if not text or len(text) < 5:
                continue
            
            combined_check = (text + ' ' + href).lower()
            if 'test' in combined_check and 'contest' not in combined_check and 't20' not in combined_check:
                continue
            
            if is_excluded_format(text) or is_excluded_format(href):
                continue
            
            text_lower = text.lower()
            
            completed_match = re.search(r'(\w[\w\s]*?)\s+won', text_lower)
            is_completed = completed_match or any(ind in text_lower for ind in [
                'won by', 'no result', 'abandoned', 'tied',
                'result:', 'match drawn'
            ])
            
            has_score = re.search(r'\d+/\d+|\(\d+\.?\d*\s*ov', text)
            has_live_indicator = any(ind in text_lower for ind in [
                'live', 'batting', 'bowling', 'need', 'lead', 'trail',
                'innings break', 'break', 'stumps', 'tea', 'lunch', 'dinner',
                'session break', 'rain', 'delayed', 'in progress', 'day ',
                'opt to', 'opted to', 'chose to', 'elected to'
            ])
            is_upcoming = any(ind in text_lower for ind in [
                'preview', 'upcoming', 'toss',
                'hrs to go', 'hours to go', 'mins to go', 'minutes to go'
            ])
            
            if not has_score and not has_live_indicator and not is_completed:
                is_upcoming = True
            
            result_text = ''
            if is_completed:
                won_match = re.search(r'-\s*(.+?won.*)$', text.strip())
                if won_match:
                    result_text = won_match.group(1).strip()
                elif 'no result' in text_lower:
                    result_text = 'No Result'
                elif 'abandoned' in text_lower:
                    result_text = 'Abandoned'
                elif 'tied' in text_lower:
                    result_text = 'Tied'
                elif 'match drawn' in text_lower:
                    result_text = 'Match Drawn'
                else:
                    result_text = 'Completed'
                
            match_id = re.search(r'/(\d+)/', href)
            if not match_id:
                continue
            
            combined_text = (text + ' ' + href).lower()
            has_t20 = any(k in combined_text for k in ['t20', 't-20', 'twenty20', 'twenty-20'])
            has_world_cup = any(k in combined_text for k in ['world-cup', 'world cup', 'cwc'])
            is_odi = any(k in combined_text for k in ['odi', '-odi-', 'one-day', 'oneday', 'asia-cup', 'asia cup', 'vijay-hazare', 'vijay hazare'])
            if has_world_cup and not has_t20:
                is_odi = True
            if has_t20:
                is_odi = False
            is_womens = any(k in combined_text for k in ['women', 'wbbl', 'wpl', 'wpsl'])
            is_youth = any(k in combined_text for k in ['u19', 'under-19', 'under 19', 'u-19', 'youth'])
            match_format = 'ODI' if is_odi else 'T20'
            
            format_suffix = match_format
            if is_youth:
                format_suffix += ' U19'
            if is_womens:
                format_suffix += 'W'
            
            teams = extract_teams_from_text(text)
            if teams:
                tournament = extract_tournament_name(href)
                label_parts = [format_suffix]
                if tournament:
                    label_parts.append(tournament)
                label = ', '.join(label_parts)
                if is_completed:
                    match_status = 'Completed'
                    status_label = f" - {result_text}" if result_text else " (Completed)"
                elif is_upcoming:
                    match_status = 'Upcoming'
                    status_label = " (Upcoming)"
                else:
                    match_status = 'Live'
                    status_label = " (Live)"
                matches.append({
                    'id': f"cb_{match_id.group(1)}",
                    'url': f"https://www.cricbuzz.com{href}",
                    'teams': teams,
                    'display_text': f"{teams[0]} vs {teams[1]} • {label}{status_label}",
                    'status': match_status,
                    'source': 'cricbuzz',
                    'format': match_format,
                    'is_womens': is_womens,
                    'is_youth': is_youth
                })
        
        status_order = {'Live': 0, 'Upcoming': 1, 'Completed': 2}
        matches.sort(key=lambda m: status_order.get(m.get('status', 'Live'), 3))
        logger.info(f"Cricbuzz: Found {len(matches)} cricket matches")
        return matches[:15]
        
    except Exception as e:
        logger.debug(f"Cricbuzz error: {e}")
        return []


def try_espn_api() -> List[Dict]:
    """Try ESPN Cricinfo API endpoint for multiple cricket leagues (T20 and ODI)"""
    matches = []
    leagues = [
        't20-blast', 'ipl', 'big-bash-league', 'psl', 'cpl', 'sa20', 'ilt20', 't20i',
        't20-world-cup', 'mens-t20-world-cup', 'icc-mens-t20-world-cup',
        'wbbl', 'wpl', 'womens-t20-world-cup', 'womens-t20i',
        'odi', 'womens-odi', 'world-cup', 'womens-world-cup',
        'u19-world-cup', 'u19-t20-world-cup', 'u19-odi', 'u19-t20i',
        'womens-u19-world-cup', 'womens-u19-t20-world-cup'
    ]
    
    odi_leagues = ['odi', 'womens-odi', 'world-cup', 'womens-world-cup', 'u19-world-cup', 'u19-odi', 'womens-u19-world-cup']
    t20_leagues = ['t20-world-cup', 'mens-t20-world-cup', 'icc-mens-t20-world-cup', 'u19-t20-world-cup', 'womens-t20-world-cup', 'womens-u19-t20-world-cup']
    womens_leagues = ['wbbl', 'wpl', 'womens-t20-world-cup', 'womens-t20i', 'womens-odi', 'womens-world-cup', 'womens-u19-world-cup', 'womens-u19-t20-world-cup']
    youth_leagues = ['u19-world-cup', 'u19-t20-world-cup', 'u19-odi', 'u19-t20i', 'womens-u19-world-cup', 'womens-u19-t20-world-cup']
    
    for league_name in leagues:
        try:
            url = f"https://site.web.api.espn.com/apis/v2/scoreboard/header?sport=cricket&league={league_name}"
            response = requests.get(url, headers=HEADERS, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'sports' in data:
                    for sport in data.get('sports', []):
                        for league in sport.get('leagues', []):
                            for event in league.get('events', []):
                                match_state = event.get('status', {}).get('type', {}).get('state', '')
                                status_desc = event.get('status', {}).get('type', {}).get('description', '').lower()
                                # Include matches in progress OR on innings/session breaks
                                is_active = match_state == 'in' or any(brk in status_desc for brk in [
                                    'break', 'innings', 'stumps', 'tea', 'lunch', 'dinner', 'rain', 'delayed'
                                ])
                                if is_active:
                                    competitors = event.get('competitors', [])
                                    if len(competitors) >= 2:
                                        is_t20 = league_name in t20_leagues
                                        is_odi = league_name in odi_leagues and not is_t20
                                        is_womens = league_name in womens_leagues
                                        is_youth = league_name in youth_leagues
                                        match_format = 'ODI' if is_odi else 'T20'
                                        format_suffix = match_format
                                        if is_youth:
                                            format_suffix += ' U19'
                                        if is_womens:
                                            format_suffix += 'W'
                                        # Determine match status display
                                        if match_state == 'in':
                                            match_status = 'Live'
                                        elif 'break' in status_desc or 'innings' in status_desc:
                                            match_status = 'Innings Break'
                                        elif any(brk in status_desc for brk in ['stumps', 'tea', 'lunch', 'dinner']):
                                            match_status = 'Session Break'
                                        elif 'rain' in status_desc or 'delayed' in status_desc:
                                            match_status = 'Delayed'
                                        else:
                                            match_status = 'In Progress'
                                        
                                        tournament = league_name.replace('-', ' ').title()
                                        tour_upper = {'Icc': 'ICC', 'Ipl': 'IPL', 'T20': 'T20', 'Odi': 'ODI',
                                                      'Bbl': 'BBL', 'Cpl': 'CPL', 'Psl': 'PSL', 'Wpl': 'WPL',
                                                      'Sa20': 'SA20', 'Bpl': 'BPL', 'Cwc': 'CWC', 'Wbbl': 'WBBL',
                                                      'U19': 'U19', 'Uae': 'UAE', 'T20I': 'T20I'}
                                        for old, new in tour_upper.items():
                                            tournament = tournament.replace(old, new)
                                        label = f"{format_suffix}, {tournament}" if tournament else format_suffix
                                        event_name = event.get('name', '')
                                        teams_list = [c.get('displayName', '') for c in competitors[:2]]
                                        display = f"{teams_list[0]} vs {teams_list[1]} • {label}" if len(teams_list) >= 2 else f"{event_name} • {label}"
                                        matches.append({
                                            'id': str(event.get('id')),
                                            'url': event.get('links', [{}])[0].get('href', ''),
                                            'teams': teams_list,
                                            'display_text': display,
                                            'status': match_status,
                                            'source': 'espn_api',
                                            'format': match_format,
                                            'is_womens': is_womens,
                                            'is_youth': is_youth
                                        })
        except Exception as e:
            logger.debug(f"ESPN API error for {league_name}: {e}")
            continue
    
    return matches


def try_espn_scrape() -> List[Dict]:
    """Fallback: try to scrape ESPNCricinfo live page"""
    try:
        url = "https://www.espncricinfo.com/live-cricket-score"
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch live matches: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        matches = []
        
        match_cards = soup.find_all('a', href=re.compile(r'/live-cricket-score/'))
        
        seen_urls = set()
        for card in match_cards:
            try:
                href = card.get('href', '')
                if href in seen_urls:
                    continue
                seen_urls.add(href)
                
                match_text = card.get_text(separator=' ', strip=True)
                
                if 'test' in match_text.lower():
                    continue
                
                if is_excluded_format(match_text):
                    continue
                
                mt_lower = match_text.lower()
                has_t20_indicator = any(k in mt_lower for k in ['t20', 't-20', 'twenty20', 'twenty-20'])
                has_wc = any(k in mt_lower for k in ['world cup', 'cwc'])
                is_odi = any(k in mt_lower for k in ['odi', 'one day'])
                if has_wc and not has_t20_indicator:
                    is_odi = True
                if has_t20_indicator:
                    is_odi = False
                is_womens = any(womens_indicator in mt_lower for womens_indicator in ['women', 'wt20', 'wbbl', 'wpsl', 'wpl'])
                match_format = 'ODI' if is_odi else 'T20'
                
                match_url = f"https://www.espncricinfo.com{href}" if href.startswith('/') else href
                
                match_id = extract_match_id(href)
                if not match_id:
                    continue
                
                teams = extract_teams_from_text(match_text)
                
                if teams:
                    tournament = extract_tournament_name(href)
                    fmt_label = match_format + ('W' if is_womens else '')
                    label_parts = [fmt_label]
                    if tournament:
                        label_parts.append(tournament)
                    label = ', '.join(label_parts)
                    matches.append({
                        'id': match_id,
                        'url': match_url,
                        'teams': teams,
                        'display_text': f"{teams[0]} vs {teams[1]} • {label}" if len(teams) >= 2 else match_text[:50],
                        'status': 'Live',
                        'format': match_format,
                        'is_womens': is_womens
                    })
            except Exception as e:
                logger.debug(f"Error parsing match card: {e}")
                continue
        
        logger.info(f"Found {len(matches)} potential T20 matches")
        return matches[:10]
        
    except Exception as e:
        logger.error(f"Error fetching live matches: {e}")
        return []


def extract_match_id(url: str) -> Optional[str]:
    """Extract match ID from ESPNCricinfo URL"""
    patterns = [
        r'/(\d+)/',
        r'/live-cricket-score/(\d+)',
        r'-(\d+)$',
        r'match/(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def extract_teams_from_text(text: str) -> List[str]:
    """Extract team names from match text"""
    vs_patterns = [
        r'(.+?)\s+vs?\s+(.+?)(?:\s+\d|,|$|\s+-)',
        r'(.+?)\s+v\s+(.+?)(?:\s+\d|,|$|\s+-)',
    ]
    
    for pattern in vs_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            team1 = match.group(1).strip()[:30]
            team2 = match.group(2).strip()[:30]
            team1 = re.sub(r'\d+[/-]\d+.*', '', team1).strip()
            team2 = re.sub(r'\d+[/-]\d+.*', '', team2).strip()
            if team1 and team2:
                return [team1, team2]
    
    return []


def get_match_details(match_id: str) -> Optional[Dict]:
    """Fetch detailed match data including scorecard. Returns partial data when full details unavailable."""
    if match_id.startswith('cb_'):
        return get_cricbuzz_match_details(match_id[3:])
    
    match_data = {
        'match_id': match_id,
        'current_score': 0,
        'wickets': 0,
        'overs': 0.0,
        'innings': 1,
        'target': 0,
        'batsmen': [],
        'bowlers': [],
        'venue': '',
        'teams': [],
        'partial': False,
        'loaded_fields': [],
    }
    
    try:
        import time
        cache_bust = int(time.time() * 1000)
        urls_to_try = [
            f"https://www.espncricinfo.com/matches/engine/match/{match_id}.html?_cb={cache_bust}",
            f"https://www.espncricinfo.com/ci/engine/match/{match_id}.html?_cb={cache_bust}",
        ]
        
        response = None
        for url in urls_to_try:
            try:
                response = requests.get(url, headers=HEADERS, timeout=15)
                if response.status_code == 200:
                    break
            except:
                continue
        
        if not response or response.status_code != 200:
            fallback = get_match_from_live_page(match_id)
            if fallback:
                return fallback
            match_data['partial'] = True
            return match_data
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        score_elements = soup.find_all(class_=re.compile(r'score|runs', re.I))
        last_score = None
        for elem in score_elements:
            text = elem.get_text(strip=True)
            score_match = re.search(r'(\d+)[/-](\d+)\s*\((\d+\.?\d*)\s*ov', text)
            if score_match:
                last_score = score_match
        if last_score:
            match_data['current_score'] = int(last_score.group(1))
            match_data['wickets'] = int(last_score.group(2))
            match_data['overs'] = float(last_score.group(3))
            match_data['loaded_fields'].extend(['current_score', 'wickets', 'overs'])
        
        try:
            batsmen_data = extract_batsmen(soup)
            if batsmen_data:
                match_data['batsmen'] = batsmen_data
                match_data['loaded_fields'].append('batsmen')
        except Exception as e:
            logger.debug(f"Could not extract batsmen: {e}")
        
        try:
            bowlers_data = extract_bowlers(soup)
            if bowlers_data:
                match_data['bowlers'] = bowlers_data
                match_data['loaded_fields'].append('bowlers')
        except Exception as e:
            logger.debug(f"Could not extract bowlers: {e}")
        
        try:
            venue_elem = soup.find(class_=re.compile(r'venue|ground', re.I))
            if venue_elem:
                match_data['venue'] = re.sub(r'\s+', ' ', venue_elem.get_text(strip=True)).strip()
                match_data['loaded_fields'].append('venue')
        except Exception as e:
            logger.debug(f"Could not extract venue: {e}")
        
        if not match_data['loaded_fields']:
            match_data['partial'] = True
        elif len(match_data['loaded_fields']) < 4:
            match_data['partial'] = True
        
        return match_data
        
    except Exception as e:
        logger.error(f"Error fetching match details for {match_id}: {e}")
        match_data['partial'] = True
        return match_data


def get_match_from_live_page(match_id: str) -> Optional[Dict]:
    """Fallback: try to get match data from live score page. Returns partial data when possible."""
    match_data = {
        'match_id': match_id,
        'current_score': 0,
        'wickets': 0,
        'overs': 0.0,
        'innings': 1,
        'target': 0,
        'batsmen': [],
        'bowlers': [],
        'venue': '',
        'teams': [],
        'raw_score_text': '',
        'partial': False,
        'loaded_fields': [],
    }
    
    try:
        import time
        cache_bust = int(time.time() * 1000)
        url = f"https://www.espncricinfo.com/live-cricket-score/{match_id}?_cb={cache_bust}"
        response = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        
        if response.status_code != 200:
            match_data['partial'] = True
            return match_data
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text(separator=' ', strip=True)
        
        score_patterns = [
            r'(\d+)[/-](\d+)\s*\((\d+\.?\d*)\s*(?:ov|overs?)\)',
            r'(\d+)/(\d+)\s+\((\d+\.?\d*)\)',
        ]
        
        for pattern in score_patterns:
            all_matches = list(re.finditer(pattern, page_text))
            if all_matches:
                score_match = all_matches[-1]
                match_data['current_score'] = int(score_match.group(1))
                match_data['wickets'] = int(score_match.group(2))
                match_data['overs'] = float(score_match.group(3))
                match_data['raw_score_text'] = score_match.group(0)
                match_data['loaded_fields'].extend(['current_score', 'wickets', 'overs'])
                break
        
        target_match = re.search(r'target[:\s]+(\d+)', page_text, re.I)
        if target_match:
            match_data['target'] = int(target_match.group(1))
            match_data['innings'] = 2
            match_data['loaded_fields'].append('target')
        
        need_match = re.search(r'need\s+(\d+)\s+(?:runs?|more)', page_text, re.I)
        if need_match:
            runs_needed = int(need_match.group(1))
            match_data['target'] = match_data['current_score'] + runs_needed
            match_data['innings'] = 2
            match_data['loaded_fields'].append('target')
        
        try:
            batsmen = extract_batsmen(soup)
            if batsmen:
                match_data['batsmen'] = batsmen
                match_data['loaded_fields'].append('batsmen')
        except Exception as e:
            logger.debug(f"Could not extract batsmen in fallback: {e}")
        
        try:
            bowlers = extract_bowlers(soup)
            if bowlers:
                match_data['bowlers'] = bowlers
                match_data['loaded_fields'].append('bowlers')
        except Exception as e:
            logger.debug(f"Could not extract bowlers in fallback: {e}")
        
        if len(match_data['loaded_fields']) < 4:
            match_data['partial'] = True
        
        return match_data
        
    except Exception as e:
        logger.error(f"Error in fallback match fetch: {e}")
        match_data['partial'] = True
        return match_data


def extract_batsmen(soup: BeautifulSoup) -> List[Dict]:
    """Extract current batsmen information"""
    batsmen = []
    
    try:
        batsman_rows = soup.find_all('tr')
        for row in batsman_rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 3:
                text = row.get_text(separator=' ', strip=True)
                if any(indicator in text.lower() for indicator in ['batting', 'not out', '*']):
                    name_cell = cells[0].get_text(strip=True)
                    name = re.sub(r'[\*\(\)]+', '', name_cell).strip()
                    
                    if len(name) < 2 or name.isdigit():
                        continue
                    
                    runs = 0
                    balls = 0
                    
                    for cell in cells[1:]:
                        cell_text = cell.get_text(strip=True)
                        if cell_text.isdigit():
                            if runs == 0:
                                runs = int(cell_text)
                            elif balls == 0:
                                balls = int(cell_text)
                                break
                    
                    if name:
                        batsmen.append({
                            'name': name,
                            'runs': runs,
                            'balls': balls
                        })
                    
                    if len(batsmen) >= 2:
                        break
        
        if not batsmen:
            page_text = soup.get_text()
            batsman_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*\*?\s+(\d+)\s*\((\d+)\)'
            matches = re.findall(batsman_pattern, page_text)
            for match in matches[:2]:
                batsmen.append({
                    'name': match[0],
                    'runs': int(match[1]),
                    'balls': int(match[2])
                })
                
    except Exception as e:
        logger.debug(f"Error extracting batsmen: {e}")
    
    return batsmen


def extract_bowlers(soup: BeautifulSoup, max_overs_per_bowler: float = 4.0) -> List[Dict]:
    """Extract bowling figures for all bowlers who have bowled"""
    bowlers = []
    seen_names = set()
    
    try:
        bowling_tables = soup.find_all('table')
        for table in bowling_tables:
            table_text = table.get_text().lower()
            if 'bowling' in table_text or 'overs' in table_text:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 4:
                        row_text = ' '.join(c.get_text(strip=True) for c in cells)
                        figures = re.search(r'(\d+\.?\d*)\s+(\d+)\s+(\d+)\s+(\d+)', row_text)
                        if figures:
                            name_cell = cells[0].get_text(strip=True)
                            name = re.sub(r'[\*\(\)\[\]]+', '', name_cell).strip()
                            name = re.sub(r'\s+', ' ', name)
                            
                            if name and len(name) > 2 and name.lower() not in seen_names:
                                if not re.match(r'^\d', name) and 'total' not in name.lower():
                                    overs_bowled = float(figures.group(1))
                                    bowlers.append({
                                        'name': name,
                                        'overs_bowled': overs_bowled,
                                        'maidens': int(figures.group(2)),
                                        'runs_conceded': int(figures.group(3)),
                                        'wickets': int(figures.group(4)),
                                        'overs_remaining': max(0, max_overs_per_bowler - overs_bowled)
                                    })
                                    seen_names.add(name.lower())
        
        if not bowlers:
            page_text = soup.get_text(separator=' ', strip=True)
            bowling_sections = re.split(r'Bowler\s+O\s+M\s+R\s+W(?:\s+NB\s+WD\s+ECO)?', page_text)
            if len(bowling_sections) > 1:
                for section in bowling_sections[1:]:
                    end_match = re.search(r'Fall of Wickets|Yet to Bat|\d+(?:st|nd|rd|th)\s+Innings|Extras|Total', section)
                    bowl_text = section[:end_match.start()] if end_match else section[:600]
                    entries = re.findall(
                        r'([A-Z][a-zA-Z\'\-]+(?:\s+[A-Za-z\'\-]+){1,4}(?:\s*\([cwk]+\))?)\s+(\d+\.?\d*)\s+(\d+)\s+(\d+)\s+(\d+)',
                        bowl_text
                    )
                    for entry in entries:
                        name = re.sub(r'\s*\([cwk]+\)', '', entry[0]).strip()
                        name = re.sub(r'\s+', ' ', name)
                        skip_words = {'Bowler', 'Menu', 'Live', 'Total', 'Extras', 'Fall'}
                        if name and len(name) > 2 and name.lower() not in seen_names and not any(w in name for w in skip_words):
                            overs_bowled = float(entry[1])
                            bowlers.append({
                                'name': name,
                                'overs_bowled': overs_bowled,
                                'maidens': int(entry[2]),
                                'runs_conceded': int(entry[3]),
                                'wickets': int(entry[4]),
                                'overs_remaining': max(0, max_overs_per_bowler - overs_bowled)
                            })
                            seen_names.add(name.lower())

        if not bowlers:
            page_text = soup.get_text()
            bowling_pattern = r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})\s+(\d+\.?\d*)-(\d+)-(\d+)-(\d+)'
            matches = re.findall(bowling_pattern, page_text)
            
            for match in matches:
                name = match[0].strip()
                if name.lower() not in seen_names and 'Menu' not in name and 'Live' not in name:
                    overs_bowled = float(match[1])
                    bowlers.append({
                        'name': name,
                        'overs_bowled': overs_bowled,
                        'maidens': int(match[2]),
                        'runs_conceded': int(match[3]),
                        'wickets': int(match[4]),
                        'overs_remaining': max(0, max_overs_per_bowler - overs_bowled)
                    })
                    seen_names.add(name.lower())
        
        if not bowlers:
            bowler_rows = soup.find_all('tr')
            for row in bowler_rows:
                cells = row.find_all('td')
                if len(cells) >= 5:
                    text = ' '.join(c.get_text(strip=True) for c in cells)
                    if re.search(r'\d+\.?\d*\s*-\s*\d+\s*-\s*\d+\s*-\s*\d+', text):
                        name = cells[0].get_text(strip=True)
                        name = re.sub(r'[\*\(\)\[\]]+', '', name).strip()
                        
                        if name and name.lower() not in seen_names and len(name) > 2:
                            figures = re.search(r'(\d+\.?\d*)\s*-\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)', text)
                            if figures:
                                overs_bowled = float(figures.group(1))
                                bowlers.append({
                                    'name': name,
                                    'overs_bowled': overs_bowled,
                                    'maidens': int(figures.group(2)),
                                    'runs_conceded': int(figures.group(3)),
                                    'wickets': int(figures.group(4)),
                                    'overs_remaining': max(0, max_overs_per_bowler - overs_bowled)
                                })
                                seen_names.add(name.lower())
                            
    except Exception as e:
        logger.debug(f"Error extracting bowlers: {e}")
    
    return bowlers


def get_cricbuzz_match_details(match_id: str) -> Optional[Dict]:
    """Fetch match details from Cricbuzz. Returns partial data when full details unavailable."""
    match_data = {
        'match_id': f"cb_{match_id}",
        'current_score': 0,
        'wickets': 0,
        'overs': 0.0,
        'innings': 1,
        'target': 0,
        'batsmen': [],
        'bowlers': [],
        'last_over_bowler': '',
        'venue': '',
        'teams': [],
        'source': 'cricbuzz',
        'partial': False,
        'loaded_fields': [],
    }
    
    try:
        import time
        cache_bust = int(time.time() * 1000)
        url = f"https://www.cricbuzz.com/live-cricket-scores/{match_id}?_cb={cache_bust}"
        response = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        
        if response.status_code != 200:
            logger.debug(f"Cricbuzz match details failed: {response.status_code}")
            match_data['partial'] = True
            return match_data
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text(separator=' ', strip=True)
        raw_html = response.text
        
        teams = []
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text()
            title_after_pipe = title_text.split('|')[-1].strip() if '|' in title_text else title_text
            teams = extract_teams_from_text(title_after_pipe)
        if not teams:
            teams = extract_teams_from_text(page_text[:200])
        if teams:
            match_data['teams'] = teams
            match_data['loaded_fields'].append('teams')

        bat_team = re.search(r'batTeamObj.*?teamScore.*?(\d+)-(\d+)', raw_html)
        if bat_team:
            match_data['current_score'] = int(bat_team.group(1))
            match_data['wickets'] = int(bat_team.group(2))
            match_data['loaded_fields'].extend(['current_score', 'wickets'])
        
        over_match = re.search(r'overNumber.*?(\d+)', raw_html)
        if over_match:
            match_data['overs'] = float(over_match.group(1))
            match_data['loaded_fields'].append('overs')
        
        if 'current_score' not in match_data['loaded_fields']:
            all_scores = list(re.finditer(r'(\d+)[/-](\d+)\s*\((\d+\.?\d*)\s*(?:ov|overs?)\)', page_text))
            if all_scores:
                score_fallback = all_scores[-1]
                match_data['current_score'] = int(score_fallback.group(1))
                match_data['wickets'] = int(score_fallback.group(2))
                match_data['overs'] = float(score_fallback.group(3))
                match_data['loaded_fields'].extend(['current_score', 'wickets', 'overs'])
        
        target_match = re.search(r'target[:\s]+(\d+)', page_text, re.I)
        if target_match:
            match_data['target'] = int(target_match.group(1))
            match_data['innings'] = 2
            match_data['loaded_fields'].append('target')
        
        need_match = re.search(r'need\s+(\d+)\s+(?:runs?|more)', page_text, re.I)
        if need_match:
            runs_needed = int(need_match.group(1))
            match_data['target'] = match_data['current_score'] + runs_needed
            match_data['innings'] = 2
            if 'target' not in match_data['loaded_fields']:
                match_data['loaded_fields'].append('target')
        
        if match_data['innings'] == 1 and 'target' not in match_data['loaded_fields']:
            inn2_patterns = [
                re.search(r'2nd\s+inn', page_text, re.I),
                re.search(r'chasing\s+(\d+)', page_text, re.I),
                re.search(r'trail\s+by\s+(\d+)', page_text, re.I),
                re.search(r'require\s+(\d+)\s+runs', page_text, re.I),
                re.search(r'CRR.*?REQ', page_text, re.I),
            ]
            for pat in inn2_patterns:
                if pat:
                    match_data['innings'] = 2
                    chase_val = pat.groups()[0] if pat.groups() else None
                    if chase_val and chase_val.isdigit():
                        match_data['target'] = int(chase_val)
                        match_data['loaded_fields'].append('target')
                    break

        def is_valid_team_score(score, wickets, overs):
            """Check if parsed values look like a team innings score, not bowling figures."""
            return score >= 20 and wickets <= 10 and 0.1 <= overs <= 50

        all_score_patterns = list(re.finditer(r'([A-Z]{2,5})\s+(\d+)\s*/\s*(\d+)\s*\(\s*(\d+\.?\d*)\s*\)', page_text))

        if match_data['innings'] == 1 and len(all_score_patterns) >= 2:
            first_score = int(all_score_patterns[0].group(2))
            first_wickets = int(all_score_patterns[0].group(3))
            first_overs = float(all_score_patterns[0].group(4))
            second_score = int(all_score_patterns[1].group(2))
            second_wickets = int(all_score_patterns[1].group(3))
            second_overs = float(all_score_patterns[1].group(4))
            if is_valid_team_score(first_score, first_wickets, first_overs) and is_valid_team_score(second_score, second_wickets, second_overs):
                match_data['innings'] = 2
                match_data['target'] = first_score + 1
                match_data['current_score'] = second_score
                match_data['wickets'] = second_wickets
                match_data['overs'] = second_overs
                if 'target' not in match_data['loaded_fields']:
                    match_data['loaded_fields'].append('target')
                logger.debug(f"Detected 2nd innings from dual scores: {first_score}+1 target, {second_score}/{second_wickets} ({second_overs})")

        if match_data['innings'] == 1:
            flexible_scores = list(re.finditer(
                r'([A-Z]{2,5})\s+(\d+)(?:\s*/\s*(\d+))?\s*\(\s*(\d+\.?\d*)\s*\)',
                page_text
            ))
            valid_flex = []
            for m in flexible_scores:
                sc = int(m.group(2))
                wk = int(m.group(3)) if m.group(3) else 10
                ov = float(m.group(4))
                if is_valid_team_score(sc, wk, ov):
                    valid_flex.append((m, sc, wk, ov))
            if len(valid_flex) >= 2:
                first_score = valid_flex[0][1]
                second_score = valid_flex[1][1]
                second_wickets = valid_flex[1][2]
                second_overs = valid_flex[1][3]
                match_data['innings'] = 2
                match_data['target'] = first_score + 1
                match_data['current_score'] = second_score
                match_data['wickets'] = second_wickets
                match_data['overs'] = second_overs
                if 'target' not in match_data['loaded_fields']:
                    match_data['loaded_fields'].append('target')
                logger.debug(f"Detected 2nd innings from flexible dual scores: target={first_score+1}, {second_score}/{second_wickets} ({second_overs})")

        won_by_match = re.search(r'(\w[\w\s]*?)\s+won\s+by\s+(\d+)\s+(runs?|wickets?)', page_text, re.I)
        if won_by_match and match_data['innings'] == 1:
            match_data['innings'] = 2
            logger.debug(f"Detected completed match: {won_by_match.group(0)}")
        
        try:
            start_gmt = re.search(r'Match starts at\s+([A-Za-z]+\s+\d{1,2},?\s+\d{1,2}:\d{2})\s*GMT', page_text)
            if start_gmt:
                match_data['start_time_gmt'] = start_gmt.group(1).strip()
                match_data['loaded_fields'].append('start_time_gmt')
        except Exception as e:
            logger.debug(f"Could not extract start time: {e}")

        try:
            striker = re.search(r'batStrikerObj.*?playerName.*?([A-Za-z\s]+).*?playerScore.*?(\d+)\((\d+)\)', raw_html)
            non_striker = re.search(r'batNonStrikerObj.*?playerName.*?([A-Za-z\s]+).*?playerScore.*?(\d+)\((\d+)\)', raw_html)
            
            if striker:
                match_data['batsmen'].append({
                    'name': striker.group(1).strip().replace('\\', ''),
                    'runs': int(striker.group(2)),
                    'balls': int(striker.group(3))
                })
            if non_striker:
                match_data['batsmen'].append({
                    'name': non_striker.group(1).strip().replace('\\', ''),
                    'runs': int(non_striker.group(2)),
                    'balls': int(non_striker.group(3))
                })
            if match_data['batsmen']:
                match_data['loaded_fields'].append('batsmen')
        except Exception as e:
            logger.debug(f"Could not extract batsmen from Cricbuzz: {e}")
        
        is_odi = 'ODI' in page_text or 'One Day' in page_text
        max_overs_per_bowler = 10.0 if is_odi else 4.0
        
        bowler_patterns = [
            r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})\s+(\d+\.?\d*)-(\d+)-(\d+)-(\d+)',
            r'([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[^0-9]*(\d+\.?\d*-\d+-\d+-\d+)',
        ]
        
        seen_bowlers = set()
        
        for pattern in bowler_patterns:
            matches = re.findall(pattern, page_text)
            for match in matches:
                name = match[0].strip()
                if name.lower() not in seen_bowlers and 'Menu' not in name and 'Live' not in name:
                    try:
                        if len(match) == 5:
                            overs_bowled = float(match[1])
                            match_data['bowlers'].append({
                                'name': name,
                                'overs_bowled': overs_bowled,
                                'maidens': int(match[2]),
                                'runs_conceded': int(match[3]),
                                'wickets': int(match[4]),
                                'overs_remaining': max(0, max_overs_per_bowler - overs_bowled)
                            })
                            seen_bowlers.add(name.lower())
                        elif len(match) == 2:
                            figures = match[1]
                            parts = figures.split('-')
                            if len(parts) == 4:
                                overs_bowled = float(parts[0])
                                match_data['bowlers'].append({
                                    'name': name.strip(),
                                    'overs_bowled': overs_bowled,
                                    'maidens': int(parts[1]),
                                    'runs_conceded': int(parts[2]),
                                    'wickets': int(parts[3]),
                                    'overs_remaining': max(0, max_overs_per_bowler - overs_bowled)
                                })
                                seen_bowlers.add(name.lower())
                    except (ValueError, IndexError):
                        pass
        
        to_pattern = re.findall(r'([A-Z][a-z]+ [A-Z][a-z]+) to ([A-Z][a-z]+)', raw_html)
        if to_pattern:
            match_data['last_over_bowler'] = to_pattern[-1][0]
        
        if match_data['bowlers']:
            match_data['loaded_fields'].append('bowlers')
        
        page_text_pipe = soup.get_text(separator='|', strip=True)
        venue_pipe = re.search(r'Venue:\|([^|]+)', page_text_pipe)
        if venue_pipe:
            match_data['venue'] = re.sub(r'\s+', ' ', venue_pipe.group(1)).strip()
            match_data['loaded_fields'].append('venue')
        else:
            venue_match = re.search(r'venue.*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Stadium|Ground|Cricket Ground|Sports Club|Oval|Park)))', raw_html, re.I)
            if venue_match:
                match_data['venue'] = re.sub(r'\s+', ' ', venue_match.group(1)).strip()
                match_data['loaded_fields'].append('venue')
        
        yet_to_bat = []
        bowling_team_11 = []
        try:
            scorecard_url = f"https://www.cricbuzz.com/live-cricket-scorecard/{match_id}?_cb={cache_bust}"
            sc_response = requests.get(scorecard_url, headers=HEADERS, timeout=10)
            if sc_response.status_code == 200:
                sc_html = sc_response.text
                sc_soup = BeautifulSoup(sc_html, 'html.parser')
                
                current_innings = match_data.get('innings', 1)
                innings_markers = re.findall(r'([\w\s]+)\s+Innings', sc_html)
                logger.debug(f"Found innings markers: {innings_markers}, current innings: {current_innings}")
                
                current_batting_team = None
                if current_innings == 2 and len(innings_markers) >= 2:
                    current_batting_team = innings_markers[1].strip()
                elif len(innings_markers) >= 1:
                    current_batting_team = innings_markers[0].strip()
                
                logger.debug(f"Current batting team: {current_batting_team}")
                
                innings_sections = re.split(r'([\w\s]+\s+Innings)', sc_html)
                target_section = None
                
                for i, section in enumerate(innings_sections):
                    if current_batting_team and current_batting_team in section:
                        if i + 1 < len(innings_sections):
                            target_section = innings_sections[i] + innings_sections[i + 1]
                            logger.debug(f"Found target innings section for {current_batting_team}")
                            break
                
                try:
                    sc_text = sc_soup.get_text(separator=' ', strip=True)
                    bowling_parts = re.split(r'Bowler\s+O\s+M\s+R\s+W(?:\s+NB\s+WD\s+ECO)?', sc_text)
                    target_bowl_idx = current_innings if current_innings <= len(bowling_parts) - 1 else 1
                    if len(bowling_parts) > target_bowl_idx:
                        bowl_text = bowling_parts[target_bowl_idx]
                        end_match = re.search(r'Fall of Wickets|Yet to Bat|\d+(?:st|nd|rd|th)\s+Innings|Extras|Total', bowl_text)
                        bowl_text = bowl_text[:end_match.start()] if end_match else bowl_text[:600]
                        entries = re.findall(
                            r'([A-Z][a-zA-Z\'\-]+(?:\s+[A-Za-z\'\-]+){1,4}(?:\s*\([cwk]+\))?)\s+(\d+\.?\d*)\s+(\d+)\s+(\d+)\s+(\d+)',
                            bowl_text
                        )
                        if entries:
                            match_data['bowlers'] = []
                            skip_words = {'Bowler', 'Menu', 'Live', 'Total', 'Extras', 'Fall'}
                            for entry in entries:
                                name = re.sub(r'\s*\([cwk]+\)', '', entry[0]).strip()
                                name = re.sub(r'\s+', ' ', name)
                                if name and len(name) > 2 and not any(w in name for w in skip_words):
                                    overs_bowled = float(entry[1])
                                    match_data['bowlers'].append({
                                        'name': name,
                                        'overs_bowled': overs_bowled,
                                        'maidens': int(entry[2]),
                                        'runs_conceded': int(entry[3]),
                                        'wickets': int(entry[4]),
                                        'overs_remaining': max(0, max_overs_per_bowler - overs_bowled)
                                    })
                            if match_data['bowlers'] and 'bowlers' not in match_data['loaded_fields']:
                                match_data['loaded_fields'].append('bowlers')
                            logger.debug(f"Scorecard bowling: {len(match_data['bowlers'])} bowlers from innings {current_innings}")
                except Exception as e:
                    logger.debug(f"Could not extract bowlers from scorecard section: {e}")

                if target_section:
                    ytb_match = re.search(r'Yet to Bat.*?</div>\s*</div>\s*</div>', target_section, re.DOTALL | re.IGNORECASE)
                    if ytb_match:
                        ytb_html = ytb_match.group(0)
                        ytb_soup = BeautifulSoup(ytb_html, 'html.parser')
                        ytb_links = ytb_soup.find_all('a', href=re.compile(r'/profiles/\d+'))
                        for link in ytb_links[:8]:
                            pname = link.get_text(strip=True)
                            pname = re.sub(r'\s*\([wkc]+\)', '', pname).strip().rstrip(',')
                            if pname and len(pname) > 1:
                                yet_to_bat.append({'name': pname})
                        if not yet_to_bat:
                            players = re.findall(r'>([A-Z][a-zA-Z\'\-]+ [A-Za-z\'\-]+(?:\s+[A-Za-z\'\-]+)?(?:\s*\([wkc]+\))?)', ytb_html)
                            for p in players[:8]:
                                clean_name = re.sub(r'\s*\([wkc]+\)', '', p).strip().rstrip(',')
                                yet_to_bat.append({'name': clean_name})
                        logger.debug(f"Extracted yet to bat from {current_batting_team}'s section: {[p['name'] for p in yet_to_bat]}")
                else:
                    ytb_sections = list(re.finditer(r'Yet to Bat.*?</div>\s*</div>\s*</div>', sc_html, re.DOTALL | re.IGNORECASE))
                    if current_innings == 2 and len(ytb_sections) >= 2:
                        ytb_html = ytb_sections[1].group(0)
                    elif len(ytb_sections) >= 1:
                        ytb_html = ytb_sections[0].group(0)
                    else:
                        ytb_html = ""
                    
                    if ytb_html:
                        ytb_soup = BeautifulSoup(ytb_html, 'html.parser')
                        ytb_links = ytb_soup.find_all('a', href=re.compile(r'/profiles/\d+'))
                        for link in ytb_links[:8]:
                            pname = link.get_text(strip=True)
                            pname = re.sub(r'\s*\([wkc]+\)', '', pname).strip().rstrip(',')
                            if pname and len(pname) > 1:
                                yet_to_bat.append({'name': pname})
                        if not yet_to_bat:
                            players = re.findall(r'>([A-Z][a-zA-Z\'\-]+ [A-Za-z\'\-]+(?:\s+[A-Za-z\'\-]+)?(?:\s*\([wkc]+\))?)', ytb_html)
                            for p in players[:8]:
                                clean_name = re.sub(r'\s*\([wkc]+\)', '', p).strip().rstrip(',')
                                yet_to_bat.append({'name': clean_name})
                        logger.debug(f"Extracted yet to bat (fallback): {[p['name'] for p in yet_to_bat]}")
                
                batting_crease_names = set()
                for b in match_data.get('batsmen', []):
                    if isinstance(b, dict):
                        batting_crease_names.add(b.get('name', '').lower().strip())
                for ytb in yet_to_bat:
                    if isinstance(ytb, dict):
                        batting_crease_names.add(ytb.get('name', '').lower().strip())
                
                bowling_team_names = set()
                try:
                    squads_url = f"https://www.cricbuzz.com/cricket-match-squads/{match_id}"
                    sq_response = requests.get(squads_url, headers=HEADERS, timeout=10)
                    if sq_response.status_code == 200:
                        sq_soup = BeautifulSoup(sq_response.text, 'html.parser')
                        sq_links = sq_soup.find_all('a', href=re.compile(r'/profiles/\d+'))
                        seen_hrefs = set()
                        all_squad_players = []
                        roles_to_strip = ['Batter', 'Bowler', 'Batting Allrounder', 'Bowling Allrounder', 'WK-Batter', 'Allrounder']
                        for sq_link in sq_links:
                            sq_href = sq_link.get('href', '')
                            if sq_href in seen_hrefs:
                                continue
                            seen_hrefs.add(sq_href)
                            pname = sq_link.get_text(strip=True)
                            pname = re.sub(r'\((?:WK|C|wk|c)\)', '', pname).strip()
                            for role in roles_to_strip:
                                if pname.endswith(role):
                                    pname = pname[:-len(role)].strip()
                            pname = re.sub(r'WK-$', '', pname).strip()
                            if pname and len(pname) > 2 and not any(k in pname for k in ['Menu', 'Coach', 'Trainer', 'Analyst', 'Manager', 'Physio', 'Head']):
                                all_squad_players.append(pname)
                        
                        team1_xi = all_squad_players[:11]
                        team2_xi = all_squad_players[11:22]
                        
                        team1_lower = {n.lower() for n in team1_xi}
                        team2_lower = {n.lower() for n in team2_xi}
                        
                        overlap_team1 = len(batting_crease_names & team1_lower)
                        overlap_team2 = len(batting_crease_names & team2_lower)
                        
                        if overlap_team1 > overlap_team2 and overlap_team1 >= 2:
                            bowling_xi = team2_xi
                            match_data['bowling_team_squad_idx'] = 1
                            logger.debug(f"Batting team is team1 (overlap {overlap_team1} vs {overlap_team2}), bowling XI = team2: {team2_xi}")
                        elif overlap_team2 > overlap_team1 and overlap_team2 >= 2:
                            bowling_xi = team1_xi
                            match_data['bowling_team_squad_idx'] = 0
                            logger.debug(f"Batting team is team2 (overlap {overlap_team2} vs {overlap_team1}), bowling XI = team1: {team1_xi}")
                        elif overlap_team1 > 0 or overlap_team2 > 0:
                            if overlap_team1 >= overlap_team2:
                                bowling_xi = team2_xi
                            else:
                                bowling_xi = team1_xi
                            logger.debug(f"Low-confidence squad overlap ({overlap_team1} vs {overlap_team2}), not setting squad idx")
                        else:
                            bowling_xi = team2_xi
                            logger.debug(f"No squad overlap detected, defaulting bowling XI = team2")
                        
                        bowling_team_names = set(bowling_xi)
                        logger.debug(f"Full bowling XI from squads page: {bowling_xi}")
                except Exception as e:
                    logger.debug(f"Could not fetch squads page: {e}")
                
                scorecard_bowlers = []
                scorecard_seen = set()
                
                def extract_bowler_from_element(name, overs_bowled, maidens, runs, wickets):
                    """Parse and validate a bowler entry, appending to scorecard_bowlers if valid."""
                    name = re.sub(r'\s*\([wkc]+\)', '', name).strip()
                    if not name or len(name) <= 2 or name.lower() in scorecard_seen:
                        return
                    if any(skip in name.lower() for skip in ['total', 'extras', 'menu', 'live']):
                        return
                    if re.match(r'^\d', name):
                        return
                    scorecard_bowlers.append({
                        'name': name,
                        'overs_bowled': overs_bowled,
                        'maidens': maidens,
                        'runs_conceded': runs,
                        'wickets': wickets,
                        'overs_remaining': max(0, max_overs_per_bowler - overs_bowled)
                    })
                    scorecard_seen.add(name.lower())
                    logger.debug(f"Extracted bowler from scorecard: {name} - {overs_bowled}-{maidens}-{runs}-{wickets}")
                
                sc_bowling_section = None
                if target_section:
                    bowling_header = re.search(r'Bowling', target_section, re.I)
                    if bowling_header:
                        sc_bowling_section = target_section[bowling_header.start():]
                        logger.debug("Found bowling section within current innings section")
                
                if not sc_bowling_section:
                    bowling_sections = list(re.finditer(r'Bowling', sc_html, re.I))
                    if current_innings == 2 and len(bowling_sections) >= 2:
                        sc_bowling_section = sc_html[bowling_sections[1].start():]
                        if len(bowling_sections) >= 3:
                            sc_bowling_section = sc_html[bowling_sections[1].start():bowling_sections[2].start()]
                        logger.debug("Using 2nd bowling section for 2nd innings")
                    elif len(bowling_sections) >= 1:
                        end_pos = bowling_sections[1].start() if len(bowling_sections) >= 2 else len(sc_html)
                        sc_bowling_section = sc_html[bowling_sections[0].start():end_pos]
                        logger.debug("Using 1st bowling section for 1st innings")
                
                if sc_bowling_section:
                    bowling_soup = BeautifulSoup(sc_bowling_section, 'html.parser')
                    
                    sc_tables = bowling_soup.find_all('table')
                    for table in sc_tables:
                        rows = table.find_all('tr')
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 4:
                                link = cells[0].find('a')
                                name_text = link.get_text(strip=True) if link else cells[0].get_text(strip=True)
                                row_text = ' '.join(c.get_text(strip=True) for c in cells[1:5])
                                figures = re.search(r'(\d+\.?\d*)\s+(\d+)\s+(\d+)\s+(\d+)', row_text)
                                if figures and name_text:
                                    extract_bowler_from_element(name_text, float(figures.group(1)), int(figures.group(2)), int(figures.group(3)), int(figures.group(4)))
                    
                    if not scorecard_bowlers:
                        bowling_divs = bowling_soup.find_all('div', class_=re.compile(r'cb-col.*cb-scrd-itms', re.I))
                        for div in bowling_divs:
                            div_text = div.get_text(separator=' ', strip=True)
                            figures = re.search(r'(\d+\.?\d*)\s+(\d+)\s+(\d+)\s+(\d+)', div_text)
                            if figures:
                                name_elem = div.find('a')
                                if name_elem:
                                    name = name_elem.get_text(strip=True)
                                    overs_bowled = float(figures.group(1))
                                    if overs_bowled > 0:
                                        extract_bowler_from_element(name, overs_bowled, int(figures.group(2)), int(figures.group(3)), int(figures.group(4)))
                    
                    if not scorecard_bowlers:
                        bowling_text = bowling_soup.get_text()
                        bowl_pattern = r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})\s+(\d+\.?\d*)-(\d+)-(\d+)-(\d+)'
                        bowl_matches = re.findall(bowl_pattern, bowling_text)
                        for bm in bowl_matches:
                            extract_bowler_from_element(bm[0].strip(), float(bm[1]), int(bm[2]), int(bm[3]), int(bm[4]))
                
                if scorecard_bowlers:
                    merged = list(scorecard_bowlers)
                    for lb in match_data.get('bowlers', []):
                        if lb['name'].lower() not in scorecard_seen:
                            merged.append(lb)
                    match_data['bowlers'] = merged
                    logger.debug(f"Replaced bowlers with scorecard data: {len(scorecard_bowlers)} from scorecard, {len(merged)} total")
                else:
                    logger.debug(f"No scorecard bowlers found, keeping {len(match_data.get('bowlers', []))} from live page")
                
                if bowling_team_names:
                    bowling_team_names_lower = {n.lower() for n in bowling_team_names}
                    filtered_bowlers = []
                    for bowler in match_data['bowlers']:
                        if bowler['name'].lower() in bowling_team_names_lower:
                            filtered_bowlers.append(bowler)
                        else:
                            logger.debug(f"Filtered out bowler (not in bowling team): {bowler['name']}")
                    if filtered_bowlers:
                        match_data['bowlers'] = filtered_bowlers
                    else:
                        logger.debug("Squad filter would remove ALL bowlers - keeping unfiltered list")
                
                bowling_team_11 = list(bowling_team_names)[:11] if bowling_team_names else []
                
                logger.debug(f"Extracted bowling team 11: {bowling_team_11}")
                logger.debug(f"Total bowlers in match_data after processing: {len(match_data['bowlers'])}")
                
        except Exception as e:
            logger.debug(f"Could not fetch scorecard data: {e}")
        
        crease_names = set()
        for b in match_data.get('batsmen', []):
            if isinstance(b, dict):
                crease_names.add(b.get('name', '').lower().strip())
            else:
                crease_names.add(str(b).lower().strip())
        yet_to_bat = [p for p in yet_to_bat if p.get('name', '').lower().strip() not in crease_names]
        
        match_data['yet_to_bat'] = yet_to_bat
        match_data['bowling_team_11'] = bowling_team_11
        
        if len(match_data['loaded_fields']) < 4:
            match_data['partial'] = True
        
        return match_data
        
    except Exception as e:
        logger.error(f"Error fetching Cricbuzz match details: {e}")
        match_data['partial'] = True
        return match_data


def refresh_live_matches() -> List[Dict]:
    """Force refresh of live matches cache"""
    global live_matches_cache
    matches = get_live_matches()
    live_matches_cache = {
        'matches': matches,
        'timestamp': datetime.now()
    }
    return matches


def get_cached_live_matches() -> List[Dict]:
    """Get live matches with caching"""
    global live_matches_cache
    
    if live_matches_cache:
        cache_age = (datetime.now() - live_matches_cache['timestamp']).seconds
        if cache_age < CACHE_DURATION_SECONDS:
            return live_matches_cache['matches']
    
    return refresh_live_matches()
