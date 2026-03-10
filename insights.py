"""
Dismissal Insights Engine
Predicts how batsmen are likely to get out based on match situation,
pitch conditions, bowler strengths, and batsman weaknesses.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from ipl_stats import (
    get_comprehensive_batting_stats, get_comprehensive_bowling_stats,
    VENUE_HISTORICAL_STATS, get_venue_weather, get_pitch_tempo,
    get_bowler_venue_dismissal_pattern, VENUE_PITCH_TEMPO
)
from player_data import get_player_by_name
from prediction import (
    get_venue_conditions, get_venue_factors, classify_bowler_type,
    get_current_phase, get_odi_phase, FORMAT_CONFIG, PHASE_RUN_RATES,
    ODI_PHASE_RUN_RATES
)


DISMISSAL_MODES = [
    'caught_boundary',
    'caught_infield',
    'bowled',
    'lbw',
    'run_out',
    'stumped',
]

DISMISSAL_LABELS = {
    'caught_boundary': 'Caught at Boundary',
    'caught_infield': 'Caught in Infield',
    'bowled': 'Bowled',
    'lbw': 'LBW',
    'run_out': 'Run Out',
    'stumped': 'Stumped',
}

DISMISSAL_ICONS = {
    'caught_boundary': 'bi-arrow-up-circle',
    'caught_infield': 'bi-hand-index',
    'bowled': 'bi-bullseye',
    'lbw': 'bi-shield-x',
    'run_out': 'bi-arrow-left-right',
    'stumped': 'bi-lightning',
}

DISMISSAL_COLORS = {
    'caught_boundary': '#e74c3c',
    'caught_infield': '#e67e22',
    'bowled': '#3498db',
    'lbw': '#9b59b6',
    'run_out': '#f39c12',
    'stumped': '#1abc9c',
}

BASE_DISMISSAL_PROBS = {
    'caught_boundary': 0.28,
    'caught_infield': 0.22,
    'bowled': 0.18,
    'lbw': 0.12,
    'run_out': 0.10,
    'stumped': 0.10,
}


@dataclass
class DismissalInsight:
    mode: str
    label: str
    probability: float
    icon: str
    color: str
    reasons: List[str]


@dataclass
class BatsmanInsights:
    batsman_name: str
    dismissal_modes: List[DismissalInsight]
    overall_risk: str
    confidence: str
    confidence_reasons: List[str]
    survival_estimate: int
    key_insight: str
    match_context: str


def _get_phase_name(overs: float, is_odi: bool) -> str:
    """Return a human-readable phase name (e.g. 'Powerplay') for the current over."""
    if is_odi:
        phase = get_odi_phase(overs)
        names = {
            'powerplay_1': 'Powerplay',
            'middle_1': 'Middle Overs (11-30)',
            'middle_2': 'Middle Overs (31-40)',
            'death': 'Death Overs (41-50)'
        }
        return names.get(phase, phase)
    else:
        phase = get_current_phase(overs)
        names = {
            'powerplay': 'Powerplay',
            'consolidation': 'Consolidation (7-14)',
            'acceleration': 'Acceleration (15-17)',
            'finish': 'Finish (18-20)'
        }
        return names.get(phase, phase)


def _get_phase_key(overs: float, is_odi: bool) -> str:
    """Return the internal phase key (e.g. 'death', 'powerplay') for the current over."""
    if is_odi:
        return get_odi_phase(overs)
    else:
        return get_current_phase(overs)


def _classify_batsman_type(player_data: dict, batting_stats: dict) -> str:
    """Classify a batsman as 'aggressive', 'anchor', 'allrounder', or 'tailender' by role and SR."""
    role = (player_data.get('role', '') or '').lower()
    if 'bowler' in role and 'all' not in role:
        return 'tailender'
    if 'all' in role:
        return 'allrounder'
    sr = batting_stats.get('sr', 0) if batting_stats else 0
    if sr > 145:
        return 'aggressive'
    elif sr > 125:
        return 'balanced'
    else:
        return 'anchor'


def _get_pressure_factor(overs: float, wickets: int, current_score: int,
                          target: int, is_chase: bool, is_odi: bool) -> Tuple[float, List[str]]:
    """Compute a 0-0.6 pressure score from required run rate, wickets lost, and phase."""
    max_overs = 50 if is_odi else 20
    pressure = 0.0
    reasons = []

    if is_chase and target > 0:
        balls_remaining = (max_overs - overs) * 6
        runs_needed = target - current_score
        if balls_remaining > 0:
            rrr = (runs_needed / balls_remaining) * 6
            if rrr > 12:
                pressure += 0.4
                reasons.append(f"Extreme run rate pressure (RRR: {rrr:.1f})")
            elif rrr > 9:
                pressure += 0.25
                reasons.append(f"High required run rate ({rrr:.1f} per over)")
            elif rrr > 7:
                pressure += 0.1
                reasons.append(f"Above-average run rate needed ({rrr:.1f} per over)")

    if wickets >= 7:
        pressure += 0.3
        reasons.append(f"Batting with the tail ({wickets} wickets down)")
    elif wickets >= 5:
        pressure += 0.15
        reasons.append(f"Under pressure ({wickets} wickets down)")

    finish_threshold = 40 if is_odi else 17
    accel_threshold = 30 if is_odi else 14
    if overs >= finish_threshold:
        pressure += 0.15
        reasons.append("Finish overs — batsmen push for quick runs")
    elif overs >= accel_threshold:
        pressure += 0.08
        reasons.append("Acceleration phase — scoring rate increasing")

    return min(pressure, 0.6), reasons


def _apply_phase_modifiers(probs: Dict[str, float], overs: float, is_odi: bool) -> Dict[str, List[str]]:
    """Adjust dismissal probabilities based on current phase (T20: powerplay/consolidation/acceleration/finish, ODI: powerplay/middle/death)."""
    mode_reasons: Dict[str, List[str]] = {m: [] for m in DISMISSAL_MODES}
    phase = _get_phase_key(overs, is_odi)

    if is_odi:
        phase_data = ODI_PHASE_RUN_RATES.get(phase, {})
    else:
        phase_data = PHASE_RUN_RATES.get(phase, {})

    if phase in ['finish', 'death']:
        probs['caught_boundary'] *= 1.45
        probs['run_out'] *= 1.35
        probs['caught_infield'] *= 0.85
        probs['lbw'] *= 0.80
        probs['stumped'] *= 0.70
        mode_reasons['caught_boundary'].append("Finish overs — batsmen go for big shots, boundary catches increase")
        mode_reasons['run_out'].append("Finish overs — hurried running between wickets raises run-out risk")
    elif phase == 'acceleration':
        probs['caught_boundary'] *= 1.30
        probs['run_out'] *= 1.20
        probs['caught_infield'] *= 0.90
        probs['lbw'] *= 0.85
        probs['stumped'] *= 0.80
        mode_reasons['caught_boundary'].append("Acceleration phase — set batsmen target boundaries, catches in deep increase")
        mode_reasons['run_out'].append("Acceleration phase — quick singles and risky running raise run-out chances")
    elif phase in ['powerplay', 'powerplay_1']:
        probs['caught_boundary'] *= 1.15
        probs['bowled'] *= 1.15
        probs['lbw'] *= 1.10
        probs['caught_infield'] *= 0.90
        probs['run_out'] *= 0.85
        mode_reasons['caught_boundary'].append("Powerplay — only 2 fielders outside, gaps at boundary for catches")
        mode_reasons['bowled'].append("Powerplay — new ball moves more, bowled dismissals rise")
        mode_reasons['lbw'].append("Powerplay — full-length deliveries with new ball increase LBW chances")
    elif phase in ['consolidation', 'middle', 'middle_1', 'middle_2']:
        probs['caught_infield'] *= 1.20
        probs['stumped'] *= 1.15
        probs['caught_boundary'] *= 0.90
        probs['run_out'] *= 0.95
        mode_reasons['caught_infield'].append("Consolidation — 4 fielders outside, close catchers in play")
        mode_reasons['stumped'].append("Consolidation — spinners dominate, stumping chances increase")

    return mode_reasons


def _apply_venue_modifiers(probs: Dict[str, float], venue: str) -> Dict[str, List[str]]:
    """Adjust dismissal probabilities for pitch type (pace-friendly, spin-friendly, etc.)."""
    mode_reasons: Dict[str, List[str]] = {m: [] for m in DISMISSAL_MODES}
    conditions = get_venue_conditions(venue)
    pitch_type = conditions.get('pitch_type', 'balanced')

    if pitch_type == 'pace-friendly':
        probs['bowled'] *= 1.25
        probs['lbw'] *= 1.20
        probs['caught_boundary'] *= 1.10
        probs['stumped'] *= 0.75
        mode_reasons['bowled'].append("Pace-friendly surface — seam movement beats the bat more often")
        mode_reasons['lbw'].append("Pace-friendly pitch — nipping deliveries trap batsmen in front")
        mode_reasons['caught_boundary'].append("Extra bounce on pace tracks carries edges to boundary catchers")
    elif pitch_type == 'spin-friendly':
        probs['stumped'] *= 1.50
        probs['lbw'] *= 1.20
        probs['caught_infield'] *= 1.15
        probs['bowled'] *= 1.10
        probs['caught_boundary'] *= 0.85
        mode_reasons['stumped'].append("Spin-friendly pitch — turn draws batsmen out of crease")
        mode_reasons['lbw'].append("Spin-friendly surface — deliveries that grip can pin batsmen LBW")
        mode_reasons['caught_infield'].append("Turning pitch creates inside edges and bat-pad chances")
    elif pitch_type == 'batting-paradise':
        probs['caught_boundary'] *= 1.30
        probs['bowled'] *= 0.80
        probs['lbw'] *= 0.85
        mode_reasons['caught_boundary'].append("Flat batting track — batsmen attack freely, skied catches likely")

    return mode_reasons


def _apply_weather_modifiers(probs: Dict[str, float], venue: str,
                              overs: float) -> Dict[str, List[str]]:
    """Adjust dismissal probabilities for weather conditions, dew, and swing window."""
    mode_reasons: Dict[str, List[str]] = {m: [] for m in DISMISSAL_MODES}
    weather = get_venue_weather(venue)
    conditions = weather.get('typical_conditions', 'varied')
    dew_factor = weather.get('dew_factor', 0.3)
    swing_window = weather.get('swing_window', 'first_6')
    humidity = weather.get('humidity', 'medium')

    in_swing_window = False
    if swing_window == 'all_innings':
        in_swing_window = True
    elif swing_window == 'first_4' and overs < 4:
        in_swing_window = True
    elif swing_window == 'first_6' and overs < 6:
        in_swing_window = True
    elif swing_window == 'first_10' and overs < 10:
        in_swing_window = True

    if conditions == 'overcast_cool':
        probs['bowled'] *= 1.20
        probs['lbw'] *= 1.15
        probs['caught_infield'] *= 1.10
        probs['stumped'] *= 0.80
        mode_reasons['bowled'].append("Overcast skies help swing — ball moves more off the seam")
        mode_reasons['lbw'].append("Cloud cover aids lateral movement, increasing LBW chances")
        if in_swing_window:
            probs['bowled'] *= 1.10
            probs['lbw'] *= 1.10
            mode_reasons['bowled'].append(f"Within swing window ({swing_window.replace('_', ' ')}) — maximum movement")
    elif conditions == 'hot_humid':
        if dew_factor >= 0.7 and overs >= 10:
            probs['stumped'] *= 0.80
            probs['caught_infield'] *= 0.90
            probs['caught_boundary'] *= 1.10
            probs['run_out'] *= 1.10
            mode_reasons['caught_boundary'].append("Dew makes ball skid on — batsmen attack freely, aerial shots increase")
            mode_reasons['run_out'].append("Wet outfield from dew causes misfields and run-out chances")
        if in_swing_window and humidity == 'high':
            probs['bowled'] *= 1.10
            probs['lbw'] *= 1.05
            mode_reasons['bowled'].append("Humid air assists early swing before dew sets in")
    elif conditions == 'hot_dry':
        if overs >= 15:
            probs['bowled'] *= 1.10
            probs['lbw'] *= 1.05
            mode_reasons['bowled'].append("Dry, abrasive pitch enables reverse swing in later overs")
            mode_reasons['lbw'].append("Reverse swing on dry pitches creates surprise LBW deliveries")
        probs['stumped'] *= 0.90
    elif conditions == 'dry_warm':
        if in_swing_window:
            probs['bowled'] *= 1.05

    return mode_reasons


def _apply_pitch_tempo_modifiers(probs: Dict[str, float], venue: str) -> Dict[str, List[str]]:
    """Adjust dismissal probabilities for pitch tempo (high bounce, low-slow, etc.)."""
    mode_reasons: Dict[str, List[str]] = {m: [] for m in DISMISSAL_MODES}
    tempo = get_pitch_tempo(venue)

    if tempo == 'high_bounce':
        probs['caught_boundary'] *= 1.15
        probs['caught_infield'] *= 1.10
        probs['bowled'] *= 1.10
        probs['stumped'] *= 0.85
        mode_reasons['caught_boundary'].append("High-bounce pitch — extra carry sends edges to slip/gully catchers")
        mode_reasons['caught_infield'].append("Uneven bounce creates catching chances close to the bat")
        mode_reasons['bowled'].append("Variable bounce can beat the bat and hit the stumps")
    elif tempo == 'low_slow':
        probs['lbw'] *= 1.15
        probs['stumped'] *= 1.20
        probs['caught_infield'] *= 1.10
        probs['caught_boundary'] *= 0.90
        probs['bowled'] *= 1.05
        mode_reasons['stumped'].append("Low, slow pitch — ball holds up, draws batsmen forward for stumping")
        mode_reasons['lbw'].append("Slow surface keeps ball low — LBW appeals more successful")
        mode_reasons['caught_infield'].append("Low bounce creates leading edges and bat-pad chances")
    elif tempo == 'true_pace':
        probs['bowled'] *= 1.20
        probs['lbw'] *= 1.15
        probs['caught_boundary'] *= 1.05
        probs['stumped'] *= 0.80
        mode_reasons['bowled'].append("True pace and carry — consistent bounce rewards good-length bowling")
        mode_reasons['lbw'].append("Even bounce on true pitch makes LBW decisions more predictable")
    elif tempo == 'batting_road':
        probs['caught_boundary'] *= 1.25
        probs['run_out'] *= 1.10
        probs['bowled'] *= 0.85
        probs['lbw'] *= 0.85
        mode_reasons['caught_boundary'].append("Flat batting road — batsmen attack freely, caught at boundary rises")
        mode_reasons['run_out'].append("Easy batting conditions encourage quick singles and run-out risk")

    return mode_reasons


def _apply_bowler_venue_patterns(probs: Dict[str, float], bowler_type: str,
                                   venue: str) -> Dict[str, List[str]]:
    """Blend venue-specific historical dismissal patterns for the bowler type into probs."""
    mode_reasons: Dict[str, List[str]] = {m: [] for m in DISMISSAL_MODES}
    pattern, tempo = get_bowler_venue_dismissal_pattern(bowler_type, venue)

    if tempo == 'default':
        return mode_reasons

    tempo_labels = {
        'high_bounce': 'high-bounce',
        'low_slow': 'low & slow',
        'true_pace': 'true pace',
        'batting_road': 'flat batting',
    }
    tempo_label = tempo_labels.get(tempo, tempo)

    for mode, pct in pattern.items():
        base = BASE_DISMISSAL_PROBS.get(mode, 0.15)
        if pct > base:
            ratio = pct / base
            probs[mode] *= (1 + (ratio - 1) * 0.5)
            mode_label = DISMISSAL_LABELS.get(mode, mode)
            mode_reasons[mode].append(
                f"{bowler_type.title()} bowlers on {tempo_label} pitches get {pct:.0%} of wickets via {mode_label}"
            )
        elif pct < base:
            ratio = pct / base
            probs[mode] *= (1 + (ratio - 1) * 0.3)

    return mode_reasons


def _apply_bowler_modifiers(probs: Dict[str, float], bowler_name: str,
                             bowling_stats: dict) -> Dict[str, List[str]]:
    """Adjust dismissal probabilities based on bowler's style (pace/spin) and career stats."""
    mode_reasons: Dict[str, List[str]] = {m: [] for m in DISMISSAL_MODES}
    player = get_player_by_name(bowler_name)
    if not player:
        return mode_reasons

    bowling_style = player.get('bowling_style', '') or ''
    bowler_type = classify_bowler_type(bowling_style)

    if bowler_type == 'pace':
        probs['bowled'] *= 1.20
        probs['lbw'] *= 1.15
        probs['caught_boundary'] *= 1.10
        probs['stumped'] *= 0.60
        mode_reasons['bowled'].append(f"{bowler_name} bowls pace — seam movement can beat the bat")
        mode_reasons['lbw'].append(f"{bowler_name}'s pace keeps batsmen rooted — LBW risk rises")
        mode_reasons['caught_boundary'].append(f"Pace bowling from {bowler_name} forces edges that carry to boundary")

        style_lower = bowling_style.lower()
        if 'fast' in style_lower and 'medium' not in style_lower:
            probs['bowled'] *= 1.10
            probs['caught_boundary'] *= 1.10
            mode_reasons['caught_boundary'].append("Express pace generates extra bounce — edges carry further")
    elif bowler_type == 'spin':
        probs['stumped'] *= 1.60
        probs['lbw'] *= 1.15
        probs['caught_infield'] *= 1.20
        probs['bowled'] *= 1.05
        probs['caught_boundary'] *= 0.80
        mode_reasons['stumped'].append(f"{bowler_name} bowls spin — batsmen lured forward for stumping")
        mode_reasons['caught_infield'].append(f"Spin from {bowler_name} creates close catching chances")
        mode_reasons['lbw'].append(f"{bowler_name}'s spin can trap batsmen playing across the line")

        style_lower = bowling_style.lower()
        if 'leg' in style_lower or 'googly' in style_lower:
            probs['stumped'] *= 1.15
            probs['bowled'] *= 1.10
            mode_reasons['stumped'].append("Wrist spin creates deception — batsmen miss, keeper stumps")
            mode_reasons['bowled'].append("Leg-spin variations can turn through the gate")
        elif 'orthodox' in style_lower or 'offbreak' in style_lower:
            probs['caught_infield'] *= 1.10
            mode_reasons['caught_infield'].append("Finger spin builds dot-ball pressure — batsmen nick to close catchers")

    if bowling_stats:
        econ = bowling_stats.get('econ', 8.0)
        sr = bowling_stats.get('sr', 20.0)
        if sr < 16:
            probs['bowled'] *= 1.15
            probs['lbw'] *= 1.10
            mode_reasons['bowled'].append(f"Excellent strike rate ({sr:.1f}) — takes wickets frequently")
        elif sr > 25:
            probs['caught_boundary'] *= 1.10
            mode_reasons['caught_boundary'].append(f"Economy of {econ:.1f} invites attacking shots — aerial chances rise")

    return mode_reasons


