# Real-model fielding effect-strength replay

## Scope and safeguards

This experiment calls `prediction.predict_score` on the exact 400 fixtures and
1,800 checkpoints in the four committed first-innings reports. Each fixture and
checkpoint is identical across strengths. All three fielding effects (runs,
wickets, boundaries) change together, after the original clamps.

The default remains **1.0**. No rating values, live team mapping, authentication,
referrals, Stripe, production data or committed backtest JSON/CSV were changed.
User-facing percentages now say **Fielding rating (analyst estimate)** and have
the tooltip **Hand-assigned, not a measured statistic.** The same result template
serves prediction and demo pages. No public documentation link was added.

The imported approximation reproduces the committed MAEs at k=1:
21.06, 16.22, 41.47, 37.20 (men's T20, women's T20, men's ODI, women's ODI).
It is a run-only reconstruction, not the real-model ablation below.

## Reproduction and provenance

```sh
python -m research.fielding_rating_audit
python -m research.fielding_strength_replay
pytest -q tests --tb=short
```

The replay requires the original cached Cricsheet archives under `backtest_cache/`.
It verifies archive hashes against the committed reports, exact fixture IDs,
gender/format, actual targets and observed checkpoint scores/wickets. It fails
rather than substituting fixtures or skipping a failed prediction.

Outputs are ignored by Git and deployment, under
`generated-artifacts/fielding-strength/`:

- `predictions.csv`: 7,200 rows, 1,800 observations at four strengths.
- `metrics.csv` and `metrics.json`: full, earlier-fit and later-test metrics.
- `manifest.json`: source/fixture/archive/report hashes, strengths, selected
  fixture IDs and date boundaries.
- `report.md`: comparison tables.

Sixteen full prediction-output fingerprints were recorded from the unchanged
engine before adding the strength parameter. They cover all four formats, both
innings, several teams and the unlisted fallback. At strength 1.0, all sixteen
remain identical. Additional checks verify the original raw modifiers for every
listed team, neutral modifiers at zero, and women's keys in both innings.

## Women's historical key correction

Historical state construction now resolves women's raw team names to an
available `<team> W` key, matching the live route's women's-key rule. Men's keys
are unchanged. An unlisted team still uses 0.85. Names without a dedicated
women's key retain the base-key fallback, as live autofill does. Raw names remain
in source/report records; cached matches are corrected at state construction.

This harness correction changes women's replay results even at k=1:

| Format | Committed report run MAE | Real replay k=1 after key correction |
|---|---:|---:|
| Men's T20 | 21.06 | 21.06 |
| Women's T20 | 16.22 | 16.64 |
| Men's ODI | 41.47 | 41.47 |
| Women's ODI | 37.20 | 38.30 |

Do not interpret that difference as a production model change. The corrected
k=1 replay is the comparison baseline for every arm below.

## Full-cohort results

Bias is predicted minus actual. Run metrics are runs; wicket metrics are wickets.
Each T20 arm has 500 checkpoints; each ODI arm has 400, across 100 matches each.

| Format | k | Run MAE | Wicket MAE | Run bias | Wicket bias |
|---|---:|---:|---:|---:|---:|
| Men's T20 | 0 | 20.85 | 2.00 | -2.03 | -1.62 |
| Men's T20 | 0.25 | 20.88 | 2.02 | -1.85 | -1.64 |
| Men's T20 | 0.5 | 20.93 | 2.03 | -1.63 | -1.65 |
| Men's T20 | 1 | 21.06 | 2.05 | -1.22 | -1.67 |
| Women's T20 | 0 | 15.41 | 1.73 | -0.60 | -1.21 |
| Women's T20 | 0.25 | 15.62 | 1.75 | +0.09 | -1.24 |
| Women's T20 | 0.5 | 15.92 | 1.75 | +0.78 | -1.26 |
| Women's T20 | 1 | 16.64 | 1.76 | +2.14 | -1.31 |
| Men's ODI | 0 | 41.37 | 3.05 | -7.57 | -2.92 |
| Men's ODI | 0.25 | 41.20 | 3.05 | -6.56 | -2.92 |
| Men's ODI | 0.5 | 41.18 | 3.06 | -5.56 | -2.93 |
| Men's ODI | 1 | 41.47 | 3.11 | -3.50 | -2.98 |
| Women's ODI | 0 | 36.12 | 2.96 | +3.34 | -2.88 |
| Women's ODI | 0.25 | 36.30 | 2.97 | +4.42 | -2.88 |
| Women's ODI | 0.5 | 36.69 | 2.98 | +5.54 | -2.89 |
| Women's ODI | 1 | 38.30 | 2.99 | +7.81 | -2.90 |

