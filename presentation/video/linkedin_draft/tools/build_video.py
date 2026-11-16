#!/usr/bin/env python3
"""Assemble the CricPredict LinkedIn draft (1080x1350, 4:5) from scene art + scenes.json.

  python3 tools/build_video.py                     # silent draft with clearly marked face-cam placeholders
  python3 tools/build_video.py --facecam take.mp4  # real footage replaces the placeholders
Options: --out FILE, --face-x 0.5 (horizontal face position in the footage, 0..1), --audio (use the footage's audio)
Face-camera footage is read on the same timeline as the video (scene start = footage time) unless a scene sets
"fc_start" (seconds into the footage) in scenes.json. No footage is ever generated: without --facecam you get placeholders.
"""
import argparse, json, pathlib, subprocess, tempfile, shutil, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--facecam"); ap.add_argument("--out", default=str(ROOT.parent / "CricPredict_LinkedIn_Updated_Draft.mp4"))
ap.add_argument("--face-x", type=float, default=0.5); ap.add_argument("--audio", action="store_true")
a = ap.parse_args()
cfg = json.load(open(ROOT / "scenes.json")); W, H = cfg["size"]; FPS = cfg["fps"]; XF = cfg["crossfade"]
P = cfg["pip"]; SC = ROOT / "assets" / "scenes"; PH = ROOT / "assets" / "placeholders"
tmp = pathlib.Path(tempfile.mkdtemp(prefix="cp_draft_"))
def run(cmd): subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
base = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
segs = []; jobs = []; t0 = 0.0
for i, s in enumerate(cfg["scenes"]):
    d = s["dur"] + (XF if i < len(cfg["scenes"]) - 1 else 0)   # extra frames so each fade has material
    out = tmp / f"seg{i:02d}.mp4"; fs = s.get("fc_start", t0)
    if s["type"] == "face":
        if a.facecam:
            cmd = base + ["-ss", str(fs), "-t", str(d), "-i", a.facecam, "-loop", "1", "-framerate", str(FPS), "-t", str(d), "-i", str(SC / f"{s['id']}.png"),
                "-filter_complex", f"[0:v]scale=-2:{H},crop={W}:{H}:(iw-{W})*{a.face_x}:0,fps={FPS}[bg];[1:v]scale={W}:{H}[ov];[bg][ov]overlay,format=yuv420p[v]"]
        else:
            cmd = base + ["-loop", "1", "-framerate", str(FPS), "-t", str(d), "-i", str(PH / "ph_full.png"), "-loop", "1", "-framerate", str(FPS), "-t", str(d), "-i", str(SC / f"{s['id']}.png"),
                "-filter_complex", f"[0:v]scale={W}:{H}[bg];[1:v]scale={W}:{H}[ov];[bg][ov]overlay,format=yuv420p[v]"]
    else:
        zoom = f"scale=1620:2025,scale=w='trunc(1620*(1+0.045*t/{d})/2)*2':h=-2:eval=frame,crop=1620:2025:(iw-1620)/2:(ih-2025)*0.40,scale={W}:{H},fps={FPS}"
        ins = ["-loop", "1", "-framerate", str(FPS), "-t", str(d), "-i", str(SC / f"{s['id']}.png")]
        if a.facecam:
            ins += ["-ss", str(fs), "-t", str(d), "-i", a.facecam]
            # circular crop of the footage (alpha mask drawn with geq)
            pip = (f"[1:v]crop=ih:ih:(iw-ih)*{a.face_x}:0,scale={P['size']}:{P['size']},format=rgba,"
                   f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lte(hypot(X-{P['size']}/2,Y-{P['size']}/2),{P['size']}/2),255,0)'[fc];")
            ins_extra = ["-loop", "1", "-framerate", str(FPS), "-t", str(d), "-i", str(PH / "ring.png")]
            cmd = base + ins + ins_extra + ["-filter_complex",
                f"[0:v]{zoom}[z];{pip}[z][fc]overlay={P['x']}:{P['y']}[a];[2:v]scale={P['size']}:{P['size']}[r];[a][r]overlay={P['x']}:{P['y']},format=yuv420p[v]"]
        else:
            cmd = base + ins + ["-loop", "1", "-framerate", str(FPS), "-t", str(d), "-i", str(PH / "ph_pip.png"), "-loop", "1", "-framerate", str(FPS), "-t", str(d), "-i", str(PH / "ring.png"),
                "-filter_complex", f"[0:v]{zoom}[z];[1:v]scale={P['size']}:{P['size']}[p];[2:v]scale={P['size']}:{P['size']}[r];[z][p]overlay={P['x']}:{P['y']}[a];[a][r]overlay={P['x']}:{P['y']},format=yuv420p[v]"]
    cmd += ["-map", "[v]", "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-r", str(FPS), str(out)]
    jobs.append(cmd); segs.append((out, s)); t0 += s["dur"]
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(4) as ex: list(ex.map(run, jobs))
# cross-fade chain
cmd = base[:]; [cmd.extend(["-i", str(p)]) for p, _ in segs]
chain = ""; last = "[0:v]"; cum = 0.0; xs = 0.0
for i in range(1, len(segs)):
    x = segs[i][1].get("xfade", XF); cum += segs[i-1][1]["dur"]; xs += x
    chain += f"{last}[{i}:v]xfade=transition=fade:duration={x}:offset={cum - xs:.3f}"
    last = f"[x{i}]"; chain += last + ";"
chain = chain.rstrip(";")
total = sum(s["dur"] for _, s in segs) - sum(s.get("xfade", XF) for _, s in segs[1:])
cmd += ["-filter_complex", chain, "-map", last]
if a.facecam and a.audio:
    cmd += ["-ss", "0", "-i", a.facecam, "-map", f"{len(segs)}:a", "-af", "highpass=f=80,afftdn=nr=12,loudnorm=I=-16:TP=-1.5:LRA=9", "-c:a", "aac", "-b:a", "128k", "-t", f"{total:.3f}"]
else:
    cmd += ["-an"]
cmd += ["-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out]
run(cmd); shutil.rmtree(tmp)
print(f"wrote {a.out}  (~{total:.1f}s, {W}x{H}, {'face-cam footage' if a.facecam else 'placeholders'})")
