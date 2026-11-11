"""Offline audit of the hand-assigned team fielding ratings (TEAM_FIELDING_EFFICIENCY).

Reads the committed backtest reports (data/backtests/*.json) and asks, without re-running
the model: do the fixed ratings improve run prediction? It is a research tool only; it must
not be imported by a request handler.

    python -m research.fielding_rating_audit

NOTE: superseded for k < 1 by research.fielding_strength_replay (real model, corrected women's keys).
Method (approximate, stated limits in docs/fielding-rating-audit.md): the run modifier from
prediction.get_fielding_modifier scales projected remaining runs. For each stored prediction
the no-modifier projection is reconstructed as
    score_at_checkpoint + (predicted - score_at_checkpoint) / run_modifier
and a partial-strength version scales the modifier's effect by k (k=1 is today's model).
At k=1 this reproduces the committed predictions exactly, which is the built-in sanity check.
"""
import json
import os
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORMATS = ("mens_t20", "womens_t20", "mens_odi", "womens_odi")


def _load():
    sys.path.insert(0, ROOT)
    os.environ.setdefault("SESSION_SECRET", "audit-only-not-a-secret-0123456789abcdef")
    os.environ.setdefault("REPL_ID", "audit")
    os.environ.setdefault("DATABASE_URL", "sqlite://")
    from prediction import TEAM_FIELDING_EFFICIENCY as ratings, get_fielding_modifier
    rows = []
    for fmt in FORMATS:
        with open(os.path.join(ROOT, "data", "backtests", fmt + ".json")) as fh:
            for r in json.load(fh)["results"]:
                r["fmt"] = fmt
                r["rated"] = r["fielding_team"] in ratings
                r["rm"] = get_fielding_modifier(r["fielding_team"])["run_modifier"]
                rows.append(r)
    return rows, ratings, get_fielding_modifier


def project(r, k=1.0):
    """Prediction with the run modifier's effect scaled by k (k=1 current, k=0 none)."""
    remaining = (r["predicted"] - r["score_at_cp"]) / r["rm"]
    return r["score_at_cp"] + remaining * (1 + k * (r["rm"] - 1))


def mae(rows, k=1.0):
    return sum(abs(project(r, k) - r["actual"]) for r in rows) / len(rows)


def bias(rows, k=1.0):
    return st.mean(r["actual"] - project(r, k) for r in rows)


