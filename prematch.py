"""Pre-match analysis module.

Generates venue-specific analysis before a match starts, including
bat-first vs chase records, surface descriptions, par score ranges,
phase-by-phase expectations, and toss advice based on historical data,
pitch tempo, weather, and dew conditions.
"""
from datetime import datetime
import pytz
from ipl_stats import (
    VENUE_HISTORICAL_STATS, get_venue_weather, get_pitch_tempo,
    VENUE_PITCH_TEMPO, PHASE_RUN_RATES
)
from prediction import FORMAT_CONFIG, get_venue_timezone


def get_venue_country(venue):
    """Return the country string for a venue from historical stats, or 'Unknown'."""
    stats = VENUE_HISTORICAL_STATS.get(venue, {})
    return stats.get("country", "Unknown")


def get_bat_first_vs_chase_record(venue, match_format):
    """Estimate bat-first vs chase win percentages at a venue.

    Uses average 1st/2nd innings scores and dew factor to derive a
    percentage split, then returns a verdict string.

    Args:
        venue: Venue name.
        match_format: Format string (e.g. 'mens_t20', 'mens_odi').

    Returns:
        Dict with bat_first_wins, chase_wins, total_matches, verdict, dew_factor.
    """
    stats = VENUE_HISTORICAL_STATS.get(venue, {})
    if not stats:
        return {"bat_first_wins": 50, "chase_wins": 50, "total_matches": 0, "verdict": "Even contest"}

    avg_1st = stats.get("avg_1st_innings", 165)
    avg_2nd = stats.get("avg_2nd_innings", 155)
    matches = stats.get("matches", 50)
    pace_pct = stats.get("pace_wickets_pct", 0.48)
    spin_pct = stats.get("spin_wickets_pct", 0.40)

    margin = avg_1st - avg_2nd
    weather = get_venue_weather(venue)
    dew = weather.get("dew_factor", 0.3)

    if dew >= 0.7:
        chase_boost = 8
    elif dew >= 0.5:
        chase_boost = 4
    else:
        chase_boost = 0

    if margin > 15:
        bat_first_pct = 58
    elif margin > 10:
        bat_first_pct = 55
    elif margin > 5:
        bat_first_pct = 52
    else:
        bat_first_pct = 48

    bat_first_pct = max(35, min(65, bat_first_pct - chase_boost))
    chase_pct = 100 - bat_first_pct

    if bat_first_pct >= 58:
        verdict = "Strong advantage batting first — teams setting totals dominate here"
    elif bat_first_pct >= 54:
        verdict = "Slight edge batting first — defendable totals are common"
    elif chase_pct >= 58:
        verdict = "Strong advantage chasing — dew and conditions favour the team batting second"
    elif chase_pct >= 54:
        verdict = "Slight edge chasing — batting gets easier under lights"
    else:
        verdict = "Even contest — both batting first and chasing have a fair chance"

    return {
        "bat_first_wins": bat_first_pct,
        "chase_wins": chase_pct,
        "total_matches": matches,
        "verdict": verdict,
        "dew_factor": dew
    }


