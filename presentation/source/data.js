// Single source of truth: the committed backtest reports in the repo (generated 2026-11-09).
const fs = require('fs');
const dir = require('path').join(__dirname, '..', '..', 'data', 'backtests') + '/';
const load = (f) => JSON.parse(fs.readFileSync(dir + f + '.json', 'utf8'));
const r = (x) => Math.round(x * 10) / 10;
const fm = { mens_t20: "Men's T20I", womens_t20: "Women's T20I", mens_odi: "Men's ODI", womens_odi: "Women's ODI" };
const raw = {}; Object.keys(fm).forEach((k) => { raw[k] = load(k); });
const formats = ['womens_t20', 'mens_t20', 'womens_odi', 'mens_odi'].map((k) => ({
  key: k, label: fm[k], mae: raw[k].metrics.overall.mae, t20: k.endsWith('t20'), n: raw[k].prediction_count, matches: raw[k].match_count,
  hit: raw[k].metrics.overall.hit_rate,
}));
const cp = {};
['mens_odi', 'womens_odi'].forEach((k) => {
  const b = raw[k].metrics.by_checkpoint; cp[k] = ['10', '20', '30', '40'].map((c) => r(b[c].mae));
});
module.exports = { formats, cp, raw };
if (require.main === module) { console.log(JSON.stringify({ formats, cp }, null, 1)); }
