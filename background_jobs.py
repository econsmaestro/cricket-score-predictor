"""
Background data collection: scrapes recently completed T20 and ODI matches
from Cricbuzz daily and stores them in the database.

Data collected per match:
  - Teams, venue, format, date
  - First and second innings scores / wickets / overs
  - Winner and result text
  - Toss winner + decision (where available)
  - Playing XIs for both teams (where available)

This feeds both HistoricalMatch (for display) and MatchOutcome (for learning).
"""

import logging
import json
import re
from datetime import datetime, date, timedelta

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Entry point — called by APScheduler once per day
# ---------------------------------------------------------------------------

def daily_match_scrape():
    """
    Scrape recently completed matches and store results.
    Safe to call multiple times — duplicates are silently skipped.
    """
    from app import app
    with app.app_context():
        try:
            _run_scrape()
        except Exception as exc:
            logger.error(f"daily_match_scrape failed: {exc}", exc_info=True)


def _run_scrape():
    """Inner scrape logic (runs inside app context)."""
    from app import db
    from models import ScrapedMatch
    from live_match_scraper import get_live_matches, get_match_details

    logger.info("Background scrape: fetching completed matches…")

    try:
        all_matches = get_live_matches()
    except Exception as exc:
        logger.warning(f"get_live_matches() failed: {exc}")
        return

    completed = [m for m in all_matches if m.get('status') == 'Completed']
    logger.info(f"Found {len(completed)} completed match(es) to process.")

    saved = 0
    for match in completed:
        match_id = match.get('id', '')
        if not match_id:
            continue

        # Skip if already stored
        if ScrapedMatch.query.filter_by(match_id=match_id).first():
            continue

        # Fetch detailed data (score, venue, squads, toss)
        try:
            details = get_match_details(match_id)
        except Exception as exc:
            logger.debug(f"Could not fetch details for {match_id}: {exc}")
            details = {}

        record = _build_record(match, details or {})
        if record is None:
            continue

        # Fetch weather for the match date/venue
        try:
            from weather_scraper import get_match_weather
            wx = get_match_weather(record.venue, record.match_date)
            if wx:
                record.weather_temp_c       = wx.get('temp_c')
                record.weather_humidity_pct = wx.get('humidity_pct')
                record.weather_dewpoint_c   = wx.get('dewpoint_c')
                record.weather_precip_mm    = wx.get('precip_mm')
                record.weather_cloud_pct    = wx.get('cloud_pct')
                record.weather_wind_kph     = wx.get('wind_kph')
                record.weather_description  = wx.get('description')
                record.weather_rain_risk    = wx.get('rain_risk')
                record.weather_dew_risk     = wx.get('dew_risk')
        except Exception as wx_err:
            logger.debug(f"Weather fetch skipped for {record.venue}: {wx_err}")

        db.session.add(record)
        try:
            db.session.commit()
            saved += 1
            logger.info(f"Saved: {record.team1} vs {record.team2} — {record.result_text}")

            # Feed into the learning engine MatchOutcome table
            _record_outcome_for_learning(record)

        except Exception as exc:
            db.session.rollback()
            logger.warning(f"Could not save match {match_id}: {exc}")

    # Re-run learning cycle if we got new data
    if saved > 0:
        try:
            from learning_engine import run_learning_cycle
            run_learning_cycle()
            logger.info(f"Learning cycle triggered after saving {saved} new match(es).")
        except Exception as exc:
            logger.warning(f"Learning cycle failed after scrape: {exc}")

    # Update last-run timestamp
    _set_last_scrape(db)
    logger.info(f"Scrape complete — {saved} new match(es) saved.")


# ---------------------------------------------------------------------------
# Record builder
# ---------------------------------------------------------------------------

