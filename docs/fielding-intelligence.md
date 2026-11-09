# Fielding Intelligence Engine — audit and implementation record

## Stage 1: audit, sources and plan

The existing phase-based prediction engine is `prediction.py`. Its manually
assigned `TEAM_FIELDING_EFFICIENCY` changes future runs, wickets, next-over
runs, boundary rate and wicket probability. Chase win probabilities are
heuristic, not an independently calibrated probability model. Existing
hardcoded fielding values remain intact pending validation of replacements.

`Player` uses a unique display name (not a globally safe identity).
`DiscoveredPlayer` has a unique ESPN ID. The new registry links those ESPN IDs
and does not merge people just because they have the same name.

The live Cricbuzz scraper fetches score pages, scorecards and squads. It does
not retain structured ball-by-ball commentary or failed fielding chances.
Player-statistics scraping also uses ESPNcricinfo. Existing backtests replay
Cricsheet first innings in four men's/women's ODI/T20 cohorts. Those replays
are not proof that every existing model prior was learned before the fixture.

### Sources investigated

Checked official documentation on 2026-11-05:

* https://cricsheet.org/format/json/
* https://cricsheet.org/register/
* https://cricsheet.org/downloads/
* https://cricsheet.org/licensing/
* https://developer.sportradar.com/cricket/reference/cricket-faq
* https://sportradar.com/content-hub/news/sportradar-launches-new-comprehensive-live-fielding-data-capture-solution-at-cricket-world-cup/
* https://www.statsperform.com/team-performance/performance-solutions-for-cricket/
* https://www.statsperform.com/faqs/stats-perform-faqs-pricing-licensing/

**Cricsheet:** freely downloadable JSON and registry, licensed ODC Attribution
1.0 (not CC BY for JSON; XML alone uses CC BY 4.0). Public uses of derived
data must attribute Cricsheet and retain the licence notices. The registry
covers players **and officials**, not every professional in the world.
Coverage spans internationals and multiple domestic/franchise competitions,
with format/gender and historical gaps; some Afghanistan matches are withheld.
Stable person IDs, aliases and provider mappings are available. Cricbuzz ID
mapping is sparse: name-only live matches may remain unresolved.

Observed data: deliveries, runs, dismissal type, named fielders in successful
dismissals, match rosters and dates. Multiple named run-out participants are
observed involvement, **not proof of a direct hit or assist role**. Caught and
bowled identifies the bowler as the catcher. Exact substitute fielding time,
dropped catches, catch opportunity counts, difficulty, positions, direct hits,
misfields and runs saved are not supplied by the standard JSON schema.

**Sportradar:** the official FAQ documents fielding-level coverage for selected
major ICC events and CPL, including coordinates and multi-player events.
That is not universal coverage and does not establish that every desired
variable is available for every historical match. Access, historical depth,
exact field definitions, commercial-display/model-training rights, retention,
request limits and a price quote need contractual confirmation. No price
or API access is assumed and no subscription has been purchased.

**Opta/Stats Perform:** official materials advertise detailed ball-by-ball and
fielding metrics across elite internationals, T20 leagues and leading domestic
first-class/List A competitions. Their pricing is customised by competition,
country and data level. The public pages do not provide an unrestricted fielding
event dump, exact dropped-chance/difficulty schema, universal coverage or a
fixed public price. Those require a licensed sample and contractual confirmation.

### Implementation sequence

1. Central stable-ID registry and idempotent provenance-aware Cricsheet ingestion.
2. Observed statistics separated from unavailable opportunity denominators.
3. Opportunity/conversion estimation with learned shrinkage, only for labelled data.
4. Research-only fielding-pressure analysis with explicit data sufficiency checks.
5. Shadow integration: preserve existing live results; no double-counted wickets.
6. Chronological, fixture-disjoint comparison with published limitations.

Production deployment and external paid providers are not enabled automatically.
New tables use the existing database; Publish handles managed production schema
changes. Never copy development data over production to install this feature.

## Stage 2: registry and observation ingestion

Implemented in `fielding_intelligence/registry.py`, `ingestion.py`, `sources.py`
and `models.py`. The development database contains six additive tables:
`fielding_person`, `fielding_identifier`, `fielding_alias`, `fielding_match`,
`fielding_trial`, and `fielding_cache`. Existing tables were not redefined.
Provider identity conflicts and ambiguous aliases require reconciliation,
not a guessed merge. Existing ESPN identities are linked to `DiscoveredPlayer`.

Real imported coverage is recorded in
`generated-artifacts/fielding/coverage.json`. Registry and fixture ingestion are
idempotent. Match content hashes, source revisions, creation dates and parser
versions are retained. Unknown fielder names are counted explicitly.
Raw ZIPs, reports and source CSVs are excluded from Git and publishing.
The persistent application records are in the existing development PostgreSQL.

The global registry is not a guarantee of all-professional coverage. Actual
format/gender/date and competition counts must be read from the coverage report,
not inferred from the number of names. Source snapshots have differing dates.

## Stages 3–4: statistics, confidence and two-part probabilities

`ratings.py` separates observed dismissal counts from opportunity-adjusted
conversion. Complete delivery/opportunity labels are required to estimate
occurrence; explicitly observed successes and failures support conditional
conversion. Catching and run-out conversion each expose sample sizes and 95%
credible intervals. Beta-binomial shrinkage hyperparameters are learned within
one format/gender/provider cohort; degenerate cohorts use an explicitly disclosed
Jeffreys reference prior rather than invented team-specific pseudo-observations.

Ground fielding has separate event counts and descriptive uncertainty. Missing
or sparse evidence stays missing. A ground-event mean is not a complete
opportunity-adjusted ability estimate. Repeated-match clustering limits naive
event-level intervals, as reported alongside the statistic.

