// Presenter talking points. Used for the PowerPoint speaker notes and the separate presenter script.
const SCRIPT = [
  { n: 1, title: 'Cover', time: '0:45', points: [
    'Thank the team for the time. One line on who you are: you built CricPredict, a live cricket intelligence and prediction platform.',
    'Set up the three things you will cover: what it does, how it actually performs (including where it falls short), and one data gap you think could improve accuracy: fielding.',
    'End the opening with the ask, so nobody is waiting for it: you would like to explore whether there is something worth doing together.',
    'Roughly 15 minutes plus questions. Invite interruptions.',
  ] },
  { n: 2, title: 'The problem', time: '1:30', points: [
    'State the problem in one sentence, out loud: a scoreboard reports what has happened, but it does not tell fans what is likely to happen next, or why it changed.',
    'A scoreboard says 84 for 4 after 17 overs. It does not say whether that is good, bad, or about to change.',
    'Run through the six questions quickly. Pause on the last two, because they are the bridge to the fielding section: question 5 is about chances (a dropped catch or missed run-out) and question 6 is about runs saved by good fielding even when nobody gets out (ground fielding, dives, boundary saves).',
    'The point is the gap between reporting what happened and helping fans understand what might happen next. Do not claim that nobody else offers predictions.',
  ] },
  { n: 3, title: 'The solution', time: '1:30', points: [
    'Frame this slide as the answer to the problem. Each pillar answers specific numbered questions from the previous slide: Predict answers 1 and 2, Explain answers 3 and 4, Quantify answers 5 and 6.',
    'Three pillars: Predict, Explain, Quantify. Use the colour legend: green is live on the site today, amber is research that is not in production.',
    'Predict: projected final score with a range, wickets to fall, next-over expectation, and a win probability in chases. Be upfront that the chase win probability is a heuristic estimate, not an independently calibrated model.',
    'Explain: plain-English reading of each projection and the drivers behind it (run rate, wickets in hand, overs left, momentum, venue and pitch).',
    'Quantify is the research direction. Today fielding is one fixed rating per team. Hold the detail for slide 7.',
  ] },
  { n: 4, title: 'The product (live demo)', time: '3:30', points: [
    'Switch to the live site: cricket-score-predictor.com. If a real match is on, use Live Game mode; otherwise enter a match state by hand.',
    'Show the flow: choose format, venue and match state, then the prediction, range, wickets to fall and next-over expectation. Scroll to the "what this means" text and the factors behind the number.',
    'Open the Backtesting page and show a report: this is the bridge to the next two slides.',
    'The screenshots on the slide are from the app\'s built-in sample scenario (India vs Australia, MCG T20), not a live match. Say so if asked.',
    'Backup if the network fails: stay on this slide and talk through the screenshots.',
    'Mention the Pro tier (saved predictions, match alerts) only if asked; it is not the point of today.',
  ] },
  { n: 5, title: 'A real prediction', time: '1:30', points: [
    'New Zealand vs India, an ODI. At 17 overs, 84 for 4, the model projected 199 with a range of 170 to 228.',
    'At 37.3 overs, 171 for 9, it had revised to 183. The actual score was 185.',
    'Be candid in how you read it: the early projection was 14 runs high but inside the range; the late revision was 2 runs away. It reacted to the wickets.',
    'Do not oversell: one match is a story, not evidence. The next slide is the evidence.',
  ] },
  { n: 6, title: 'Backtesting', time: '2:30', points: [
    'The experiment: 400 first innings, 100 per format, from Cricsheet ball-by-ball data. Each innings is replayed at completed-over checkpoints using only the deliveries available at that point.',
    'MAE is the average gap between predicted and actual final score, in runs. Women\'s T20I 16.6, Men\'s T20I 21.1, Women\'s ODI 38.3, Men\'s ODI 41.5. As a share of the average final score that is roughly 13 to 16% in every format.',
    'Right-hand chart: error falls as the innings unfolds. Men\'s ODI goes from 59.4 runs at over 10 to 21.6 at over 40.',
    'Be candid about what this is: a historical replay of the current model, not an out-of-time holdout, and some ODI model revisions were evaluated on this same set. Treat it as a calibration check, not independent validation.',
    'Predicted ranges contained the final score between 47 and 56% of the time depending on format. That is a known area to work on.',
    'ODI score prediction is the biggest improvement opportunity, and the early-innings checkpoints are where better inputs matter most.',
    'Numbers come from the report committed to the repository (run of 11 November 2026, after women\'s fixtures were switched to the women\'s fielding rating keys) and can be reproduced.',
  ] },
  { n: 7, title: 'The next frontier: fielding', time: '2:00', points: [
    'Batting and bowling are in the score data. Fielding mostly is not.',
    'Today CricPredict uses one hand-assigned rating per team (for example India 0.92, Australia 0.94). That is a placeholder, not a measurement.',
    'We tested our own placeholder with the real model. Switching the fielding effect off gives run MAE 27.3 against 28.2 at today\'s strength, across 1,800 checkpoint predictions. So today\'s ratings do not earn their keep. Be clear this is a replay of the current model, not an out-of-time test, and the gap is under a run; the point is that the ratings are not evidence of anything, which is why real event data matters.',
    'Public ball-by-ball data names fielders only on successful dismissals. Dropped catches, misfields, direct hits, runs saved and positions are not recorded.',
    'Walk the eight numbered events on the field. There are two ways good fielding moves the predicted score. Chances: catches and run-outs taken or missed change wicket probability. Runs saved: ground fielding, diving stops and boundary saves change how many runs the batting side scores, even when nobody gets out.',
    'Be candid about measurability. Runs saved needs a counterfactual: how many runs the ball would have gone for without the fielder. That needs fielder positions or ball-tracking style data, which public ball-by-ball files do not contain. Today one team rating scales both runs and wickets, and the slide shows that it does not improve accuracy.',
    'The goal is to measure how much good fielding changes the predicted score, through chances and runs saved, not to invent a fielding score.',
  ] },
  { n: 8, title: 'How the fielding rating works today', time: '1:30', points: [
    'Be direct: today\'s fielding rating is a hand-assigned prior, one value per team. It is not a measured statistic, and the slide says so. Be careful on history: the values were added in May 2026 without a recorded derivation. The reasons on the slide are why a measured rating is not possible today, not a record of what was thought at the time.',
    'Why a prior and not a measurement, three reasons. One: public ball-by-ball data names fielders only on successful dismissals, so there are no opportunities, drops, misfields, direct hits or runs saved. You cannot estimate catching skill from catches taken without knowing how many were chances. Two: event-level fielding data does exist, but it is sold under commercial licences, and the project uses free sources only. Three: outcome measures such as catches and wickets cannot separate fielding from bowling and overall team quality. Do not say the problem is too few matches: most of the 24 men\'s teams have 20 or more innings in the data.',
    'Structure: leading sides sit at 0.90 to 0.94, established sides at 0.80 to 0.85, the rest at 0.71 to 0.79. In effect it is a coarse prior that follows overall team standing.',
    'What it does: it scales projected runs by 0.90 to 1.15 and wickets by 0.79 to 1.15. It is bounded, unlisted teams are neutral, and for runs every team at 0.90 or above gets the same effect.',
    'How we tested it, honestly. Accuracy: switching it off moves run MAE from 28.2 to 27.3, so no gain at full strength; the best strength is about a quarter to a half of today\'s.',
    'Observed outcomes: the ordering tracks catches and wickets per innings (rank correlation +0.3 to +0.7, 9 to 21 teams per cohort). That mostly reflects overall team quality, and runs conceded per over does not agree. So it is consistent with team standing, not proof of fielding skill.',
    'Close the loop: we are labelling it an analyst estimate, calibrating the effect size on held-out matches, and replacing it with event-level evidence. That last step is the reason for this conversation.',
  ] },
  { n: 9, title: 'The research opportunity', time: '1:45', points: [
    'Six steps. The first three need data from a partner; the last three are modelling and evaluation. Step 2 covers both chances and run-saving actions such as stops and dives; step 4 estimates the effect on the predicted score through both wickets and runs saved.',
    'Be precise about what exists: research tooling (player registry and ingestion for public data, a shadow-mode comparison against the live model, and an activation gate). It is not in production and it claims no improvement. Its output is identical to the baseline until there are validated signals.',
    'What is missing is labelled events. Public data cannot supply them, which is why today\'s fielding rating is only a prior (the previous slide) and why this conversation matters. Link the two out loud: the placeholder exists because this data does not.',
    'This is proposed research, not a shipped feature. Say that plainly.',
  ] },
  { n: 10, title: 'Why Cricketviz', time: '1:30', points: [
    'Position it as a possible collaboration. Do not assume what Cricketviz holds: ask.',
    'Walk the six items you would like to explore: ball-by-ball fielding events, dropped catches and missed opportunities, run-out attempts and outcomes, fielder attribution, runs saved or conceded, and historical coverage.',
    'The proposed first step is deliberately small: a sample dataset and its data dictionary.',
    'Ask what would make this worthwhile on their side. Listen before proposing terms.',
  ] },
  { n: 11, title: 'Value for fans', time: '1:15', points: [
    'Keep it fan-first. The five outcomes: understand why a prediction changes, appreciate individual fielding contributions, understand key moments, explore what-if scenarios, see beyond the scoreboard.',
    'The sketch is a concept, clearly labelled; there are no numbers on it and it is not model output.',
    'Explaining why a prediction moved is more valuable to a fan than the number itself.',
  ] },
  { n: 12, title: 'Next steps', time: '1:00', points: [
    'Three discussion points, not demands: understand the data, explore a small-scale arrangement, test whether it helps.',
    'Questions to leave them with: What fielding data exists? Who would be the right person to talk to? What would be useful to Cricketviz?',
  ] },
  { n: 13, title: 'Closing', time: '0:30', points: [
    'Read the closing line: you are interested in how better cricket data can help build better predictions and give fans a deeper understanding of the game.',
    'Thank the Cricketviz team. Invite them to try the site, then open the floor for questions.',
  ] },
];

