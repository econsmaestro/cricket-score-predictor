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


def _bat_chase_tactical(bat_chase, weather):
    """Generate specific bat-first vs chase tactical advice from conditions."""
    chase_pct = bat_chase['chase_wins']
    bat_pct = bat_chase['bat_first_wins']
    dew = weather.get('dew_factor', 0.3)
    swing = weather.get('swing_window', 'first_6')
    conditions = weather.get('typical_conditions', 'varied')

    if chase_pct >= 58:
        base = "Win the toss and chase without hesitation."
        if dew >= 0.6:
            return (base + " Heavy dew under lights will make the surface slicker and spinners will lose grip — "
                    "batting second is a significant advantage. If defending, bowl your best pacers in the powerplay "
                    "before the ball gets wet and aim for par + 20.")
        return (base + " Chasing teams here have a proven edge — the target is visible, the outfield quickens under "
                "floodlights, and pressure is on the defending side. Keep wickets in hand through the powerplay "
                "and launch in the death.")

    if chase_pct >= 54:
        if dew >= 0.5:
            return ("Slight preference for chasing. Dew settles quickly at this venue — front-load your best pacers "
                    "in the powerplay before the ball turns slippery. If forced to bat first, aim 15+ above par "
                    "to account for the second-innings batting advantage.")
        return ("Chasing is marginally preferred but not a lock. If batting first, be aggressive in the back 5 overs "
                "to give your bowlers a total they can defend. Don't hold wickets in hand at the expense of runs here.")

    if bat_pct >= 58:
        if 'overcast' in conditions or swing in ('all_innings', 'first_10'):
            return ("Bat first — the overcast skies that look threatening are deceptive. Getting through the new ball "
                    "under cloud cover is tough but the surface settles. A first-innings platform of 170+ is hard to "
                    "chase as the pitch dries and conditions clear for the bowling side.")
        return ("Bat first with confidence. The pitch deteriorates significantly through two innings — a first-innings "
                "score of par + 15 becomes very difficult to chase as the surface gets two-paced and slower.")

    if bat_pct >= 54:
        return ("Slight lean toward batting first. The pitch doesn't hold its pace through two innings — set a total, "
                "then use the wearing surface with your spinners in the chase. Don't be afraid to attack from over 1.")

    # Neutral — but give specific actionable advice
    if dew >= 0.6:
        return ("Toss is close, but tonight's dew is the deciding factor. Under lights the surface will ease — "
                "chasing is the smarter call if dew arrives early. If you do bat first, target par + 10 minimum "
                "to overcome the second-innings batting advantage, and bowl your best spinner early before the "
                "ball loses grip.")
    if 'overcast' in conditions or swing in ('all_innings', 'first_10'):
        return ("Overcast conditions tilt this toward bowling first. Swing will be available early — "
                "use your best inswing bowler in the powerplay to attack the top order, then chase under "
                "clearer skies as the cloud cover typically lifts through the evening.")
    if swing == 'first_4':
        return ("Bowl first and exploit the first 4 overs — the new ball will dart around significantly. "
                "Once the shine goes the surface flattens and run-scoring becomes easier. A chase on a "
                "true surface is the ideal scenario at this venue.")
    return ("No strong toss preference — both strategies are viable here. Either way, the powerplay is decisive: "
            "a strong start with the bat sets you up to attack in the death; a strong start with the ball "
            "builds pressure that compounds through the innings. Don't let the first 6 slip.")