def _apply_batsman_modifiers(probs: Dict[str, float], batsman_name: str,
                              batsman_runs: int, batsman_balls: int,
                              batting_stats: dict) -> Dict[str, List[str]]:
    """Adjust dismissal probabilities for batsman type, current SR, and time at crease."""
    mode_reasons: Dict[str, List[str]] = {m: [] for m in DISMISSAL_MODES}
    player = get_player_by_name(batsman_name)
    if not player:
        return mode_reasons

    batsman_type = _classify_batsman_type(player, batting_stats)

    if batsman_type == 'aggressive':
        probs['caught_boundary'] *= 1.30
        probs['caught_infield'] *= 0.85
        probs['bowled'] *= 0.90
        mode_reasons['caught_boundary'].append(f"{batsman_name} plays aggressively — aerial shots create boundary catching chances")
    elif batsman_type == 'anchor':
        probs['lbw'] *= 1.15
        probs['bowled'] *= 1.10
        probs['caught_boundary'] *= 0.85
        mode_reasons['lbw'].append(f"{batsman_name} plays anchor role — compact technique but front-pad vulnerable")
        mode_reasons['bowled'].append(f"{batsman_name}'s defensive approach can lead to playing around the ball")
    elif batsman_type == 'tailender':
        probs['bowled'] *= 1.40
        probs['lbw'] *= 1.25
        probs['caught_infield'] *= 1.15
        probs['caught_boundary'] *= 0.80
        mode_reasons['bowled'].append(f"{batsman_name} is a lower-order batsman — more likely to miss straight deliveries")
        mode_reasons['lbw'].append(f"Tail-ender {batsman_name} has limited defensive technique — LBW risk high")

    if batsman_balls > 0:
        current_sr = (batsman_runs / batsman_balls) * 100
        if current_sr > 170:
            probs['caught_boundary'] *= 1.20
            mode_reasons['caught_boundary'].append(f"Batting at SR {current_sr:.0f} today — high-risk shots increase aerial chances")
        elif current_sr < 90 and batsman_balls > 10:
            probs['lbw'] *= 1.10
            probs['bowled'] *= 1.10
            mode_reasons['bowled'].append(f"Struggling for timing (SR: {current_sr:.0f}) — more likely to miss straight ones")
            mode_reasons['lbw'].append(f"Low strike rate ({current_sr:.0f}) suggests difficulty reading the ball")

    if batsman_balls > 0 and batsman_balls <= 6:
        probs['bowled'] *= 1.20
        probs['lbw'] *= 1.15
        mode_reasons['bowled'].append("New at the crease — still adjusting to pace and bounce")
        mode_reasons['lbw'].append("Fresh batsman vulnerable to full deliveries before getting set")

    batting_hand = (player.get('batting_style', '') or '').lower()
    if batting_hand:
        if 'left' in batting_hand:
            probs['lbw'] *= 1.05

    return mode_reasons


