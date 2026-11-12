const sharp = require('sharp'); const fs = require('fs'); const path = require('path');
const A = path.join(__dirname, 'assets');
const stripes = (x0, x1, w, y0, y1, op) => { let s = ''; for (let x = x0, i = 0; x < x1; x += w, i++) if (i % 2) s += `<rect x="${x}" y="${y0}" width="${w}" height="${y1 - y0}" fill="#fff" opacity="${op}"/>`; return s; };

// 1) cover / closing art: floodlit oval, partly cropped by the slide edge (7in x 7.5in region -> 700x750 viewBox)
const cover = (flip) => `
<svg xmlns="http://www.w3.org/2000/svg" width="2100" height="2250" viewBox="0 0 700 750">
  <defs>
    <radialGradient id="g" cx="45%" cy="48%" r="60%"><stop offset="0" stop-color="#23704a"/><stop offset="0.6" stop-color="#154530"/><stop offset="1" stop-color="#0c2419"/></radialGradient>
    <clipPath id="c"><ellipse cx="430" cy="385" rx="370" ry="335"/></clipPath>
    <radialGradient id="glow" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#E0A93B" stop-opacity="0.55"/><stop offset="1" stop-color="#E0A93B" stop-opacity="0"/></radialGradient>
  </defs>
  <g ${flip ? 'transform="translate(700,0) scale(-1,1)"' : ''}>
  <ellipse cx="430" cy="385" rx="392" ry="357" fill="#34C26B" opacity="0.07"/>
  <ellipse cx="430" cy="385" rx="370" ry="335" fill="url(#g)"/>
  <g clip-path="url(#c)">${stripes(60, 800, 46, 40, 740, 0.045)}</g>
  <ellipse cx="430" cy="385" rx="370" ry="335" fill="none" stroke="#34C26B" stroke-opacity="0.65" stroke-width="3"/>
  <ellipse cx="430" cy="385" rx="222" ry="200" fill="none" stroke="#fff" stroke-opacity="0.32" stroke-width="2" stroke-dasharray="9 9"/>
  <g transform="rotate(16 430 385)">
    <rect x="414" y="272" width="32" height="226" rx="3" fill="#cdbd91" opacity="0.92"/>
    <line x1="405" y1="296" x2="455" y2="296" stroke="#fff" stroke-width="1.6" opacity="0.85"/>
    <line x1="405" y1="474" x2="455" y2="474" stroke="#fff" stroke-width="1.6" opacity="0.85"/>
    <g fill="#f4efe0">${[-5,0,5].map(d => `<rect x="${430 + d - 1}" y="268" width="2" height="9" rx="1"/><rect x="${430 + d - 1}" y="493" width="2" height="9" rx="1"/>`).join('')}</g>
  </g>
  <g fill="#fff" stroke="#0e2a1d" stroke-width="2">${[[430, 520], [352, 556], [520, 560], [300, 430], [558, 440], [312, 285], [575, 300], [455, 168], [205, 395], [650, 395]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="8.5"/>`).join('')}</g>
  <path d="M452 470 C 520 400, 580 330, 640 262" fill="none" stroke="#E0A93B" stroke-width="3" stroke-dasharray="3 9" stroke-linecap="round" opacity="0.9"/>
  <circle cx="540" cy="372" r="46" fill="url(#glow)"/>
  <circle cx="540" cy="372" r="22" fill="none" stroke="#E0A93B" stroke-width="2" opacity="0.7"/>
  <circle cx="540" cy="372" r="10" fill="#E0A93B" stroke="#0e2a1d" stroke-width="2"/>
  </g>
</svg>`;
// 2) clean field base for the fielding slide (1000x1000, circle-ish)
const field = `
<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="2000" viewBox="0 0 1000 1000">
  <defs>
    <radialGradient id="g" cx="50%" cy="48%" r="62%"><stop offset="0" stop-color="#1f6444"/><stop offset="0.65" stop-color="#143f2d"/><stop offset="1" stop-color="#0d291d"/></radialGradient>
    <clipPath id="c"><ellipse cx="500" cy="500" rx="480" ry="460"/></clipPath>
  </defs>
  <ellipse cx="500" cy="500" rx="497" ry="477" fill="#34C26B" opacity="0.07"/>
  <ellipse cx="500" cy="500" rx="480" ry="460" fill="url(#g)"/>
  <g clip-path="url(#c)">${stripes(20, 980, 60, 20, 980, 0.04)}</g>
  <ellipse cx="500" cy="500" rx="480" ry="460" fill="none" stroke="#34C26B" stroke-opacity="0.7" stroke-width="4"/>
  <ellipse cx="500" cy="500" rx="215" ry="205" fill="none" stroke="#fff" stroke-opacity="0.34" stroke-width="2.5" stroke-dasharray="11 10"/>
  <rect x="485" y="420" width="30" height="160" rx="3" fill="#cdbd91" opacity="0.93"/>
  <line x1="472" y1="438" x2="528" y2="438" stroke="#fff" stroke-width="2" opacity="0.85"/>
  <line x1="472" y1="562" x2="528" y2="562" stroke="#fff" stroke-width="2" opacity="0.85"/>
  <g fill="#f4efe0">${[-6, 0, 6].map(d => `<rect x="${500 + d - 1.2}" y="413" width="2.4" height="10" rx="1"/><rect x="${500 + d - 1.2}" y="577" width="2.4" height="10" rx="1"/>`).join('')}</g>
  <g fill="#fff" stroke="#0d291d" stroke-width="2.5" opacity="0.95">${[[500, 612], [455, 640], [425, 668], [380, 590], [640, 520], [620, 400], [350, 400], [250, 520], [800, 380], [210, 700]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="11"/>`).join('')}</g>
</svg>`;
(async () => {
  await sharp(Buffer.from(cover(false))).png().toFile(path.join(A, 'cover_art.png'));
  await sharp(Buffer.from(cover(true))).png().toFile(path.join(A, 'closing_art.png'));
  await sharp(Buffer.from(field)).png().toFile(path.join(A, 'field_base.png'));
  console.log('art done');
})();
