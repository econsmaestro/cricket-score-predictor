# First-innings report refresh

The four first-innings JSON reports and their matching attached CSVs were
regenerated from exactly the same 100-match cohorts, ordered checkpoints and
actual targets. No second-innings report was changed.

Default fielding effect strength remains **1.0**. Prediction engine source and
rating values were not changed. Women's fixtures now use the women's fielding
rating keys. Existing methodology text was preserved verbatim, with only that
sentence appended.

## Before → after

Report display precision is retained. Signed bias is predicted minus actual.

| Format | Run MAE | Wicket MAE | Run bias | Wicket bias | Interval hit rate |
|---|---:|---:|---:|---:|---:|
| Men's T20 | 21.1 → 21.1 | 2.05 → 2.05 | −1.2 → −1.2 | −1.67 → −1.67 | 51.6% → 51.6% |
| Women's T20 | 16.2 → 16.6 | 1.75 → 1.76 | +1.3 → +2.1 | −1.28 → −1.31 | 56.0% → 56.0% |
| Men's ODI | 41.5 → 41.5 | 3.11 → 3.11 | −3.5 → −3.5 | −2.98 → −2.98 | 46.8% → 46.8% |
| Women's ODI | 37.2 → 38.3 | 2.91 → 2.99 | +3.6 → +7.8 | −2.82 → −2.90 | 51.7% → 51.7% |

This corrects evaluation inputs; it is not an accuracy improvement. These are
current-model historical replays, not independent out-of-time validation.

## Verification

- The archived `ResearchChecks::test_sources_unchanged` failed only for
  `prediction.py`, `backtest.py` and `backtest_data.py`, intentionally edited in
  the preceding fielding-strength and canonical-key work. All other protected
  hashes matched. Its assertion and test source were left unchanged.
- The reviewed hashes and a refresh command are versioned outside the ignored
  artifact directory. Run `python -m research.refresh_wicket_audit_hashes` to
  update only `protected_hashes` in the existing archived diagnostics.
- All 16 frozen complete prediction-output digests at strength 1.0 still match;
  the strength regression module's 40 tests passed.
- Backtesting preview loaded successfully. All four first-innings report APIs
  and CSV exports returned HTTP 200 and matched the committed report data and
  corresponding CSV contents.
- Full collection: `pytest -q --tb=short` — **481 passed, 26 warnings**.
  No tests skipped. Warnings concern existing SQLAlchemy legacy API usage and
  synthetic test JWT key length.
- The new report-consistency test initially failed in four format cases because
  JSON object keys are strings and computed checkpoint keys are integers.
  With explicit user approval, computed metrics are JSON-normalized before the
  full exact equality assertion. No tolerance, filtering or rounding was added.
- No production database changes, publishing, auth/referral/Stripe changes or
  prediction behaviour changes were made.

Reproduction: `python -m research.refresh_first_innings_reports`, using the
cached archives whose hashes must match the existing reports.

The platform checkpoint saved the regenerated reports separately from the
hash refresh under an automatically generated commit title; that title's
reference to removing unused ODI rows is inaccurate. No cohort or checkpoint
rows were removed. This report records the actual scope.