No overall FQR is produced. A simple mean of player conversion rates would also
assume an opportunity allocation across the XI that we do not observe. Contextual
position/difficulty/shot/batter/bowler and throwing-distance models are not yet
validated. No direct-hit attempt rate is inferred from one named run-out fielder.

`learning.py` provides research-only residual regression with learned coefficients
and regularisation chosen by chronological cross-validation. It requires complete,
validated component features; it cannot train using successful catches alone.
Training targets are residuals from the existing engine, not extra dismissal
counts to add to existing wicket projections. Trained artifacts are not
automatically authorised for activation, interval adjustment or chase win changes.
Synthetic tests of this code are not empirical validation of the model.

## Stage 5: controlled pressure research

`controlled_pressure` requires explicit event annotations and complete fielding
coverage, not commentary or unlabelled dot balls. It compares scoring changes and
subsequent wicket probabilities using controls-only versus controls-plus-event
models. Controls include innings/chase, score, wickets lost, over number, required
run rate, preceding scoring and preceding wickets. A missing chase required run
rate is excluded, not invented. Training and testing split by earlier/later
fixtures. The event delivery's immediate runs saved are excluded from the
subsequent outcome window.

No real pressure model was fitted: imported Cricsheet files lack the event labels.
Before/after summaries and controlled regressions remain associations, not
causal or psychological measurements. Overlapping windows require
fixture-clustered inference before any significance claim. No FPI or psychological
multiplier is generated.

## Stage 6: baseline-preserving integration

`prediction.py` is unchanged. `adapter.py` returns a `ShadowPrediction` containing
the original baseline result, a separate candidate copy and evidence diagnostics.
No fielding dismissals are added to the existing forecast. Existing prediction
routes continue to call the original engine. The adapter accepts real stable XI
IDs when supplied and reports missing coverage explicitly; it does not fabricate
an XI from player names or use a live provider call.

The read-only research endpoints are:

* `/api/fielding/status`
* `/api/fielding/players/<stable_id>?format=mens_odi&as_of=YYYY-MM-DD`

These are research data endpoints, not an automatically enabled live fielding UI.
They include source attribution, unavailable metrics and component confidence.
Historical cutoff dates conservatively exclude the entire current day.
Database caching is available for repeated historical component calculations;
online prediction paths never request provider APIs.

## Stage 7: comparison and limitations

The comparison reuses `backtest.build_state_at_over` and the original
`prediction.predict_score`. `backtest_data.parse_matches` gained only an optional
local archive path so the same eligibility rules can replay franchise archives.
All international cohort defaults remain unchanged.

`evaluation.py` compares the baseline and shadow on identical observations:
score MAE/bias, wicket MAE/bias, exact wicket-count accuracy and interval
coverage/width. It supports Brier/log-loss/calibration bins when real probability
and outcome pairs exist; first-innings replay supplies none, so no win calibration
is claimed. An activation gate rejects no-op/non-improving candidates and requires
opportunity labels, an independent holdout and interval/win approval.

New history uses only earlier completed matches with source creation before the
cutoff; actual labelled-event models additionally check known availability dates.
Conflicting event corrections are rejected rather than silently rewriting an
earlier historical event. Cricsheet's current revised files do not establish when
each correction was historically available. Existing prediction priors may also
reflect later data. Thus compatibility replay is not clean out-of-time validation
of the complete baseline, and previously used latest-match cohorts are not an
untouched holdout. The report explicitly discloses these limitations.

The numerical shadow output is intentionally identical while no component has
validated predictive value. This is evidence of compatibility, not improvement.
Test cricket is ingested, but the existing engine has no Test baseline; no Test
score, wicket or win improvement is claimed.

## Reproduction

Run offline only; obtain separate approval before production ingestion.

```sh
python -m fielding_intelligence registry
python -m fielding_intelligence ingest backtest_cache/odis_male_json.zip backtest_cache/odis_female_json.zip backtest_cache/t20s_male_json.zip backtest_cache/t20s_female_json.zip
python -m fielding_intelligence download tests_male_json.zip tests_female_json.zip ipl_json.zip bbl_json.zip wbb_json.zip psl_json.zip cpl_json.zip wpl_json.zip
python -m fielding_intelligence ingest generated-artifacts/fielding/sources/tests_male_json.zip generated-artifacts/fielding/sources/tests_female_json.zip generated-artifacts/fielding/sources/ipl_json.zip generated-artifacts/fielding/sources/bbl_json.zip generated-artifacts/fielding/sources/wbb_json.zip generated-artifacts/fielding/sources/psl_json.zip generated-artifacts/fielding/sources/cpl_json.zip generated-artifacts/fielding/sources/wpl_json.zip
python -m fielding_intelligence coverage > generated-artifacts/fielding/coverage.json
python -m fielding_intelligence evaluate --matches 100 --include-franchise
python -m pytest -q --junitxml=generated-artifacts/fielding/tests.xml
python -m fielding_intelligence report --test-results generated-artifacts/fielding/tests.xml
```

Legally obtained detailed event JSONL can be ingested with
`python -m fielding_intelligence trials <path>`. Each event requires provider
source, stable event/match/person identities, format/gender, event and known
availability dates, provenance, and explicit coverage/label fields.
Never assert exhaustive opportunity coverage for a successful-dismissal-only feed.
Unknown fields can be retained in the context object; unobserved values remain null.

Annotated delivery JSON can be investigated with
`python -m fielding_intelligence pressure <path> --split-date YYYY-MM-DD`.
Each record must include fixture/innings identity and the pre-event situation
variables used by the controlled analysis. This does not activate a live effect.
