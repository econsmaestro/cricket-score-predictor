"""Cricket match score prediction engine.

Provides real-time score predictions for T20 and ODI cricket matches based on
current match state, venue statistics, player performance data, and phase-based
run rate modeling. Supports both men's and women's formats.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
from ipl_stats import (
    get_comprehensive_batting_stats, get_comprehensive_bowling_stats,
    get_venue_stats, PHASE_RUN_RATES, calculate_matchup_factor,
    get_current_phase, get_remaining_phase_overs, calculate_phase_projected_runs,
    VENUE_HISTORICAL_STATS,
    get_batting_phase_modifier, get_bowling_phase_modifier
)
from player_data import get_player_by_name

IPL_VENUES = [
    "M. Chinnaswamy Stadium, Bengaluru",
    "Wankhede Stadium, Mumbai", 
    "Eden Gardens, Kolkata",
    "Arun Jaitley Stadium, Delhi",
    "MA Chidambaram Stadium, Chennai",
    "Rajiv Gandhi International Stadium, Hyderabad",
    "Sawai Mansingh Stadium, Jaipur",
    "Punjab Cricket Association Stadium, Mohali",
    "Narendra Modi Stadium, Ahmedabad",
    "DY Patil Stadium, Navi Mumbai",
    "Brabourne Stadium, Mumbai",
    "Maharashtra Cricket Association Stadium, Pune",
    "Himachal Pradesh Cricket Association Stadium, Dharamsala",
    "Holkar Cricket Stadium, Indore",
    "JSCA International Stadium Complex, Ranchi",
    "Barabati Stadium, Cuttack",
    "Ekana Cricket Stadium, Lucknow"
]

ALL_VENUES = list(VENUE_HISTORICAL_STATS.keys())

COUNTRY_TIMEZONES = {
    "India": "Asia/Kolkata",
    "Australia": "Australia/Sydney",
    "England": "Europe/London",
    "South Africa": "Africa/Johannesburg",
    "New Zealand": "Pacific/Auckland",
    "Pakistan": "Asia/Karachi",
    "West Indies": "America/Barbados",
    "Sri Lanka": "Asia/Colombo",
    "Bangladesh": "Asia/Dhaka",
    "Zimbabwe": "Africa/Harare",
    "Afghanistan": "Asia/Kabul",
    "Ireland": "Europe/Dublin",
    "UAE": "Asia/Dubai",
    "USA": "America/New_York",
    "Scotland": "Europe/London",
    "Netherlands": "Europe/Amsterdam",
    "Nepal": "Asia/Kathmandu",
    "Namibia": "Africa/Windhoek",
    "Oman": "Asia/Muscat",
    "Canada": "America/Toronto",
    "Hong Kong": "Asia/Hong_Kong",
    "Kenya": "Africa/Nairobi",
    "Uganda": "Africa/Kampala",
    "Papua New Guinea": "Pacific/Port_Moresby",
}

VENUE_TIMEZONE_OVERRIDES = {
    "Perth Stadium, Perth": "Australia/Perth",
    "Optus Stadium, Perth": "Australia/Perth",
    "Adelaide Oval, Adelaide": "Australia/Adelaide",
    "The Gabba, Brisbane": "Australia/Brisbane",
    "Bellerive Oval, Hobart": "Australia/Hobart",
    "Manuka Oval, Canberra": "Australia/Sydney",
    "Melbourne Cricket Ground, Melbourne": "Australia/Melbourne",
    "Sydney Cricket Ground, Sydney": "Australia/Sydney",
    "Grand Prairie Stadium, Texas": "America/Chicago",
    "Nassau County International Cricket Stadium, New York": "America/New_York",
    "Broward County Stadium, Florida": "America/New_York",
    "Providence Stadium, Guyana": "America/Guyana",
}

def get_venue_timezone(venue: str) -> str:
    """Resolve the IANA timezone string for a cricket venue.

    Args:
        venue: Full venue name as stored in VENUE_HISTORICAL_STATS.

    Returns:
        IANA timezone identifier (e.g. 'Asia/Kolkata'). Falls back to 'UTC'
        if neither a venue-specific override nor the venue's country is found.
    """
    if venue in VENUE_TIMEZONE_OVERRIDES:
        return VENUE_TIMEZONE_OVERRIDES[venue]
    stats = VENUE_HISTORICAL_STATS.get(venue, {})
    country = stats.get("country", "")
    return COUNTRY_TIMEZONES.get(country, "UTC")

def get_venues_by_country() -> Dict[str, List[str]]:
    """Group all known venues by their country, sorted alphabetically.

    Returns:
        Dict mapping country name to a sorted list of venue names.
    """
    venues_by_country = {}
    for venue, stats in VENUE_HISTORICAL_STATS.items():
        country = stats.get("country", "Other")
        if country not in venues_by_country:
            venues_by_country[country] = []
        venues_by_country[country].append(venue)
    for country in venues_by_country:
        venues_by_country[country].sort()
    return venues_by_country

DEFAULT_VENUE_FACTORS = {"avg_score": 165, "boundary_rate": 0.15, "wicket_rate": 0.088}

TEAM_FIELDING_EFFICIENCY = {
    "India": 0.92,
    "Australia": 0.94,
    "England": 0.90,
    "New Zealand": 0.93,
    "South Africa": 0.91,
    "Pakistan": 0.82,
    "Sri Lanka": 0.84,
    "Bangladesh": 0.80,
    "West Indies": 0.85,
    "Afghanistan": 0.79,
    "Zimbabwe": 0.78,
    "Ireland": 0.81,
    "Netherlands": 0.77,
    "Scotland": 0.79,
    "Namibia": 0.76,
    "USA": 0.78,
    "Nepal": 0.75,
    "Oman": 0.74,
    "UAE": 0.76,
    "Canada": 0.75,
    "Kenya": 0.73,
    "Uganda": 0.72,
    "Papua New Guinea": 0.71,
    "Hong Kong": 0.74,
    "India W": 0.88,
    "Australia W": 0.93,
    "England W": 0.90,
    "South Africa W": 0.87,
    "New Zealand W": 0.89,
    "West Indies W": 0.83,
    "Pakistan W": 0.78,
    "Sri Lanka W": 0.79,
    "Bangladesh W": 0.76,
}

FIELDING_TEAMS = sorted(TEAM_FIELDING_EFFICIENCY.keys())

def get_fielding_modifier(fielding_team: str) -> dict:
    efficiency = TEAM_FIELDING_EFFICIENCY.get(fielding_team, 0.85)
    drop_rate = 1.0 - efficiency
    baseline_drop = 0.15
    relative_drop = drop_rate / baseline_drop

    wicket_mod = 1.0 + (efficiency - 0.85) * 1.5
    wicket_mod = max(0.7, min(1.3, wicket_mod))

    run_mod = 1.0 + (baseline_drop - drop_rate) * -2.0
    run_mod = max(0.9, min(1.15, run_mod))

    boundary_save_mod = 1.0 - (efficiency - 0.85) * 0.8
    boundary_save_mod = max(0.85, min(1.15, boundary_save_mod))

    return {
        "efficiency": efficiency,
        "wicket_modifier": wicket_mod,
        "run_modifier": run_mod,
        "boundary_modifier": boundary_save_mod,
        "drop_rate": drop_rate,
    }

def classify_bowler_type(bowling_style: str) -> str:
    """Classify a bowler as 'pace', 'spin', or 'unknown' based on bowling style."""
    if not bowling_style:
        return "unknown"
    style_lower = bowling_style.lower()
    pace_keywords = ['fast', 'medium', 'seam']
    spin_keywords = ['spin', 'offbreak', 'orthodox', 'leg-break', 'legbreak', 'chinaman', 'googly', 'slow']
    if any(kw in style_lower for kw in pace_keywords):
        return "pace"
    if any(kw in style_lower for kw in spin_keywords):
        return "spin"
    return "unknown"

def get_bowler_type_from_name(bowler_name: str) -> str:
    """Get bowler type from player database."""
    player = get_player_by_name(bowler_name)
    if player and player.get("bowling_style"):
        return classify_bowler_type(player["bowling_style"])
    return "unknown"

def get_venue_bowler_modifier(venue: str, bowler_name: str) -> tuple:
    """Get venue-based modifier for bowler effectiveness and return (modifier, bowler_type)."""
    venue_factors = get_venue_factors(venue)
    bowler_type = get_bowler_type_from_name(bowler_name)
    
    if bowler_type == "pace":
        modifier = venue_factors.get("pace_effectiveness", 1.0)
    elif bowler_type == "spin":
        modifier = venue_factors.get("spin_effectiveness", 1.0)
    else:
        modifier = 1.0
    
    return modifier, bowler_type

def get_venue_conditions(venue: str) -> dict:
    """Get detailed venue conditions including pitch type classification."""
    stats = VENUE_HISTORICAL_STATS.get(venue, {})
    pace_pct = stats.get("pace_wickets_pct", 0.48)
    spin_pct = stats.get("spin_wickets_pct", 0.40)
    avg_score = stats.get("avg_1st_innings", 165)
    
    if pace_pct >= 0.55:
        pitch_type = "pace-friendly"
        pitch_desc = "Seam movement expected - pace bowlers have advantage"
    elif spin_pct >= 0.48:
        pitch_type = "spin-friendly"
        pitch_desc = "Turning track - spinners could dominate"
    elif avg_score >= 175:
        pitch_type = "batting-paradise"
        pitch_desc = "High-scoring venue - batters have advantage"
    else:
        pitch_type = "balanced"
        pitch_desc = "Even contest between bat and ball"
    
    pace_multiplier = 1.0 + (pace_pct - 0.48) * 0.5
    spin_multiplier = 1.0 + (spin_pct - 0.40) * 0.5
    
    return {
        "pitch_type": pitch_type,
        "pitch_description": pitch_desc,
        "pace_wickets_pct": pace_pct,
        "spin_wickets_pct": spin_pct,
        "pace_effectiveness": min(1.25, max(0.75, pace_multiplier)),
        "spin_effectiveness": min(1.25, max(0.75, spin_multiplier)),
        "avg_score": avg_score
    }

def get_venue_factors(venue: str) -> dict:
    """Compute batting/bowling adjustment factors for a venue.

    Derives boundary rate, wicket rate, pace/spin effectiveness, and pitch
    classification from historical venue statistics.

    Args:
        venue: Full venue name.

    Returns:
        Dict with keys: avg_score, boundary_rate, wicket_rate,
        pace_effectiveness, spin_effectiveness, pitch_type, pitch_description.
    """
    stats = VENUE_HISTORICAL_STATS.get(venue, {})
    if stats:
        venue_conditions = get_venue_conditions(venue)
        return {
            "avg_score": stats.get("avg_1st_innings", 165),
            "boundary_rate": 0.15 + (stats.get("avg_1st_innings", 165) - 165) * 0.001,
            "wicket_rate": 0.088 + (165 - stats.get("avg_1st_innings", 165)) * 0.0005,
            "pace_effectiveness": venue_conditions["pace_effectiveness"],
            "spin_effectiveness": venue_conditions["spin_effectiveness"],
            "pitch_type": venue_conditions["pitch_type"],
            "pitch_description": venue_conditions["pitch_description"]
        }
    return {**DEFAULT_VENUE_FACTORS, "pace_effectiveness": 1.0, "spin_effectiveness": 1.0, 
            "pitch_type": "balanced", "pitch_description": "Even contest between bat and ball"}

@dataclass
class Batsman:
    """Current batting state for a batsman at the crease.

    Attributes:
        name: Player's full name.
        runs: Runs scored in the current innings.
        balls_faced: Balls faced in the current innings.
    """
    name: str
    runs: int
    balls_faced: int
    
    @property
    def strike_rate(self) -> float:
        if self.balls_faced == 0:
            return 0.0
        return (self.runs / self.balls_faced) * 100

@dataclass
class Bowler:
    """Current bowling figures for a bowler in the match.

    Attributes:
        name: Player's full name.
        overs_bowled: Overs bowled so far in the innings.
        runs_conceded: Runs given away.
        wickets: Wickets taken.
        overs_remaining: Overs left in the bowler's spell quota.
    """
    name: str
    overs_bowled: float
    runs_conceded: int
    wickets: int
    overs_remaining: float
    
    @property
    def economy(self) -> float:
        if self.overs_bowled == 0:
            return 8.0
        return self.runs_conceded / self.overs_bowled

# Format-specific rules: overs limit, bowler quota, average score, and ODI flag
FORMAT_CONFIG = {
    'mens_t20': {'max_overs': 20, 'max_bowler_overs': 4, 'avg_score': 165, 'is_odi': False},
    'womens_t20': {'max_overs': 20, 'max_bowler_overs': 4, 'avg_score': 140, 'is_odi': False},
    'mens_odi': {'max_overs': 50, 'max_bowler_overs': 10, 'avg_score': 280, 'is_odi': True},
    'womens_odi': {'max_overs': 50, 'max_bowler_overs': 10, 'avg_score': 230, 'is_odi': True}
}

# ODI phase benchmarks: run rates, risk, wicket rates, and ball outcome probabilities per phase
ODI_PHASE_RUN_RATES = {
    "powerplay_1": {"overs": (0, 10), "avg_runs_per_over": 5.8, "strike_rate": 95, "risk_factor": 1.15, "wicket_per_over": 0.12, "boundary_rate": 0.18, "dot_ball_rate": 0.35},
    "middle_1": {"overs": (10, 30), "avg_runs_per_over": 5.2, "strike_rate": 88, "risk_factor": 1.0, "wicket_per_over": 0.10, "boundary_rate": 0.12, "dot_ball_rate": 0.42},
    "middle_2": {"overs": (30, 40), "avg_runs_per_over": 5.6, "strike_rate": 95, "risk_factor": 1.05, "wicket_per_over": 0.11, "boundary_rate": 0.15, "dot_ball_rate": 0.38},
    "death": {"overs": (40, 50), "avg_runs_per_over": 7.5, "strike_rate": 120, "risk_factor": 1.35, "wicket_per_over": 0.18, "boundary_rate": 0.25, "dot_ball_rate": 0.28}
}

def get_format_config(match_format: str) -> dict:
    """Look up format configuration by match format key.

    Args:
        match_format: One of 'mens_t20', 'womens_t20', 'mens_odi', 'womens_odi'.

    Returns:
        Dict with max_overs, max_bowler_overs, avg_score, is_odi. Defaults to
        mens_t20 if the format key is unrecognised.
    """
    return FORMAT_CONFIG.get(match_format, FORMAT_CONFIG['mens_t20'])

def get_odi_phase(overs: float) -> str:
    """Determine the current ODI phase based on overs completed.

    Args:
        overs: Overs bowled so far.

    Returns:
        Phase key: 'powerplay_1', 'middle_1', 'middle_2', or 'death'.
    """
    if overs < 10:
        return "powerplay_1"
    elif overs < 30:
        return "middle_1"
    elif overs < 40:
        return "middle_2"
    else:
        return "death"

def get_odi_remaining_phase_overs(overs_completed: float) -> Dict[str, float]:
    """Calculate remaining overs in each ODI phase from current position.

    Args:
        overs_completed: Overs bowled so far.

    Returns:
        Dict mapping phase key to the number of overs still available in that phase.
    """
    remaining = {}
    if overs_completed < 10:
        remaining["powerplay_1"] = 10 - overs_completed
        remaining["middle_1"] = 20
        remaining["middle_2"] = 10
        remaining["death"] = 10
    elif overs_completed < 30:
        remaining["middle_1"] = 30 - overs_completed
        remaining["middle_2"] = 10
        remaining["death"] = 10
    elif overs_completed < 40:
        remaining["middle_2"] = 40 - overs_completed
        remaining["death"] = 10
    else:
        remaining["death"] = 50 - overs_completed
    return remaining

@dataclass
class MatchState:
    """Snapshot of the current match situation used as input to the prediction engine.

    Captures batting/bowling lineups, score, venue, format, and innings context
    so that predict_score() can project the final outcome.
    """
    current_score: int
    wickets_fallen: int
    overs_completed: float
    venue: str
    batsmen: List[Batsman]
    bowlers: List[Bowler]
    next_over_bowler: str = ""
    last_over_bowler: str = ""
    batsmen_to_come: Optional[List[str]] = None
    innings: int = 1
    target: int = 0
    match_format: str = "mens_t20"
    fielding_team: str = ""
    
    def __post_init__(self):
        if self.batsmen_to_come is None:
            self.batsmen_to_come = []
    
    @property
    def format_config(self) -> dict:
        return get_format_config(self.match_format)
    
    @property
    def max_overs(self) -> int:
        return self.format_config['max_overs']
    
    @property
    def max_bowler_overs(self) -> int:
        return self.format_config['max_bowler_overs']
    
    @property
    def is_odi(self) -> bool:
        return self.format_config['is_odi']

@dataclass
class PredictionResult:
    """Output of the predict_score() engine containing all prediction metrics.

    Includes projected final score, next-over breakdown, win probability for
    chases, and venue/bowler context used in the prediction.
    """
    predicted_final_score: int
    predicted_wickets: int
    predicted_next_over_runs: int
    score_range: Tuple[int, int]
    wicket_probability: float
    boundary_count: int
    dot_ball_count: int
    singles_doubles_count: int
    win_probability: float = 0.0
    is_chase: bool = False
    runs_needed: int = 0
    required_run_rate: float = 0.0
    pitch_type: str = "balanced"
    pitch_description: str = ""
    bowler_type: str = "unknown"
    venue_bowler_advantage: float = 1.0
    auto_next_over_runs: int = 0
    bowler_specified: bool = True
    fielding_team: str = ""
    fielding_efficiency: float = 0.85
    momentum_short_term_rr: float = 0.0
    momentum_medium_term_rr: float = 0.0
    momentum_long_term_rr: float = 0.0
    momentum_factor: float = 1.0
    batsman_smoothed_sr: float = 0.0
    current_run_rate: float = 0.0
    overs_remaining: float = 0.0
    wickets_in_hand: int = 10

def validate_bowling_rules(match_state: MatchState) -> List[str]:
    """Check bowling constraints (consecutive overs, per-bowler quota).

    Args:
        match_state: Current match snapshot.

    Returns:
        List of human-readable error strings. Empty list means valid.
    """
    errors = []
    max_overs = match_state.max_overs
    max_bowler_overs = match_state.max_bowler_overs
    overs_remaining = max_overs - match_state.overs_completed
    format_name = "ODI" if match_state.is_odi else "T20"
    
    if match_state.last_over_bowler and match_state.next_over_bowler:
        if match_state.last_over_bowler == match_state.next_over_bowler:
            errors.append(f"{match_state.next_over_bowler} cannot bowl consecutive overs")
    
    for bowler in match_state.bowlers:
        if bowler.overs_bowled > max_bowler_overs:
            errors.append(f"{bowler.name} cannot bowl more than {max_bowler_overs} overs in {format_name} (currently {bowler.overs_bowled})")
        
        if bowler.overs_remaining > max_bowler_overs:
            errors.append(f"{bowler.name} cannot have more than {max_bowler_overs} overs remaining in {format_name}")
        
        total_overs = bowler.overs_bowled + bowler.overs_remaining
        if total_overs > max_bowler_overs:
            errors.append(f"{bowler.name}: bowled ({bowler.overs_bowled}) + remaining ({bowler.overs_remaining}) cannot exceed {max_bowler_overs} overs in {format_name}")
    
    for bowler in match_state.bowlers:
        if bowler.overs_remaining >= overs_remaining and overs_remaining >= max_bowler_overs:
            other_bowlers = [b for b in match_state.bowlers if b.name != bowler.name and b.overs_remaining > 0]
            if not other_bowlers:
                errors.append(f"Cannot rely on only {bowler.name} for remaining {overs_remaining} overs - need multiple bowlers")
    
    return errors

def calculate_run_rate(score: int, overs: float) -> float:
    """Calculate the current run rate.

    Args:
        score: Runs scored.
        overs: Overs bowled.

    Returns:
        Runs per over, or 0.0 if no overs bowled.
    """
    if overs == 0:
        return 0.0
    return score / overs


def calculate_blended_momentum(match_state, default_rr: float, is_odi: bool) -> float:
    """Calculate a blended momentum factor using three run-rate time windows.

    Uses short-term (current batsmen at the crease — proxy for recent form),
    medium-term (bowler economy figures — proxy for recent bowling spells),
    and long-term (overall innings CRR) windows with weighted blending.

    Exponential smoothing anchors toward the format baseline early in the
    innings (when sample size is small) but loosens as more overs are bowled,
    letting sustained trends move the projection. The final multiplier is
    clamped to [0.80, 1.20] so no single factor can dominate.

    Args:
        match_state: Current match snapshot.
        default_rr: Baseline expected run rate for the format (e.g. 8.0 for T20).
        is_odi: Whether this is an ODI match.

    Returns:
        A momentum multiplier centred around 1.0 (range 0.80 – 1.20).
    """
    overs = match_state.overs_completed
    score = match_state.current_score

    if overs <= 0:
        return {
            "factor": 1.0,
            "short_term_rr": 0.0,
            "medium_term_rr": 0.0,
            "long_term_rr": 0.0,
        }

    long_term_rr = score / overs

    medium_term_rr = long_term_rr
    if match_state.bowlers:
        recent_bowlers = [b for b in match_state.bowlers if b.overs_bowled > 0]
        if recent_bowlers:
            total_bowler_runs = sum(b.runs_conceded for b in recent_bowlers)
            total_bowler_overs = sum(b.overs_bowled for b in recent_bowlers)
            if total_bowler_overs > 0:
                medium_term_rr = total_bowler_runs / total_bowler_overs

    short_term_rr = long_term_rr
    if match_state.batsmen:
        total_bat_runs = sum(b.runs for b in match_state.batsmen if b.balls_faced > 0)
        total_bat_balls = sum(b.balls_faced for b in match_state.batsmen if b.balls_faced > 0)
        if total_bat_balls > 0:
            short_term_rr = (total_bat_runs / total_bat_balls) * 6.0

    if overs < 3:
        w_short, w_medium, w_long = 0.15, 0.25, 0.60
    elif overs < 8:
        w_short, w_medium, w_long = 0.20, 0.35, 0.45
    else:
        w_short, w_medium, w_long = 0.25, 0.40, 0.35

    blended_rr = (short_term_rr * w_short +
                  medium_term_rr * w_medium +
                  long_term_rr * w_long)

    if overs < 4:
        alpha = 0.35
    elif overs < 10:
        alpha = 0.55
    elif is_odi and overs < 30:
        alpha = 0.65
    else:
        alpha = 0.75

    smoothed_rr = alpha * blended_rr + (1 - alpha) * default_rr

    raw_momentum = smoothed_rr / default_rr if default_rr > 0 else 1.0

    clamped = min(1.20, max(0.80, raw_momentum))

    return {
        "factor": clamped,
        "short_term_rr": round(short_term_rr, 2),
        "medium_term_rr": round(medium_term_rr, 2),
        "long_term_rr": round(long_term_rr, 2),
    }


def calculate_smoothed_batsman_sr(match_state, base_sr: float, is_odi: bool) -> float:
    """Compute a smoothed average batsman strike rate that resists short-term noise.

    Blends career SR with current match SR using adaptive weights that scale
    with sample size: with fewer than 12 balls faced, career data dominates
    (60% weight) to prevent a handful of dots from crashing the projection.
    As more balls are faced the current form gets progressively more influence,
    reaching 65% weight after 60+ balls so sustained trends are reflected.

    A floor and ceiling clamp prevents extreme outliers, while an exponential
    smoothing step pulls the result toward the career average — more strongly
    in T20s where sample sizes are inherently smaller.

    Args:
        match_state: Current match snapshot with batsmen data.
        base_sr: Format baseline SR (e.g. 130 for T20, 90 for ODI).
        is_odi: Whether this is an ODI match.

    Returns:
        Smoothed strike rate for use in phase projections.
    """
    if not match_state.batsmen:
        return base_sr

    career_srs = []
    current_srs = []

    for batsman in match_state.batsmen:
        career_stats = get_comprehensive_batting_stats(batsman.name)
        if career_stats:
            career_srs.append(career_stats["sr"])

        if batsman.balls_faced > 0:
            current_srs.append(batsman.strike_rate)

    if not career_srs and not current_srs:
        return base_sr

    avg_career_sr = sum(career_srs) / len(career_srs) if career_srs else base_sr

    if not current_srs:
        return avg_career_sr

    avg_current_sr = sum(current_srs) / len(current_srs)
    total_balls = sum(b.balls_faced for b in match_state.batsmen if b.balls_faced > 0)

    if total_balls < 12:
        career_weight = 0.60
    elif total_balls < 30:
        career_weight = 0.45
    elif total_balls < 60:
        career_weight = 0.35
    else:
        career_weight = 0.25 if is_odi else 0.30

    blended_sr = avg_current_sr * (1 - career_weight) + avg_career_sr * career_weight

    sr_floor = base_sr * 0.55
    sr_ceiling = base_sr * 1.85
    blended_sr = max(sr_floor, min(sr_ceiling, blended_sr))

    if total_balls < 12:
        alpha = 0.45
    elif total_balls < 30:
        alpha = 0.60
    elif total_balls < 60:
        alpha = 0.75
    else:
        alpha = 0.85

    smoothed_sr = alpha * blended_sr + (1 - alpha) * avg_career_sr

    return smoothed_sr

def calculate_required_run_rate(target: int, current_score: int, overs_remaining: float) -> float:
    """Calculate the required run rate to reach a chase target.

    Args:
        target: Target score to chase.
        current_score: Runs scored so far.
        overs_remaining: Overs left in the innings.

    Returns:
        Required runs per over, or infinity if no overs remain.
    """
    if overs_remaining == 0:
        return float('inf')
    return (target - current_score) / overs_remaining

def predict_score(match_state: MatchState) -> PredictionResult:
    """Main prediction engine — projects the final innings score and next-over breakdown.

    The algorithm works in several stages:
    1. Retrieves venue factors and historical stats for pitch/conditions context.
    2. Computes a blended batsman strike rate from career data and current form.
    3. Determines bowler economy from the nominated next-over bowler or team average.
    4. Applies a wicket-decay factor that progressively reduces scoring potential
       as more wickets fall, with tail-quality adjustments.
    5. Estimates effective overs remaining by considering all-out probability
       based on current wicket fall rate.
    6. Projects runs phase-by-phase (powerplay/middle/death) using phase-specific
       run rates adjusted for batsman SR, momentum, and wicket pressure.
    7. Predicts next-over runs using bowler economy, venue bowling modifier,
       and phase context. Adjusts for chase intent in the 2nd innings.
    8. Calculates win probability in chases using required run rate, wickets in
       hand, momentum, and runs-per-wicket survival analysis.
    9. Computes ball-outcome distribution (boundaries, dots, singles/doubles).

    Args:
        match_state: Complete snapshot of the current match situation.

    Returns:
        PredictionResult with projected score, wickets, next-over stats,
        win probability, and supporting context.
    """
    venue_factors = get_venue_factors(match_state.venue)
    venue_historical = get_venue_stats(match_state.venue)
    format_config = match_state.format_config
    max_overs = match_state.max_overs
    is_odi = match_state.is_odi
    
    fielding_mod = get_fielding_modifier(match_state.fielding_team) if match_state.fielding_team else get_fielding_modifier("")
    
    overs_remaining = float(max_overs) - match_state.overs_completed
    default_rr = 5.5 if is_odi else 8.0
    current_run_rate = calculate_run_rate(match_state.current_score, match_state.overs_completed) if match_state.overs_completed > 0 else default_rr
    
    if is_odi:
        current_phase = get_odi_phase(match_state.overs_completed)
        remaining_phase_overs = get_odi_remaining_phase_overs(match_state.overs_completed)
        phase_rates = ODI_PHASE_RUN_RATES
    else:
        current_phase = get_current_phase(match_state.overs_completed)
        remaining_phase_overs = get_remaining_phase_overs(match_state.overs_completed)
        phase_rates = PHASE_RUN_RATES
    
    base_sr = 90.0 if is_odi else 130.0
    avg_batsman_sr = calculate_smoothed_batsman_sr(match_state, base_sr, is_odi)

    momentum_data = calculate_blended_momentum(match_state, default_rr, is_odi)
    momentum_factor = momentum_data["factor"]
    
    bowler_specified = bool(match_state.next_over_bowler and match_state.next_over_bowler.strip() and match_state.next_over_bowler != "Unknown")

    next_bowler = None
    bowler_career_stats = None
    if bowler_specified:
        for bowler in match_state.bowlers:
            if bowler.name.lower() == match_state.next_over_bowler.lower():
                next_bowler = bowler
                break
        bowler_career_stats = get_comprehensive_bowling_stats(match_state.next_over_bowler)

    if bowler_specified and next_bowler:
        bowler_economy = next_bowler.economy
    elif bowler_specified and bowler_career_stats:
        bowler_economy = bowler_career_stats["econ"]
    else:
        team_economies = [b.economy for b in match_state.bowlers if b.overs_bowled > 0]
        if team_economies:
            bowler_economy = sum(team_economies) / len(team_economies)
        else:
            bowler_economy = 8.0
    
    wickets_fallen = match_state.wickets_fallen
    
    if wickets_fallen <= 2:
        tail_quality_factor = 1.0
    elif wickets_fallen <= 4:
        tail_quality_factor = 0.85
    elif wickets_fallen <= 6:
        tail_quality_factor = 0.65
    elif wickets_fallen == 7:
        tail_quality_factor = 0.48
    elif wickets_fallen <= 8:
        tail_quality_factor = 0.38
    else:
        tail_quality_factor = 0.25
    
    wicket_factor = (1.0 - (wickets_fallen * 0.06)) * tail_quality_factor
    if wickets_fallen >= 8:
        wicket_factor = max(0.15, wicket_factor)
    elif wickets_fallen >= 7:
        wicket_factor = max(0.20, wicket_factor)
    else:
        wicket_factor = max(0.25, wicket_factor)
    
    avg_score = format_config.get('avg_score', 165)
    base_run_rate = venue_historical.get("avg_1st_innings", avg_score) / max_overs
    
    phase_projected_runs = 0.0
    phase_projected_wickets = 0.0
    
    wickets_remaining = 10 - wickets_fallen
    tail_wicket_rate_per_over = 0.12
    if wickets_fallen >= 8:
        tail_wicket_rate_per_over = 0.28
    elif wickets_fallen >= 7:
        tail_wicket_rate_per_over = 0.24
    elif wickets_fallen >= 5:
        tail_wicket_rate_per_over = 0.18
    elif wickets_fallen >= 3:
        tail_wicket_rate_per_over = 0.15
    
    if wickets_remaining > 0 and tail_wicket_rate_per_over > 0:
        expected_overs_to_allout = wickets_remaining / tail_wicket_rate_per_over
    else:
        expected_overs_to_allout = overs_remaining
    
    effective_overs_remaining = min(overs_remaining, expected_overs_to_allout)
    
    if wickets_fallen >= 8:
        effective_overs_remaining = min(effective_overs_remaining, overs_remaining * 0.5)
    elif wickets_fallen >= 6:
        effective_overs_remaining = min(effective_overs_remaining, overs_remaining * 0.75)
    
    effective_overs_remaining = max(1.0, effective_overs_remaining)
    
    overs_reduction_ratio = effective_overs_remaining / overs_remaining if overs_remaining > 0 else 1.0
    
    set_batsmen_boost = 1.0
    if match_state.batsmen and len(match_state.batsmen) >= 2:
        balls_per_bat = [b.balls_faced for b in match_state.batsmen]
        min_balls = min(balls_per_bat)
        avg_balls = sum(balls_per_bat) / len(balls_per_bat)
        set_threshold = 25 if is_odi else 15
        if min_balls >= set_threshold:
            set_batsmen_boost = 1.06 + min(0.09, (avg_balls - set_threshold) * 0.003)
        elif min_balls > 0 and avg_balls >= set_threshold:
            set_batsmen_boost = 1.03 + min(0.05, (avg_balls - set_threshold) * 0.002)
        set_batsmen_boost = min(set_batsmen_boost, 1.15)

    innings_progress = match_state.overs_completed / max_overs
    middle_phase = (0.35 <= innings_progress <= 0.65) if not is_odi else (0.20 <= innings_progress <= 0.60)
    acceleration_boost = 1.0
    if middle_phase and wickets_fallen <= 3:
        if wickets_fallen <= 1:
            acceleration_boost = 1.20
        elif wickets_fallen <= 2:
            acceleration_boost = 1.14
        else:
            acceleration_boost = 1.08
        if current_run_rate > base_run_rate * 1.1:
            acceleration_boost *= 1.05
        acceleration_boost = min(acceleration_boost, 1.30)

    for phase_name, phase_overs in remaining_phase_overs.items():
        if phase_overs > 0:
            phase_data = phase_rates[phase_name]
            
            adjusted_phase_overs = phase_overs * overs_reduction_ratio
            
            phase_base_rpo = phase_data["avg_runs_per_over"]
            phase_risk = phase_data["risk_factor"]
            phase_wicket_rate = phase_data["wicket_per_over"]
            
            bat_phase_mod = 1.0
            if not is_odi and match_state.batsmen:
                bat_mods = [get_batting_phase_modifier(b.name, phase_name) for b in match_state.batsmen]
                bat_phase_mod = sum(bat_mods) / len(bat_mods)
            
            batsman_sr_factor = (avg_batsman_sr / phase_data["strike_rate"]) * bat_phase_mod
            
            adjusted_rpo = phase_base_rpo * wicket_factor * batsman_sr_factor * momentum_factor * set_batsmen_boost
            
            if phase_name in ["powerplay", "powerplay_1"]:
                adjusted_rpo *= 1.05
            elif phase_name in ["acceleration", "finish", "death"]:
                adjusted_rpo *= phase_risk
                if acceleration_boost > 1.0:
                    adjusted_rpo *= acceleration_boost
            
            phase_projected_runs += adjusted_rpo * adjusted_phase_overs * fielding_mod["run_modifier"]
            
            phase_wickets = phase_wicket_rate * adjusted_phase_overs * fielding_mod["wicket_modifier"]
            if phase_name in ["finish", "death"]:
                phase_wickets *= 1.3
            phase_projected_wickets += phase_wickets
    
    predicted_final_score = int(match_state.current_score + phase_projected_runs)
    
    min_rpo = 3.5 if is_odi else 4
    max_rpo = 12 if is_odi else 18
    predicted_final_score = max(predicted_final_score, match_state.current_score + int(effective_overs_remaining * min_rpo))
    predicted_final_score = min(predicted_final_score, match_state.current_score + int(effective_overs_remaining * max_rpo))
    
    if match_state.innings == 2 and match_state.target > 0:
        if predicted_final_score >= match_state.target:
            predicted_final_score = match_state.target
    
    base_wicket_rate = venue_factors["wicket_rate"]
    
    if bowler_career_stats:
        career_avg = bowler_career_stats["avg"]
        if career_avg < 22:
            bowler_wicket_modifier = 1.4
        elif career_avg < 26:
            bowler_wicket_modifier = 1.2
        elif career_avg > 32:
            bowler_wicket_modifier = 0.8
        else:
            bowler_wicket_modifier = 1.0
    else:
        if bowler_economy < 6:
            bowler_wicket_modifier = 1.3
        elif bowler_economy < 8:
            bowler_wicket_modifier = 1.1
        elif bowler_economy > 10:
            bowler_wicket_modifier = 0.8
        else:
            bowler_wicket_modifier = 1.0
    
    expected_additional_wickets = phase_projected_wickets * bowler_wicket_modifier * wicket_factor
    expected_additional_wickets = expected_additional_wickets * 0.6
    expected_additional_wickets = min(expected_additional_wickets, 10 - match_state.wickets_fallen)
    expected_additional_wickets = max(1, min(expected_additional_wickets, 6))
    
    if wickets_fallen >= 8 and overs_remaining >= 5:
        expected_additional_wickets = 10 - wickets_fallen
    elif wickets_fallen >= 7 and overs_remaining >= 8:
        expected_additional_wickets = min(10 - wickets_fallen, expected_additional_wickets + 1)
    elif wickets_fallen >= 6 and overs_remaining >= 12:
        expected_additional_wickets = min(10 - wickets_fallen, expected_additional_wickets + 1)
    
    if match_state.innings == 2 and match_state.target > 0 and overs_remaining > 0:
        chase_rrr = (match_state.target - match_state.current_score) / overs_remaining
        if chase_rrr <= 4:
            expected_additional_wickets *= 0.4
        elif chase_rrr <= 5:
            expected_additional_wickets *= 0.5
        elif chase_rrr <= 6:
            expected_additional_wickets *= 0.65
        elif chase_rrr <= 7:
            expected_additional_wickets *= 0.8
        elif chase_rrr <= 8:
            expected_additional_wickets *= 0.9
        expected_additional_wickets = max(0, expected_additional_wickets)
    
    predicted_wickets = match_state.wickets_fallen + int(round(expected_additional_wickets))
    predicted_wickets = min(predicted_wickets, 10)
    
    current_phase_data = phase_rates[current_phase]
    next_over_phase_rpo = current_phase_data["avg_runs_per_over"]
    batsman_factor = (avg_batsman_sr / base_sr) if avg_batsman_sr > 0 else 1.0
    
    bowler_types_cache = {}
    for b in match_state.bowlers:
        player = get_player_by_name(b.name)
        bowler_types_cache[b.name] = classify_bowler_type(player.get("bowling_style", "") if player else "")

    pace_count = sum(1 for t in bowler_types_cache.values() if t == "pace")
    spin_count = sum(1 for t in bowler_types_cache.values() if t == "spin")
    pace_mod = venue_factors.get("pace_effectiveness", 1.0)
    spin_mod = venue_factors.get("spin_effectiveness", 1.0)
    if pace_count > 0 or spin_count > 0:
        auto_venue_bowler_mod = (pace_mod * pace_count + spin_mod * spin_count) / (pace_count + spin_count)
    else:
        auto_venue_bowler_mod = 1.0

    if bowler_specified:
        venue_bowler_mod, bowler_type = get_venue_bowler_modifier(match_state.venue, match_state.next_over_bowler)
    else:
        bowler_type = "unknown"
        venue_bowler_mod = auto_venue_bowler_mod
    venue_bowling_factor = 2.0 - venue_bowler_mod
    
    bowl_phase_mod = 1.0
    if not is_odi and bowler_specified and match_state.next_over_bowler:
        bowl_phase_mod = get_bowling_phase_modifier(match_state.next_over_bowler, current_phase)
    
    bat_next_phase_mod = 1.0
    if not is_odi and match_state.batsmen:
        bat_mods_next = [get_batting_phase_modifier(b.name, current_phase) for b in match_state.batsmen]
        bat_next_phase_mod = sum(bat_mods_next) / len(bat_mods_next)
    
    if current_phase in ["powerplay", "powerplay_1"]:
        next_over_base = max(next_over_phase_rpo, bowler_economy) * 1.1
    elif current_phase in ["acceleration", "finish", "death"]:
        next_over_base = next_over_phase_rpo * current_phase_data["risk_factor"]
    else:
        next_over_base = (bowler_economy + next_over_phase_rpo) / 2
    
    next_over_base *= venue_bowling_factor * bowl_phase_mod * bat_next_phase_mod
    
    predicted_next_over_runs = int(round(next_over_base * batsman_factor * wicket_factor * fielding_mod["run_modifier"]))
    max_next_over = 18 if is_odi else 24
    predicted_next_over_runs = max(2, min(predicted_next_over_runs, max_next_over))
    
    chase_intent_factor = 1.0
    if match_state.innings == 2 and match_state.target > 0 and overs_remaining > 0:
        chase_rrr = (match_state.target - match_state.current_score) / overs_remaining
        if chase_rrr <= 4:
            chase_intent_factor = 0.55
        elif chase_rrr <= 5:
            chase_intent_factor = 0.65
        elif chase_rrr <= 6:
            chase_intent_factor = 0.75
        elif chase_rrr <= 7:
            chase_intent_factor = 0.85
        elif chase_rrr <= 8:
            chase_intent_factor = 0.92
        elif chase_rrr <= 10:
            chase_intent_factor = 1.0
        else:
            chase_intent_factor = 1.15
        
        chase_target_rpo = chase_rrr * 1.05
        predicted_next_over_runs = int(round(
            predicted_next_over_runs * chase_intent_factor * 0.5 + chase_target_rpo * 0.5
        ))
        predicted_next_over_runs = max(2, min(predicted_next_over_runs, max_next_over))
    
    variance_factor = 0.15
    if match_state.overs_completed > 10:
        variance_factor = 0.12
    if match_state.overs_completed > 15:
        variance_factor = 0.08
    
    variance = int(predicted_final_score * variance_factor)
    score_range = (predicted_final_score - variance, predicted_final_score + variance)
    
    current_wicket_rate = current_phase_data["wicket_per_over"]
    if current_phase in ["finish", "death"]:
        current_wicket_rate *= 1.4
    wicket_probability = current_wicket_rate * bowler_wicket_modifier * venue_bowler_mod * fielding_mod["wicket_modifier"]
    if match_state.innings == 2 and match_state.target > 0 and overs_remaining > 0:
        if chase_rrr <= 4:
            wicket_probability *= 0.4
        elif chase_rrr <= 5:
            wicket_probability *= 0.55
        elif chase_rrr <= 6:
            wicket_probability *= 0.7
        elif chase_rrr <= 7:
            wicket_probability *= 0.85
        elif chase_rrr > 10:
            wicket_probability *= 1.2
    wicket_probability = min(0.55, max(0.05, wicket_probability))
    
    boundary_rate = current_phase_data.get("boundary_rate", 0.15) * batsman_factor * fielding_mod["boundary_modifier"]
    if current_phase in ["powerplay", "powerplay_1"]:
        boundary_rate *= 1.15
    elif current_phase == "acceleration":
        boundary_rate *= 1.15
    elif current_phase in ["finish", "death"]:
        boundary_rate *= 1.25
    if chase_intent_factor < 0.8:
        boundary_rate *= chase_intent_factor
    boundary_rate = min(0.38, max(0.10, boundary_rate))
    
    dot_ball_rate = current_phase_data.get("dot_ball_rate", 0.35)
    if current_phase in ["finish", "death"]:
        dot_ball_rate *= 0.7
    elif current_phase == "acceleration":
        dot_ball_rate *= 0.85
    if chase_intent_factor < 0.8:
        dot_ball_rate *= (1.0 + (1.0 - chase_intent_factor))
    dot_ball_rate = max(0.20, min(0.50, dot_ball_rate))
    
    boundary_count = int(round(boundary_rate * 6))
    dot_ball_count = int(round(dot_ball_rate * 6))
    
    boundary_count = max(0, min(6, boundary_count))
    dot_ball_count = max(0, min(6, dot_ball_count))
    
    if boundary_count + dot_ball_count > 6:
        if dot_ball_count > boundary_count:
            dot_ball_count = 6 - boundary_count
        else:
            boundary_count = 6 - dot_ball_count
    
    singles_doubles_count = 6 - boundary_count - dot_ball_count
    
    win_probability = 0.0
    is_chase = False
    runs_needed = 0
    required_run_rate = 0.0
    
    if match_state.innings == 2 and match_state.target > 0:
        is_chase = True
        runs_needed = match_state.target - match_state.current_score
        
        if runs_needed <= 0:
            win_probability = 1.0
        elif overs_remaining <= 0:
            win_probability = 0.0
        else:
            required_run_rate = runs_needed / overs_remaining
            
            rrr_factor = current_run_rate / required_run_rate if required_run_rate > 0 else 2.0
            
            wickets_in_hand = 10 - match_state.wickets_fallen
            
            if required_run_rate <= 4:
                base_win_prob = 0.92
            elif required_run_rate <= 5:
                base_win_prob = 0.85
            elif required_run_rate <= 6:
                base_win_prob = 0.75
            elif required_run_rate <= 7:
                base_win_prob = 0.60
            elif required_run_rate <= 8:
                base_win_prob = 0.45
            elif required_run_rate <= 9:
                base_win_prob = 0.30
            elif required_run_rate <= 10:
                base_win_prob = 0.18
            elif required_run_rate <= 12:
                base_win_prob = 0.08
            elif required_run_rate <= 15:
                base_win_prob = 0.03
            else:
                base_win_prob = 0.01
            
            wicket_multiplier = (wickets_in_hand / 10.0) ** 1.5
            
            if rrr_factor < 0.5:
                momentum_factor = 0.3
            elif rrr_factor < 0.7:
                momentum_factor = 0.5
            elif rrr_factor < 0.9:
                momentum_factor = 0.75
            elif rrr_factor < 1.1:
                momentum_factor = 1.0
            elif rrr_factor < 1.3:
                momentum_factor = 1.15
            else:
                momentum_factor = 1.3
            
            if runs_needed > 200:
                difficulty_factor = 0.4
            elif runs_needed > 150:
                difficulty_factor = 0.6
            elif runs_needed > 100:
                difficulty_factor = 0.8
            else:
                difficulty_factor = 1.0
            
            runs_per_wicket_needed = runs_needed / wickets_in_hand if wickets_in_hand > 0 else 999
            
            if runs_per_wicket_needed > 60:
                survival_probability = 0.05
            elif runs_per_wicket_needed > 50:
                survival_probability = 0.15
            elif runs_per_wicket_needed > 40:
                survival_probability = 0.30
            elif runs_per_wicket_needed > 30:
                survival_probability = 0.50
            elif runs_per_wicket_needed > 20:
                survival_probability = 0.70
            elif runs_per_wicket_needed > 10:
                survival_probability = 0.85
            else:
                survival_probability = 0.95
            
            win_probability = base_win_prob * wicket_multiplier * momentum_factor * difficulty_factor * survival_probability
            
            win_probability = max(0.01, min(0.99, win_probability))
    
    team_economies_auto = [b.economy for b in match_state.bowlers if b.overs_bowled > 0]
    auto_economy = sum(team_economies_auto) / len(team_economies_auto) if team_economies_auto else 8.0
    auto_venue_factor = 2.0 - auto_venue_bowler_mod

    if current_phase in ["powerplay", "powerplay_1"]:
        auto_base = max(next_over_phase_rpo, auto_economy) * 1.1
    elif current_phase in ["acceleration", "finish", "death"]:
        auto_base = next_over_phase_rpo * current_phase_data["risk_factor"]
    else:
        auto_base = (auto_economy + next_over_phase_rpo) / 2
    auto_base *= auto_venue_factor

    auto_next_over_runs = int(round(auto_base * batsman_factor * wicket_factor * fielding_mod["run_modifier"]))
    max_next_over_auto = 18 if is_odi else 24
    auto_next_over_runs = max(2, min(auto_next_over_runs, max_next_over_auto))
    
    if match_state.innings == 2 and match_state.target > 0 and overs_remaining > 0:
        chase_target_rpo_auto = chase_rrr * 1.05
        auto_next_over_runs = int(round(
            auto_next_over_runs * chase_intent_factor * 0.5 + chase_target_rpo_auto * 0.5
        ))
        auto_next_over_runs = max(2, min(auto_next_over_runs, max_next_over_auto))

    return PredictionResult(
        predicted_final_score=predicted_final_score,
        predicted_wickets=predicted_wickets,
        predicted_next_over_runs=predicted_next_over_runs,
        score_range=score_range,
        wicket_probability=wicket_probability,
        boundary_count=boundary_count,
        dot_ball_count=dot_ball_count,
        singles_doubles_count=singles_doubles_count,
        win_probability=win_probability,
        is_chase=is_chase,
        runs_needed=runs_needed,
        required_run_rate=required_run_rate,
        pitch_type=venue_factors.get("pitch_type", "balanced"),
        pitch_description=venue_factors.get("pitch_description", ""),
        bowler_type=bowler_type,
        venue_bowler_advantage=venue_bowler_mod,
        auto_next_over_runs=auto_next_over_runs,
        bowler_specified=bowler_specified,
        fielding_team=match_state.fielding_team,
        fielding_efficiency=fielding_mod["efficiency"],
        momentum_short_term_rr=momentum_data["short_term_rr"],
        momentum_medium_term_rr=momentum_data["medium_term_rr"],
        momentum_long_term_rr=momentum_data["long_term_rr"],
        momentum_factor=momentum_data["factor"],
        batsman_smoothed_sr=round(avg_batsman_sr, 1),
        current_run_rate=round(current_run_rate, 2),
        overs_remaining=round(overs_remaining, 1),
        wickets_in_hand=10 - match_state.wickets_fallen
    )
