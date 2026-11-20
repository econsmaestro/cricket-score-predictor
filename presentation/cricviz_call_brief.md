# CricViz call: brief (goal: a small fielding-data sample plus its data dictionary)

## 60-second opening (cold intro)
"I'm [name], the independent developer of CricPredict, a cricket score-prediction site for fans: projected final score, range, wickets and chase probability. It's entertainment only, not betting. I'm here because I've hit a ceiling on one thing: fielding. Public ball-by-ball data only names a fielder when a wicket falls, so I can't measure drops, misfields, direct hits or runs saved. I'd like to understand what your fielding-event data looks like and whether a small research sample is possible."

## Demo run-through (Try Demo button, about 3 minutes)
1. Home page, tap **Try Demo, See a Sample Prediction**. Say it is a sample with pre-filled data: India v Australia, MCG, Men's T20, **87/2 after 10.3 overs**.
2. Banner: venue conditions ("pace friendly"), format, and the fielding badge. Say plainly: the fielding badge is **one hand-assigned team rating, an analyst estimate**, not a measured signal. This is the gap you want data for.
3. **Predicted final score: 205/4, range 181-229.** Then scroll **slowly**: the wickets and next-over numbers count up as they scroll into view, and show 0 until they do. Wickets card, next-over card with expected ball-by-ball.
4. (Optional) Backtesting page: Men's T20 21.1, Women's T20 16.6, Men's ODI 41.5, Women's ODI 38.3 runs MAE; 100 matches per format; a historical replay of the current model, not an out-of-time test. Skip the women's tiles if the live site has not been republished (it may still show 16.2 / 37.2).

## What is true about fielding (say only this)
* Today's fielding input is a hand-assigned rating per team (three tiers). It does not come from event data.
* A replay on 1,800 checkpoint predictions: run error 28.2 with the rating, 27.3 without. The blunt rating did not help.
* Research tooling (player registry, opportunity-adjusted estimates, shadow-mode comparison) exists but is **not in production** and is **not validated**.
* The project uses free sources only (Cricsheet). No agreement with any data provider exists.

## The ask
"A small sample of fielding-event data, even a handful of matches, plus the data dictionary. I'd run it in shadow mode against the current model, judged on runs and on wickets separately, and share what I find."

## Questions for them
1. What fielding events do you record per delivery (catch taken/dropped, chance difficulty, misfield, direct hit, boundary save, runs saved)? How are runs saved defined?
2. Which formats, competitions and years are covered, and how far back?
3. Can a sample cover matches that also exist in public ball-by-ball data (e.g. Cricsheet), so events can be joined to deliveries?
4. How is data delivered (files, API), under what licence, and is a research or non-commercial sample possible? Any NDA?
5. Are there any restrictions on publishing aggregate findings, and on crediting the source?
6. What does a typical commercial arrangement look like, so I know what is realistic later?

## Likely questions from them and honest answers
* **How accurate is it?** Men's ODI average error 41.5 runs, Men's T20 21.1 (Women's: ODI 38.3, T20 16.6), measured on 100 matches per format as a historical replay of the current model, not an out-of-time test.
* **Does fielding improve the prediction today?** No evidence it does. The rating test went from 27.3 to 28.2 with it on.
* **What do you want from us?** A sample and data dictionary to test whether event-level fielding adds anything. Nothing more yet.
* **Why not use public data?** Fielders are named only on successful dismissals, and catches and wickets alone mix up fielding with bowling and team quality.
* **Is it betting?** No. Entertainment only; the site says so.

## Do not say
* That fielding data will improve accuracy, or that a fielding model is live or validated.
* That you have, or are getting, CricViz data, or that there is any partnership.
* That the backtest is an out-of-time test.
