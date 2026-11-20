# CricViz call: cheat sheet

**Goal:** ask for a small fielding-event data sample plus its data dictionary. Stay honest, stay short.

## Key numbers (all from the committed backtests)
* Average error (runs): Men's T20 **21.1**, Women's T20 **16.6**, Men's ODI **41.5**, Women's ODI **38.3**. 100 matches per format. Historical replay, **not** an out-of-time test.
* Men's T20 at the 6-over checkpoint: error **28.3** runs (weakest point), range contains the final score **49%** of the time. Overall hit rate 51.6%. Error falls to 13.8 by the 16th over.
* Fielding rating test (1,800 predictions): run error **28.2 with** it, **27.3 without**. It did not help (slightly worse).

## 1. Who are you, and what is CricPredict? (about 25 seconds)
* Anjaneya Sharma, 19, Singapore. Loved cricket since Dhawan's 137 at the MCG. NUS (AI) in 2028; built CricPredict for real-world experience.
* A cricket prediction site for fans. You give it the match state, venue, batters and bowlers. It gives a projected final total with a range (1st innings), win probability (chases), wickets to fall and next over.
* Entertainment only, not betting.
* Third Umpire AI is a separate chat assistant on the site.

## 2. Is it a trained machine-learning model? What data?
* A **statistical** model: phase-by-phase run rates, venue history, player batting and bowling stats.
* A small feedback layer learns venue and phase corrections from recorded outcomes.
* Do **not** say "trained ML" or "weather is an input". Weather is shown, not used in the projection.
* Data: live match state from Cricbuzz; player stats module from ESPNcricinfo (say the one you rely on); backtests on Cricsheet.
* No public ground-fielding data: public data names a fielder only on a dismissal.

## 3. Are you allowed to scrape that data? Commercial plans?
* "All the data I use right now is publicly available."
* "There's a small Pro tier, but the user base is small and it's early days."
* "If your data came into this, I'd agree terms with you first."
* "I'm asking for a research sample, not a commercial deal. I'm also a self-funded student."
* Only say "we got permission" if it is true, specific and in writing.

## 4. What do you want from us, and why say yes?
* **Ask:** ball-by-ball fielding data: catches taken and dropped, run-outs, misfields, runs saved. A small sample plus the data dictionary.
* **Why:** public data only shows wickets. Fielding is one limit I can name and can't test myself.
* **Why it's safe for you:** low cost, you set the terms, an independent test of whether fielding data helps, with credit if you want it.
* Do not claim "quite accurate". Say "reasonable for a small independent project".

## 5. Is 28 runs at 6 overs good? Is fielding the missing piece?
* "Hard to judge on its own. It's a historical replay and I have no benchmark against a professional model."
* "Fielding is **a** limitation I can name, not **the** one. I don't know yet whether it matters. That's what a small sample would tell me."

## 6. Your fielding rating didn't help. Why would event data?
* "The rating was static and hand-assigned per team. It didn't help; error was slightly higher with it on."
* "Fielding depends on who is in the XI. Event data lets me rate individual fielders, not a country label."
* "I don't know it will beat the baseline. I'd test it."

## 7. How would you know it worked, and what would you share?
* Same fresh matches, new model against current model. Runs error and wickets error separately, plus bias and range coverage.
* Check the gain is bigger than random noise. Fine to report "no clear improvement".
* Share results in the form and with the credit you prefer, **before** anything is published.

## 8. What's the smallest next step, and when? (suggested; adjust to your own plan)
* A small sample (a handful of matches) plus the data dictionary, under your terms. An NDA is fine.
* Who is the right person to talk to?
* "I'll send a short follow-up email today with exactly what I'm asking for. [Your timeline here]."

## Questions to ask them
* Which fielding events do you record per delivery, and how are runs saved defined?
* Which formats, competitions and years are covered?
* Can a sample cover matches that also exist in public data, so events can be joined to deliveries?
* How is data delivered, under what licence, and is a research sample possible?
* Any limits on publishing aggregate findings, and on crediting the source?

## Do not say
* That fielding data **will** improve accuracy, or that a fielding model is live or validated.
* That you have, or are getting, CricViz data, or any partnership.
* That the backtest is out-of-time, or that win probability is calibrated.
* "AI-powered prediction", "trained ML", or that weather feeds the prediction.
