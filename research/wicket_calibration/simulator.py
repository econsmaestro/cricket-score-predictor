"""Empirical joint delivery simulation: no independent score/wicket forecasts."""
import hashlib
import numpy as np

from .data import phase, rate_bucket, wicket_bucket

LEVELS = {
    "joint_phase": "phase",
    "joint_state": "state",
    "joint_resources": "resources",
    "joint_cluster": "cluster",
    "joint_full": "full",
}


def seed_for(fmt, match_id, checkpoint):
    return int.from_bytes(hashlib.sha256(
        f"phase2:20261105:{fmt}:{match_id}:{checkpoint}".encode()).digest()[:8], "little")


def predict(state, priors, variant, alpha, seed, paths=256):
    priors.assert_as_of(state["as_of"])
    level = LEVELS[variant]
    rng = np.random.default_rng(seed)
    roster = priors.batting_order(state["players"])
    index = {p: i for i, p in enumerate(roster)}
    nplayers = len(roster)
    if nplayers < 2:
        raise ValueError("Cannot simulate without a playing roster")
    unavailable = np.zeros((paths, nplayers), dtype=bool)
    for p in state["gone"]:
        if p in index:
            unavailable[:, index[p]] = True
    active = np.full((paths, 2), -1, dtype=int)
    for j, p in enumerate(state["active"]):
        if p in index:
            active[:, j] = index[p]
            unavailable[:, index[p]] = True
    # Unknown replacement/openers use only prior batting positions and the
    # pre-match XI. Historical inferred order is not actual future batting order.
    def replacements(mask, side):
        ids = np.flatnonzero(mask & (active[:, side] < 0) & (~unavailable).any(axis=1))
        if not len(ids):
            return
        weights = (~unavailable[ids]).astype(float)
        if level not in ("resources", "full"):
            weights *= rng.random(weights.shape)
        chosen = weights.argmax(axis=1)
        active[ids, side] = chosen
        unavailable[ids, chosen] = True

    replacements(np.ones(paths, dtype=bool), 0)
    replacements(np.ones(paths, dtype=bool), 1)
    scores = np.full(paths, state["score"], dtype=int)
    wickets = np.full(paths, state["wickets"], dtype=int)
    balls = np.full(paths, state["balls"], dtype=int)
    history = np.full((paths, 10), -1000, dtype=int)
    recent = state["recent_wickets"][-10:]
    if recent:
        history[:, :len(recent)] = recent
    values = np.array(priors.outcomes, dtype=int)
    # Precompute the complete conditional CDF tensor once per roster/variant.
    # Simulation then has no per-path Python probability lookup.
    table_key = tuple(roster), level, alpha
    if not hasattr(priors, "simulation_tables"):
        priors.simulation_tables = {}
    if table_key not in priors.simulation_tables:
        table = []
        for ph in range(4):
            for wk in range(3):
                for rb in range(3):
                    for rec in range(2):
                        for player in roster:
                            table.append(np.cumsum(priors.distribution(
                                ph, wk, rb, rec, player, level, alpha)))
        priors.simulation_tables[table_key] = np.asarray(table)
    cdf = priors.simulation_tables[table_key]
    total_balls = state["max_balls"]
    iterations = 0
    while True:
        alive = (balls < total_balls) & (wickets < 10) & (active[:, 0] >= 0) & (active[:, 1] >= 0)
        if not alive.any():
            break
        iterations += 1
        if iterations > (total_balls - state["balls"] + 1) * 20:
            raise RuntimeError("Excessive illegal deliveries; empirical process did not terminate")
        ids = np.flatnonzero(alive)
        thresholds = (60, 180, 240) if state["format"].endswith("odi") else (36, 84, 102)
        ph = sum((balls[ids] >= t).astype(int) for t in thresholds)
        wk = (wickets[ids] >= 4).astype(int) + (wickets[ids] >= 7).astype(int)
        rpo = scores[ids] * 6 / np.maximum(1, balls[ids])
        low, high = (4, 6) if state["format"].endswith("odi") else (6, 9)
        rb = (rpo >= low).astype(int) + (rpo >= high).astype(int)
        rec = (history[ids] > balls[ids, None] - 12).any(axis=1).astype(int)
        context = ((((ph * 3 + wk) * 3 + rb) * 2 + rec) * nplayers + active[ids, 0])
        selected = (rng.random((len(ids), 1)) > cdf[context]).sum(axis=1)
        sampled = values[np.minimum(selected, len(values) - 1)]
        legal, runs, bat_runs, out, non_striker_out, rotation = sampled.T
        scores[ids] += runs
        falling = ids[out.astype(bool)]
        history[falling, np.minimum(9, wickets[falling])] = balls[falling]
        active[falling, non_striker_out[out.astype(bool)]] = -1
        wickets[ids] += out
        flip = ids[rotation.astype(bool)]
        active[flip] = active[flip, ::-1]
        balls[ids] += legal
        over_end = ids[(legal == 1) & (balls[ids] % 6 == 0)]
        active[over_end] = active[over_end, ::-1]
        live_after = (balls < total_balls) & (wickets < 10)
        replacements(live_after, 0)
        replacements(live_after, 1)
    assert np.all(wickets <= 10) and np.all(wickets >= state["wickets"])
    assert np.all(balls <= total_balls)
    return {
        "score": int(round(float(scores.mean()))),
        "wickets": int(round(float(wickets.mean()))),
        "low": int(np.quantile(scores, .1, method="lower")),
        "high": int(np.quantile(scores, .9, method="higher")),
        "allout_probability": float(np.mean(wickets == 10)),
        "mean_legal_balls_remaining": float(np.mean(balls - state["balls"])),
        "score_mc_se": float(scores.std(ddof=1) / np.sqrt(paths)),
        "wicket_mc_se": float(wickets.std(ddof=1) / np.sqrt(paths)),
        "paths": paths,
    }
