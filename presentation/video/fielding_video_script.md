# Fielding video: script, frames and shot list

About 190 words, roughly 80 seconds at a natural pace. Format: screen frames with your facecam bubble
in the bottom-right corner (300 px, centred about x 1690, y 870 on a 1920x1080 frame; see
`frames/00_facecam_guide.png`). Captions are in `captions.srt`; re-time them after you record.

| Time | Frame | Say |
|---|---|---|
| 0:00-0:10 | `01_hook.png` | "A dropped catch. A diving stop on the boundary. Fielding can swing a match, and no scoreboard tells you by how much." |
| 0:10-0:25 | `02_two_ways.png` | "It moves the score in two different ways. Chances: catches and run-outs, taken or missed, change the odds of a wicket. Runs saved: ground fielding, dives and boundary stops change how many runs get scored, even when nobody is out." |
| 0:25-0:42 | `03_the_numbers.png` | "Here is the honest part. In CricPredict today, fielding is one hand-assigned rating per team. I tested it. With the rating, run error is 28.2. With it switched off, 27.3. So it is not earning its place." |
| 0:42-0:57 | `04_why_not_measure.png` | "Why not measure it? Public ball-by-ball data names fielders only on successful dismissals. No drops, no misfields, no runs saved. And catches and wickets alone mix up fielding with bowling and team quality." |
| 0:57-1:10 | `05_built_vs_missing.png` | "What exists is the research tooling, running in shadow mode, not in production. What is missing is labelled fielding-event data. Until we have it, there is no validated fielding prediction." |
| 1:10-1:22 | `06_the_ask.png` | "If you hold structured fielding-event data, I would like to compare notes. A small sample and a data dictionary is enough to start. Details at cricket-score-predictor.com." |

## Where each claim comes from
* 28.2 vs 27.3: real-model replay, `docs/fielding-strength-replay.md` (1,800 checkpoints; a replay of the current model, not an out-of-time test, and the frame says so).
* Public data names fielders only on successful dismissals; paid event-level data; free sources only: `docs/fielding-intelligence.md`.
* Research tooling in shadow mode, not in production; no validated fielding prediction: same notes and `docs/fielding-rating-audit.md`.

## Production notes
* Record in Tella (or OBS) and edit in Descript, or lay the frames and your voice into CapCut. Import `captions.srt` and re-time.
* Keep the bottom-right corner clear when you add the facecam; every frame leaves it empty.
* Use one take per beat so cuts land on the frame changes.
* Do not add claims about accuracy gains or a launch: fielding is research and is not in live predictions.
