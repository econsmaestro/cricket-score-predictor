"""
Fielding statistics engine.

Two-layer calibration:
  1. Cricsheet ball-by-ball data  — authoritative long-run fielding events
     (catches, run-outs direct/relay, stumpings, runs-allowed rate).
     Computed when Cricsheet zips are available locally or downloaded fresh.
  2. Backtest bias calibration  — fine-tunes using prediction error signals
     per (fielding_team, format). Positive bias = better fielding = higher efficiency.

Team efficiency combines both layers; player-level dismissal stats come
exclusively from Cricsheet ball-by-ball data.
"""

import json
import logging
from pathlib import Path
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)

FIELDING_DIR = Path("data/fielding")
TEAM_RATINGS_FILE = FIELDING_DIR / "team_ratings.json"
PLAYER_STATS_FILE = FIELDING_DIR / "player_stats.json"

BACKTEST_FILES = {
    "mens_odi": "data/backtests/mens_odi.json",
    "womens_odi": "data/backtests/womens_odi.json",
    "mens_t20": "data/backtests/mens_t20.json",
    "womens_t20": "data/backtests/womens_t20.json",
}

# Minimum matches per (team, format) to trust the bias signal
MIN_MATCHES_FOR_ADJUSTMENT = 3

# Full confidence at this many matches; below it, adjustment is dampened
FULL_CONFIDENCE_MATCHES = 15

# How many runs of bias map to 1.0 of efficiency adjustment (damping factor)
BIAS_SCALE = 400.0


def _load_hardcoded_baseline() -> dict:
    """Return the hardcoded TEAM_FIELDING_EFFICIENCY dict as a fallback baseline."""
    try:
        from prediction import TEAM_FIELDING_EFFICIENCY
        return dict(TEAM_FIELDING_EFFICIENCY)
    except Exception:
        return {}


def compute_team_ratings(
    min_matches: int = MIN_MATCHES_FOR_ADJUSTMENT,
    bias_scale: float = BIAS_SCALE,
    save: bool = True,
) -> dict:
    """
    Compute fielding efficiency ratings from backtest prediction errors.

    Returns:
        {team_name: {format: {efficiency, bias_runs, matches, ...}}}
    """
    hardcoded = _load_hardcoded_baseline()

    # Accumulate per-match mean errors: {team: {fmt: [per_match_avg_error]}}
    match_errors: dict = defaultdict(lambda: defaultdict(list))

    for fmt, path_str in BACKTEST_FILES.items():
        p = Path(path_str)
        if not p.exists():
            logger.debug("Backtest file missing, skipping: %s", path_str)
            continue

        with open(p) as f:
            data = json.load(f)

        # Average checkpoints per match to get one error value per match
        per_match: dict = defaultdict(list)
        for r in data.get("results", []):
            ft = r.get("fielding_team", "")
            if ft:
                per_match[(r["match_id"], ft)].append(r["error"])

        for (match_id, ft), errs in per_match.items():
            match_errors[ft][fmt].append(sum(errs) / len(errs))

    ratings: dict = {}

    for team, fmt_map in match_errors.items():
        ratings[team] = {}

        for fmt, errors in fmt_map.items():
            n = len(errors)
            if n < min_matches:
                # Too few observations — record raw data but don't adjust efficiency
                ratings[team][fmt] = {
                    "efficiency": round(hardcoded.get(team, 0.85), 4),
                    "baseline_efficiency": round(hardcoded.get(team, 0.85), 4),
                    "bias_runs": round(sum(errors) / n, 2),
                    "adjustment": 0.0,
                    "confidence": round(n / FULL_CONFIDENCE_MATCHES, 3),
                    "matches": n,
                    "note": "insufficient_data",
                }
                continue

            mean_bias = sum(errors) / n
            confidence = min(1.0, n / FULL_CONFIDENCE_MATCHES)
            baseline = hardcoded.get(team, 0.85)

            # Positive bias → better fielding → increase efficiency
            raw_adj = mean_bias / bias_scale
            adj = round(confidence * raw_adj, 4)
            efficiency = round(max(0.65, min(0.98, baseline + adj)), 4)

            ratings[team][fmt] = {
                "efficiency": efficiency,
                "baseline_efficiency": round(baseline, 4),
                "bias_runs": round(mean_bias, 2),
                "adjustment": adj,
                "confidence": round(confidence, 3),
                "matches": n,
            }

    if save:
        FIELDING_DIR.mkdir(parents=True, exist_ok=True)
        with open(TEAM_RATINGS_FILE, "w") as f:
            json.dump(ratings, f, indent=2, sort_keys=True)
        logger.info("Saved fielding ratings: %d teams across all formats", len(ratings))

    return ratings


