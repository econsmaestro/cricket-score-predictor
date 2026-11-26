# Fielding: the moments the data can't see (v4)

**90-second LinkedIn video / voiceover.** Same story as v3, with the plan reworded around who is actually in the XI. No provider named. About 255 words, roughly 100 seconds. Trim the "Later..." paragraph for a shorter cut.

---

Two runs off. But fielding is where I can't tell you the whole story.

I'm building CricPredict: a cricket prediction app for fans. Entertainment only, not betting.

First ODI of India's 2026 tour of New Zealand. Virat Kohli took a one-handed diving catch at second slip to dismiss Nathan Smith. Rohit Sharma made a sharp run-out assist. Moments like these swing a match.

At 84/4, after 17 overs, CricPredict predicted 199/7. New Zealand finished 185 all out: fourteen runs lower, but three wickets more than predicted.

Later, at 171/9 after 37.3 overs, it predicted 183 all out. Two runs off. Encouraging, but a much shorter horizon.

Did fielding explain the gap? I can't prove it. But the model has room to improve: in my backtest on men's ODIs, its average error is 41.5 runs. Fielding is one thing it can't see properly. Today it is just one hand-assigned rating per team, a reputation, not who is actually on the field. I think that is part of what's holding accuracy back, on runs and on wickets.

Public ball-by-ball data names a fielder only when a wicket falls, including run-outs from direct hits. It doesn't show dropped catches, runs saved by brilliant effort, or how difficult a catching chance was.

So here is the plan. Start with what public data does give me, the catches and run-outs that end in a wicket, and build a first fielding model from that in shadow mode, knowing its limits. Then, if I can get ball-by-ball fielding data, use it to rate the actual fielders in each XI. Test the effect on runs and wickets separately, on fresh matches. If it doesn't beat the current model, it doesn't ship.

If you hold fielding data, or work at a data provider, message me. Try CricPredict at cricket-score-predictor.com.

---

## Check before you record
* 41.5 runs: Men's ODI error from the public Backtesting page (100 matches, 400 checkpoint predictions, Cricsheet). A historical replay, not an out-of-time test.
* "One hand-assigned rating per team": true today (analyst estimate, three tiers).
* "I think that is part of what's holding accuracy back" is your belief, worded as one. The rating test did not help (28.2 with, 27.3 without), so do not say fielding data **will** improve accuracy.
* The plan is a plan. No data supplier or agreement exists. Do not name a provider.
* Match scores, predictions and the two fielding moments are verified by you.
