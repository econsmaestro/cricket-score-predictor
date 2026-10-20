"""Backtesting engine: replay historical first innings at checkpoints."""
import math
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

T20_CHECKPOINTS = [6, 10, 11, 15, 16]
ODI_CHECKPOINTS = [10, 20, 30, 40, 45]

FORMAT_CHECKPOINTS = {
    "mens_t20":   T20_CHECKPOINTS,
    "womens_t20": T20_CHECKPOINTS,
    "mens_odi":   ODI_CHECKPOINTS,
    "womens_odi": ODI_CHECKPOINTS,
}

# Score buckets for each format family
T20_BUCKETS  = [("under_160", None, 160), ("160_200", 160, 200), ("over_200", 200, None)]
ODI_BUCKETS  = [("under_250", None, 250), ("250_300", 250, 300), ("over_300", 300, None)]

FORMAT_BUCKETS = {
    "mens_t20":   T20_BUCKETS,
    "womens_t20": T20_BUCKETS,
    "mens_odi":   ODI_BUCKETS,
    "womens_odi": ODI_BUCKETS,
}

_VENUE_MAP = None


def _build_venue_map():
    from ipl_stats import VENUE_HISTORICAL_STATS
    known = list(VENUE_HISTORICAL_STATS.keys())
    return known, [v.lower() for v in known]


def _resolve_venue(raw_venue):
    global _VENUE_MAP
    if _VENUE_MAP is None:
        _VENUE_MAP = _build_venue_map()
    known, known_lower = _VENUE_MAP
    if raw_venue in known:
        return raw_venue
    raw_lower = raw_venue.lower()
    for i, kl in enumerate(known_lower):
        if raw_lower == kl:
            return known[i]
    for i, kl in enumerate(known_lower):
        stadium = kl.split(",")[0].strip()
        if len(stadium) > 6 and stadium in raw_lower:
            return known[i]
    return raw_venue


def build_state_at_over(match, checkpoint_over, fmt="mens_t20"):
    """Reconstruct MatchState from ball-by-ball data at checkpoint_over."""
    from prediction import MatchState, Batsman, Bowler
    from backtest_data import FORMATS

    max_bowler_overs = 4 if "t20" in fmt else 10

    current_score = 0
    wickets_fallen = 0
    batter_stats = {}
    batting_order = []
    current_batters = []
    bowler_stats = {}

    for over_data in match["overs"]:
        if over_data["over"] >= checkpoint_over:
            break
        for d in over_data["deliveries"]:
            batter = d["batter"]
            bowler = d["bowler"]
            extras = d.get("extras", {})
            is_wide = "wides" in extras
            is_noball = "noballs" in extras

            if batter not in batter_stats:
                batter_stats[batter] = {"runs": 0, "balls": 0, "out": False}
                batting_order.append(batter)
            if batter not in current_batters and len(current_batters) < 2:
                current_batters.append(batter)

            batter_stats[batter]["runs"] += d["runs_batter"]
            if not is_wide:
                batter_stats[batter]["balls"] += 1

            if bowler not in bowler_stats:
                bowler_stats[bowler] = {"balls": 0, "runs": 0, "wickets": 0}
            bowler_stats[bowler]["runs"] += d["runs_total"]
            if not is_wide and not is_noball:
                bowler_stats[bowler]["balls"] += 1

            current_score += d["runs_total"]

            for w in d.get("wickets", []):
                player_out = w.get("player_out", "")
                if player_out in batter_stats:
                    batter_stats[player_out]["out"] = True
                if player_out in current_batters:
                    current_batters.remove(player_out)
                wickets_fallen += 1
                bowler_stats[bowler]["wickets"] += 1

    batsmen = [
        Batsman(name=n, runs=batter_stats[n]["runs"], balls_faced=batter_stats[n]["balls"])
        for n in current_batters
        if n in batter_stats and not batter_stats[n]["out"]
    ]

    batted = set(batting_order)
    all_players = match["players"].get(match["batting_team"], [])
    batsmen_to_come = [p for p in all_players if p not in batted]

    bowlers = []
    for name, s in bowler_stats.items():
        ob = s["balls"] / 6.0
        bowlers.append(Bowler(
            name=name,
            overs_bowled=ob,
            runs_conceded=s["runs"],
            wickets=s["wickets"],
            overs_remaining=max(0.0, float(max_bowler_overs) - ob),
        ))

    return MatchState(
        current_score=current_score,
        wickets_fallen=wickets_fallen,
        overs_completed=float(checkpoint_over),
        venue=_resolve_venue(match["venue"]),
        batsmen=batsmen,
        bowlers=bowlers,
        batsmen_to_come=batsmen_to_come,
        innings=1,
        target=0,
        match_format=fmt,
        fielding_team=match.get("fielding_team", ""),
    )