def get_surface_description(venue, match_format):
    """Build a narrative description of the pitch surface and bowler analysis.

    Args:
        venue: Venue name.
        match_format: Format string.

    Returns:
        Dict with surface text, bowler_analysis, pace/spin wicket percentages, pitch_tempo.
    """
    stats = VENUE_HISTORICAL_STATS.get(venue, {})
    tempo = get_pitch_tempo(venue)
    weather = get_venue_weather(venue)
    pace_pct = stats.get("pace_wickets_pct", 0.48)
    spin_pct = stats.get("spin_wickets_pct", 0.40)

    is_odi = 'odi' in match_format

    tempo_descriptions = {
        "high_bounce": "The pitch offers significant bounce and carry. Fast bowlers will get the ball to rear up, and edges carry to the cordon and keeper. Batsmen need to be watchful of the short ball.",
        "low_slow": "A slow, low surface where the ball grips and turns. The pitch tends to keep low, making strokeplay difficult. Spinners will be crucial, especially in the middle overs.",
        "true_pace": "A quality cricket pitch with consistent bounce and pace. The ball comes on nicely, rewarding good technique. Seam bowlers get movement early before it settles down.",
        "batting_road": "A flat, true batting surface where the ball comes on to the bat beautifully. Boundaries flow freely and bowlers need to be disciplined. Expect a high-scoring contest.",
        "default": "A standard cricket pitch with something for everyone. Conditions should be fair for both batsmen and bowlers."
    }

    surface_desc = tempo_descriptions.get(tempo, tempo_descriptions["default"])

    if pace_pct >= 0.55:
        bowler_desc = "Pace bowlers dominate here, accounting for the majority of wickets. Fast bowlers with good lengths and movement will be key."
    elif spin_pct >= 0.45:
        bowler_desc = "Spinners thrive at this venue, taking a high proportion of wickets. Teams with quality spin options have a significant advantage."
    elif abs(pace_pct - spin_pct) < 0.1:
        bowler_desc = "Both pace and spin share wickets roughly equally here. A balanced bowling attack is ideal."
    else:
        bowler_desc = "Pace bowlers have a slight edge, but spinners also play a role, especially in the middle overs."

    return {
        "surface": surface_desc,
        "bowler_analysis": bowler_desc,
        "pace_wicket_pct": round(pace_pct * 100),
        "spin_wicket_pct": round(spin_pct * 100),
        "pitch_tempo": tempo
    }


def get_par_score_analysis(venue, match_format):
    """Compute par score, competitive range, and scoring narrative for a venue/format.

    Adjusts historical T20 averages by ODI and women's scaling factors, then
    selects a scoring vibe based on pitch tempo.

    Args:
        venue: Venue name.
        match_format: Format string (may contain 'odi' or 'womens').

    Returns:
        Dict with par_score, competitive_range, highest/lowest recorded,
        scoring_vibe, scoring_detail, avg_1st, avg_2nd.
    """
    stats = VENUE_HISTORICAL_STATS.get(venue, {})
    tempo = get_pitch_tempo(venue)
    weather = get_venue_weather(venue)

    is_odi = 'odi' in match_format
    is_womens = 'womens' in match_format

    avg_1st = stats.get("avg_1st_innings", 165)
    avg_2nd = stats.get("avg_2nd_innings", 155)
    highest = stats.get("highest", 220)
    lowest = stats.get("lowest", 80)

    if is_odi:
        odi_factor = 1.55
        avg_1st = int(avg_1st * odi_factor)
        avg_2nd = int(avg_2nd * odi_factor)
        highest = int(highest * odi_factor)
        lowest = int(lowest * odi_factor)

    if is_womens:
        womens_factor = 0.82
        avg_1st = int(avg_1st * womens_factor)
        avg_2nd = int(avg_2nd * womens_factor)
        highest = int(highest * womens_factor)
        lowest = int(lowest * womens_factor)

    par_score = avg_1st
    competitive_low = par_score - 15 if not is_odi else par_score - 25
    competitive_high = par_score + 15 if not is_odi else par_score + 25

    if tempo == "batting_road":
        scoring_vibe = "high-scoring"
        scoring_detail = f"Expect a run-fest. Anything below {par_score - 10} could be under-par. Bowlers need early wickets or the game can get away quickly."
    elif tempo == "high_bounce":
        scoring_vibe = "pace-dominated"
        scoring_detail = f"The extra bounce keeps batsmen honest. Quick bowlers with good lines will be rewarded. Scores tend to be moderate unless a set batsman goes big."
    elif tempo == "low_slow":
        scoring_vibe = "low-scoring spin battle"
        scoring_detail = f"Batting is hard work here — the ball grips and turns, making timing difficult. A score of {par_score} would be very competitive. Spinners will be the match-winners."
    elif tempo == "true_pace":
        scoring_vibe = "balanced"
        scoring_detail = f"Good cricket surface that rewards skill. Seam bowlers get early movement before conditions ease for batting. A score around {par_score} is par."
    else:
        scoring_vibe = "balanced"
        scoring_detail = f"Standard conditions expected. A score around {par_score} would be competitive."

    return {
        "par_score": par_score,
        "competitive_range": f"{competitive_low}-{competitive_high}",
        "highest_recorded": highest,
        "lowest_recorded": lowest,
        "scoring_vibe": scoring_vibe,
        "scoring_detail": scoring_detail,
        "avg_1st": avg_1st,
        "avg_2nd": avg_2nd
    }