## Chronological strength selection

Choose from 0, 0.25, 0.5, 1 using earlier-match run MAE first and wicket MAE to
break exact ties. Prefer the unchanged baseline if both metrics tie. Evaluate
the chosen arm on later matches without using those outcomes for selection.

The split is nearest to half by match count at a strict fixture-date boundary;
same-date fixtures are not divided between fit and test.

| Format | Earlier / later matches | Last earlier date | First later date | Selected k |
|---|---:|---|---|---:|
| Men's T20 | 49 / 51 | 2026-10-04 | 2026-10-05 | 0.5 |
| Women's T20 | 50 / 50 | 2026-09-03 | 2026-09-04 | 0 |
| Men's ODI | 49 / 51 | 2026-07-19 | 2026-07-21 | 0.25 |
| Women's ODI | 50 / 50 | 2025-10-16 | 2025-10-17 | 0.25 |

Later-fixture results, with three decimals to show small wicket differences:

| Format | Arm | Run MAE | Wicket MAE | Run bias | Wicket bias |
|---|---|---:|---:|---:|---:|
| Men's T20 | Baseline k=1 | 20.133 | 2.063 | -4.369 | -1.576 |
| Men's T20 | Selected k=0.5 | 19.886 | 2.055 | -4.129 | -1.576 |
| Women's T20 | Baseline k=1 | 18.024 | 1.748 | +0.848 | -1.300 |
| Women's T20 | Selected k=0 | 17.196 | 1.736 | -1.644 | -1.248 |
| Men's ODI | Baseline k=1 | 42.534 | 3.206 | -2.093 | -3.147 |
| Men's ODI | Selected k=0.25 | 42.368 | 3.098 | -8.064 | -3.039 |
| Women's ODI | Baseline k=1 | 38.055 | 3.010 | +11.655 | -2.950 |
| Women's ODI | Selected k=0.25 | 35.145 | 2.995 | +7.555 | -2.935 |

## Interpretation and recommendation

The earlier-selected strengths reduce later run MAE in all four formats and
also reduce wicket MAE, albeit only slightly in some formats. The largest run
gain is women's ODI, about 2.91 runs; the men's ODI gain is only about 0.17 runs.
Men's ODI run bias worsens from -2.09 to -8.06 despite the lower MAE. Women's T20
bias also moves from +0.85 to -1.64. These tradeoffs need monitoring.

Keep the production default at 1.0, as requested. The replay supports testing
smaller effects, not presenting these hand-assigned percentages as measured
ability or automatically promoting a change. A future untouched, timestamp-safe
evaluation should pre-register the earlier-selected candidates rather than
choose the best candidate using the later half. Do not change the ratings to
fit these same fixtures.

**This is a replay of the current model, not an out-of-time holdout.** Underlying
player/venue priors and model revisions are not frozen at each prediction date.
Earlier ODI revisions were evaluated on this same cohort. The committed
first-innings checkpoint eligibility favours innings reaching those checkpoints;
this task preserves that selection to maintain identical comparisons.
Checkpoint rows within a match are correlated, and no statistical-significance
claim is made. Team/bowling strength remains confounded with the fielding prior.
Changing three effects together does not isolate a causal contribution from
catching, run prevention or boundaries.

## Archived test disclosure

Final maintained-suite command: `pytest -q tests --tb=short` — **469 passed**,
26 warnings (the existing SQLAlchemy legacy lookup and short synthetic JWT
test-key warnings). No maintained test failed.

The maintained suite is the acceptance suite by user approval. Unrestricted
test discovery previously returned 470 passes and one failure:

`generated-artifacts/wicket-audit/test_research.py::ResearchChecks::test_sources_unchanged`

Error: `AssertionError` comparing current source fingerprints with the historical
`diagnostics.json` protected hashes. This test **passes on pre-change commit
40ac64e**, checked in an isolated temporary source snapshot. It fails after the
explicitly requested edits to prediction and backtest source files. The archived
test and its historical expected hashes were not edited, skipped or weakened.
