"""Independent, checkpoint-eligible Cricsheet replay with stable player IDs."""
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import zipfile

FORMATS = {
    "mens_odi": ("odis_male_json.zip", "male", "ODI", 50, (0, 10, 20, 30, 40)),
    "womens_odi": ("odis_female_json.zip", "female", "ODI", 50, (0, 10, 20, 30, 40)),
    "mens_t20": ("t20s_male_json.zip", "male", "T20", 20, (0, 6, 10, 11, 15, 16)),
    "womens_t20": ("t20s_female_json.zip", "female", "T20", 20, (0, 6, 10, 11, 15, 16)),
}
NON_WICKETS = {"retired hurt", "retired not out"}


def phase(fmt, balls):
    over = balls / 6
    if fmt.endswith("odi"):
        return 0 if over < 10 else 1 if over < 30 else 2 if over < 40 else 3
    return 0 if over < 6 else 1 if over < 14 else 2 if over < 17 else 3


def wicket_bucket(wickets):
    return 0 if wickets <= 3 else 1 if wickets <= 6 else 2


def rate_bucket(fmt, score, balls):
    rate = 6 * score / max(1, balls)
    lo, hi = (4, 6) if fmt.endswith("odi") else (6, 9)
    return 0 if rate < lo else 1 if rate < hi else 2


def iso_next_day(day):
    # Source dates have no reliable intraday timezone. Two full calendar days
    # conservatively embargo results across timezone/day-boundary uncertainty.
    return (date.fromisoformat(str(day)) + timedelta(days=2)).isoformat()


def load_archive(root, fmt, first_seen, end_before=None, limit=650):
    filename, gender, match_type, overs, checkpoints = FORMATS[fmt]
    path = Path(root) / "backtest_cache" / filename
    exclusion = Counter()
    matches = []
    with zipfile.ZipFile(path) as archive:
        assert len(archive.namelist()) == len(set(archive.namelist())), "Duplicate ZIP members"
        for name in archive.namelist():
            if not name.endswith(".json"):
                continue
            raw_bytes = archive.read(name)
            raw = json.loads(raw_bytes)
            info = raw.get("info", {})
            if info.get("gender") != gender or info.get("match_type") != match_type:
                exclusion["wrong_format_or_gender"] += 1
                continue
            if info.get("overs") != overs or info.get("balls_per_over", 6) != 6:
                exclusion["nonstandard_length_or_ball_count"] += 1
                continue
            if end_before and iso_next_day(str(max(info["dates"]))) > end_before:
                exclusion["outside_preregistered_historical_window"] += 1
                continue
            if info.get("outcome", {}).get("method"):
                exclusion["revised_conditions"] += 1
                continue
            if not raw.get("innings") or not raw["innings"][0].get("overs"):
                exclusion["missing_first_innings"] += 1
                continue
            first = raw["innings"][0]
            if len(info.get("players", {}).get(first["team"], [])) != 11:
                exclusion["non_XI_roster_or_unknown_substitute_timing"] += 1
                continue
            penalty = first.get("penalty_runs", {})
            if sum(penalty.values()):
                # Penalty timing cannot be reconstructed from a summary-only field.
                exclusion["untimed_penalty_runs"] += 1
                continue
            registry = info.get("registry", {}).get("people", {})
            names = set(info.get("players", {}).get(first["team"], []))
            names.update(d[p] for o in first["overs"] for d in o["deliveries"]
                         for p in ("batter", "non_striker", "bowler"))
            if any(n not in registry for n in names):
                exclusion["missing_stable_player_id"] += 1
                continue
            events = []
            ambiguous_multi_wicket = False
            for over in first["overs"]:
                for d in over["deliveries"]:
                    extras = d.get("extras", {})
                    dismissals = [w for w in d.get("wickets", []) if w["kind"] not in NON_WICKETS]
                    if len(dismissals) > 1:
                        ambiguous_multi_wicket = True
                    events.append({
                        "batter": registry[d["batter"]], "non_striker": registry[d["non_striker"]],
                        "bowler": registry[d["bowler"]], "runs": d["runs"]["total"],
                        "bat_runs": d["runs"]["batter"],
                        "legal": int(not ("wides" in extras or "noballs" in extras)),
                        "faced": int("wides" not in extras),
                        "bowler_runs": d["runs"]["total"] - extras.get("byes", 0) - extras.get("legbyes", 0),
                        "bowler_wicket": int(bool(dismissals) and dismissals[0]["kind"] not in {
                            "run out", "retired out", "obstructing the field"}),
                        "wicket": len(dismissals),
                        "out": registry[dismissals[0]["player_out"]] if dismissals else None,
                        "unavailable": [registry[w["player_out"]] for w in d.get("wickets", [])],
                        "rotation": (d["runs"]["total"] - int(bool(extras.get("wides")))
                                     - int(bool(extras.get("noballs"))) - extras.get("penalty", 0)) % 2,
                    })
            if ambiguous_multi_wicket:
                # Includes mass-retirement records and mutually incompatible
                # dismissals recorded on one ball. Do not invent their timing.
                exclusion["ambiguous_multiple_wicket_timing_requires_review"] += 1
                continue
            balls = sum(e["legal"] for e in events)
            wickets = sum(e["wicket"] for e in events)
            if wickets > 10 or balls > overs * 6:
                exclusion["invalid_terminal_state"] += 1
                continue
            if wickets != 10 and balls != overs * 6:
                exclusion["incomplete_first_innings"] += 1
                continue
            start = str(min(info["dates"]))
            end = str(max(info["dates"]))
            matches.append({
                "id": name.removesuffix(".json"), "format": fmt, "date": start,
                "completed_before": iso_next_day(end), "available_at": first_seen,
                "published_created": raw.get("meta", {}).get("created"),
                "revision": raw.get("meta", {}).get("revision"),
                "sha256": hashlib.sha256(raw_bytes).hexdigest(),
                "venue": info.get("venue", ""), "team": first["team"],
                "fielding_team": next((t for t in info["teams"] if t != first["team"]), ""),
                "players": [registry[n] for n in info["players"][first["team"]]],
                "names": {v: k for k, v in registry.items()}, "events": events,
                "actual_score": sum(e["runs"] for e in events), "actual_wickets": wickets,
                "legal_balls": balls, "max_balls": overs * 6,
            })
            if len(matches) > limit:
                matches.sort(key=lambda m: (m["date"], m["id"]))
                matches.pop(0)
    assert len({m["id"] for m in matches}) == len(matches), "Duplicate fixture IDs"
    matches.sort(key=lambda m: (m["date"], m["id"]))
    return matches, dict(exclusion), hashlib.sha256(path.read_bytes()).hexdigest()