def run_backtest(fmt="mens_t20", max_matches=100):
    """Run backtest for up to max_matches games of the given format."""
    from backtest_data import parse_matches
    from prediction import predict_score

    matches = parse_matches(fmt)[:max_matches]
    checkpoints = FORMAT_CHECKPOINTS[fmt]
    results = []

    for match in matches:
        for cp in checkpoints:
            try:
                state = build_state_at_over(match, cp, fmt)
                pred = predict_score(state)
                actual = match["actual_final_score"]
                low, high = pred.score_range
                results.append({
                    "match_id": match["match_id"],
                    "date": match["date"],
                    "venue": match["venue"],
                    "batting_team": match["batting_team"],
                    "format": fmt,
                    "checkpoint": cp,
                    "score_at_cp": state.current_score,
                    "wickets_at_cp": state.wickets_fallen,
                    "predicted": pred.predicted_final_score,
                    "pred_low": low,
                    "pred_high": high,
                    "actual": actual,
                    "error": pred.predicted_final_score - actual,
                    "abs_error": abs(pred.predicted_final_score - actual),
                    "in_range": low <= actual <= high,
                    "range_width": high - low,
                })
            except Exception as e:
                logger.debug("Skipped %s cp=%d fmt=%s: %s", match["match_id"], cp, fmt, e)

    return results


def compute_metrics(results, fmt="mens_t20"):
    """Aggregate metrics overall and per checkpoint for a single format."""
    buckets_def = FORMAT_BUCKETS.get(fmt, T20_BUCKETS)
    checkpoints = FORMAT_CHECKPOINTS.get(fmt, T20_CHECKPOINTS)

    def _metrics(rows):
        n = len(rows)
        if n == 0:
            return None
        errors = [r["error"] for r in rows]
        abs_err = [r["abs_error"] for r in rows]
        mae = sum(abs_err) / n
        rmse = math.sqrt(sum(e ** 2 for e in errors) / n)
        bias = sum(errors) / n
        hit_rate = sum(1 for r in rows if r["in_range"]) / n * 100
        avg_width = sum(r["range_width"] for r in rows) / n

        bucket_data = {key: [] for key, _, _ in buckets_def}
        for r in rows:
            a = r["actual"]
            for key, lo, hi in buckets_def:
                if (lo is None or a >= lo) and (hi is None or a < hi):
                    bucket_data[key].append(r["abs_error"])
                    break

        return {
            "n": n,
            "mae": round(mae, 1),
            "rmse": round(rmse, 1),
            "bias": round(bias, 1),
            "hit_rate": round(hit_rate, 1),
            "avg_width": round(avg_width, 1),
            "bucket_mae": {
                k: round(sum(v) / len(v), 1) if v else None
                for k, v in bucket_data.items()
            },
            "bucket_labels": [key for key, _, _ in buckets_def],
        }

    cp_groups = defaultdict(list)
    for r in results:
        cp_groups[r["checkpoint"]].append(r)

    by_cp = {cp: _metrics(cp_groups.get(cp, [])) for cp in checkpoints}
    return {"overall": _metrics(results), "by_checkpoint": by_cp, "checkpoints": checkpoints}


def generate_summary(metrics, fmt="mens_t20"):
    """Plain-English summary of accuracy for a given format."""
    ov = metrics.get("overall")
    if not ov:
        return "No data."

    label = {"mens_t20": "Men's T20I", "womens_t20": "Women's T20I",
             "mens_odi": "Men's ODI", "womens_odi": "Women's ODI"}.get(fmt, fmt)

    lines = [
        f"{label}: across {ov['n']} predictions, MAE {ov['mae']} runs, RMSE {ov['rmse']} runs."
    ]
    bias_dir = "overshoots" if ov["bias"] > 0 else "undershoots"
    lines.append(f"Bias {ov['bias']:+.1f} runs (model {bias_dir} on average).")
    lines.append(
        f"Actual score inside predicted range {ov['hit_rate']:.1f}% of the time "
        f"(avg range width {ov['avg_width']:.0f} runs)."
    )

    bm = ov["bucket_mae"]
    parts = [f"{k.replace('_', ' ')}: {v} runs" for k, v in bm.items() if v is not None]
    if parts:
        lines.append("MAE by score bucket — " + ", ".join(parts) + ".")

    by_cp = metrics.get("by_checkpoint", {})
    valid = [cp for cp in by_cp if by_cp[cp]]
    if valid:
        worst = max(valid, key=lambda cp: by_cp[cp]["mae"])
        best  = min(valid, key=lambda cp: by_cp[cp]["mae"])
        lines.append(
            f"Weakest at {worst}-over mark (MAE {by_cp[worst]['mae']}), "
            f"strongest at {best} overs (MAE {by_cp[best]['mae']})."
        )

    return " ".join(lines)
