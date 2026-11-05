---
name: Backtesting scope and interpretation
description: Required cohort sizes and honest interpretation of historical replay.
---

The backtesting webpage must cover 100 men's ODI matches, 100 men's T20 matches, 100 women's T20 matches, and 100 women's ODI matches.

**Why:** The user explicitly requested 100 matches in each category, not 100 pooled across formats and not 100 checkpoint predictions.

**How to apply:** Count distinct fixtures independently of checkpoint rows. Do not advertise a full cohort when any matches failed to replay. Clearly distinguish retrospective replay of the current model from independent out-of-time validation; existing model priors may already reflect historical results.

When the user asks for the *latest* 100 matches, refresh the source archives before replaying; regenerating a report against an old cached download does not meet that request.

**Why:** Earlier reports had been generated from weeks-old archives while newer completed matches were available.

**How to apply:** Record the source snapshot and newest included match date, and validate that each format has 100 distinct eligible fixtures. Track final-wicket error alongside runs so changes to fielding models can be assessed on both outcomes.

ODI calibration changes must stay isolated from T20 behavior.

**Why:** The user explicitly said the T20 engine is fine and requested ODI-specific corrections without changing T20 logic.

**How to apply:** Compare T20 predictions before and after ODI changes, not only overall averages. Report any range widening separately from improvement in point forecasts. A cohort used to diagnose or adjust a model is calibration data, not independent validation.

Freeze and disclose the replay's empirical-input providers and learned-adjustment context, not just its model-source hash. A chronological split alone does not establish leakage-free evaluation.

**Why:** Diagnostic replay can match saved reports while using different effective historical priors or learned offsets from a live session. Unversioned aggregates cannot establish what was available at a past forecast timestamp.

**How to apply:** Separate production-input sensitivity comparisons from training-only historical-input controls. Keep all fixtures/checkpoints paired, disclose unsupported historical provenance, and require untouched validation before activating corrections.

Retain early all-out innings in experimental evaluation. Use an innings-start forecast and only checkpoints reached while active; never pad ended innings with perfect terminal predictions.

**Why:** The user explicitly required early collapses and innings ending before configured checkpoints to remain in evaluation.

**How to apply:** Report active-checkpoint counts, exclusions and configured-only metrics separately so changed sampling is not mistaken for model improvement.

Never backdate source availability to a fixture's event date. Treat event-time reconstruction and verified source-availability validation as different evidence levels.

**Why:** Downloaded historical archives do not prove when their corrected record versions were published; the user withheld approval because chronological splitting alone did not resolve leakage.

**How to apply:** Preserve actual first-seen times and immutable prior/source versions. Keep approval blocked when historical revision availability or model tuning provenance cannot be established.
