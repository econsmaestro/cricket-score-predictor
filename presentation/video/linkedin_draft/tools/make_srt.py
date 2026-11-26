#!/usr/bin/env python3
"""Write an .srt for the talking-head cut. Subtitles are an OPTIONAL separate file; nothing is burned into the video.

  python3 tools/make_srt.py TIMELINE.json OUT.srt     # TIMELINE.json = {"01_open": seconds, ...} written by build_talking.py
Optional hard-burned copy:  ffmpeg -i cut.mp4 -vf "subtitles=OUT.srt:force_style='FontName=Inter,FontSize=18,Outline=2,MarginV=380'" burned.mp4"""
import json, re, sys, pathlib
R = pathlib.Path(__file__).resolve().parent.parent
tl = json.load(open(sys.argv[1])); cap = json.load(open(R / "captions_v4.json")); out = sys.argv[2]
def split(text, limit=84):
    sents = re.split(r"(?<=[.!?:])\s+", text.strip()); cues = []; cur = ""
    for s in sents:
        if cur and len(cur) + len(s) + 1 > limit: cues.append(cur); cur = s
        else: cur = (cur + " " + s).strip()
    if cur: cues.append(cur)
    return cues
def wrap(t, w=44):
    words = t.split(); lines = []; cur = ""
    for x in words:
        if cur and len(cur) + len(x) + 1 > w: lines.append(cur); cur = x
        else: cur = (cur + " " + x).strip()
    lines.append(cur); return "\n".join(lines)
def ts(x): h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60; return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")
t0 = 0.0; n = 1; res = []
for bid, dur in tl.items():
    cues = split(cap.get(bid, "")); tot = sum(len(c) for c in cues) or 1; a = t0 + 0.15; span = dur - 0.3
    for c in cues:
        d = span * len(c) / tot; res.append(f"{n}\n{ts(a)} --> {ts(a + d - 0.05)}\n{wrap(c)}\n"); n += 1; a += d
    t0 += dur
open(out, "w").write("\n".join(res)); print("wrote", out, n - 1, "cues")