def chronological_split(rows, fmt):
    rs = sorted((r for r in rows if r["fmt"] == fmt), key=lambda r: (r["date"], r["match_id"]))
    ids = list(dict.fromkeys(r["match_id"] for r in rs))
    early = set(ids[: len(ids) // 2])
    return [r for r in rs if r["match_id"] in early], [r for r in rs if r["match_id"] not in early]


HIST_COMMIT = "8121e80"  # last commit that holds data/fielding/team_ratings.json (older fielding_stats engine)


def _spearman(a, b):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        out, i = [0.0] * len(v), 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                out[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return out
    ra, rb = rank(a), rank(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / den if den else float("nan")


def observed_outcomes_check(ratings, min_innings=20):
    """Do the assigned ratings agree with observed Cricsheet team outcomes?

    Uses team_ratings.json from the older fielding_stats engine (kept in git history), which holds
    per-team catches, dismissals, run-out involvement and runs allowed per over computed from
    Cricsheet ball-by-ball files. These are outcomes, not opportunity-adjusted fielding skill.
    """
    import subprocess
    try:
        raw = subprocess.run(["git", "show", f"{HIST_COMMIT}:data/fielding/team_ratings.json"],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout
        data = json.loads(raw)
    except Exception as exc:  # shallow clone or file missing
        print(f"\n(Observed-outcomes check skipped: {exc})")
        return
    print(f"\n## Agreement with observed Cricsheet team outcomes (Spearman rank correlation, teams with {min_innings}+ innings)")
    print("| Cohort | Teams | Catches / innings | Dismissals / innings | Runs allowed / over | Run-out involvement / innings |\n|---|---|---|---|---|---|")
    for fmt, suffix in (("mens_t20", ""), ("mens_odi", ""), ("womens_t20", " W"), ("womens_odi", " W")):
        pts = []
        for team, by_fmt in data.items():
            x = by_fmt.get(fmt)
            if x and x["innings"] >= min_innings and team + suffix in ratings:
                pts.append((ratings[team + suffix], x["catches"] / x["innings"], x["dismissals_per_innings"],
                            x["rpo_allowed"], x["run_out_involved"] / x["innings"]))
        if len(pts) >= 6:
            a = [p[0] for p in pts]
            cells = " | ".join(f"{_spearman(a, [p[i] for p in pts]):+.2f}" for i in (1, 2, 3, 4))
            print(f"| {fmt} | {len(pts)} | {cells} |")
    print("\nReading: a positive value for catches and dismissals means higher-rated teams take more of both. "
          "That mostly reflects overall team quality (bowling included), not fielding alone. For runs allowed, "
          "a negative value would support the ratings; positive values do not.")


def main():
    rows, ratings, modifier = _load()
    print("# Fielding rating audit (generated)\n")
    print("Sanity: committed MAE reproduced at k=1:",
          {f: round(mae([r for r in rows if r['fmt'] == f]), 2) for f in FORMATS})
    print("\n## Effect of the ratings on the modifier (current formulas)")
    print("| Rating | Run modifier | Wicket modifier |\n|---|---|---|")
    for e in (0.95, 0.92, 0.90, 0.85, 0.80, 0.75, 0.70):
        ratings_probe = {"_p": e}
        sys.modules["prediction"].TEAM_FIELDING_EFFICIENCY.update(ratings_probe)
        m = modifier("_p")
        print(f"| {e:.2f} | {m['run_modifier']:.2f} | {m['wicket_modifier']:.2f} |")
    sys.modules["prediction"].TEAM_FIELDING_EFFICIENCY.pop("_p", None)

    print("\n## Score MAE with vs without the run modifier (all 1,800 checkpoint predictions)")
    print("| Group | Rows | MAE now (k=1) | MAE without (k=0) | Mean residual now / without |\n|---|---|---|---|---|")

    def line(name, rs):
        if rs:
            print(f"| {name} | {len(rs)} | {mae(rs):.2f} | {mae(rs, 0):.2f} | {bias(rs):+.1f} / {bias(rs, 0):+.1f} |")
    line("All", rows)
    line("Opposition has a listed rating", [r for r in rows if r["rated"]])
    line("Opposition unlisted (neutral 0.85)", [r for r in rows if not r["rated"]])
    for f in FORMATS:
        line(f, [r for r in rows if r["fmt"] == f])
    for name, test in (("Strong fielding rating >= 0.90", lambda e: e >= 0.90),
                       ("Mid rating 0.80-0.89", lambda e: 0.80 <= e < 0.90),
                       ("Weak rating < 0.80", lambda e: e < 0.80)):
        line(name, [r for r in rows if r["rated"] and test(ratings[r["fielding_team"]])])

    print("\n## MAE by effect strength k (in-sample; k=1 is today)")
    ks = (0, 0.25, 0.5, 0.75, 1.0, 1.25)
    print("| Format | " + " | ".join(f"k={k}" for k in ks) + " |\n|---|" + "---|" * len(ks))
    for f in (None,) + FORMATS:
        rs = [r for r in rows if f is None or r["fmt"] == f]
        print(f"| {f or 'All'} | " + " | ".join(f"{mae(rs, k):.2f}" for k in ks) + " |")

    print("\n## Chronological split: fit k on the earlier half of matches, test on the later half")
    print("| Format | Fitted k | Test MAE now | Test MAE fitted | Test MAE none |\n|---|---|---|---|---|")
    grid = [i / 20 for i in range(0, 41)]
    tot = {"now": 0.0, "fit": 0.0, "none": 0.0}
    n = 0
    for f in FORMATS:
        early, late = chronological_split(rows, f)
        kb = min(grid, key=lambda k: mae(early, k))
        a, b, c = mae(late), mae(late, kb), mae(late, 0)
        print(f"| {f} | {kb:.2f} | {a:.2f} | {b:.2f} | {c:.2f} |")
        for key, v in (("now", a), ("fit", b), ("none", c)):
            tot[key] += v * len(late)
        n += len(late)
    print(f"| Pooled | | {tot['now'] / n:.2f} | {tot['fit'] / n:.2f} | {tot['none'] / n:.2f} |")

    observed_outcomes_check(ratings)
    women = [r for r in rows if r["fmt"].startswith("womens") and r["fielding_team"] in ratings]
    print(f"\nHarness note: {len(women)} women's rows matched a men's table key (e.g. 'India'), and "
          f"{sum(1 for r in rows if r['fielding_team'].endswith(' W'))} matched a women's 'X W' key. "
          "The backtest passes raw team names, so the women's ratings are never exercised.")


if __name__ == "__main__":
    main()