def get_team_efficiency(team: str, match_format: str = "mens_t20") -> Optional[float]:
    """
    Look up computed fielding efficiency for a team and format.

    Falls back gracefully:
      1. Exact (team, format) match
      2. Same gender, different format type
      3. Any available format for this team
      4. Returns None if team has no data at all

    Returns None when no data exists so the caller can apply its own fallback.
    """
    if not TEAM_RATINGS_FILE.exists():
        try:
            compute_team_ratings()
        except Exception as exc:
            logger.error("Could not build fielding ratings: %s", exc)
            return None

    try:
        with open(TEAM_RATINGS_FILE) as f:
            ratings = json.load(f)
    except Exception:
        return None

    team_data = ratings.get(team, {})

    if match_format in team_data:
        return team_data[match_format]["efficiency"]

    # Same gender, any format
    is_womens = "womens" in match_format
    for fmt, data in team_data.items():
        if ("womens" in fmt) == is_womens:
            return data["efficiency"]

    # Any format at all for this team
    if team_data:
        vals = list(team_data.values())
        return vals[0]["efficiency"]

    return None


def rebuild_ratings() -> dict:
    """Force recompute team ratings from current backtest data."""
    return compute_team_ratings(save=True)


# ---------------------------------------------------------------------------
# Cricsheet-based fielding pipeline (player + team level)
# ---------------------------------------------------------------------------

CRICSHEET_FORMATS = ["mens_t20", "womens_t20", "mens_odi", "womens_odi"]