def _build_phase_structure(is_odi):
    """Return a list of phase dicts (name, icon, color) for T20 or ODI."""
    if is_odi:
        return [
            {"name": "Powerplay (Overs 1-10)", "icon": "bi-lightning-charge", "color": "#3498db"},
            {"name": "Middle Overs (11-40)", "icon": "bi-shield", "color": "#2ecc71"},
            {"name": "Death Overs (41-50)", "icon": "bi-fire", "color": "#e74c3c"},
        ]
    else:
        return [
            {"name": "Powerplay (Overs 1-6)", "icon": "bi-lightning-charge", "color": "#3498db"},
            {"name": "Consolidation (Overs 7-14)", "icon": "bi-shield", "color": "#2ecc71"},
            {"name": "Acceleration (Overs 15-17)", "icon": "bi-rocket-takeoff", "color": "#f39c12"},
            {"name": "Finish (Overs 18-20)", "icon": "bi-fire", "color": "#e74c3c"},
        ]


def _fill_1st_innings_phases(phases, tempo, conditions, pace_pct, spin_pct, dew):
    """Populate expectation and wicket_type fields on 1st-innings phase dicts in place."""
    is_4_phase = len(phases) == 4

    if tempo == "true_pace" or conditions == "overcast_cool":
        phases[0]["expectation"] = "Expect seam movement and swing. Pace bowlers will test the batsmen early. Wickets are likely if the ball moves off the surface."
        phases[0]["wicket_type"] = "Pace bowlers — caught behind, bowled, LBW"
    elif tempo == "high_bounce":
        phases[0]["expectation"] = "Extra bounce makes batting tricky early. Short balls and rising deliveries can surprise batsmen. Fast bowlers will look to attack."
        phases[0]["wicket_type"] = "Pace bowlers — caught at slip/gully, fended catches"
    elif tempo == "low_slow":
        phases[0]["expectation"] = "The new ball will skid on, so openers can score freely. Pace bowlers need to be tight — the pitch won't offer much help."
        phases[0]["wicket_type"] = "Pace bowlers — yorkers and cutters most effective"
    elif tempo == "batting_road":
        phases[0]["expectation"] = "A flat deck means batsmen can play their shots freely from ball one. Expect aggressive batting with boundaries flowing."
        phases[0]["wicket_type"] = "Wickets from poor shots — caught in the deep"
    else:
        phases[0]["expectation"] = "Standard opening phase. Pace bowlers will look for early movement while batsmen aim to see off the new ball."
        phases[0]["wicket_type"] = "Mix of pace and movement-based dismissals"

    if spin_pct >= 0.45:
        phases[1]["expectation"] = "Spinners will dominate this phase. The pitch will grip and turn, making run-scoring difficult. Dot-ball pressure will create chances."
        phases[1]["wicket_type"] = "Spinners — stumped, caught close, LBW"
    elif pace_pct >= 0.55:
        phases[1]["expectation"] = "Even in the middle overs, pace bowlers remain dangerous here. Cutters and slower balls will be important for controlling the run rate."
        phases[1]["wicket_type"] = "Pace changes — caught in the deep, bowled by variations"
    else:
        phases[1]["expectation"] = "A balanced phase where both pace and spin share the workload. Smart bowling changes and field placement will be key."
        phases[1]["wicket_type"] = "Mix of spin and pace — fielding pressure creates run outs"

    if is_4_phase:
        if tempo == "batting_road":
            phases[2]["expectation"] = "Set batsmen launch their assault — with 4 fielders outside the circle, gaps still exist for boundaries. This is where the innings shifts gear."
            phases[2]["wicket_type"] = "Caught at boundary from aggressive shots, bowled by yorkers"
        elif tempo == "low_slow":
            phases[2]["expectation"] = "Acceleration is harder on a slow surface. Batsmen must manufacture shots — the ball won't come on to the bat. Smart placement over raw power."
            phases[2]["wicket_type"] = "Bowled playing across the line, stumped charging spinners"
        else:
            phases[2]["expectation"] = "The transition phase where set batsmen begin attacking. Run rate climbs as batsmen target specific bowlers. High-risk, high-reward cricket."
            phases[2]["wicket_type"] = "Caught in the deep, bowled by variations, run outs from quick singles"

        if tempo == "batting_road":
            phases[3]["expectation"] = "On this flat pitch, the final 3 overs will be explosive. Set batsmen will target boundaries aggressively. Bowlers need pinpoint yorkers to survive."
            phases[3]["wicket_type"] = "Caught in the deep from big hits, run outs from quick singles"
        elif tempo == "low_slow":
            phases[3]["expectation"] = "Even in the finish, this pitch won't come on easily. Slogging is difficult when the ball doesn't come on to the bat. Lower-than-usual scoring."
            phases[3]["wicket_type"] = "Bowled playing across the line, caught mishitting on slow surface"
        else:
            phases[3]["expectation"] = "All-out assault in the last 3 overs. Every ball is a boundary opportunity. Death bowlers must be precise — yorkers and slower balls are the only weapons."
            phases[3]["wicket_type"] = "Caught in the deep, bowled by yorkers, run outs"
    else:
        if tempo == "batting_road":
            phases[2]["expectation"] = "On this flat pitch, death overs will be explosive. Set batsmen will target boundaries aggressively. Bowlers need pinpoint yorkers to survive."
            phases[2]["wicket_type"] = "Caught in the deep from big hits, run outs from quick singles"
        elif tempo == "low_slow":
            phases[2]["expectation"] = "Even in the death, this pitch won't come on easily. Slogging is difficult when the ball doesn't come on to the bat. Lower-than-usual death overs scoring."
            phases[2]["wicket_type"] = "Bowled playing across the line, caught mishitting on slow surface"
        else:
            phases[2]["expectation"] = "Standard death-overs action with batsmen looking to accelerate. Bowlers will rely on variations — yorkers, slower balls, and wide lines."
            phases[2]["wicket_type"] = "Caught in the deep, bowled by yorkers, run outs"