def _build_record(match: dict, details: dict):
    """Build a ScrapedMatch ORM object from scraper dicts. Returns None if unusable."""
    from models import ScrapedMatch

    match_id   = match.get('id', '')
    fmt        = (match.get('format') or details.get('format') or '').upper()
    # Only T20 and ODI are interesting for the learning engine
    if fmt not in ('T20', 'ODI', 'T20I', 'ODI'):
        # Accept any format string containing T20 or ODI
        if 'T20' not in fmt and 'ODI' not in fmt:
            fmt_check = match.get('display_text', '') + match.get('format', '')
            if 'T20' not in fmt_check.upper() and 'ODI' not in fmt_check.upper():
                return None  # skip Test matches, etc.

    teams      = match.get('teams') or details.get('teams') or []
    team1      = teams[0] if len(teams) > 0 else ''
    team2      = teams[1] if len(teams) > 1 else ''
    if not team1 or not team2:
        return None

    result_text = match.get('result_text') or _extract_result(match.get('display_text', ''))
    venue       = details.get('venue') or ''
    match_fmt   = _normalise_format(fmt or match.get('display_text', ''))

    # Scores — details gives current_score for the batting team
    inn1_score   = details.get('current_score') or 0
    inn1_wickets = details.get('wickets') or 0
    inn1_overs   = details.get('overs') or 0.0
    inn2_score   = details.get('target', 0) - 1 if details.get('target') else None

    # Toss — parse from display_text or details
    toss_winner, toss_decision = _parse_toss(details)

    # Playing XIs
    team1_xi = details.get('team1_xi') or details.get('bowling_team_squad') or []
    team2_xi = details.get('team2_xi') or details.get('yet_to_bat') or []

    today = date.today()

    return ScrapedMatch(
        match_id=match_id,
        match_date=today,
        venue=venue,
        team1=team1,
        team2=team2,
        match_format=match_fmt,
        result_text=result_text or '',
        winner=_extract_winner(result_text or '', team1, team2),
        inn1_score=int(inn1_score) if inn1_score else 0,
        inn1_wickets=int(inn1_wickets) if inn1_wickets else 0,
        inn1_overs=float(inn1_overs) if inn1_overs else 0.0,
        inn2_score=int(inn2_score) if inn2_score else None,
        inn2_wickets=None,
        inn2_overs=None,
        toss_winner=toss_winner,
        toss_decision=toss_decision,
        team1_xi=json.dumps(team1_xi) if team1_xi else None,
        team2_xi=json.dumps(team2_xi) if team2_xi else None,
        source='cricbuzz',
        scraped_at=datetime.utcnow(),
    )


def _record_outcome_for_learning(record):
    """Store an outcome in MatchOutcome so the learning engine can use it."""
    if not record.venue or not record.inn1_score:
        return
    try:
        from learning_engine import record_match_outcome
        fmt_key = 'mens_t20' if 'T20' in (record.match_format or '').upper() else 'mens_odi'
        record_match_outcome(
            match_id=record.match_id,
            venue=record.venue,
            match_format=fmt_key,
            final_score=record.inn1_score,
            wickets=record.inn1_wickets,
            source='auto',
        )
    except Exception as exc:
        logger.debug(f"Could not record outcome for learning: {exc}")


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _extract_result(display_text: str) -> str:
    """Pull result text after the '•' separator."""
    if ' - ' in display_text:
        return display_text.split(' - ', 1)[-1].strip()
    return ''


def _extract_winner(result_text: str, team1: str, team2: str) -> str:
    m = re.search(r'([A-Za-z\s]+?)\s+won', result_text)
    if m:
        return m.group(1).strip()
    return ''


def _parse_toss(details: dict):
    """Return (toss_winner, toss_decision) from match details, or (None, None)."""
    # Some scrapers embed toss in a 'toss' key
    toss_raw = details.get('toss', '') or ''
    if toss_raw:
        winner = None
        decision = None
        low = toss_raw.lower()
        if 'bat' in low:
            decision = 'bat'
        elif 'field' in low or 'bowl' in low:
            decision = 'field'
        # Try to extract team name before "won the toss"
        m = re.search(r'^(.+?)\s+won\s+the\s+toss', toss_raw, re.I)
        if m:
            winner = m.group(1).strip()
        return winner, decision
    return None, None


def _normalise_format(raw: str) -> str:
    raw_up = raw.upper()
    if 'T20' in raw_up:
        return 'T20'
    if 'ODI' in raw_up:
        return 'ODI'
    return raw.strip()[:20] if raw else 'Unknown'


# ---------------------------------------------------------------------------
# Last-scrape timestamp (stored as a row in AppConfig)
# ---------------------------------------------------------------------------

def get_last_scrape_time():
    """Return the datetime of the last successful scrape, or None."""
    try:
        from models import AppConfig
        row = AppConfig.query.filter_by(key='last_match_scrape').first()
        if row:
            return datetime.fromisoformat(row.value)
    except Exception:
        pass
    return None


def _set_last_scrape(db):
    try:
        from models import AppConfig
        row = AppConfig.query.filter_by(key='last_match_scrape').first()
        if row:
            row.value = datetime.utcnow().isoformat()
        else:
            db.session.add(AppConfig(key='last_match_scrape', value=datetime.utcnow().isoformat()))
        db.session.commit()
    except Exception as exc:
        logger.debug(f"Could not update last_match_scrape: {exc}")
