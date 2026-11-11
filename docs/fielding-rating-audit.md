# Fielding rating audit

How the team fielding ratings were assigned, what they do to predictions, and whether the
committed backtest data supports them. Reproduce every table below with
`python -m research.fielding_rating_audit` (offline; reads `data/backtests/*.json`).

> **Status update.** The approximate ablation in section 3 was superseded by a real-model replay:
> see `docs/fielding-strength-replay.md`. That replay also corrected a backtest-harness bug (women's
> fixtures used the men's rating keys), so the committed women's reports changed (see
> `docs/first-innings-report-refresh.md`). The approximation below reproduces the committed MAE at
> k=1 by construction, but its k<1 figures for women's rows predate the key fix and should not be
> quoted. Use the real-model numbers: pooled run MAE 28.2 at today's strength vs 27.3 with no fielding effect.

## 1. Provenance: what we can and cannot say

* `TEAM_FIELDING_EFFICIENCY` in `prediction.py` is a hand-assigned table (for example India 0.92,
  Australia 0.94, Uganda 0.72). It first appears in commit `04f9846` (3 May 2026, "Fix overs
  calculation and fielding team display issues"). No source, derivation or reference date was
  recorded, and the fielding research notes (`docs/fielding-intelligence.md`) describe the values
  as manually assigned.
* The code frames each rating as a catch-conversion-style figure (`drop_rate = 1 - rating`),
  but nothing was measured to produce it. The site displays it as a percentage, for example
  "Australia fielding 94%", which reads as a measured statistic. **It is not one.**
* Honest description today: an analyst's prior about relative team fielding quality.

## 2. What the ratings do to a prediction

Defined in `get_fielding_modifier`, applied to projected remaining runs, expected wickets,
next-over runs, wicket probability and boundary rate:

| Rating | Run modifier | Wicket modifier |
|---|---|---|
| 0.95 | 0.90 | 1.15 |
| 0.92 | 0.90 | 1.10 |
| 0.90 | 0.90 | 1.08 |
| 0.85 (default for unlisted teams) | 1.00 | 1.00 |
| 0.80 | 1.10 | 0.93 |
| 0.75 | 1.15 | 0.85 |
| 0.70 | 1.15 | 0.77 |

Because the run modifier is clamped to 0.90 to 1.15, every team rated 0.90 or higher gets the
same run effect, and every team rated 0.75 or lower gets the same effect. The rating differences
between those teams change nothing for runs.

## 3. Does the data support them?

Method: the committed backtest stores each prediction, its checkpoint score and the fielding
team. The run modifier is divided back out to reconstruct a no-modifier projection, and the
modifier's effect can be scaled by a strength `k` (`k = 1` is today). At `k = 1` this reproduces
the committed MAE exactly (21.06, 16.22, 41.47, 37.20), which is the sanity check.

Score MAE (runs), 1,800 checkpoint predictions from 400 first innings:

| Group | Rows | MAE now (k=1) | MAE without (k=0) |
|---|---|---|---|
| All | 1800 | 27.84 | 27.25 |
| Opposition has a listed rating | 1109 | 34.06 | 33.11 |
| Opposition unlisted (neutral) | 691 | 17.85 | 17.85 |
| Men's T20 | 500 | 21.06 | 20.75 |
| Women's T20 | 500 | 16.22 | 15.42 |
| Men's ODI | 400 | 41.47 | 41.27 |
| Women's ODI | 400 | 37.20 | 36.15 |
| Strong rating (>= 0.90) | 322 | 33.11 | 34.84 |
| Mid rating (0.80 to 0.89) | 396 | 36.56 | 36.16 |
| Weak rating (< 0.80) | 391 | 32.32 | 28.60 |

Strength sweep and chronological check (fit `k` on the earlier half of each format's matches,
test on the later half):

| Format | Fitted k | Test MAE now | Test MAE fitted | Test MAE none |
|---|---|---|---|---|
| Men's T20 | 0.15 | 20.08 | 19.66 | 19.59 |
| Women's T20 | 0.00 | 17.63 | 17.20 | 17.20 |
| Men's ODI | 0.35 | 42.72 | 42.32 | 42.71 |
| Women's ODI | 0.50 | 36.77 | 34.94 | 34.62 |
| Pooled | | 28.14 | 27.41 | 27.40 |

What this shows:

1. **The ratings do not currently improve run prediction.** At full strength they are slightly
   worse than no fielding adjustment in every format (about 0.2 to 1.1 runs).
2. **The direction is partly right and the size is too large.** Against strongly rated sides the
   modifier helps (33.11 vs 34.84), but it over-corrects (mean residual +10 runs). Against weakly
   rated sides it hurts (32.32 vs 28.60).
3. **A much smaller effect fits better.** The best strength is roughly a quarter to a half of
   today's, and on the later half of matches a fitted or zero effect beats the current one.

### 3b. Agreement with observed outcomes

The older `fielding_stats` engine (commit `8121e80`, still in git history) computed per-team
Cricsheet outcomes. Rank correlation between the assigned rating and those outcomes, for teams
with 20+ innings:

| Cohort | Teams | Catches / innings | Dismissals / innings | Runs allowed / over | Run-out involvement / innings |
|---|---|---|---|---|---|
| Men's T20 | 21 | +0.50 | +0.30 | +0.82 | -0.22 |
| Men's ODI | 19 | +0.43 | +0.59 | +0.46 | +0.24 |
| Women's T20 | 9 | +0.49 | +0.52 | -0.20 | -0.05 |
| Women's ODI | 9 | +0.73 | +0.70 | -0.27 | -0.62 |

Higher-rated teams do take more catches and more wickets per innings, but that mostly reflects
overall team quality (bowling included), not fielding alone. Runs allowed per over does not
agree: for the ratings to be supported it should be negative, and in men's cohorts it is positive.
Nine to 21 teams per cohort is a small sample. These are outcomes, not opportunity-adjusted
fielding skill, so they cannot validate the ratings; they only show the ordering is not
unrelated to team standing.

Structure of the table itself (men's, 24 teams): 0.90 to 0.94 for five leading sides, 0.80 to
0.85 for five established sides, 0.71 to 0.79 for fourteen others. Women's table: nine teams,
0.76 to 0.93.

## 4. Limits of this evidence

* Approximate: assumes the run modifier scales projected remaining runs. Other adjustments in
  the engine may interact with it.
* The backtest is a replay of the current model, not an out-of-time holdout. Differences are
  small (about 0.6 runs of roughly 28) and were not tested for statistical significance;
  rows from the same innings are correlated.
* Confounded with team strength. A strong fielding side is usually also a strong bowling side
  and its opponents are chosen differently. This does not isolate fielding.
* Wicket effects were not audited (only runs can be reconstructed from stored fields).
* **Harness gap:** the backtest passes raw team names, so 578 women's rows matched the men's
  keys (for example "India" 0.92) and none matched the women's "India W" keys. The women's
  ratings are never exercised in backtests.
* This does not show that fielding is unimportant. It shows these ratings do not evidence it.

## 5. What free data can and cannot justify

Cricsheet names fielders only on successful dismissals. Catch opportunities, drops, misfields,
direct hits and runs saved are not recorded, so a measured catching or overall fielding rating
cannot be derived from it (see `docs/fielding-intelligence.md`). Any rating justified by
evidence needs labelled opportunity data, which is the point of the proposed data collaboration.

## 6. Options (nothing here has been changed in production)

* **A. Label honestly (no model change).** Show "analyst estimate" instead of a percentage and
  link to this page. Cheap and removes the misleading precision.
* **B. Calibrate the effect size.** Shrink the modifier (for example `k` between 0.25 and 0.5),
  chosen by chronological validation, and fix the women's key mapping in the backtest. Judged
  first on run MAE, then wicket MAE, per the project's own acceptance rule.
* **C. Replace with player-level, dated, free-source evidence.** Continue the shadow-mode
  `fielding_intelligence` work; promote only what improves held-out run and wicket MAE.