def _fill_2nd_innings_phases(phases, tempo, conditions, pace_pct, spin_pct, dew):
    """Populate expectation and wicket_type fields on 2nd-innings phase dicts in place."""
    is_4_phase = len(phases) == 4

    if dew >= 0.6:
        phases[0]["expectation"] = "Dew on the surface reduces swing and seam movement. The new ball won't do as much — openers can be more aggressive from the start."
        phases[0]["wicket_type"] = "Pace bowlers less effective — wickets from batsman error"
    elif tempo == "true_pace" or conditions == "overcast_cool":
        phases[0]["expectation"] = "Conditions may still assist pace, but the pitch has settled after the 1st innings. Chasing teams often start more cautiously."
        phases[0]["wicket_type"] = "Pace bowlers — but less movement than 1st innings"
    elif tempo == "low_slow":
        phases[0]["expectation"] = "Pitch has worn further — the ball may keep low and turn early. Openers need to be watchful against both pace and spin."
        phases[0]["wicket_type"] = "Mix of pace and early spin — variable bounce causes trouble"
    elif tempo == "batting_road":
        phases[0]["expectation"] = "Flat pitch remains easy to bat on. Chasing team can be aggressive in the powerplay knowing the surface is true."
        phases[0]["wicket_type"] = "Wickets from aggressive shots — caught at boundary"
    else:
        phases[0]["expectation"] = "Second innings powerplay tends to be more run-focused. The pitch offers less for bowlers and chasers look to build momentum early."
        phases[0]["wicket_type"] = "Batsman errors under chase pressure"

    if dew >= 0.6 and spin_pct >= 0.45:
        phases[1]["expectation"] = "Dew neutralises spinners — the ball won't grip or turn as much. This is the phase where the chase really accelerates as spinners struggle for control."
        phases[1]["wicket_type"] = "Run outs from aggressive running, caught at boundary from slogging"
    elif spin_pct >= 0.45:
        phases[1]["expectation"] = "Worn pitch will turn more in the 2nd innings. Spinners become even more dangerous — chasers need to be smart rotating strike and picking the right balls to attack."
        phases[1]["wicket_type"] = "Spinners — stumped, LBW, caught close as pitch deteriorates"
    elif pace_pct >= 0.55:
        phases[1]["expectation"] = "Pace bowlers still dominate in middle overs. With the ball getting older, reverse swing becomes a factor. Chasers must maintain scoreboard pressure."
        phases[1]["wicket_type"] = "Reverse swing — bowled, LBW, caught behind"
    else:
        phases[1]["expectation"] = "Balanced middle overs in the chase. The team batting second has the advantage of knowing the target — expect calculated aggression."
        phases[1]["wicket_type"] = "Mix of dismissals — pressure from required rate creates chances"

    if is_4_phase:
        if dew >= 0.6:
            phases[2]["expectation"] = "Dew helps batsmen as the ball skids on. Chasers will look to break the game open in the acceleration phase — boundaries become easier to hit."
            phases[2]["wicket_type"] = "Catches in the deep from aggressive hitting"
        elif tempo == "batting_road":
            phases[2]["expectation"] = "Known target on a flat pitch — chasers can plan exactly when to attack. This 3-over window is where the required rate gets managed down."
            phases[2]["wicket_type"] = "Caught at boundary targeting specific bowlers"
        else:
            phases[2]["expectation"] = "The chase intensifies in the acceleration phase. If the equation is manageable, expect smart aggression. If the rate is high, risky shots and wickets follow."
            phases[2]["wicket_type"] = "Caught in the deep, run outs from pressure running"

        if dew >= 0.6:
            phases[3]["expectation"] = "Dew makes gripping the ball very difficult for bowlers. Death bowling becomes a nightmare — full tosses and boundary-hitting opportunities increase significantly."
            phases[3]["wicket_type"] = "Yorkers and slower balls — anything short or full gets punished"
        elif tempo == "batting_road":
            phases[3]["expectation"] = "If the chase is on, expect fireworks. Flat pitch and known target means batsmen can plan their assault on specific bowlers in the finish."
            phases[3]["wicket_type"] = "Caught in the deep from calculated big hits"
        elif tempo == "low_slow":
            phases[3]["expectation"] = "Chasing on a worn, slow pitch is tricky in the finish. The ball won't come on to the bat — batsmen need to manufacture shots."
            phases[3]["wicket_type"] = "Bowled slogging, stumped charging, caught mishitting"
        else:
            phases[3]["expectation"] = "The final 3 overs decide the chase. If the equation is tight, expect aggressive batting and risky running. Fielding and nerve will decide the outcome."
            phases[3]["wicket_type"] = "Run outs, caught at boundary, yorker bowled"
    else:
        if dew >= 0.6:
            phases[2]["expectation"] = "Dew makes gripping the ball very difficult for bowlers. Death bowling becomes a nightmare — full tosses and boundary-hitting opportunities increase significantly."
            phases[2]["wicket_type"] = "Yorkers and slower balls — anything short or full gets punished"
        elif tempo == "batting_road":
            phases[2]["expectation"] = "If the chase is on, expect fireworks. Flat pitch and known target means batsmen can plan their assault on specific bowlers in the death."
            phases[2]["wicket_type"] = "Caught in the deep from calculated big hits"
        elif tempo == "low_slow":
            phases[2]["expectation"] = "Chasing on a worn, slow pitch is tricky in the death. The ball won't come on to the bat — batsmen need to manufacture shots. If the required rate is high, expect wickets."
            phases[2]["wicket_type"] = "Bowled slogging, stumped charging, caught mishitting"
        else:
            phases[2]["expectation"] = "Standard death-overs chase scenario. If the equation is tight, expect aggressive batting and risky running. Fielding and nerve will decide the outcome."
            phases[2]["wicket_type"] = "Run outs, caught at boundary, yorker bowled"


