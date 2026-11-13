const pptxgen = require('pptxgenjs');
const sharp = require('sharp');
const React = require('react');
const ReactDOMServer = require('react-dom/server');
const path = require('path');
const fs = require('fs');
const { applyTheme } = require('/root/.claude/skills/synced/5ef16cc9-a0f2-4818-a29a-cb91f20c953b_f01ee306-48b9-4766-87d4-83ca64cd9c24/pptx/scripts/apply_theme.js');
const NOTES = require('./notes.js');
const D = require('./data.js');

const A = (f) => path.join(__dirname, 'assets', f);
const OUT = process.argv[2] || path.join(__dirname, 'CricPredict_Cricketviz.pptx');

const THEME = {
  name: 'CricPredict Dark',
  headFontFace: 'Cambria',
  bodyFontFace: 'Calibri',
  colors: {
    dk1: '0B0F0D', lt1: 'FFFFFF', dk2: '141A17', lt2: 'A7B2AC',
    accent1: '34C26B', accent2: 'E0A93B', accent3: '8FD9AE', accent4: 'C8553D',
    accent5: '5B6B63', accent6: '22332B', hlink: '34C26B', folHlink: 'A7B2AC',
  },
};
// hex copies for options that cannot take scheme colours (charts)
const HEX = { green: '34C26B', amber: 'E0A93B', mint: '8FD9AE', white: 'FFFFFF', muted: 'A7B2AC', grid: '26332C' };

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.333 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = 'CricPredict: understand the game beyond the scoreboard';
pres.author = 'Anjaneya Sharma';
pres.subject = 'CricPredict live cricket intelligence: demonstration for Cricketviz';
const C = pres.SchemeColor;
const SH = pres.shapes;

// ---------- layouts ----------
pres.defineSlideMaster({
  title: 'COVER', background: { color: C.text1 }, objects: [],
});
pres.defineSlideMaster({
  title: 'CONTENT', background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: 'eyebrow', type: 'body', x: 0.6, y: 0.38, w: 9, h: 0.3, fontSize: 12, bold: true, color: C.accent1, charSpacing: 3, margin: 0, valign: 'top', align: 'left' }, text: '' } },
    { placeholder: { options: { name: 'title', type: 'title', x: 0.6, y: 0.68, w: 12.13, h: 1.15, fontSize: 32, bold: true, color: C.background1, margin: 0, valign: 'top', align: 'left' }, text: '' } },
    { text: { text: 'CricPredict  ·  cricket-score-predictor.com', options: { x: 0.6, y: 7.05, w: 6, h: 0.25, fontSize: 10, color: C.accent5, margin: 0, isTextBox: true } } },
  ],
  slideNumber: { x: 12.23, y: 7.05, w: 0.5, h: 0.25, fontSize: 10, color: C.accent5, align: 'right' },
});

// ---------- helpers ----------
function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: '#' + color, size: String(size) }));
  return sharp(Buffer.from(svg)).png().toBuffer().then((b) => 'image/png;base64,' + b.toString('base64'));
}
const md = require('react-icons/md');
const ICON = (n) => { if (!md[n]) throw new Error('missing icon ' + n); return md[n]; };

function card(s, x, y, w, h, name, opts = {}) {
  s.addShape(SH.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: opts.fill || C.text2 }, line: { color: opts.line || C.accent6, width: 1 }, objectName: name });
}
function txt(s, text, o) { s.addText(text, Object.assign({ isTextBox: true, margin: 0, valign: 'top' }, o)); }
function pill(s, label, x, y, w, color, name, textColor) {
  s.addShape(SH.ROUNDED_RECTANGLE, { x, y, w, h: 0.28, rectRadius: 0.14, fill: { color }, line: { color, width: 0 }, objectName: name });
  txt(s, label, { x, y, w, h: 0.28, fontSize: 11, bold: true, color: textColor || C.text1, align: 'center', valign: 'middle', charSpacing: 1, objectName: name + ' label' });
}
async function iconCircle(s, comp, x, y, d, name, bg, fg) {
  s.addShape(SH.OVAL, { x, y, w: d, h: d, fill: { color: bg || C.accent6 }, line: { color: bg || C.accent6, width: 0 }, objectName: name + ' bg' });
  const pad = d * 0.24;
  s.addImage({ data: await icon(comp, fg || HEX.green), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, altText: name, objectName: name });
}
function footnote(s, text) { txt(s, text, { x: 0.6, y: 6.78, w: 12.13, h: 0.24, fontSize: 11, color: C.background2, objectName: 'Footnote' }); }
function content(title, eyebrow, section) {
  const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: section });
  s.addText(eyebrow, { placeholder: 'eyebrow' });
  s.addText(title, { placeholder: 'title' });
  return s;
}

