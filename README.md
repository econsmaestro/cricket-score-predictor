# Cricket Score Predictor
AI-powered cricket match score prediction engine
https://cricket-score-predictor.com

## Score calibration layer

`prediction.py` is a hand-tuned engine. `score_calibration.py` adds a leakage-free ridge
correction and split-conformal 80% intervals on top of it, learned from Cricsheet backtests.
Retrain/evaluate with `python calibrate_scores.py [--save]`. Fitted coefficients live in
`data/calibration/<format>.json`.

Held-out results (newest 150 matches per format, trained only on older matches):

| Format | MAE before → after | RMSE before → after | Interval hit rate before → after |
|---|---|---|---|
| Men's T20 | 19.8 → 16.0 | 26.3 → 20.6 | 54.7% → 80.3% |
| Women's T20 | 15.2 → 12.3 | 19.9 → 15.9 | 59.6% → 87.6% |
| Men's ODI | 42.0 → 29.7 | 54.9 → 38.7 | 45.8% → 85.2% |
| Women's ODI | 35.4 → 28.5 | 47.3 → 37.5 | 53.5% → 79.5% |

Not yet wired into the live prediction route; call `score_calibration.calibrate(...)` on a
`predict_score` result to use it.
