---
name: Backtesting scope and interpretation
description: Required cohort sizes and honest interpretation of historical replay.
---

The backtesting webpage must cover 100 men's ODI matches, 100 men's T20 matches, 100 women's T20 matches, and 100 women's ODI matches.

**Why:** The user explicitly requested 100 matches in each category, not 100 pooled across formats and not 100 checkpoint predictions.

**How to apply:** Count distinct fixtures independently of checkpoint rows. Do not advertise a full cohort when any matches failed to replay. Clearly distinguish retrospective replay of the current model from independent out-of-time validation; existing model priors may already reflect historical results.

ODI calibration changes must stay isolated from T20 behavior.

**Why:** The user explicitly said the T20 engine is fine and requested ODI-specific corrections without changing T20 logic.

**How to apply:** Compare T20 predictions before and after ODI changes, not only overall averages. Report any range widening separately from improvement in point forecasts. A cohort used to diagnose or adjust a model is calibration data, not independent validation.