(async () => {
  // ======================================================= 1. COVER
  pres.addSection({ title: 'Opening' });
  let s = pres.addSlide({ masterName: 'COVER', sectionTitle: 'Opening' });
  s.addImage({ path: A('cover_art.png'), x: 6.333, y: 0, w: 7.0, h: 7.5, altText: 'Top-down illustration of a cricket field with fielders, a pitch and a highlighted fielding event', objectName: 'Cover field art' });
  txt(s, 'LIVE CRICKET INTELLIGENCE', { x: 0.7, y: 1.55, w: 6, h: 0.3, fontSize: 13, bold: true, color: C.accent1, charSpacing: 4, objectName: 'Cover eyebrow' });
  txt(s, 'CricPredict', { x: 0.7, y: 2.0, w: 6.0, h: 1.3, fontSize: 66, bold: true, color: C.background1, fontFace: 'Cambria', objectName: 'Cover title' });
  txt(s, 'Understand the game beyond the scoreboard.', { x: 0.7, y: 3.45, w: 5.4, h: 1.0, fontSize: 26, color: C.background1, objectName: 'Cover subtitle' });
  txt(s, 'An AI-powered live cricket intelligence and prediction platform.', { x: 0.7, y: 4.65, w: 5.2, h: 0.7, fontSize: 16, color: C.background2, objectName: 'Cover description' });
  txt(s, 'cricket-score-predictor.com', { x: 0.7, y: 5.55, w: 5, h: 0.35, fontSize: 18, bold: true, color: C.accent1, objectName: 'Cover URL' });
  txt(s, 'Prepared for the Cricketviz team  ·  November 2026', { x: 0.7, y: 6.75, w: 5.6, h: 0.3, fontSize: 12, color: C.background2, objectName: 'Cover byline' });
  s.addNotes(NOTES[1]);

  // ======================================================= 2. PROBLEM
  pres.addSection({ title: 'Problem and solution' });
  s = content('Cricket fans see the score. But do they understand the game?', 'THE PROBLEM', 'Problem and solution');
  const qs = ['What is a realistic final score?', 'How likely is the batting team to reach 200?', 'Has the batting team actually gained momentum?', 'How significant was that wicket?', 'How much did a dropped catch or missed run-out change the game?', 'How many runs does good fielding save, even when nobody gets out?'];
  qs.forEach((q, i) => {
    const y = 2.0 + i * 0.76;
    card(s, 0.6, y, 6.45, 0.64, 'Question card ' + (i + 1));
    s.addShape(SH.OVAL, { x: 0.82, y: y + 0.11, w: 0.42, h: 0.42, fill: { color: C.accent6 }, line: { color: C.accent6, width: 0 }, objectName: 'Question number bg ' + (i + 1) });
    txt(s, String(i + 1), { x: 0.82, y: y + 0.11, w: 0.42, h: 0.42, fontSize: 14, bold: true, color: C.accent1, align: 'center', valign: 'middle', objectName: 'Question number ' + (i + 1) });
    txt(s, q, { x: 1.45, y: y + 0.02, w: 5.4, h: 0.6, fontSize: 16, color: C.background1, valign: 'middle', objectName: 'Question text ' + (i + 1) });
  });
  card(s, 7.4, 2.05, 5.33, 2.9, 'Scoreboard card');
  txt(s, 'SCOREBOARD  ·  17.0 OVERS', { x: 7.7, y: 2.3, w: 4.7, h: 0.28, fontSize: 12, bold: true, color: C.background2, charSpacing: 2, objectName: 'Scoreboard label' });
  txt(s, '84/4', { x: 7.7, y: 2.62, w: 4.7, h: 1.2, fontSize: 80, bold: true, color: C.background1, objectName: 'Scoreboard score' });
  ['Final score', 'Reaches 200?', 'Momentum'].forEach((l, i) => {
    const x = 7.7 + i * 1.62;
    s.addShape(SH.ROUNDED_RECTANGLE, { x, y: 3.98, w: 1.48, h: 0.7, rectRadius: 0.1, fill: { color: C.text1 }, line: { color: C.accent6, width: 1 }, objectName: 'Unknown chip ' + (i + 1) });
    txt(s, l, { x: x + 0.14, y: 4.04, w: 1.3, h: 0.24, fontSize: 12, color: C.background2, objectName: 'Unknown chip label ' + (i + 1) });
    txt(s, '?', { x: x + 0.14, y: 4.26, w: 1.2, h: 0.4, fontSize: 22, bold: true, color: C.accent2, objectName: 'Unknown chip mark ' + (i + 1) });
  });
  card(s, 7.4, 5.2, 5.33, 1.33, 'Statement card');
  txt(s, 'THE PROBLEM, IN ONE SENTENCE', { x: 7.7, y: 5.34, w: 4.7, h: 0.26, fontSize: 12, bold: true, color: C.accent2, charSpacing: 2, objectName: 'Problem label' });
  txt(s, [
    { text: 'A scoreboard reports what has happened. ', options: { color: C.background2 } },
    { text: 'It does not tell fans what is likely to happen next, or why it changed.', options: { color: C.background1, bold: true } },
  ], { x: 7.7, y: 5.64, w: 4.75, h: 0.82, fontSize: 16, objectName: 'Statement text' });
  s.addNotes(NOTES[2]);

  // ======================================================= 3. SOLUTION
  s = content('From score reporting to cricket intelligence', 'THE SOLUTION  ·  HOW CRICPREDICT ANSWERS THE PROBLEM', 'Problem and solution');
  const pillars = [
    { name: 'PREDICT', icon: 'MdInsights', solves: 'Answers questions 1 and 2', chip: 'LIVE ON SITE', chipW: 1.3, chipColor: C.accent1, bullets: ['Projected final score, with a range', 'Wickets still to fall', 'Next-over expectation', 'Win probability in chases (heuristic estimate)'] },
    { name: 'EXPLAIN', icon: 'MdLightbulb', solves: 'Answers questions 3 and 4', chip: 'LIVE ON SITE', chipW: 1.3, chipColor: C.accent1, bullets: ['Plain-English reading of each projection', 'Drivers shown: run rate, wickets in hand, overs left, momentum', 'Venue and pitch conditions', 'Re-run at any match state to see how it moves'] },
    { name: 'QUANTIFY', icon: 'MdScience', solves: 'Answers questions 5 and 6', chip: 'PROPOSED RESEARCH', chipW: 1.85, chipColor: C.accent2, bullets: ['Today: one fixed fielding rating per team', 'Proposed: measure the effect of chances (dropped catches, run-outs) and of runs saved (ground fielding, dives, boundary saves)', 'Research tooling is built; it needs labelled event data'] },
  ];
  for (let i = 0; i < 3; i++) {
    const p = pillars[i]; const x = 0.6 + i * 4.125;
    card(s, x, 2.0, 3.85, 4.4, 'Pillar card ' + p.name);
    await iconCircle(s, ICON(p.icon), x + 0.3, 2.3, 0.62, 'Pillar icon ' + p.name);
    txt(s, p.name, { x: x + 1.1, y: 2.3, w: 2.5, h: 0.62, fontSize: 22, bold: true, color: C.background1, valign: 'middle', charSpacing: 2, objectName: 'Pillar name ' + p.name });
    pill(s, p.chip, x + 0.3, 3.1, p.chipW, p.chipColor, 'Pillar status ' + p.name);
    txt(s, p.solves + ' (previous slide)', { x: x + 0.3, y: 3.5, w: 3.3, h: 0.26, fontSize: 12.5, bold: true, color: C.accent3, objectName: 'Pillar answers ' + p.name });
    txt(s, p.bullets.map((b, k) => ({ text: b, options: { bullet: { indent: 16 }, breakLine: k < p.bullets.length - 1, paraSpaceAfter: 6 } })), { x: x + 0.3, y: 3.92, w: 3.3, h: 2.35, fontSize: 14.5, color: C.background1, objectName: 'Pillar bullets ' + p.name });
  }
  footnote(s, 'LIVE ON SITE = available in the product today.  PROPOSED RESEARCH = experimental or planned; not part of the production prediction.');
  s.addNotes(NOTES[3]);

  // ======================================================= 4. PRODUCT
  pres.addSection({ title: 'Product and proof' });
  s = content('A live intelligence layer for cricket', 'THE PRODUCT', 'Product and proof');
  const SW = 3.8, SHT = SW / 1.15;
  s.addImage({ path: A('ui_pred_a.png'), x: 0.6, y: 2.3, w: SW, h: SHT, altText: 'Screenshot of the CricPredict prediction page for a sample scenario, showing a predicted final score, a range and wickets to fall', objectName: 'Screenshot projection and range' });
  s.addImage({ path: A('fade.png'), x: 0.6, y: 2.3 + SHT - 0.8, w: SW, h: 0.8, altText: '', objectName: 'Fade projection' });
  s.addImage({ path: A('ui_pred_b.png'), x: 4.6, y: 2.3, w: SW, h: SHT, altText: 'Screenshot of the CricPredict prediction page for a synthetic chase, showing a 14 percent chase probability, wickets to fall and a next-over prediction', objectName: 'Screenshot chase' });
  s.addImage({ path: A('fade.png'), x: 4.6, y: 2.3 + SHT - 0.8, w: SW, h: 0.8, altText: '', objectName: 'Fade chase' });
  pill(s, 'PROJECTION AND RANGE  ·  SAMPLE SCENARIO', 0.6, 1.96, 3.8, C.accent1, 'Caption projection');
  pill(s, 'WIN PROBABILITY  ·  SYNTHETIC CHASE', 4.6, 1.96, 3.8, C.accent1, 'Caption chase');
  const caps = [
    ['MdInsights', 'Projections with a range', 'Final score, wickets to fall and a likely range, not one number.'],
    ['MdEmojiEvents', 'Win probability in chases', 'Chase probability, runs needed and required rate.'],
    ['MdTimeline', 'Predictions that evolve', 'Re-run as wickets, overs and conditions change (example on the next slide).'],
    ['MdLightbulb', 'Explained, not just stated', 'Plain-English meaning and the factors behind each number.'],
  ];
  for (let i = 0; i < caps.length; i++) {
    const y = 2.0 + i * 0.88;
    await iconCircle(s, ICON(caps[i][0]), 8.85, y + 0.04, 0.5, 'Capability icon ' + (i + 1));
    txt(s, caps[i][1], { x: 9.55, y, w: 3.18, h: 0.3, fontSize: 15.5, bold: true, color: C.background1, objectName: 'Capability title ' + (i + 1) });
    txt(s, caps[i][2], { x: 9.55, y: y + 0.32, w: 3.18, h: 0.5, fontSize: 13, color: C.background2, objectName: 'Capability text ' + (i + 1) });
  }
  card(s, 0.6, 5.85, 12.13, 0.75, 'Also strip');
  txt(s, [
    { text: 'ALSO IN THE PRODUCT   ', options: { bold: true, color: C.accent2, fontSize: 12, charSpacing: 2 } },
    { text: 'Pre-match insights  ·  Analytics  ·  Saved predictions and match alerts (Pro)', options: { color: C.background1, fontSize: 14 } },
  ], { x: 0.88, y: 5.85, w: 8.4, h: 0.75, valign: 'middle', objectName: 'Also text' });
  s.addImage({ data: await icon(ICON('MdPlayCircleOutline'), HEX.green), x: 9.75, y: 6.07, w: 0.32, h: 0.32, altText: 'Play', objectName: 'Walkthrough icon' });
  txt(s, 'Live walkthrough next', { x: 10.18, y: 5.85, w: 2.45, h: 0.75, fontSize: 14, bold: true, color: C.accent1, valign: 'middle', objectName: 'Walkthrough text' });
  footnote(s, 'Screenshots: the current product with synthetic inputs (a built-in sample scenario and a made-up chase, 92/3 chasing 168). Neither is live or real match data.');
  s.addNotes(NOTES[4]);

  // ======================================================= 5. REAL PREDICTION
  s = content('Predictions that evolve with the game', 'A REAL PREDICTION  ·  NEW ZEALAND VS INDIA, ODI', 'Product and proof');
  const arrow = await icon(ICON('MdChevronRight'), 'A7B2AC');
  const st = [
    { tag: 'AT 17.0 OVERS', score: '84/4', pred: '199', sub: 'Range 170 – 228', big: C.accent1 },
    { tag: 'AT 37.3 OVERS', score: '171/9', pred: '183', sub: 'Revised after five more wickets', big: C.accent1 },
    { tag: 'FINAL', score: '', pred: '185', sub: 'Revised prediction was 2 runs away', big: C.accent2 },
  ];
  st.forEach((p, i) => {
    const x = 0.6 + i * 4.115;
    card(s, x, 1.95, 3.8, 2.3, 'Station card ' + (i + 1));
    txt(s, p.tag, { x: x + 0.28, y: 2.15, w: 2.2, h: 0.26, fontSize: 12, bold: true, color: C.background2, charSpacing: 2, objectName: 'Station tag ' + (i + 1) });
    txt(s, p.score, { x: x + 2.0, y: 2.1, w: 1.55, h: 0.36, fontSize: 18, bold: true, color: C.background1, align: 'right', objectName: 'Station score ' + (i + 1) });
    txt(s, i === 2 ? 'Actual final score' : 'Predicted final score', { x: x + 0.28, y: 2.65, w: 3.2, h: 0.28, fontSize: 13, color: C.background2, objectName: 'Station caption ' + (i + 1) });
    txt(s, p.pred, { x: x + 0.28, y: 2.88, w: 3.2, h: 0.85, fontSize: 54, bold: true, color: p.big, objectName: 'Station number ' + (i + 1) });
    txt(s, p.sub, { x: x + 0.28, y: 3.78, w: 3.3, h: 0.3, fontSize: 13, color: C.background1, objectName: 'Station sub ' + (i + 1) });
    if (i < 2) {
      s.addImage({ data: arrow, x: x + 3.8 + 0.0325, y: 2.92, w: 0.25, h: 0.25, altText: 'Then', objectName: 'Station arrow ' + (i + 1) });
    }
  });
  // number line 160-240
  const X0 = 0.9, PX = 0.14375, nx = (v) => X0 + (v - 160) * PX;
  txt(s, 'WHERE EACH ESTIMATE LANDED (FINAL SCORE, RUNS)', { x: 0.6, y: 4.5, w: 8, h: 0.26, fontSize: 12, bold: true, color: C.background2, objectName: 'Number line label' });
  s.addShape(SH.RECTANGLE, { x: nx(170), y: 5.2, w: nx(228) - nx(170), h: 0.62, fill: { color: C.accent1, transparency: 82 }, line: { color: C.accent1, width: 1 }, objectName: 'Range band 170-228' });
  txt(s, 'Range at 17 overs: 170 – 228', { x: nx(206), y: 5.2, w: nx(228) - nx(206) - 0.1, h: 0.62, fontSize: 12, color: C.accent3, align: 'right', valign: 'middle', objectName: 'Range band label' });
  s.addShape(SH.LINE, { x: X0, y: 5.82, w: 80 * PX, h: 0, line: { color: C.accent5, width: 1.5 }, objectName: 'Number line axis' });
  for (let v = 160; v <= 240; v += 10) {
    s.addShape(SH.LINE, { x: nx(v), y: 5.82, w: 0, h: 0.08, line: { color: C.accent5, width: 1 }, objectName: 'Tick ' + v });
    txt(s, String(v), { x: nx(v) - 0.3, y: 5.94, w: 0.6, h: 0.22, fontSize: 12, color: C.background2, align: 'center', objectName: 'Tick label ' + v });
  }
  s.addShape(SH.OVAL, { x: nx(199) - 0.13, y: 5.51, w: 0.26, h: 0.26, fill: { color: C.accent1 }, line: { color: C.text1, width: 2 }, objectName: 'Marker 199' });
  txt(s, '199  ·  at 17 overs', { x: nx(199) - 1.0, y: 4.88, w: 2.0, h: 0.28, fontSize: 13, bold: true, color: C.background1, align: 'center', objectName: 'Marker label 199' });
  s.addShape(SH.OVAL, { x: nx(183) - 0.13, y: 5.51, w: 0.26, h: 0.26, fill: { color: C.accent3 }, line: { color: C.text1, width: 2 }, objectName: 'Marker 183' });
  txt(s, '183  ·  at 37.3 overs', { x: nx(183) - 1.15, y: 4.88, w: 2.1, h: 0.28, fontSize: 13, bold: true, color: C.background1, align: 'center', objectName: 'Marker label 183' });
  s.addShape(SH.LINE, { x: nx(185), y: 5.08, w: 0, h: 0.86, line: { color: C.accent2, width: 3 }, objectName: 'Actual score line' });
  txt(s, 'Actual: 185', { x: nx(185) - 0.6, y: 6.2, w: 1.2, h: 0.26, fontSize: 13, bold: true, color: C.accent2, align: 'center', objectName: 'Actual score label' });
  footnote(s, 'One match illustrates how the model behaves. It does not establish overall accuracy; see the 400-innings backtest on the next slide.');
  s.addNotes(NOTES[5]);

  // ======================================================= 6. BACKTESTING
  s = content('Testing predictions against real cricket', 'BEYOND DEMONSTRATIONS  ·  400-INNINGS BACKTEST', 'Product and proof');
  card(s, 0.6, 1.95, 6.3, 3.05, 'Chart card MAE by format');
  txt(s, 'Average error in final score, by format (MAE, runs)', { x: 0.85, y: 2.08, w: 5.8, h: 0.28, fontSize: 13, bold: true, color: C.background1, objectName: 'Chart title MAE' });
  s.addChart(pres.charts.BAR, [{ name: 'Score MAE (runs)', labels: D.formats.map((f) => f.label), values: D.formats.map((f) => f.mae) }], {
    x: 0.7, y: 2.4, w: 6.1, h: 2.55, objectName: 'Chart MAE by format',
    barDir: 'bar', catAxisOrientation: 'maxMin', chartColors: D.formats.map((f) => (f.t20 ? HEX.green : HEX.amber)),
    valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 52, valGridLine: { style: 'none' }, catGridLine: { style: 'none' },
    showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 15, dataLabelFontBold: true, dataLabelColor: HEX.white, dataLabelFontFace: '+mn-lt', dataLabelFormatCode: '0.0',
    catAxisLabelFontSize: 13, catAxisLabelColor: HEX.muted, catAxisLabelFontFace: '+mn-lt', catAxisLineShow: false,
    barGapWidthPct: 42, showLegend: false, showTitle: false,
  });
  card(s, 7.1, 1.95, 5.63, 3.05, 'Chart card ODI by checkpoint');
  txt(s, 'ODI error falls as the innings unfolds (MAE, runs)', { x: 7.35, y: 2.08, w: 5.2, h: 0.28, fontSize: 13, bold: true, color: C.background1, objectName: 'Chart title ODI' });
  s.addChart(pres.charts.LINE, [
    { name: "Men's ODI", labels: ['Over 10', 'Over 20', 'Over 30', 'Over 40'], values: D.cp.mens_odi },
    { name: "Women's ODI", labels: ['Over 10', 'Over 20', 'Over 30', 'Over 40'], values: D.cp.womens_odi },
  ], {
    x: 7.2, y: 2.4, w: 5.43, h: 2.55, objectName: 'Chart ODI MAE by checkpoint',
    chartColors: [HEX.amber, HEX.mint], lineSize: 3, lineDataSymbolSize: 9,
    valAxisMinVal: 0, valAxisMaxVal: 70, valAxisMajorUnit: 10, valAxisLabelColor: HEX.muted, valAxisLabelFontSize: 11, valAxisLabelFontFace: '+mn-lt',
    valGridLine: { color: HEX.grid, size: 0.75 }, catGridLine: { style: 'none' }, catAxisLabelColor: HEX.muted, catAxisLabelFontSize: 12, catAxisLabelFontFace: '+mn-lt',
    showLegend: true, legendPos: 'b', legendColor: HEX.white, legendFontSize: 12, legendFontFace: '+mn-lt', showTitle: false,
  });
  // lower row
  txt(s, [{ text: '400', options: { fontSize: 44, bold: true, color: C.accent1, breakLine: true } }, { text: 'first innings replayed', options: { fontSize: 14, color: C.background1, breakLine: true } }, { text: '100 per format  ·  1,800 checkpoint predictions', options: { fontSize: 12, color: C.background2 } }], { x: 0.6, y: 5.2, w: 3.6, h: 1.5, objectName: 'Backtest headline' });
  txt(s, [{ text: 'WHAT MAE MEANS', options: { fontSize: 11, bold: true, color: C.background2, charSpacing: 2, breakLine: true } },
          { text: 'The average gap, in runs, between predicted and actual final score. Roughly 13 to 16% of the average final score in each format.', options: { fontSize: 14, color: C.background1 } }], { x: 4.45, y: 5.2, w: 3.9, h: 1.5, objectName: 'MAE explainer' });
  txt(s, [{ text: 'WHERE WE ARE HONEST', options: { fontSize: 11, bold: true, color: C.accent2, charSpacing: 2, breakLine: true } },
          { text: 'ODI score prediction is the biggest improvement opportunity. Death-over acceleration and other match-specific factors remain hard. Predicted ranges held the final score 47 to 56% of the time.', options: { fontSize: 14, color: C.background1 } }], { x: 8.6, y: 5.2, w: 4.13, h: 1.5, objectName: 'Honest observations' });
  footnote(s, 'Historical replay of the current model on the 100 most recent eligible full-length internationals per format (Cricsheet); not an out-of-time holdout or independent validation. Run of 11 Nov 2026.');
  s.addNotes(NOTES[6]);

  // ======================================================= 7. WHY FIELDING MATTERS
  pres.addSection({ title: 'The fielding opportunity' });
  s = content('Fielding changes a match in two different ways', 'THE NEXT FRONTIER  ·  WHY FIELDING MATTERS', 'The fielding opportunity');
  const FX = 0.6, FY = 1.95, FS = 4.75, fx = (v) => FX + (v * FS) / 1000, fy = (v) => FY + (v * FS) / 1000;
  s.addImage({ path: A('field_base.png'), x: FX, y: FY, w: FS, h: FS, altText: 'Top-down cricket field with the pitch, a 30-yard circle and fielders', objectName: 'Field diagram' });
  const chances = [['Dropped catch', 580, 655], ['Missed run-out', 525, 392], ['Successful run-out', 438, 578], ['Exceptional catch', 150, 600]];
  const saved = [['Boundary save (dive)', 880, 470], ['Ground fielding: runs saved', 672, 548], ['Diving stop in the ring', 322, 428], ['Misfield (extra runs)', 665, 345]];
  const evs = chances.map((e) => e.concat([C.accent2])).concat(saved.map((e) => e.concat([C.accent3])));
  evs.forEach((e, i) => {
    s.addShape(SH.OVAL, { x: fx(e[1]) - 0.16, y: fy(e[2]) - 0.16, w: 0.32, h: 0.32, fill: { color: e[3] }, line: { color: C.text1, width: 2 }, objectName: 'Event marker ' + (i + 1) });
    txt(s, String(i + 1), { x: fx(e[1]) - 0.16, y: fy(e[2]) - 0.16, w: 0.32, h: 0.32, fontSize: 12, bold: true, color: C.text1, align: 'center', valign: 'middle', objectName: 'Event number ' + (i + 1) });
  });
  txt(s, [
    { text: 'Fielding moves the score in two different ways: ', options: { bold: true, color: C.background1 } },
    { text: 'by creating or wasting chances, and by saving runs even when no one is out.', options: { color: C.background2 } },
  ], { x: 5.75, y: 1.95, w: 6.98, h: 0.85, fontSize: 16, objectName: 'Two ways statement' });
  const groups = [
    { x: 5.75, w: 3.4, label: 'CHANCES  →  WICKETS', col: C.accent2, items: chances, off: 0, note: 'Change the chance of a wicket.', name: 'Chances' },
    { x: 9.3, w: 3.43, label: 'RUNS SAVED  →  RUNS', col: C.accent3, items: saved, off: 4, note: 'Change runs scored, even with no wicket.', name: 'Runs saved' },
  ];
  groups.forEach((g) => {
    card(s, g.x, 2.9, g.w, 2.6, g.name + ' card');
    txt(s, g.label, { x: g.x + 0.25, y: 3.05, w: g.w - 0.4, h: 0.26, fontSize: 12, bold: true, color: g.col, charSpacing: 1.5, objectName: g.name + ' label' });
    g.items.forEach((e, k) => {
      const y = 3.45 + k * 0.42;
      s.addShape(SH.OVAL, { x: g.x + 0.25, y, w: 0.3, h: 0.3, fill: { color: g.col }, line: { color: g.col, width: 0 }, objectName: g.name + ' dot ' + (k + 1) });
      txt(s, String(g.off + k + 1), { x: g.x + 0.25, y, w: 0.3, h: 0.3, fontSize: 12, bold: true, color: C.text1, align: 'center', valign: 'middle', objectName: g.name + ' number ' + (k + 1) });
      txt(s, e[0], { x: g.x + 0.65, y, w: g.w - 0.8, h: 0.3, fontSize: 14, color: C.background1, valign: 'middle', objectName: g.name + ' item ' + (k + 1) });
    });
    txt(s, g.note, { x: g.x + 0.25, y: 5.12, w: g.w - 0.4, h: 0.3, fontSize: 13, italic: true, color: C.background2, objectName: g.name + ' note' });
  });
  card(s, 5.75, 5.65, 6.98, 1.0, 'Why measure card');
  txt(s, [
    { text: 'WHY MEASURE IT', options: { bold: true, color: C.accent1, fontSize: 12, charSpacing: 2, breakLine: true, paraSpaceAfter: 4 } },
    { text: 'Wickets and runs both feed the projected total and the win probability. Measuring contributions could explain swings in a match and sharpen projections.', options: { color: C.background1, fontSize: 14 } },
  ], { x: 5.98, y: 5.65, w: 6.55, h: 1.0, valign: 'middle', objectName: 'Why measure text' });
  footnote(s, 'Illustrative field diagram: marker positions are generic, not data. Amber = chances, green = runs saved.');
  s.addNotes(NOTES[7]);

  // ======================================================= 8. WHY THE CURRENT APPROACH IS NOT ENOUGH
  s = content('Why today\'s fielding rating is not enough', 'THE CURRENT APPROACH', 'The fielding opportunity');
  const cx = (i) => 0.6 + i * 4.125;
  // column 1
  card(s, cx(0), 1.95, 3.85, 3.7, 'Approach card');
  txt(s, 'WHAT IT IS AND DOES', { x: cx(0) + 0.28, y: 2.12, w: 3.3, h: 0.26, fontSize: 12, bold: true, color: C.accent1, charSpacing: 2, objectName: 'Approach label' });
  txt(s, [
    { text: 'A hand-assigned prior: one value per team (0.71–0.94, for example India 0.92), in three tiers', options: { bullet: { indent: 16 }, breakLine: true, paraSpaceAfter: 10 } },
    { text: 'Scales projected runs ×0.90–1.15 and wickets ×0.79–1.15', options: { bullet: { indent: 16 }, breakLine: true, paraSpaceAfter: 10 } },
    { text: 'Ignores who is playing and recent form. Unlisted teams are neutral', options: { bullet: { indent: 16 } } },
  ], { x: cx(0) + 0.28, y: 2.5, w: 3.35, h: 3.05, fontSize: 16, color: C.background1, objectName: 'Approach bullets' });
  // column 2
  card(s, cx(1), 1.95, 3.85, 3.7, 'Evidence card');
  txt(s, 'WHAT THE EVIDENCE SHOWS', { x: cx(1) + 0.28, y: 2.12, w: 3.3, h: 0.26, fontSize: 12, bold: true, color: C.accent2, charSpacing: 2, objectName: 'Evidence label' });
  txt(s, '28.2', { x: cx(1) + 0.28, y: 2.45, w: 1.6, h: 0.7, fontSize: 40, bold: true, color: C.accent2, objectName: 'MAE with' });
  txt(s, 'with the rating', { x: cx(1) + 0.28, y: 3.13, w: 1.6, h: 0.26, fontSize: 13, color: C.background2, objectName: 'MAE with caption' });
  txt(s, '27.3', { x: cx(1) + 2.05, y: 2.45, w: 1.6, h: 0.7, fontSize: 40, bold: true, color: C.accent1, objectName: 'MAE without' });
  txt(s, 'switched off', { x: cx(1) + 2.05, y: 3.13, w: 1.6, h: 0.26, fontSize: 13, color: C.background2, objectName: 'MAE without caption' });
  txt(s, 'Run MAE, real-model replay, 1,800 checkpoints: no gain at full strength.', { x: cx(1) + 0.28, y: 3.5, w: 3.35, h: 0.5, fontSize: 13, color: C.background1, objectName: 'MAE caption' });
  txt(s, [
    { text: 'The best strength is about a quarter to a half of today\'s', options: { bullet: { indent: 16 }, breakLine: true, paraSpaceAfter: 6 } },
    { text: 'Ratings track catches and wickets per innings (rank correlation +0.3 to +0.7), but not runs conceded per over', options: { bullet: { indent: 16 } } },
  ], { x: cx(1) + 0.28, y: 4.1, w: 3.35, h: 1.5, fontSize: 13, color: C.background1, objectName: 'Evidence bullets' });
  // column 3
  card(s, cx(2), 1.95, 3.85, 3.7, 'Data card');
  txt(s, 'WHY PUBLIC DATA CANNOT FIX IT', { x: cx(2) + 0.28, y: 2.12, w: 3.4, h: 0.26, fontSize: 12, bold: true, color: C.accent1, charSpacing: 1.5, objectName: 'Data label' });
  txt(s, [
    { text: 'Missed chances and runs saved are not recorded. ', options: { bold: true, color: C.background1 } },
    { text: 'Fielders are named only on successful dismissals.', options: { color: C.background1, breakLine: true, paraSpaceAfter: 9 } },
    { text: 'Outcomes are not skill. ', options: { bold: true, color: C.background1 } },
    { text: 'Catches and wickets reflect bowling and team quality as much as fielding.', options: { color: C.background1, breakLine: true, paraSpaceAfter: 9 } },
    { text: 'Better data is paid. ', options: { bold: true, color: C.background1 } },
    { text: 'Event-level data is sold under licence; we use free sources only.', options: { color: C.background1 } },
  ], { x: cx(2) + 0.28, y: 2.5, w: 3.35, h: 3.05, fontSize: 14.5, objectName: 'Data text' });
  card(s, 0.6, 5.85, 12.13, 0.8, 'Next band', { fill: C.accent6, line: C.accent6 });
  txt(s, [
    { text: 'NEXT   ', options: { bold: true, color: C.accent2, charSpacing: 2 } },
    { text: 'Label it an analyst estimate   ·   Calibrate its strength on held-out matches   ·   Replace it with event-level evidence', options: { color: C.background1 } },
  ], { x: 0.88, y: 5.85, w: 11.6, h: 0.8, fontSize: 15, valign: 'middle', objectName: 'Next text' });
  footnote(s, 'MAE: real-model replay, full vs zero fielding effect. Rank correlations: Cricsheet team outcomes, teams with 20+ innings (9 to 21 per cohort); confounded by team strength.');
  s.addNotes(NOTES[8]);

  // ======================================================= 9. RESEARCH PIPELINE
  s = content('Turning fielding events into predictive intelligence', 'PROPOSED RESEARCH', 'The fielding opportunity');
  const stages = [
    ['Obtain event data', 'Structured historical fielding events from a partner.'],
    ['Identify opportunities', 'Chances taken or missed, and run-saving actions.'],
    ['Attribute events', 'To players and match situations, where possible.'],
    ['Quantify the effect', 'On the predicted score, through wickets and runs saved.'],
    ['Add validated signals', 'Only signals that prove predictive join the framework.'],
    ['Held-out testing', 'Backtest on matches the model has not seen.'],
  ];
  const sx = (i) => 0.6 + i * 2.043, sw = 2.0;
  const bands = [[0, 3, 'DATA  ·  LABELLED EVENTS NEEDED', C.accent2], [3, 5, 'MODEL  ·  TOOLING BUILT', C.accent1], [5, 6, 'TEST  ·  BUILT', C.accent1]];
  bands.forEach((b, k) => {
    s.addShape(SH.ROUNDED_RECTANGLE, { x: sx(b[0]), y: 1.95, w: sx(b[1] - 1) + sw - sx(b[0]), h: 0.38, rectRadius: 0.08, fill: { color: C.text2 }, line: { color: b[3], width: 1.25 }, objectName: 'Stage group ' + (k + 1) });
    txt(s, b[2], { x: sx(b[0]), y: 1.95, w: sx(b[1] - 1) + sw - sx(b[0]), h: 0.38, fontSize: 12, bold: true, color: b[3], align: 'center', valign: 'middle', charSpacing: 1.5, objectName: 'Stage group label ' + (k + 1) });
  });
  stages.forEach((st, i) => {
    const col = i < 3 ? C.accent2 : C.accent1;
    s.addShape(SH.PENTAGON, { x: sx(i), y: 2.45, w: sw, h: 0.85, fill: { color: C.accent6 }, line: { color: col, width: 1.25 }, objectName: 'Stage ' + (i + 1) });
    txt(s, String(i + 1), { x: sx(i) + 0.12, y: 2.45, w: 0.32, h: 0.85, fontSize: 18, bold: true, color: col, align: 'center', valign: 'middle', objectName: 'Stage number ' + (i + 1) });
    txt(s, st[0], { x: sx(i) + 0.5, y: 2.45, w: sw - 0.85, h: 0.85, fontSize: 13.5, bold: true, color: C.background1, valign: 'middle', objectName: 'Stage title ' + (i + 1) });
    txt(s, st[1], { x: sx(i) + 0.05, y: 3.42, w: sw - 0.15, h: 0.95, fontSize: 13, color: C.background2, objectName: 'Stage text ' + (i + 1) });
  });
  card(s, 0.6, 4.5, 6.0, 2.1, 'Built card');
  txt(s, 'ALREADY BUILT  ·  RESEARCH TOOLING, NOT IN PRODUCTION', { x: 0.88, y: 4.64, w: 5.5, h: 0.26, fontSize: 12, bold: true, color: C.accent1, charSpacing: 1, objectName: 'Built label' });
  txt(s, [
    { text: 'Player registry and ingestion for public data', options: { bullet: { indent: 16 }, breakLine: true, paraSpaceAfter: 5 } },
    { text: 'Opportunity-adjusted estimates with uncertainty', options: { bullet: { indent: 16 }, breakLine: true, paraSpaceAfter: 5 } },
    { text: 'Shadow-mode comparison with the live model, and an activation gate that blocks changes that do not improve held-out results', options: { bullet: { indent: 16 } } },
  ], { x: 0.88, y: 5.0, w: 5.55, h: 1.55, fontSize: 14.5, color: C.background1, objectName: 'Built bullets' });
  card(s, 6.75, 4.5, 5.98, 2.1, 'Missing card');
  txt(s, 'THE MISSING INGREDIENT', { x: 7.0, y: 4.64, w: 5.5, h: 0.26, fontSize: 12, bold: true, color: C.accent2, charSpacing: 1.5, objectName: 'Missing label' });
  txt(s, [
    { text: 'Labelled fielding-event data: ', options: { bold: true, color: C.background1 } },
    { text: 'dropped chances, misfields, direct hits and runs saved. Public data cannot supply it, which is why today\'s rating is only a prior (slide 8).', options: { color: C.background1, breakLine: true, paraSpaceAfter: 8 } },
    { text: 'No validated fielding prediction exists yet. ', options: { bold: true, color: C.accent2 } },
    { text: 'Shadow output equals the baseline until validated signals exist.', options: { color: C.background1 } },
  ], { x: 7.0, y: 5.0, w: 5.5, h: 1.55, fontSize: 14, objectName: 'Missing text' });
  footnote(s, 'Proposed research, not a completed production feature. No event-based fielding signal is in the live prediction; today\'s input is the hand-assigned team rating (slide 8).');
  s.addNotes(NOTES[9]);

  // ======================================================= 10. WHAT I HOPE TO EXPLORE WITH CRICKETVIZ
  pres.addSection({ title: 'Collaboration' });
  s = content('An opportunity to take cricket analytics further', 'WHY CRICKETVIZ', 'Collaboration');
  card(s, 0.6, 1.95, 4.95, 4.65, 'Bring card');
  txt(s, 'WHAT CRICKETVIZ MAY BRING', { x: 0.88, y: 2.15, w: 4.4, h: 0.26, fontSize: 12, bold: true, color: C.accent1, charSpacing: 2, objectName: 'Bring label' });
  txt(s, 'Domain knowledge, structured cricket information and data capabilities that could help investigate this problem.', { x: 0.88, y: 2.6, w: 4.4, h: 2.3, fontSize: 22, color: C.background1, objectName: 'Bring text' });
  txt(s, 'I am not assuming what data you hold or can share, or that any of it is available. That is the first conversation.', { x: 0.88, y: 4.95, w: 4.4, h: 1.4, fontSize: 15, color: C.background2, objectName: 'Bring caveat' });
  card(s, 5.8, 1.95, 6.93, 4.65, 'Explore card');
  txt(s, 'WHAT I WOULD LIKE TO EXPLORE', { x: 6.08, y: 2.15, w: 6.0, h: 0.26, fontSize: 12, bold: true, color: C.accent1, charSpacing: 2, objectName: 'Explore label' });
  const wants = ['Structured historical fielding-event data', 'Dropped catches and missed opportunities', 'Run-out attempts and outcomes', 'Runs saved or conceded (stops, dives)', 'Fielder attribution and historical coverage'];
  const chk = await icon(ICON('MdCheckCircle'), HEX.green);
  wants.forEach((w, i) => {
    const y = 2.7 + i * 0.77;
    s.addImage({ data: chk, x: 6.08, y: y + 0.04, w: 0.34, h: 0.34, altText: 'Check', objectName: 'Explore check ' + (i + 1) });
    txt(s, w, { x: 6.6, y, w: 5.9, h: 0.45, fontSize: 17, color: C.background1, valign: 'middle', objectName: 'Explore item ' + (i + 1) });
  });
  s.addNotes(NOTES[10]);

  // ======================================================= 11. FAN VALUE (CONCEPT)
  s = content('Making every moment of cricket more meaningful', 'THE POTENTIAL VALUE FOR FANS', 'Collaboration');
  card(s, 0.6, 1.95, 5.6, 1.55, 'Concept statement card', { fill: C.accent6, line: C.accent6 });
  txt(s, 'A fan should be able to see how each fielding event changes the expected outcome of the match.', { x: 0.88, y: 1.95, w: 5.1, h: 1.55, fontSize: 19, bold: true, color: C.background1, valign: 'middle', objectName: 'Concept statement' });
  const fanEx = [
    ['MdArrowUpward', C.accent3, 'Dropped catch', 'The batter survives, so the projection rises'],
    ['MdArrowUpward', C.accent3, 'Missed run-out', 'The batter survives, so the projection rises'],
    ['MdArrowDownward', C.accent2, 'Exceptional catch', 'A wicket falls, so the projection falls'],
    ['MdArrowDownward', C.accent2, 'Boundary save', 'Runs are saved, so the projection falls'],
  ];
  for (let i = 0; i < fanEx.length; i++) {
    const y = 3.68 + i * 0.73;
    card(s, 0.6, y, 5.6, 0.63, 'Example card ' + (i + 1));
    s.addShape(SH.OVAL, { x: 0.78, y: y + 0.12, w: 0.4, h: 0.4, fill: { color: C.text1 }, line: { color: fanEx[i][1], width: 1.25 }, objectName: 'Example arrow bg ' + (i + 1) });
    s.addImage({ data: await icon(ICON(fanEx[i][0]), fanEx[i][1] === C.accent3 ? HEX.mint : HEX.amber), x: 0.85, y: y + 0.19, w: 0.26, h: 0.26, altText: i < 2 ? 'Up' : 'Down', objectName: 'Example arrow ' + (i + 1) });
    txt(s, fanEx[i][2], { x: 1.38, y: y + 0.05, w: 4.7, h: 0.28, fontSize: 15, bold: true, color: C.background1, objectName: 'Example name ' + (i + 1) });
    txt(s, fanEx[i][3], { x: 1.38, y: y + 0.33, w: 4.7, h: 0.26, fontSize: 13, color: C.background2, objectName: 'Example effect ' + (i + 1) });
  }
  card(s, 6.55, 1.95, 6.18, 4.65, 'Concept card');
  pill(s, 'CONCEPT  ·  ILLUSTRATIVE, NOT MODEL OUTPUT', 6.8, 2.15, 4.1, C.accent2, 'Concept status');
  txt(s, 'How a projection could move, event by event', { x: 6.8, y: 2.62, w: 5.7, h: 0.32, fontSize: 16, bold: true, color: C.background1, objectName: 'Concept title' });
  const K = 1.3, cpts = [[0, 0.95], [0.55, 0.95], [0.75, 0.55], [1.45, 0.57], [1.65, 0.2], [2.45, 0.22], [2.65, 0.85], [3.45, 0.87], [3.65, 1.3], [5.2, 1.32]].map((p) => [p[0], p[1] * K]);
  const CX0 = 6.95, CY0 = 3.4;
  s.addShape(SH.CUSTOM_GEOMETRY, { x: CX0, y: CY0, w: 5.2, h: 1.32 * K + 0.02, line: { color: C.accent1, width: 3 }, fill: { type: 'none' },
    points: cpts.map((p, i) => (i === 0 ? { x: p[0], y: p[1], moveTo: true } : { x: p[0], y: p[1] })), objectName: 'Concept projection line' });
  const cev = [[0.65, 0.75 * K, 'Dropped catch', C.accent3, 'belowright'], [1.55, 0.385 * K, 'Missed run-out', C.accent3, 'above'], [2.55, 0.535 * K, 'Exceptional catch', C.accent2, 'right'], [3.55, 1.085 * K, 'Boundary save', C.accent2, 'right']];
  cev.forEach((m, i) => {
    s.addShape(SH.OVAL, { x: CX0 + m[0] - 0.11, y: CY0 + m[1] - 0.11, w: 0.22, h: 0.22, fill: { color: m[3] }, line: { color: C.text2, width: 2 }, objectName: 'Concept event ' + (i + 1) });
    const mode = m[4];
    const lx = mode === 'above' ? CX0 + m[0] - 0.8 : CX0 + m[0] + (mode === 'right' ? 0.2 : 0.18);
    const ly = CY0 + m[1] + (mode === 'above' ? -0.6 : mode === 'right' ? -0.14 : 0.0);
    txt(s, m[2], { x: lx, y: ly, w: 1.7, h: 0.28, fontSize: 12.5, bold: true, color: C.background1, align: mode === 'above' ? 'center' : 'left', objectName: 'Concept event label ' + (i + 1) });
  });
  txt(s, 'Projected final score', { x: 6.8, y: 5.25, w: 2.6, h: 0.26, fontSize: 12, color: C.background2, objectName: 'Concept axis y' });
  txt(s, 'Match progress  →', { x: 10.2, y: 5.25, w: 2.3, h: 0.26, fontSize: 12, color: C.background2, align: 'right', objectName: 'Concept axis x' });
  txt(s, 'Each event moves the projection, and the fan can see why.', { x: 6.8, y: 5.7, w: 5.7, h: 0.6, fontSize: 15, color: C.background1, objectName: 'Concept caption' });
  footnote(s, 'Illustrative concept, not current model output and not an existing feature. Arrows show direction for the batting side\'s projected score, not size. No numbers are implied.');
  s.addNotes(NOTES[11]);

  // ======================================================= 12. NEXT STEPS
  s = content('Let\'s explore what\'s possible', 'COLLABORATION AND NEXT STEPS', 'Collaboration');
  const ns = [
    ['Understand what data exists', 'What fielding-event data exists, how it is structured and how far back it goes.'],
    ['Explore a small-scale arrangement', 'A limited data-sharing or research arrangement, starting with a sample.'],
    ['Test whether it improves predictions', 'Evaluate predictive performance on held-out matches, run and wicket error.'],
  ];
  ns.forEach((p, i) => {
    const x = 0.6 + i * 4.125;
    card(s, x, 1.95, 3.85, 3.1, 'Next step card ' + (i + 1));
    txt(s, String(i + 1), { x: x + 0.3, y: 2.1, w: 1.0, h: 0.95, fontSize: 56, bold: true, color: C.accent1, objectName: 'Next step number ' + (i + 1) });
    txt(s, p[0], { x: x + 0.3, y: 3.15, w: 3.3, h: 0.8, fontSize: 20, bold: true, color: C.background1, objectName: 'Next step title ' + (i + 1) });
    txt(s, p[1], { x: x + 0.3, y: 3.95, w: 3.3, h: 1.0, fontSize: 15, color: C.background2, objectName: 'Next step text ' + (i + 1) });
  });
  card(s, 0.6, 5.3, 12.13, 1.0, 'First step card', { fill: C.accent6, line: C.accent6 });
  txt(s, [
    { text: 'PROPOSED FIRST STEP', options: { fontSize: 12, bold: true, color: C.accent2, charSpacing: 2, breakLine: true, paraSpaceAfter: 5 } },
    { text: 'A sample dataset and its data dictionary, so we can both see what is possible before any larger commitment.', options: { fontSize: 18, color: C.background1 } },
  ], { x: 0.88, y: 5.3, w: 11.6, h: 1.0, valign: 'middle', objectName: 'First step text' });
  txt(s, 'These are points for discussion, not requests.', { x: 0.6, y: 6.45, w: 8, h: 0.3, fontSize: 14, color: C.background2, objectName: 'Discussion note' });
  s.addNotes(NOTES[12]);

  // ======================================================= 12. CLOSING
  pres.addSection({ title: 'Close' });
  s = pres.addSlide({ masterName: 'COVER', sectionTitle: 'Close' });
  s.addImage({ path: A('closing_art.png'), x: 0, y: 0, w: 7.0, h: 7.5, altText: 'Top-down illustration of a cricket field', objectName: 'Closing field art' });
  txt(s, 'CRICPREDICT', { x: 7.45, y: 1.0, w: 5.2, h: 0.3, fontSize: 13, bold: true, color: C.accent1, charSpacing: 4, objectName: 'Closing brand' });
  txt(s, 'Understand the game beyond the scoreboard', { x: 7.45, y: 1.45, w: 5.3, h: 2.1, fontSize: 38, bold: true, color: C.background1, fontFace: 'Cambria', objectName: 'Closing title' });
  txt(s, '\u201CI\u2019m interested in exploring how better cricket data can help us build better predictions and give fans a deeper understanding of the game.\u201D', { x: 7.45, y: 3.85, w: 5.2, h: 1.5, fontSize: 16, italic: true, color: C.background2, objectName: 'Closing statement' });
  txt(s, 'Thank you, Cricketviz team.', { x: 7.45, y: 5.55, w: 5.2, h: 0.45, fontSize: 22, bold: true, color: C.background1, objectName: 'Closing thanks' });
  txt(s, 'cricket-score-predictor.com', { x: 7.45, y: 6.2, w: 5.2, h: 0.35, fontSize: 18, bold: true, color: C.accent1, objectName: 'Closing URL' });
  s.addNotes(NOTES[13]);

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log('wrote', OUT);
})().catch((e) => { console.error(e); process.exit(1); });