def compute_cricsheet_fielding(formats=None, force_download=False, save=True) -> tuple:
    """
    Download Cricsheet ball-by-ball data for all formats, then compute:
      - Per-player dismissal stats (catches, run-outs, stumpings).
      - Per-team fielding stats (dismissal rates, runs-allowed rate).
      - Per-team efficiency scores blended with backtest calibration.

    Returns (player_stats, team_ratings) dicts.
    """
    from backtest_data import download_data, parse_matches

    if formats is None:
        formats = CRICSHEET_FORMATS

    # Accumulate raw stats
    players: dict = defaultdict(lambda: {
        "catches": 0,
        "run_out_direct": 0,
        "run_out_involved": 0,
        "stumpings": 0,
        "teams": set(),
        "formats": set(),
    })

    # (team, fmt) → fielding event totals
    team_fmt: dict = defaultdict(lambda: {
        "innings": 0,
        "catches": 0,
        "run_out_direct": 0,
        "run_out_involved": 0,
        "stumpings": 0,
        "runs_allowed": 0,
        "balls_fielded": 0,
    })

    for fmt in formats:
        logger.info("Downloading/parsing Cricsheet data for %s ...", fmt)
        try:
            download_data(force=force_download, match_format=fmt)
            matches = parse_matches(match_format=fmt)
        except Exception as exc:
            logger.warning("Could not load %s: %s", fmt, exc)
            continue

        logger.info("  %d matches loaded for %s", len(matches), fmt)

        for match in matches:
            fielding_team = match.get("fielding_team", "")
            if not fielding_team:
                continue

            key = (fielding_team, fmt)
            team_fmt[key]["innings"] += 1

            for over in match.get("overs", []):
                for d in over.get("deliveries", []):
                    extras = d.get("extras", {})
                    is_wide = "wides" in extras

                    team_fmt[key]["runs_allowed"] += d.get("runs_total", 0)
                    if not is_wide:
                        team_fmt[key]["balls_fielded"] += 1

                    for wicket in d.get("wickets", []):
                        kind = wicket.get("kind", "")
                        fielder_objs = wicket.get("fielders", [])
                        names = [f.get("name", "") for f in fielder_objs if f.get("name")]

                        for name in names:
                            players[name]["teams"].add(fielding_team)
                            players[name]["formats"].add(fmt)

                        if kind == "caught":
                            team_fmt[key]["catches"] += 1
                            if names:
                                players[names[0]]["catches"] += 1

                        elif kind == "stumped":
                            team_fmt[key]["stumpings"] += 1
                            if names:
                                players[names[0]]["stumpings"] += 1

                        elif kind == "run out":
                            if len(names) == 1:
                                team_fmt[key]["run_out_direct"] += 1
                                players[names[0]]["run_out_direct"] += 1
                            else:
                                team_fmt[key]["run_out_involved"] += 1
                                for name in names:
                                    players[name]["run_out_involved"] += 1

    # Serialise player stats
    player_stats_out: dict = {}
    for name, s in players.items():
        total = s["catches"] + s["run_out_direct"] + s["run_out_involved"] + s["stumpings"]
        player_stats_out[name] = {
            "catches": s["catches"],
            "run_out_direct": s["run_out_direct"],
            "run_out_involved": s["run_out_involved"],
            "stumpings": s["stumpings"],
            "total_fielding_dismissals": total,
            "teams": sorted(s["teams"]),
            "formats": sorted(s["formats"]),
        }

    # Compute per-format baselines for normalization
    fmt_baselines: dict = {}
    for fmt in formats:
        entries = [(k, v) for k, v in team_fmt.items() if k[1] == fmt and v["innings"] >= 3]
        if not entries:
            continue
        dis_rates = [
            (v["catches"] + v["run_out_direct"] + v["run_out_involved"] + v["stumpings"]) / v["innings"]
            for _, v in entries
        ]
        rpo_vals = [
            v["runs_allowed"] / (v["balls_fielded"] / 6)
            for _, v in entries if v["balls_fielded"] > 0
        ]
        fmt_baselines[fmt] = {
            "mean_dismissal_rate": sum(dis_rates) / len(dis_rates),
            "mean_rpo": sum(rpo_vals) / len(rpo_vals) if rpo_vals else 6.5,
        }

    # Load backtest calibration for blending
    bt_calibration: dict = {}
    try:
        bt_calibration = compute_team_ratings(save=False)
    except Exception:
        pass

    # Build blended team ratings
    hardcoded = _load_hardcoded_baseline()
    team_ratings_out: dict = {}

    for (team, fmt), v in team_fmt.items():
        if v["innings"] < 1:
            continue

        base = fmt_baselines.get(fmt, {"mean_dismissal_rate": 1.5, "mean_rpo": 6.5})
        total_dis = v["catches"] + v["run_out_direct"] + v["run_out_involved"] + v["stumpings"]
        dis_per_inn = total_dis / v["innings"]
        rpo = v["runs_allowed"] / (v["balls_fielded"] / 6) if v["balls_fielded"] > 0 else base["mean_rpo"]

        # Cricsheet-based efficiency (dismissal 65%, ground-fielding RPO proxy 35%)
        dis_delta = (dis_per_inn - base["mean_dismissal_rate"]) * 0.06
        rpo_delta = (base["mean_rpo"] - rpo) * 0.015
        cricsheet_eff = max(0.65, min(0.98, 0.85 + dis_delta + rpo_delta))

        # Backtest calibration adjustment
        bt_adj = 0.0
        if team in bt_calibration and fmt in bt_calibration[team]:
            bt_entry = bt_calibration[team][fmt]
            bt_n = bt_entry.get("matches", 0)
            if bt_n >= 3:
                # Blend: Cricsheet weight grows with innings, BT weight grows with matches
                cs_weight = min(1.0, v["innings"] / 20)
                bt_weight = min(0.3, bt_n / 50)  # backtest caps at 30% influence
                blended = (cs_weight * cricsheet_eff + bt_weight * (cricsheet_eff + bt_entry["adjustment"])) / (cs_weight + bt_weight)
                efficiency = round(max(0.65, min(0.98, blended)), 4)
                bt_adj = round(bt_entry["adjustment"], 4)
            else:
                efficiency = round(cricsheet_eff, 4)
        else:
            efficiency = round(cricsheet_eff, 4)

        if team not in team_ratings_out:
            team_ratings_out[team] = {}

        team_ratings_out[team][fmt] = {
            "efficiency": efficiency,
            "cricsheet_efficiency": round(cricsheet_eff, 4),
            "backtest_adjustment": bt_adj,
            "innings": v["innings"],
            "catches": v["catches"],
            "run_out_direct": v["run_out_direct"],
            "run_out_involved": v["run_out_involved"],
            "stumpings": v["stumpings"],
            "dismissals_per_innings": round(dis_per_inn, 3),
            "rpo_allowed": round(rpo, 3),
            "source": "cricsheet",
        }

    # For teams in backtest but NOT in Cricsheet, keep the BT-calibrated rating
    for team, fmt_map in bt_calibration.items():
        for fmt, bt_entry in fmt_map.items():
            if team not in team_ratings_out or fmt not in team_ratings_out[team]:
                if team not in team_ratings_out:
                    team_ratings_out[team] = {}
                team_ratings_out[team][fmt] = {
                    "efficiency": bt_entry["efficiency"],
                    "baseline_efficiency": bt_entry["baseline_efficiency"],
                    "bias_runs": bt_entry["bias_runs"],
                    "matches": bt_entry["matches"],
                    "source": "backtest_calibration",
                }

    if save:
        FIELDING_DIR.mkdir(parents=True, exist_ok=True)
        with open(PLAYER_STATS_FILE, "w") as f:
            json.dump(player_stats_out, f, indent=2, sort_keys=True)
        with open(TEAM_RATINGS_FILE, "w") as f:
            json.dump(team_ratings_out, f, indent=2, sort_keys=True)
        logger.info(
            "Saved: %d players, %d teams (%d format entries)",
            len(player_stats_out),
            len(team_ratings_out),
            sum(len(v) for v in team_ratings_out.values()),
        )

    return player_stats_out, team_ratings_out


