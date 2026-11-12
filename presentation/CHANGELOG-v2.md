# Deck v2 change log (12 Nov 2026)

Targeted refinement of the 13-slide deck. Same narrative, theme, typography and slide count.
Version 1 is preserved, with its source, in `archive/v1-2026-11-12/`. Editable source: `source/`
(`build.js`, `notes.js`, `assets.js`); the PDF is rendered from the PPTX with LibreOffice.

## By slide

| Slide | Change |
|---|---|
| 1 Cover | No change. |
| 2 Problem | Caps labels and chip labels raised to 12pt for projection. No content change. |
| 3 Solution | No content change. |
| 4 Product | Reframed around four capabilities (projections with a range, win probability in chases, predictions that evolve, explained not just stated). Three screenshots reduced to two: a built-in sample scenario and a synthetic chase (92/3 chasing 168) showing chase probability. Pills and footnote label both as synthetic/sample, never live or real. Added "Also in the product" strip (pre-match insights, analytics, saved predictions and alerts) and a subtle "Live walkthrough next" cue. |
| 5 Real prediction | No change. |
| 6 Backtesting | Body text 13pt to 14pt; label sizes. Numbers unchanged. |
| 7 Fielding | Now "why fielding matters". Two channels made explicit: chances (opportunities) vs runs saved. Eight events colour-grouped on the field. The current-rating and MAE content moved to slide 8. |
| 8 Current approach | Now "why today's rating is not enough". Three columns: what it is and does (hand-assigned prior, 0.71 to 0.94, three tiers, modifiers, ignores XI and form); the evidence (MAE 28.2 vs 27.3 retained as large figures, best strength a quarter to a half, rank-correlation caveat); why public data cannot fix it (missed chances and runs saved unrecorded, outcomes are not skill, better data is paid). NEXT band retained. |
| 9 Research pipeline | Redesigned as a six-stage flow in three labelled groups: DATA (labelled events needed), MODEL (tooling built), TEST (built). "Already built (research tooling, not in production)" vs "The missing ingredient (labelled fielding-event data)" made equal-weight; explicit line that no validated fielding prediction exists yet. |
| 10 Cricketviz | Focused on what to explore: five items. "Proposed first step" band moved to slide 12 to avoid repetition. Caveat strengthened (no assumption of availability). |
| 11 Fans (concept) | Central concept stated; four examples (dropped catch, missed run-out, exceptional catch, boundary save) with direction arrows; concept chart relabelled event by event. Still labelled illustrative, not model output, not a feature; no numbers. |
| 12 Next steps | Three steps reworded (understand what data exists; small-scale arrangement; test on held-out matches) plus the proposed first step (sample dataset and data dictionary) and a "points for discussion" note. |
| 13 Closing | No change. |

Speaker notes, the presenter script (`CricPredict_Presenter_Script.docx`) and the Q&A were updated to match.

## Factual checks

* Every number in the deck was diffed against v1. The only additions are 92 and 168 (the synthetic chase, labelled as such). The only removals are 0.80/0.85 (tier ranges, now in the speaker notes) and 0.92 (India example, restored on slide 8). Backtest figures still read from `data/backtests/*.json` via `data.js`.
* No new backtest results. 28.2 vs 27.3 is the real-model replay already in `docs/fielding-strength-replay.md`.
* Disclosures retained: replay of the current model, not an out-of-time holdout or independent validation; win probability in chases is a heuristic estimate; fielding research tooling is not in production; no Cricketviz data capability or agreement is assumed.
* The website and app code were not modified or deployed. A local copy of the app was run read-only to capture the two screenshots.