def get_phase_expectations(venue, match_format):
    """Build phase-by-phase expectations for both innings at a venue.

    Returns:
        Dict with 'innings_1' and 'innings_2' lists of phase dicts.
    """
    stats = VENUE_HISTORICAL_STATS.get(venue, {})
    tempo = get_pitch_tempo(venue)
    weather = get_venue_weather(venue)
    pace_pct = stats.get("pace_wickets_pct", 0.48)
    spin_pct = stats.get("spin_wickets_pct", 0.40)
    dew = weather.get("dew_factor", 0.3)
    conditions = weather.get("typical_conditions", "varied")

    is_odi = 'odi' in match_format

    innings_1 = _build_phase_structure(is_odi)
    _fill_1st_innings_phases(innings_1, tempo, conditions, pace_pct, spin_pct, dew)

    innings_2 = _build_phase_structure(is_odi)
    _fill_2nd_innings_phases(innings_2, tempo, conditions, pace_pct, spin_pct, dew)

    return {"innings_1": innings_1, "innings_2": innings_2}


def build_prematch_analysis(venue, match_format, match_time=None, team1=None, team2=None):
    """Assemble the complete pre-match analysis dict for a venue and format.

    Combines bat/chase records, surface description, par score analysis,
    phase expectations, weather, and toss advice into a single payload.

    Args:
        venue: Venue name.
        match_format: Format string (e.g. 'mens_t20').
        match_time: Optional local match start time as ISO string.
        team1: Optional team 1 name.
        team2: Optional team 2 name.

    Returns:
        Dict with all pre-match analysis fields for the template.
    """
    weather = get_venue_weather(venue)
    tempo = get_pitch_tempo(venue)
    country = get_venue_country(venue)

    bat_chase = get_bat_first_vs_chase_record(venue, match_format)
    surface = get_surface_description(venue, match_format)
    par_score = get_par_score_analysis(venue, match_format)
    phases = get_phase_expectations(venue, match_format)

    format_labels = {
        'mens_t20': "Men's T20",
        'womens_t20': "Women's T20",
        'mens_odi': "Men's ODI",
        'womens_odi': "Women's ODI"
    }

    toss_advice = ""
    if bat_chase["chase_wins"] >= 58:
        toss_advice = "Win the toss and chase. Conditions heavily favour the team batting second."
    elif bat_chase["chase_wins"] >= 54:
        toss_advice = "Chasing is preferred. Dew and easier conditions make batting second advantageous."
    elif bat_chase["bat_first_wins"] >= 58:
        toss_advice = "Bat first. Defending a total is easier here — the pitch deteriorates and conditions get tougher."
    elif bat_chase["bat_first_wins"] >= 54:
        toss_advice = "Slight edge to batting first. Setting a target allows bowlers to use the pitch before it wears."
    else:
        toss_advice = "Toss is not decisive here — both batting first and chasing are viable strategies."

    match_time_utc = None
    venue_tz_name = None
    if match_time:
        try:
            venue_tz_name = get_venue_timezone(venue)
            venue_tz = pytz.timezone(venue_tz_name)
            naive_dt = datetime.strptime(match_time, "%Y-%m-%dT%H:%M")
            local_dt = venue_tz.localize(naive_dt)
            utc_dt = local_dt.astimezone(pytz.utc)
            match_time_utc = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            match_time_utc = match_time

    return {
        "venue": venue,
        "country": country,
        "match_format": match_format,
        "format_label": format_labels.get(match_format, "T20"),
        "match_time": match_time,
        "match_time_utc": match_time_utc,
        "venue_timezone": venue_tz_name,
        "team1": team1,
        "team2": team2,
        "weather": weather,
        "pitch_tempo": tempo,
        "bat_chase": bat_chase,
        "surface": surface,
        "par_score": par_score,
        "phases": phases,
        "toss_advice": toss_advice
    }
