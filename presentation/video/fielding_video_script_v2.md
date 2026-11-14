# Fielding: the rating that didn't help

**90-second LinkedIn video / voiceover.** Same style as the "Two runs off" script. About 215 words, roughly 85 seconds.

---

A dropped catch can swing a match. I can't tell you by how much.

I'm building CricPredict: a cricket prediction app for fans, with free and Pro plans. Entertainment only, not betting.

Today, fielding enters the prediction as one hand-assigned rating per team. So I tested it.

In a replay of the current model on 1,800 checkpoint predictions, run error was 28.2 with the rating on, and 27.3 with it off. The rating didn't earn its place.

Fielding is more than catches. A diving stop saves runs even when nobody is out. A dropped chance changes the odds of a wicket. It touches both the runs and the wickets.

But public ball-by-ball data only names a fielder when a wicket falls. No drops, no misfields, no runs saved.

So here is the plan. First, get ball-by-ball fielding data: every catch, drop, run-out chance, dive and boundary stop. I'm asking people who hold it for a small sample and a data dictionary.

Then test the effect on runs and wickets separately, in shadow mode, and judge it on fresh, timestamped matches.

If it doesn't beat the current model, it doesn't ship.

If you hold fielding data, message me. Try CricPredict at cricket-score-predictor.com.

---

## Checks before you record
* 28.2 vs 27.3: `docs/fielding-strength-replay.md`. It is a replay of the current model, not an out-of-time test. The script says "replay" on purpose.
* "One hand-assigned rating per team": `TEAM_FIELDING_EFFICIENCY` (analyst estimates, three tiers).
* "Public data only names fielders on dismissals": `docs/fielding-intelligence.md`.
* The plan is a plan. No data supplier or agreement exists yet, so do not say "we're partnering with" or "we've obtained".
* The run-error numbers are the only measured effect. The script makes no claim about wickets, because that test has not been done.
* Cutaways: `08_live_product_sample.png` on "one hand-assigned rating" (say it is a sample scenario); `03_the_numbers.png` on 28.2 vs 27.3; `06_the_ask.png` on the final ask.