def _apply_pressure_modifiers(probs: Dict[str, float], pressure: float,
                                pressure_reasons: List[str]) -> Dict[str, List[str]]:
    """Scale dismissal probabilities up/down based on match-situation pressure."""
    mode_reasons: Dict[str, List[str]] = {m: [] for m in DISMISSAL_MODES}
    if pressure > 0:
        probs['caught_boundary'] *= (1 + pressure * 0.5)
        probs['run_out'] *= (1 + pressure * 0.6)
        probs['stumped'] *= (1 + pressure * 0.3)
        probs['bowled'] *= (1 - pressure * 0.15)
        probs['caught_infield'] *= (1 - pressure * 0.1)
        if pressure > 0.25:
            mode_reasons['caught_boundary'].append("High pressure forces big shots — more chances of being caught at boundary")
            mode_reasons['run_out'].append("Match pressure causes hurried running between wickets")
            mode_reasons['stumped'].append("Desperation to score leads to charging down the pitch")
        elif pressure > 0.1:
            mode_reasons['caught_boundary'].append("Building pressure encourages risk-taking — aerial shots increase")
            mode_reasons['run_out'].append("Pressure for quick runs raises run-out risk")
    return mode_reasons


def _normalize_probs(probs: Dict[str, float]) -> Dict[str, float]:
    """Normalize probability values so they sum to 1.0."""
    total = sum(probs.values())
    if total == 0:
        return {k: 1.0 / len(probs) for k in probs}
    return {k: v / total for k, v in probs.items()}


