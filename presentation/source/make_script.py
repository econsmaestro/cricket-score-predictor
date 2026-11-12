"""Builds the presenter-script .docx from notes.js (run: node -e to dump script.json first; see README)."""
import json, subprocess, sys, os
from docx import Document
from docx.shared import Pt, RGBColor, Inches
here = os.path.dirname(os.path.abspath(__file__)); out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, '..', 'CricPredict_Presenter_Script.docx')
d = json.loads(subprocess.check_output(['node', '-e', "const N=require('./notes.js'); console.log(JSON.stringify({script:N.SCRIPT, qa:N.QA}))"], cwd=here))
doc = Document(); sec = doc.sections[0]; sec.left_margin = sec.right_margin = Inches(0.9); sec.top_margin = sec.bottom_margin = Inches(0.8)
st = doc.styles['Normal']; st.font.name = 'Calibri'; st.font.size = Pt(11)
for lvl, sz in (('Heading 1', 20), ('Heading 2', 13)):
    h = doc.styles[lvl]; h.font.name = 'Cambria'; h.font.size = Pt(sz); h.font.bold = True; h.font.color.rgb = RGBColor(0x14, 0x5A, 0x32)
doc.add_heading('CricPredict: presenter script', 1)
p = doc.add_paragraph('Live demonstration for the Cricketviz team  ·  about 20 minutes plus questions  ·  November 2026'); p.runs[0].font.color.rgb = RGBColor(0x55, 0x55, 0x55)
doc.add_heading('Run of show', 2)
t = doc.add_table(rows=1, cols=3); t.style = 'Light Grid Accent 1'
for i, h in enumerate(('Slide', 'Topic', 'Time')): t.rows[0].cells[i].text = h
for s in d['script']:
    r = t.add_row().cells; r[0].text = str(s['n']); r[1].text = s['title']; r[2].text = s['time']
doc.add_paragraph(); doc.add_heading('Before you start', 2)
for x in ["Open cricket-score-predictor.com in a browser tab and check it loads, including the Backtesting page. Confirm the Backtesting page shows the same numbers as slide 6 (women's T20 16.6, women's ODI 38.3); if not, the latest version has not been published yet.",
          "No live match may be available. Use the built-in sample scenario and a made-up chase for the live walkthrough, and say out loud that they are synthetic sample data, not a live or real match.",
          "Keep the PDF open as a backup in case the network fails during the demo (slide 4 has screenshots).",
          "The deck separates what is live today (green) from proposed research (amber). Keep that line clear out loud."]:
    doc.add_paragraph(x, style='List Bullet')
for s in d['script']:
    doc.add_heading(f"Slide {s['n']}  ·  {s['title']}  ({s['time']})", 2)
    for pt in s['points']: doc.add_paragraph(pt, style='List Bullet')
doc.add_heading('Numbers to have at hand', 2)
t = doc.add_table(rows=1, cols=3); t.style = 'Light Grid Accent 1'
for i, h in enumerate(('Format', 'Score MAE (runs)', 'Range hit rate')): t.rows[0].cells[i].text = h
for a, b, c in (("Women's T20I", "16.6", "56.0%"), ("Men's T20I", "21.1", "51.6%"), ("Women's ODI", "38.3", "51.7%"), ("Men's ODI", "41.5", "46.8%")):
    r = t.add_row().cells; r[0].text = a; r[1].text = b; r[2].text = c
p = doc.add_paragraph("Source: data/backtests/*.json in the CricPredict repository, run of 11 November 2026 (women's fixtures now use the women's fielding rating keys; before that fix the women's figures were 16.2 and 37.2). 100 first innings per format, 1,800 checkpoint predictions in total. Historical replay of the current model; not an out-of-time holdout. Fielding rating tests (slide 8): real-model replay, pooled run MAE 28.2 at today's strength against 27.3 with the fielding effect off (docs/fielding-strength-replay.md); rank correlations with Cricsheet team outcomes +0.3 to +0.7 for catches and wickets per innings (docs/fielding-rating-audit.md)."); p.runs[0].font.size = Pt(10)
doc.add_heading('Likely questions', 2)
for q, a in d['qa']:
    p = doc.add_paragraph(); r = p.add_run(q); r.bold = True; doc.add_paragraph(a)
doc.save(out); print('script ->', out)