const QA = [
  ['Is the accuracy independently validated?', 'No. The backtest is a historical replay of the current model on recent internationals. It is not an out-of-time holdout, and some ODI revisions were evaluated on the same set. It is a calibration check. Any fielding signal would be judged on chronological, held-out matches before it goes anywhere near production.'],
  ['Do the fielding ratings help accuracy?', 'Not on our own test. Switching the fielding effect off in a real-model replay gives run MAE 27.3 against 28.2 at today\'s strength (1,800 predictions). A smaller effect, about a quarter to a half of today\'s, fits better on later matches. This is a replay of the current model, not an out-of-time test. The write-up is in the repository (docs/fielding-rating-audit.md). It is a placeholder, which is why I am asking about real event data.'],
  ['How would good fielding change the predicted score?', 'Through two channels. Chances: catches and run-outs taken or missed change the probability of a wicket. Runs saved: ground fielding, dives and boundary saves change the runs conceded even when nobody is out. Today a single hand-assigned team rating scales both, and it does not improve accuracy in our backtest. The research would estimate each channel from labelled event data, then test whether adding it improves held-out run and wicket error. Runs saved is the harder one because it needs a counterfactual (what the ball would have gone for), which public data cannot give.'],
  ['Why not just measure fielding from public data?', 'Because public ball-by-ball data names fielders only on successful dismissals. Without the number of chances, drops, misfields and runs saved you cannot separate skill from opportunity. Commercial providers sell event-level fielding data, but under paid licences, and I use free sources. Catches and wickets alone mostly reflect bowling and overall team quality, as my own correlation check shows.'],
  ['How were the fielding ratings arrived at?', 'They are hand-assigned, one value per team, in three rough tiers that follow overall team standing. They were not derived from catch or fielding data, and I would not present them as measured. I have tested them: they do not improve run accuracy at full strength, and the ordering agrees only loosely with observed catches and wickets. The plan is to label them as an estimate, calibrate the effect size, and replace them with event-level evidence.'],
  ['Is fielding already in the model?', 'Only as one hand-assigned rating per team. The event-level research tooling is built but runs in shadow mode and changes nothing in production.'],
  ['Is the win probability calibrated?', 'In chases it is a heuristic estimate based on required run rate, wickets in hand and phase of the innings. It has not been independently calibrated, and the slides say so.'],
  ['What would you do with our data, and who owns the results?', 'Open question, and I would like to hear your constraints first. I would start with a small sample under whatever terms suit you, and agree usage, ownership and attribution before anything larger.'],
  ['Do you already use any Cricketviz data?', 'No. Match data comes from public sources, with Cricsheet for the backtests.'],
  ['Why is ODI error so much higher than T20?', 'ODI totals are larger and the early overs give less information about how the innings will unfold. Relative to the average final score the gap is small (about 14 to 16% for ODI against 13 to 14% for T20), and error falls steadily as the innings progresses.'],
];

const NOTES = {};
SCRIPT.forEach((s) => { NOTES[s.n] = `[${s.time}] ` + s.points.map((p) => '• ' + p).join('\n'); });
module.exports = NOTES;
module.exports.SCRIPT = SCRIPT;
module.exports.QA = QA;