def _surface_tactical(surface, weather):
    """Generate specific surface/pitch tactical advice from pitch and weather data."""
    pace_pct = surface.get('pace_wicket_pct', 50)
    spin_pct = surface.get('spin_wicket_pct', 40)
    tempo = surface.get('pitch_tempo', 'default')
    swing = weather.get('swing_window', 'first_6')
    conditions = weather.get('typical_conditions', 'varied')
    dew = weather.get('dew_factor', 0.3)

    if pace_pct >= 60:
        swing_detail = {
            'first_4': "Open with your most dangerous swinger — movement is extreme in the first 4 overs. Attack hard.",
            'first_6': "Front-load your pace spearhead in the powerplay. The new ball will swing and seam — attack the top 3.",
            'first_10': "Use pace for the full first 10 overs, including a second spell in overs 8–10. The ball keeps moving longer here.",
            'all_innings': "The ball swings throughout — don't rest your pace spearhead. A second spell in overs 14–16 can be as dangerous as the powerplay.",
        }.get(swing, "Attack with pace in the powerplay — new ball movement is your primary weapon.")
        return (f"Pace is king here — {pace_pct}% of wickets fall to seam. {swing_detail} "
                + ("Expect high bounce short of length — a short-pitched barrage can create awkward dismissals. " if tempo == 'high_bounce' else "")
                + "Spinners should focus purely on economy and cutting off boundaries — this is not their surface.")

    if spin_pct >= 50:
        dew_warning = (" Watch the dew — if playing under lights, the ball may stop gripping in the second innings. "
                       "Your spinners need to take wickets in the first innings while conditions hold." if dew >= 0.6 else "")
        if tempo == 'low_slow':
            return (f"Spinners will win this match — {spin_pct}% of wickets go to turn, and the surface is low and slow. "
                    "Consider opening the bowling with your best spinner — it works on this surface. Batsmen must hit "
                    "against the turn early before the pitch dries further and grip increases." + dew_warning
                    + " An extra spinner in the XI could be the selection masterstroke here.")
        return (f"This is a spinner's surface — {spin_pct}% of wickets to turn. Deploy your best spinner aggressively "
                "through overs 8–16 when the surface assists most. Batsmen should look to use their feet and "
                "attack the spinner before they settle into a rhythm." + dew_warning
                + " Picking an extra spinner gives the captain more attacking options in the crucial middle phase.")

    if tempo == 'batting_road':
        return ("This is a flat road — bowlers have nowhere to hide. "
                "Use full-pitched yorker-length deliveries at off-stump and vary your pace aggressively in the death. "
                "Spinners must bowl very straight with a leg-side field — don't give width. "
                "The captain who gets the powerplay fielding restrictions right and uses them aggressively wins the match.")

    if tempo == 'true_pace':
        return ("The pitch carries well and rewards disciplined, full-pitched bowling. "
                "Good length gets edges; back of a length gets cut away. Bowl at the top of off-stump and trust your best "
                "quick bowler in the powerplay — pace on this surface is more dangerous than spin or cutters. "
                "Save your slower-ball specialist for the death when batsmen are looking to go big.")

    if tempo == 'high_bounce':
        return (f"Bounce is the key weapon — {pace_pct}% of wickets to pace. "
                "Bowl short of a length at the body — deliveries that climb into the ribs create false shots. "
                "Batsmen must get onto the front foot and drive through the line rather than pulling or cutting. "
                "Spinners should stick to off-stump and avoid the short ball — their strength here is containment, not wickets.")

    # Balanced
    if swing in ('first_4', 'first_6'):
        return (f"A balanced contest — pace takes {pace_pct}%, spin takes {spin_pct}%. "
                "Use pace in the powerplay to exploit the new ball moving through the air, then hand over to your "
                "spinner in overs 8–15. Read each batsman individually — some will struggle against pace, others against turn. "
                "Flexibility and a captain who switches plans quickly wins on this pitch.")
    return (f"A genuine 50-50 surface — pace takes {pace_pct}%, spin takes {spin_pct}%. "
            "Rotate your bowlers based on the live match situation rather than a rigid plan. "
            "The captain who adapts quickest wins — don't let any bowler bowl through a bad spell.")


def _par_score_tactical(par_score, weather, surface):
    """Generate specific par score and scoring-vibe tactical advice."""
    vibe = par_score.get('scoring_vibe', 'balanced')
    par = par_score.get('par_score', 165)
    dew = weather.get('dew_factor', 0.3)
    tempo = surface.get('pitch_tempo', 'default')

    if vibe == 'high-scoring':
        dew_line = (" Dew will flatten any demons in the pitch for the chasing team — if chasing, stay patient early and "
                    "back the surface to come good." if dew >= 0.5
                    else " If chasing, don't let the rate climb past 10 in the death — power-hitting windows close fast on flat surfaces.")
        return (f"Par is {par} — batting first, treat anything under par + 15 as a dangerous score to defend. "
                "Attack aggressively from the powerplay: the outfield is fast, the boundaries are accessible, and "
                "this crowd rewards big hitting. Don't consolidate through overs 8–14 — rotate strike at 8+ and "
                "accelerate the moment a bowler gives you width." + dew_line)

    if vibe == 'low-scoring spin battle':
        return (f"Par here is only {par} — this is a bowler's match and every run is earned. "
                "Batting first: rotate strike obsessively and treat 6 an over through overs 6–15 as perfectly acceptable. "
                "The pitch will play harder for the chasing team as it deteriorates — a score of {par} is a genuine "
                "defending total. Don't give away wickets trying to accelerate prematurely. "
                "Bowling: bowl stump-to-stump, cut off the boundary, and let the pitch do the work. "
                "Every dot ball builds enormous pressure in a low-scoring game.")

    if vibe == 'pace-dominated':
        bat_line = ("Get through the new ball — absorb overs 1–5, accepting 4–5 runs an over, then explode once "
                    "the shine goes and the seamers tire. Don't play big shots against the new ball." if tempo != 'batting_road'
                    else "The surface is flat enough to take on the pace — back your eye and play your natural game from ball 1.")
        return (f"Pace bowlers set the tone — par of {par} reflects the seam-friendly nature of this surface. "
                f"Batting: {bat_line} "
                "Bowling: the new ball is everything — use your two best seamers for the full powerplay, then hold one in "
                "reserve for a second spell in overs 14–16 when the ball starts reversing.")

    # Balanced/default
    dew_line = (f" Dew could tilt the balance — batting first, aim {par + 10}+ to account for a slicker pitch "
                "in the second innings." if dew >= 0.6
                else " The first 6 overs set the tempo for the entire innings — don't let a slow powerplay force "
                     "you into risky big-hitting later when wickets in hand matter most.")
    return (f"Par is {par} — a competitive but achievable target in either innings. "
            "Execute your powerplay plan cleanly: batting first, look to be {par - 10} to {par} at the halfway point "
            "with at least 6 wickets in hand so you can accelerate freely in the death." + dew_line)


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

    bat_chase['tactical_implication'] = _bat_chase_tactical(bat_chase, weather)
    surface['tactical_implication'] = _surface_tactical(surface, weather)
    par_score['tactical_implication'] = _par_score_tactical(par_score, weather, surface)

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
