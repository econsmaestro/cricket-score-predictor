"""Bitemporal, immutable empirical prior snapshots; no application database."""
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
from .data import replay, wicket_bucket

# Joint observed delivery outcomes. No invented catch, fielding or pressure labels.
def outcome(event):
    return (event["legal"], event["runs"], event["bat_runs"],
            event["wicket"], int(event["out"] == event["non_striker"]), event["rotation"])


class PriorStore:
    def __init__(self, matches, cutoff, output, source_sha, mode="event_time"):
        self.cutoff = cutoff
        self.mode = mode
        self.matches = [
            m for m in matches
            if m["completed_before"] <= cutoff and
            (mode != "verified_availability" or m["available_at"] <= cutoff)
        ]
        if not self.matches:
            raise ValueError("No historical observations provably available before cutoff")
        self.maximum_source_time = max(m["completed_before"] for m in self.matches)
        self.counts = {key: defaultdict(Counter) for key in
                       ("global", "phase", "state", "cluster", "player")}
        self.bat = defaultdict(lambda: [0, 0])
        self.positions = defaultdict(list)
        self.venues = defaultdict(list)
        for match in self.matches:
            self.venues[match["venue"]].append(match["actual_score"])
            visited = set()
            for s, e in replay(match):
                ph = s["phase"]
                state = (ph, wicket_bucket(s["wickets"]), s["rate_bucket"])
                cluster = (*state, int(s["recent"] >= 1))
                value = outcome(e)
                for level, key in (("global", ()), ("phase", (ph,)), ("state", state),
                                   ("cluster", cluster), ("player", (ph, e["batter"]))):
                    self.counts[level][key][value] += 1
                self.bat[e["batter"]][0] += e["bat_runs"]
                self.bat[e["batter"]][1] += e.get("faced", e["legal"])
                for player in (e["batter"], e["non_striker"]):
                    if player not in visited:
                        position = 1.5 if not visited or len(visited) == 1 else len(visited) + 1
                        self.positions[player].append(position)
                        visited.add(player)
        self.outcomes = sorted(self.counts["global"][()].keys())
        self.index = {v: i for i, v in enumerate(self.outcomes)}
        self.arrays = {
            level: {key: np.array([values.get(o, 0) for o in self.outcomes], dtype=float)
                    for key, values in cells.items()}
            for level, cells in self.counts.items()
        }
        self.default = self.arrays["global"][()] / self.arrays["global"][()].sum()
        self.cache = {}
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": 1, "cutoff": cutoff, "availability_mode": mode,
            "source_archive_sha256": source_sha,
            "source_max_completed_before": self.maximum_source_time,
            "fixtures": [{"id": m["id"], "event_completed_before": m["completed_before"],
                          "first_seen_at": m["available_at"], "source_sha256": m["sha256"]}
                         for m in self.matches],
            "batters": dict(self.bat), "venue_scores": dict(self.venues),
            "batting_position_observations": dict(self.positions),
            "joint_outcomes": self.outcomes,
            "counts": {level: [{"key": list(key), "counts": arr.tolist()} for key, arr in cells.items()]
                       for level, cells in self.arrays.items()},
        }
        data = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        self.digest = hashlib.sha256(data.encode()).hexdigest()
        self.path = self.output / (self.digest + ".json")
        if self.path.exists():
            assert self.path.read_text() == data
        else:
            self.path.write_text(data)

    def distribution(self, ph, wickets, rate, recent, batter, level, alpha):
        key = ph, wickets, rate, recent, batter if level in ("resources", "full") else None, level, alpha
        if key in self.cache:
            return self.cache[key]
        p = self.default.copy()
        layers = [("phase", (ph,))]
        if level != "phase":
            layers.append(("state", (ph, wickets, rate)))
        if level in ("cluster", "full"):
            layers.append(("cluster", (ph, wickets, rate, recent)))
        if level in ("resources", "full"):
            layers.append(("player", (ph, batter)))
        for name, cell in layers:
            count = self.arrays[name].get(cell)
            if count is not None:
                p = (count + alpha * p) / (count.sum() + alpha)
        assert np.isclose(p.sum(), 1)
        self.cache[key] = p
        return p

    def assert_as_of(self, timestamp):
        if timestamp < self.cutoff or self.maximum_source_time > timestamp:
            raise ValueError("Prior snapshot contains future information")

    def batting_order(self, players):
        # Only historical first-appearance order. Never the target innings' future
        # order. Unknown players share the last rank and get stable-ID tie breaking.
        return sorted(players, key=lambda p: (
            np.mean(self.positions[p]) if p in self.positions else float("inf"), p))


def select_alpha(priors, validation, level):
    """Learn the pooling concentration on earlier validation deliveries only."""
    scores = {}
    for alpha in (1., 10., 100., 1000.):
        loss = n = unseen = 0
        for match in validation:
            priors.assert_as_of(match["date"])
            for s, e in replay(match):
                index = priors.index.get(outcome(e))
                if index is None:
                    # Unseen outcomes cannot select a better smoothing setting:
                    # same fixed worst-case loss for every setting, disclosed.
                    loss += -np.log(1e-12)
                    unseen += 1
                else:
                    p = priors.distribution(s["phase"], wicket_bucket(s["wickets"]),
                        s["rate_bucket"], int(s["recent"] >= 1), e["batter"], level, alpha)
                    loss += -np.log(max(1e-12, p[index]))
                n += 1
        scores[alpha] = {"log_loss": float(loss / n), "deliveries": n, "unseen_outcomes": unseen}
    best = min(scores, key=lambda a: (scores[a]["log_loss"], -a))
    return best, scores