def _calculate_confidence(batsman_known: bool, bowler_known: bool,
                           venue_known: bool, batting_stats: dict,
                           bowling_stats: dict) -> Tuple[str, List[str]]:
    """Rate prediction confidence as 'High', 'Medium', or 'Low' based on data availability."""
    score = 0
    reasons = []

    if batsman_known:
        score += 1
        reasons.append("Batsman profile found in database")
    else:
        reasons.append("Batsman not in database — using general estimates")

    if bowler_known:
        score += 1
        reasons.append("Bowler profile found in database")
    else:
        reasons.append("Bowler not in database — using general estimates")

    if venue_known:
        score += 1
        reasons.append("Venue pitch data available")
    else:
        reasons.append("Venue not in database — using average conditions")

    if batting_stats and batting_stats.get('matches', 0) > 50:
        score += 1
        reasons.append(f"Strong batting data ({batting_stats['matches']} matches)")

    if bowling_stats and bowling_stats.get('matches', 0) > 30:
        score += 1
        reasons.append(f"Good bowling data ({bowling_stats['matches']} matches)")

    if score >= 4:
        return 'High', reasons
    elif score >= 2:
        return 'Medium', reasons
    else:
        return 'Low', reasons


def _estimate_survival(probs: Dict[str, float], pressure: float, 
                        batsman_type: str, overs: float, is_odi: bool) -> int:
    """Estimate how many balls the batsman is likely to survive (3-60 range)."""
    total_risk = sum(probs.values())
    base_survival = max(6, int(36 / max(total_risk * 6, 0.5)))

    if batsman_type == 'tailender':
        base_survival = int(base_survival * 0.5)
    elif batsman_type == 'aggressive':
        base_survival = int(base_survival * 0.8)
    elif batsman_type == 'anchor':
        base_survival = int(base_survival * 1.3)

    if pressure > 0.3:
        base_survival = int(base_survival * 0.7)

    return max(3, min(60, base_survival))


