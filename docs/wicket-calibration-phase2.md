# Wicket calibration phase two — experimental only

No Flask route, production prediction equation, subscription logic, database schema,
or Fielding Intelligence module is changed. `research/wicket_calibration` is an offline
research package; it must not be imported into a request handler.

## Run

From the repository root:

```sh
python -m pytest tests/test_wicket_calibration.py -q
python -m research.wicket_calibration.evaluation --paths 128
python -m research.wicket_calibration.death_evaluation
python -m research.wicket_calibration.reporting
```

The evaluation uses the four existing ZIPs in `backtest_cache/` and the earlier audit's
`generated-artifacts/wicket-audit/ablations.json` fixture manifest. It deliberately fails
if those frozen inputs are missing. The selected earlier holdout is disjoint from every
fixture in that manifest. Results, parameter specifications, immutable prior snapshots,
source hashes and full paired forecasts are saved under ignored
`generated-artifacts/wicket-phase2/`. No downloads or new dependencies are required.

## Two clocks, not invented availability

Each prior snapshot records:

- event-completion bound, with a two-calendar-day embargo for date-only/timezone ambiguity;
- actual archive first-seen timestamp (not backdated);
- source record and ZIP hashes, cutoff, contributing fixture IDs and raw counts.

Event-time mode permits historical reconstruction from earlier completed fixtures.
Verified-availability mode additionally requires the archived version to have been
observed before the forecast. The current ZIPs lack a historical revision-publication
ledger, so a retrospective event-time reconstruction is **not** certified as-of-availability
validation. Model-constant historical tuning provenance is also unverified.
Do not weaken the verified-availability guard to advertise a leakage-free result.

## Replay

Completed, standard-length first innings are eligible, including early all-outs. Each
fixture has an innings-start forecast plus every configured checkpoint reached while
active. Already-ended checkpoints are excluded with counts, never padded with actual
final scores or wickets. Results include separate configured-only metrics.

Striker/non-striker, actual observed dismissals, pending replacements and stable
Cricsheet IDs are retained. Future batting order, batting pair and current-fixture
outcomes cannot enter a forecast. Known future information is used only as an
evaluation target or explanatory outcome group. Playing-XI metadata is assumed known
at match start; substituted/non-XI rosters are excluded because their timing is unknown.
Ambiguous multi-wicket timing and untimed penalties are explicitly flagged for review,
not converted into fabricated delivery events.

## Comparisons

The legacy equation baseline receives only frozen historical batting/venue priors,
neutral unsupported player/fielding labels and zero untimestamped database offsets.
It is an **input-controlled historical baseline**, not an exact reproduction of the
published production priors. Compare all variants within this lane.

Four legacy configurations test the 0.6 factor and one-wicket floor independently
and together. All three changes are asserted not to alter baseline scores/ranges.

Five joint models use observed joint delivery outcomes: phase only; phase/state;
state/player resources; state/recent dismissals; and full. Runs, dismissals, strike
changes, phase progression, batter replacement and all-out termination come from
the same paths. No batting-resource multiplier suppresses wicket hazards. Hierarchical
pooling concentration is selected only on preceding validation deliveries, then empirical
counts are refitted on prior training + validation fixtures and frozen for the holdout.

The resource variant infers order from past first-appearance positions, not target
innings order. Unknown players use shared empirical distributions. This does not claim
perfect XI/order availability. Recent-dismissal associations are not psychological
or causal estimates; no Fielding Pressure Index is used.

## Acceptance

Run error improvement remains the first priority; wicket error must also decrease.
Point estimates and paired fixture-bootstrap intervals are reported per format, phase
and actual final-wicket group. Joint simulations have finite Monte Carlo error,
reported per forecast; small changes require higher-path/seed confirmation.
Central 80% joint score intervals are not directly equivalent to the legacy ranges'
unspecified nominal coverage.

The late-checkpoint command is a supplementary post-primary diagnostic (ODI 45/48/49,
T20 17/18/19). It reuses identical frozen prior hashes and validation-selected settings.
It does not change candidate definitions or primary weighting, and its rows are not
pooled into the preregistered headline metrics.

No model is approved automatically. Strict source-availability provenance and untouched
validation remain requirements even when retrospective point estimates improve.
