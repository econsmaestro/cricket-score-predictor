# Deck source

Editable source for `presentation/CricPredict_Cricketviz.pptx`.

    cd presentation/source && npm install
    NODE_PATH=$PWD/node_modules node build.js ../CricPredict_Cricketviz.pptx
    soffice --headless --convert-to pdf --outdir .. ../CricPredict_Cricketviz.pptx   # PDF is rendered from the PPTX

* `build.js` slides, theme and layouts (pptxgenjs). `notes.js` speaker notes, script and Q&A.
* `data.js` reads `data/backtests/*.json`, so chart numbers always match the committed reports.
* `assets/` images (UI screenshots are crops of the app run locally with a synthetic sample scenario).
* Version 1 (before the Nov 12 refinement) is preserved in `../archive/v1-2026-11-12/`.