def replay(match):
    """Yield pre-delivery states. Never uses a later delivery to fill a current pair."""
    score = wickets = balls = 0
    faced = {}
    dismissed = set()
    recent = []
    for event in match["events"]:
        snapshot = {
            "score": score, "wickets": wickets, "balls": balls,
            "striker": event["batter"], "non_striker": event["non_striker"],
            "recent": sum(w > balls - 12 for w in recent),
            "phase": phase(match["format"], balls),
            "rate_bucket": rate_bucket(match["format"], score, balls),
        }
        yield snapshot, event
        if event["wicket"]:
            recent.append(balls)
            dismissed.add(event["out"])
        score += event["runs"]
        wickets += event["wicket"]
        balls += event["legal"]


def snapshot(match, checkpoint):
    """Post-over state. An already-completed innings has no active checkpoint."""
    target = checkpoint * 6
    if target >= match["legal_balls"]:
        return None
    score = wickets = balls = 0
    active = [None, None]
    gone = set()
    faced = {}
    seen = set()
    recent = []
    bowled = {}
    for e in match["events"]:
        if balls >= target:
            break
        active = [e["batter"], e["non_striker"]]
        seen.update(active)
        for player in active:
            faced.setdefault(player, [0, 0])
        faced[e["batter"]][0] += e["bat_runs"]
        # Raw legal flag alone cannot distinguish wide vs no-ball; derive batter
        # ball credit conservatively from actual event below, not future statistics.
        faced[e["batter"]][1] += e.get("faced", e["legal"])
        b = bowled.setdefault(e["bowler"], [0, 0, 0])
        b[0] += e["legal"]
        b[1] += e.get("bowler_runs", e["runs"])
        b[2] += e.get("bowler_wicket", e["wicket"])
        for out in e["unavailable"]:
            gone.add(out)
            active = [None if p == out else p for p in active]
        if e["wicket"]:
            recent.append(balls)
        if e["rotation"]:
            active.reverse()
        balls += e["legal"]
        if e["legal"] and balls % 6 == 0:
            active.reverse()
        score += e["runs"]
        wickets += e["wicket"]
    assert balls == target and wickets < 10
    return {
        "score": score, "wickets": wickets, "balls": balls, "active": active,
        "gone": gone, "seen": seen, "faced": faced, "bowled": bowled,
        "recent_wickets": recent, "as_of": match["date"],
        "format": match["format"], "max_balls": match["max_balls"],
        "players": list(match["players"]), "names": match["names"],
        "venue": match["venue"], "fielding_team": match["fielding_team"],
    }
