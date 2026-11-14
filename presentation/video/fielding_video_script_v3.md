# Fielding: the moments the data can't see

**90-second LinkedIn video / voiceover.** Keeps the India v New Zealand example from the "Two runs off" script, then adds the fielding moments and the data plan. About 270 words, roughly 105 seconds. Trim the "Later..." paragraph for a shorter cut.

---

Two runs off. But fielding is where I can't tell you the whole story.

I'm building CricPredict: a cricket prediction app for fans, with free and Pro plans. Entertainment only, not betting.

First ODI of India's 2026 tour of New Zealand. Virat Kohli took a one-handed diving catch at second slip to dismiss Nathan Smith. Rohit Sharma made a sharp run-out assist. Moments like these swing a match.

At 84 for four after 17 overs, CricPredict predicted 199 for seven. New Zealand finished 185 all out: fourteen runs lower, but three wickets more than predicted.

Later, at 171 for nine after 37.3 overs, it predicted 183 all out. Two runs off. Encouraging, but a much shorter horizon.

Did fielding explain the gap? I can't prove it. But here is the limit: CricPredict can't see how well a team fields. Today it is one hand-assigned rating per team, and in a replay on 1,800 checkpoint predictions, run error was 28.2 with it and 27.3 without. A blunt rating doesn't help. A real fielding signal might, and I think that gap is holding accuracy back, on runs and on wickets.

I can't build it from public data. Public ball-by-ball data only names a fielder when a wicket falls. No drops, no misfields, no dives, no runs saved.

So here is the plan. One route: ball-by-ball fielding data, and I'd like to talk to providers like CricViz about it. The other: build a fielding model of my own, starting in shadow mode. Either way, I'll test the effect on runs and wickets separately, on fresh, timestamped matches. If it doesn't beat the current model, it doesn't ship.

If you hold fielding data, or work at a data provider, message me. Try CricPredict at cricket-score-predictor.com.

---

## Must check before you record
* **Fielding moments:** you confirmed them by watching the match (Kohli's catch to dismiss Nathan Smith, Rohit's run-out assist). Say them as you saw them, no extra detail.
* **Match scores and predictions (84/4 after 17 overs to 199/7; 185 all out; 171/9 after 37.3 to 183)** are copied from your earlier "Two runs off" script. I could not check them: Cricsheet's public feed currently ends on 2026-11-03, before this ODI. Confirm against your saved predictions and the scorecard.
* Do **not** claim the catch or run-out caused the 14-run or 3-wicket gap. The script only says fielding could not be separated out, which is the honest point.
* 28.2 vs 27.3: `docs/fielding-strength-replay.md`; a replay of the current model, not an out-of-time test.
* **CricViz:** the script only says you'd like to talk to providers like CricViz. No conversation, access or agreement exists, so do not say "we're getting", "partnering with" or "using" CricViz data. Consider tagging them only if you are comfortable with the public ask.
* **The accuracy claim is a hypothesis, not a result.** What is measured: the hand-assigned rating did not improve run error (28.2 vs 27.3). "A real fielding signal might help, and I think the gap is holding accuracy back" is your belief, worded as one. Do not say fielding data *will* improve accuracy until a shadow test shows it.
* The plan is a plan. No data supplier or agreement exists yet; the in-house fielding model is research tooling, not in production.
