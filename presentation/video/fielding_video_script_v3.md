# Fielding: the moments the data can't see

**90-second LinkedIn video / voiceover.** Keeps the India v New Zealand example from the "Two runs off" script, then adds the fielding moments and the data plan. About 245 words, roughly 95 seconds. Trim the "Later..." paragraph for a shorter cut.

---

Two runs off. But fielding is where I can't tell you the whole story.

I'm building CricPredict: a cricket prediction app for fans, with free and Pro plans. Entertainment only, not betting.

First ODI of India's 2026 tour of New Zealand. **[VERIFY: Kohli's one-handed diving catch at second slip to dismiss Nathan Smith]**. **[VERIFY: Rohit Sharma's sharp run-out assist]**. Moments like these swing a match.

At 84 for four after 17 overs, CricPredict predicted 199 for seven. New Zealand finished 185 all out: fourteen runs lower, but three wickets more than predicted.

Later, at 171 for nine after 37.3 overs, it predicted 183 all out. Two runs off. Encouraging, but a much shorter horizon.

Did fielding explain the gap? I can't say. Today fielding is one hand-assigned rating per team, and when I tested it on 1,800 checkpoint predictions, run error was 28.2 with it and 27.3 without. It didn't earn its place.

The reason: public ball-by-ball data only names a fielder when a wicket falls. No drops, no misfields, no dives, no runs saved.

So here is the plan. Get ball-by-ball fielding data: every catch, drop, run-out chance, dive and boundary stop. Then test the effect on runs and on wickets separately, in shadow mode, on fresh, timestamped matches. If it doesn't beat the current model, it doesn't ship.

If you hold fielding data, message me. Try CricPredict at cricket-score-predictor.com.

---

## Must check before you record
* **The two fielding moments are NOT confirmed.** They come from a Google "AI Overview" screenshot, which also said "depending on which tour you are referring to" and did not describe any dropped catch, so I did not write one. Confirm the catch, the dismissed batter's name, the run-out and the date (Nov 4, Eden Park) on the official scorecard or highlights, then delete the **[VERIFY]** tags. Say only what the scorecard shows.
* **Match scores and predictions (84/4 after 17 overs to 199/7; 185 all out; 171/9 after 37.3 to 183)** are copied from your earlier "Two runs off" script. I could not check them: Cricsheet's public feed currently ends on 2026-11-03, before this ODI. Confirm against your saved predictions and the scorecard.
* Do **not** claim the catch or run-out caused the 14-run or 3-wicket gap. The script only says fielding could not be separated out, which is the honest point.
* 28.2 vs 27.3: `docs/fielding-strength-replay.md`; a replay of the current model, not an out-of-time test.
* The plan is a plan. No data supplier or agreement exists yet.
