// Renders each <section> in scenes.html to assets/scenes/*.png at 2x (2160x2700 for scenes). Run: node tools/render_scenes.js
const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const root = path.resolve(__dirname, '..');
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1400 }, deviceScaleFactor: 2 });
  await p.goto('file://' + path.join(root, 'scenes.html')); await p.evaluate(() => document.fonts.ready);
  const ids = await p.$$eval('section.scene', els => els.map(e => e.id));
  for (const id of ids) {
    const dir = id.startsWith('ph_') || id === 'ring' ? 'placeholders' : 'scenes';
    await p.locator('#' + id).screenshot({ path: path.join(root, 'assets', dir, id + '.png'), omitBackground: true });
  }
  await b.close(); console.log('rendered', ids.length);
})();
