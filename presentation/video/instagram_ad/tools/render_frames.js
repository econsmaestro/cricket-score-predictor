// Renders ad.html to numbered PNG frames. Usage: node tools/render_frames.js OUTDIR [fps=30] [workers=4]  |  node tools/render_frames.js --at OUTDIR t1 t2 ...
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
(async () => {
  const root = path.resolve(__dirname, '..'); const args = process.argv.slice(2);
  const test = args[0] === '--at'; if (test) args.shift();
  const out = args.shift(); fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch();
  const open = async () => { const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 }); await p.goto('file://' + path.join(root, 'ad.html')); await p.evaluate(() => window.ready()); await p.waitForTimeout(300); return p; };
  if (test) { const p = await open(); for (const t of args.map(Number)) { await p.evaluate(x => window.seek(x), t); await p.screenshot({ path: path.join(out, 't' + t.toFixed(2).replace('.', '_') + '.png') }); } await b.close(); return; }
  const fps = +(args[0] || 30), workers = +(args[1] || 4);
  const probe = await open(); const total = await probe.evaluate(() => window.TOTAL); await probe.close();
  const N = process.env.RANGE_TO ? +process.env.RANGE_TO : Math.round(total * fps) + 1; let next = process.env.RANGE_FROM ? +process.env.RANGE_FROM : 0;  // RANGE_FROM/RANGE_TO re-render part of the timeline
  const work = async () => { const p = await open(); for (;;) { const i = next++; if (i >= N) break; await p.evaluate(x => window.seek(x), i / fps); await p.screenshot({ path: path.join(out, 'f' + String(i).padStart(5, '0') + '.jpg'), type: 'jpeg', quality: 95 }); } await p.close(); };
  await Promise.all(Array.from({ length: workers }, work)); await b.close(); console.log('frames', N, 'total', total.toFixed(2) + 's');
})();