def rebuild_all(force_download=False) -> tuple:
    """Full rebuild: download Cricsheet, compute everything, save JSON files."""
    return compute_cricsheet_fielding(force_download=force_download, save=True)


def get_all_team_stats() -> dict:
    """Return full team ratings dict, building from scratch if needed."""
    if not TEAM_RATINGS_FILE.exists():
        return compute_team_ratings()
    with open(TEAM_RATINGS_FILE) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Player-level stats (requires Cricsheet ball-by-ball data)
# ---------------------------------------------------------------------------

def compute_player_stats_from_cricsheet(matches_by_format: dict) -> dict:
    """
    Extract per-player fielding dismissal stats from parsed Cricsheet matches.

    Args:
        matches_by_format: {format_name: [match_dict, ...]}
            Each match_dict must have:
              - 'overs': list of over dicts, each with 'deliveries'
              - 'fielding_team': str
            Each delivery optionally has 'wickets': [{kind, fielders: [{name}]}]

    Returns:
        {player_name: {catches, run_out_direct, run_out_involved, stumpings,
                       total_fielding_dismissals, teams, formats}}
    """
    players: dict = defaultdict(lambda: {
        "catches": 0,
        "run_out_direct": 0,
        "run_out_involved": 0,
        "stumpings": 0,
        "teams": set(),
        "formats": set(),
    })

    for fmt, matches in matches_by_format.items():
        for match in matches:
            fielding_team = match.get("fielding_team", "")
            for over in match.get("overs", []):
                for d in over.get("deliveries", []):
                    for wicket in d.get("wickets", []):
                        kind = wicket.get("kind", "")
                        fielders = wicket.get("fielders", [])
                        names = [f.get("name", "") for f in fielders if f.get("name")]

                        for name in names:
                            players[name]["teams"].add(fielding_team)
                            players[name]["formats"].add(fmt)

                        if kind == "caught":
                            if names:
                                players[names[0]]["catches"] += 1
                        elif kind == "stumped":
                            if names:
                                players[names[0]]["stumpings"] += 1
                        elif kind == "run out":
                            # 1 fielder = direct throw (ground fielding proxy)
                            if len(names) == 1:
                                players[names[0]]["run_out_direct"] += 1
                            else:
                                for name in names:
                                    players[name]["run_out_involved"] += 1

    # Serialise (sets → sorted lists)
    out: dict = {}
    for name, s in players.items():
        total = s["catches"] + s["run_out_direct"] + s["run_out_involved"] + s["stumpings"]
        out[name] = {
            "catches": s["catches"],
            "run_out_direct": s["run_out_direct"],
            "run_out_involved": s["run_out_involved"],
            "stumpings": s["stumpings"],
            "total_fielding_dismissals": total,
            "teams": sorted(s["teams"]),
            "formats": sorted(s["formats"]),
        }

    FIELDING_DIR.mkdir(parents=True, exist_ok=True)
    with open(PLAYER_STATS_FILE, "w") as f:
        json.dump(out, f, indent=2, sort_keys=True)

    logger.info("Saved player fielding stats: %d players", len(out))
    return out


def get_player_stats(player_name: str) -> Optional[dict]:
    """Return fielding stats for one player, or None if not in database."""
    if not PLAYER_STATS_FILE.exists():
        return None
    with open(PLAYER_STATS_FILE) as f:
        data = json.load(f)
    return data.get(player_name)


def get_top_fielders(fmt: Optional[str] = None, stat: str = "total_fielding_dismissals", n: int = 50) -> list:
    """
    Return the top N fielders sorted by a given stat.

    Args:
        fmt:  Filter to players who have fielded in this format (e.g. 'mens_t20').
              None = all formats.
        stat: One of catches, run_out_direct, run_out_involved, stumpings,
              total_fielding_dismissals.
        n:    Number of players to return.
    """
    if not PLAYER_STATS_FILE.exists():
        return []
    with open(PLAYER_STATS_FILE) as f:
        data = json.load(f)

    rows = []
    for name, s in data.items():
        if fmt and fmt not in s.get("formats", []):
            continue
        rows.append({"name": name, **s})

    rows.sort(key=lambda r: r.get(stat, 0), reverse=True)
    return rows[:n]