def _generate_key_insight(top_mode: str, top_prob: float, bowler_name: str,
                           batsman_name: str, pressure: float, pitch_type: str) -> str:
    """Generate a one-sentence narrative insight about the most likely dismissal mode."""
    mode_label = DISMISSAL_LABELS.get(top_mode, top_mode)

    if pressure > 0.3:
        return (f"Under heavy pressure, {batsman_name} is most likely to be dismissed "
                f"'{mode_label}' ({top_prob:.0%}). The match situation forces aggressive play.")
    elif top_prob > 0.35:
        return (f"Strong chance of {batsman_name} getting out '{mode_label}' ({top_prob:.0%}) "
                f"against {bowler_name}.")
    else:
        return (f"{batsman_name} faces a balanced set of risks. '{mode_label}' is the most "
                f"likely dismissal mode at {top_prob:.0%}.")


def build_dismissal_insights(
    batsman_name: str,
    batsman_runs: int,
    batsman_balls: int,
    bowler_name: str,
    venue: str,
    overs: float,
    wickets: int,
    current_score: int,
    target: int = 0,
    innings: int = 1,
    match_format: str = 'mens_t20'
) -> BatsmanInsights:
    """Build detailed dismissal probability insights for a single batsman vs current bowler."""
    format_config = FORMAT_CONFIG.get(match_format, FORMAT_CONFIG['mens_t20'])
    is_odi = format_config['is_odi']
    is_chase = innings == 2 and target > 0

    probs = dict(BASE_DISMISSAL_PROBS)
    all_mode_reasons: Dict[str, List[str]] = {m: [] for m in DISMISSAL_MODES}

    def _merge_reasons(new_reasons: Dict[str, List[str]]):
        """Accumulate per-mode reasoning strings from each modifier stage."""
        for mode, reasons_list in new_reasons.items():
            all_mode_reasons[mode].extend(reasons_list)

    batsman_player = get_player_by_name(batsman_name)
    bowler_player = get_player_by_name(bowler_name)
    venue_stats = VENUE_HISTORICAL_STATS.get(venue)

    batting_stats = get_comprehensive_batting_stats(batsman_name) if batsman_player else None
    bowling_stats = get_comprehensive_bowling_stats(bowler_name) if bowler_player else None

    _merge_reasons(_apply_phase_modifiers(probs, overs, is_odi))
    _merge_reasons(_apply_venue_modifiers(probs, venue))
    _merge_reasons(_apply_weather_modifiers(probs, venue, overs))
    _merge_reasons(_apply_pitch_tempo_modifiers(probs, venue))
    _merge_reasons(_apply_bowler_modifiers(probs, bowler_name, bowling_stats))

    bowler_player_check = get_player_by_name(bowler_name)
    if bowler_player_check:
        bowl_style = bowler_player_check.get('bowling_style', '') or ''
        b_type = classify_bowler_type(bowl_style)
    else:
        b_type = 'pace'
    _merge_reasons(_apply_bowler_venue_patterns(probs, b_type, venue))

    _merge_reasons(_apply_batsman_modifiers(probs, batsman_name, batsman_runs,
                                             batsman_balls, batting_stats))

    pressure, pressure_reasons = _get_pressure_factor(overs, wickets, current_score,
                                                       target, is_chase, is_odi)
    _merge_reasons(_apply_pressure_modifiers(probs, pressure, pressure_reasons))

    probs = _normalize_probs(probs)

    sorted_modes = sorted(probs.items(), key=lambda x: x[1], reverse=True)

    confidence, confidence_reasons = _calculate_confidence(
        batsman_player is not None,
        bowler_player is not None,
        venue_stats is not None,
        batting_stats,
        bowling_stats
    )

    batsman_type = 'balanced'
    if batsman_player:
        batsman_type = _classify_batsman_type(batsman_player, batting_stats)

    survival = _estimate_survival(probs, pressure, batsman_type, overs, is_odi)

    top_mode, top_prob = sorted_modes[0]
    key_insight = _generate_key_insight(top_mode, top_prob, bowler_name,
                                         batsman_name, pressure, 
                                         get_venue_conditions(venue).get('pitch_type', 'balanced'))

    phase_name = _get_phase_name(overs, is_odi)
    if is_chase:
        runs_needed = target - current_score
        max_overs_fmt = format_config['max_overs']
        balls_left = (max_overs_fmt - overs) * 6
        rrr = (runs_needed / balls_left * 6) if balls_left > 0 else 0
        match_context = (f"{phase_name} • Chasing {target} • Need {runs_needed} from "
                        f"{balls_left:.0f} balls (RRR: {rrr:.1f})")
    else:
        match_context = (f"{phase_name} • {current_score}/{wickets} after "
                        f"{overs:.1f} overs")

    max_prob = sorted_modes[0][1]
    if max_prob > 0.35 or pressure > 0.3:
        overall_risk = 'High'
    elif max_prob > 0.28 or pressure > 0.15:
        overall_risk = 'Medium'
    else:
        overall_risk = 'Low'

    dismissal_insights = []
    for mode, prob in sorted_modes:
        mode_reasons = all_mode_reasons.get(mode, [])

        if not mode_reasons and prob > 0.10:
            mode_reasons = ["General match conditions contribute to this dismissal type"]

        dismissal_insights.append(DismissalInsight(
            mode=mode,
            label=DISMISSAL_LABELS[mode],
            probability=prob,
            icon=DISMISSAL_ICONS[mode],
            color=DISMISSAL_COLORS[mode],
            reasons=mode_reasons[:3]
        ))

    return BatsmanInsights(
        batsman_name=batsman_name,
        dismissal_modes=dismissal_insights,
        overall_risk=overall_risk,
        confidence=confidence,
        confidence_reasons=confidence_reasons,
        survival_estimate=survival,
        key_insight=key_insight,
        match_context=match_context
    )


def build_match_insights(
    batsmen: List[Dict],
    bowler_name: str,
    venue: str,
    overs: float,
    wickets: int,
    current_score: int,
    target: int = 0,
    innings: int = 1,
    match_format: str = 'mens_t20'
) -> List[BatsmanInsights]:
    """Generate dismissal insights for all current batsmen against the active bowler."""
    insights = []
    for bat in batsmen:
        name = bat.get('name', '')
        runs = bat.get('runs', 0)
        balls = bat.get('balls_faced', 0)
        if name:
            insight = build_dismissal_insights(
                batsman_name=name,
                batsman_runs=runs,
                batsman_balls=balls,
                bowler_name=bowler_name,
                venue=venue,
                overs=overs,
                wickets=wickets,
                current_score=current_score,
                target=target,
                innings=innings,
                match_format=match_format
            )
            insights.append(insight)
    return insights
