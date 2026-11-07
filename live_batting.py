"""Read current Cricbuzz batting state, never historical commentary summaries."""
import json
import re


def _objects(text, key):
    decoder = json.JSONDecoder()
    for match in re.finditer(r'"' + re.escape(key) + r'"\s*:\s*(?=\{)', text):
        try:
            value, _ = decoder.raw_decode(text, match.end())
            if isinstance(value, dict):
                yield value
        except ValueError:
            continue


def current_batting_snapshot(soup, match_id):
    """Return one match-bound, internally consistent miniscore, or None.

    Next.js Flight strings are decoded as JSON, not searched across escaped
    objects. Multiple different snapshots are treated as ambiguous.
    """
    streams = []
    flight = []
    for script in soup.find_all("script"):
        text = script.string or script.get_text()
        if script.get("type") == "application/json":
            streams.append(text)
        for match in re.finditer(r'self\.__next_f\.push\(\s*', text):
            try:
                chunk, _ = json.JSONDecoder().raw_decode(text, match.end())
                if isinstance(chunk, list) and len(chunk) > 1 and isinstance(chunk[1], str):
                    flight.append(chunk[1])
            except ValueError:
                continue
    streams.append("".join(flight))
    candidates = []
    for stream in streams:
        for mini in _objects(stream, "miniscore"):
            try:
                details = mini["matchScoreDetails"]
                if str(details["matchId"]) != str(match_id):
                    continue
                innings = mini["inningsId"]
                team = mini["batTeam"]
                score, wickets, overs = team["teamScore"], team["teamWkts"], mini["overs"]
                if (type(score) is not int or type(wickets) is not int
                        or not 0 <= wickets <= 10 or score < 0
                        or type(overs) not in (int, float) or overs < 0
                        or round(overs * 10) % 10 > 5):
                    continue
                records = [r for r in details["inningsScoreList"]
                           if r.get("inningsId") == innings and r.get("batTeamId") == team["teamId"]]
                if len(records) != 1:
                    continue
                record = records[0]
                if (record.get("score"), record.get("wickets"), record.get("overs")) != (score, wickets, overs):
                    continue
                if innings not in (1, 2):
                    continue
                result = {
                    "current_score": score, "wickets": wickets, "overs": float(overs),
                    "innings": innings, "batsmen": [],
                    "batsmen_verified": False,
                    "batting_snapshot_timestamp": mini.get("responseLastUpdated"),
                }
                if innings == 1:
                    result["target"] = 0
                elif type(mini.get("target")) is int and mini["target"] > score:
                    result["target"] = mini["target"]
                # Rain suspends play, not the innings: the verified pair still
                # occupies the crease. Do not extend this to innings breaks or
                # completed games, where the provider can retain an old pair.
                if details.get("state", "").strip().casefold() not in ("in progress", "rain") or wickets == 10:
                    candidates.append(result)
                    continue
                pair = []
                for key in ("batsmanStriker", "batsmanNonStriker"):
                    player = mini.get(key) or {}
                    name = player.get("name", "").strip()
                    runs, balls = player.get("runs"), player.get("balls")
                    if (not name or not player.get("id") or type(runs) is not int
                            or type(balls) is not int or not 0 <= runs <= score
                            or balls < 0):
                        break
                    pair.append({"name": name, "runs": runs, "balls": balls,
                                 "source_player_id": str(player["id"])})
                if (len(pair) == 2 and pair[0]["source_player_id"] != pair[1]["source_player_id"]
                        and sum(p["runs"] for p in pair) <= score):
                    last_wicket = mini.get("lastWicket") or ""
                    if not any(last_wicket.casefold().startswith(p["name"].casefold() + " ")
                               for p in pair):
                        result["batsmen"] = pair
                        result["batsmen_verified"] = True
                candidates.append(result)
            except (KeyError, TypeError, ValueError, AttributeError):
                continue
    # SSR and hydration can repeat identical state with different fetch times.
    # Ignore timestamp-only differences, but never choose between different
    # batting states just because one was fetched later.
    unique = {}
    for candidate in candidates:
        state = {k: v for k, v in candidate.items() if k != "batting_snapshot_timestamp"}
        key = json.dumps(state, sort_keys=True)
        previous = unique.get(key)
        if previous is None or (candidate.get("batting_snapshot_timestamp") or 0) > (previous.get("batting_snapshot_timestamp") or 0):
            unique[key] = candidate
    return next(iter(unique.values())) if len(unique) == 1 else None
