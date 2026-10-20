"""Backtesting engine: replay historical T20I first innings at checkpoints."""
import math
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

CHECKPOINTS = [6, 10, 11, 15, 16]

_VENUE_MAP = None


def _build_venue_map():
    from ipl_stats import VENUE_HISTORICAL_STATS
    known = list(VENUE_HISTORICAL_STATS.keys())
    known_lower = [v.lower() for v in known]
    return known, known_lower


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


def build_state_at_over(match, checkpoint_over):
    """Reconstruct MatchState from ball-by-ball data at checkpoint_over."""
    from prediction import MatchState, Batsman, Bowler

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
            overs_remaining=max(0.0, 4.0 - ob),
        ))

    venue = _resolve_venue(match["venue"])

    return MatchState(
        current_score=current_score,
        wickets_fallen=wickets_fallen,
        overs_completed=float(checkpoint_over),
        venue=venue,
        batsmen=batsmen,
        bowlers=bowlers,
        batsmen_to_come=batsmen_to_come,
        innings=1,
        target=0,
        match_format="mens_t20",
        fielding_team=match.get("fielding_team", ""),
    )


def run_backtest(max_matches=200):
    """Run backtest for up to max_matches games. Returns list of per-prediction dicts."""
    from backtest_data import parse_matches
    from prediction import predict_score

    matches = parse_matches()[:max_matches]
    results = []

    for match in matches:
        for cp in CHECKPOINTS:
            try:
                state = build_state_at_over(match, cp)
                pred = predict_score(state)
                actual = match["actual_final_score"]
                low, high = pred.score_range
                results.append({
                    "match_id": match["match_id"],
                    "date": match["date"],
                    "venue": match["venue"],
                    "batting_team": match["batting_team"],
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
                logger.debug("Skipped %s cp=%d: %s", match["match_id"], cp, e)

    return results


def compute_metrics(results):
    """Aggregate metrics overall and per checkpoint."""
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

        buckets = {"under_160": [], "160_200": [], "over_200": []}
        for r in rows:
            a = r["actual"]
            if a < 160:
                buckets["under_160"].append(r["abs_error"])
            elif a <= 200:
                buckets["160_200"].append(r["abs_error"])
            else:
                buckets["over_200"].append(r["abs_error"])

        return {
            "n": n,
            "mae": round(mae, 1),
            "rmse": round(rmse, 1),
            "bias": round(bias, 1),
            "hit_rate": round(hit_rate, 1),
            "avg_width": round(avg_width, 1),
            "bucket_mae": {
                "under_160": round(sum(v) / len(v), 1) if buckets["under_160"] else None,
                "160_200": round(sum(v) / len(v), 1) if buckets["160_200"] else None,
                "over_200": round(sum(v) / len(v), 1) if buckets["over_200"] else None,
            },
        }

    by_cp = {}
    cp_groups = defaultdict(list)
    for r in results:
        cp_groups[r["checkpoint"]].append(r)
    for cp in CHECKPOINTS:
        by_cp[cp] = _metrics(cp_groups.get(cp, []))

    return {"overall": _metrics(results), "by_checkpoint": by_cp}


def generate_summary(metrics):
    """One-paragraph plain-English summary of where the model is weakest."""
    ov = metrics.get("overall")
    if not ov:
        return "No data."

    lines = []
    lines.append(
        f"Across {ov['n']} predictions the model has an MAE of {ov['mae']} runs "
        f"and RMSE of {ov['rmse']} runs."
    )

    bias_dir = "overshoots" if ov["bias"] > 0 else "undershoots"
    lines.append(
        f"Bias is {ov['bias']:+.1f} runs (the model {bias_dir} on average)."
    )

    lines.append(
        f"The predicted range captures the actual score {ov['hit_rate']:.1f}% of the time "
        f"with an average range width of {ov['avg_width']:.0f} runs."
    )

    bm = ov["bucket_mae"]
    bucket_parts = []
    if bm.get("under_160") is not None:
        bucket_parts.append(f"low-scoring (<160): {bm['under_160']} runs MAE")
    if bm.get("160_200") is not None:
        bucket_parts.append(f"mid-range (160–200): {bm['160_200']} runs MAE")
    if bm.get("over_200") is not None:
        bucket_parts.append(f"high-scoring (200+): {bm['over_200']} runs MAE")
    if bucket_parts:
        lines.append("Error by final score bucket: " + ", ".join(bucket_parts) + ".")

    by_cp = metrics.get("by_checkpoint", {})
    valid_cps = [cp for cp in by_cp if by_cp[cp]]
    if valid_cps:
        worst = max(valid_cps, key=lambda cp: by_cp[cp]["mae"])
        best = min(valid_cps, key=lambda cp: by_cp[cp]["mae"])
        lines.append(
            f"Predictions are least accurate at the {worst}-over checkpoint "
            f"(MAE {by_cp[worst]['mae']} runs) and most accurate at {best} overs "
            f"(MAE {by_cp[best]['mae']} runs)."
        )

    return " ".join(lines)
