const sharp = require('sharp'); const fs = require('fs'); const path = require('path');
const S = process.env.SHOTS_DIR || path.join(__dirname, '..', 'shots'); const A = path.join(__dirname, 'assets');

// rounded, softly bordered screenshot crop
async function shot(src, name, left, top, width, height, outW, radius = 28) {
  const scale = outW / width; const outH = Math.round(height * scale);
  const base = await sharp(path.join(S, src)).extract({ left, top, width, height }).resize(outW, outH).png().toBuffer();
  const r = Math.round(radius * 2 * scale > 0 ? radius : radius);
  const mask = Buffer.from(`<svg width="${outW}" height="${outH}"><rect width="${outW}" height="${outH}" rx="${r}" ry="${r}" fill="#fff"/></svg>`);
  const border = Buffer.from(`<svg width="${outW}" height="${outH}"><rect x="1" y="1" width="${outW-2}" height="${outH-2}" rx="${r}" ry="${r}" fill="none" stroke="#2c3a33" stroke-width="2"/></svg>`);
  const out = await sharp(base).composite([{ input: mask, blend: 'dest-in' }, { input: border, blend: 'over' }]).png().toBuffer();
  fs.writeFileSync(path.join(A, name), out); console.log(name, outW, outH, (outW / outH).toFixed(2));
}
(async () => {
  // Slide 4 (v2): first-innings sample scenario and a synthetic chase, both from the app run locally
  await shot('demo_full.png', 'ui_pred_a.png', 440, 290, 2000, 1740, 1500);
  await shot('chase_full.png', 'ui_pred_b.png', 440, 320, 2000, 1740, 1500);
  await shot('demo_full.png', 'ui_prediction.png', 440, 290, 2000, 1500, 1600);
  await shot('backtest_full.png', 'ui_backtest.png', 130, 1990, 2620, 655, 1800);
  await shot('home_full.png', 'ui_input.png', 140, 860, 2600, 1085, 1800);
  await shot('home.png', 'ui_home_top.png', 0, 0, 2880, 1800, 1800);
  const fade = Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="260"><defs><linearGradient id="f" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0B0F0D" stop-opacity="0"/><stop offset="0.85" stop-color="#0B0F0D" stop-opacity="1"/></linearGradient></defs><rect width="1600" height="260" fill="url(#f)"/></svg>');
  await sharp(fade).png().toFile(path.join(A, 'fade.png'));
})();
