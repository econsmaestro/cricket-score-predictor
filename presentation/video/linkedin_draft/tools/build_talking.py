#!/usr/bin/env python3
"""Build the 4:5 (1080x1350) talking-head LinkedIn cut from talking_cut.json.

  python3 tools/build_talking.py [--out FILE]
Per beat: cut the speaker clip at the listed times, drop pauses longer than `trim_pauses_over` (keeping `pad` seconds
each side so it still breathes), then either show the speaker full screen with the art as an overlay, or show the product scene
with a circular face window at bottom-right. Hard cuts between beats keep the speech in sync; a short fade opens and closes the video."""
import argparse, json, pathlib, re, subprocess, tempfile, shutil
R = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(R.parent / "CricPredict_LinkedIn_Talking_Cut.mp4")); a = ap.parse_args()
cfg = json.load(open(R / "talking_cut.json")); SRC = str((R / cfg["source"]).resolve()); W, H, FPS = 1080, 1350, 30
tmp = pathlib.Path(tempfile.mkdtemp(prefix="talk_")); base = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
def run(c): subprocess.run(c, check=True, stdout=subprocess.DEVNULL)
# silences in the speaker clip
out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", SRC, "-af", "silencedetect=n=-42dB:d=0.6", "-f", "null", "-"], capture_output=True, text=True).stderr
st = [float(x) for x in re.findall(r"silence_start: ([\d.e+-]+)", out)]; en = [float(x) for x in re.findall(r"silence_end: ([\d.e+-]+)", out)]
sil = [(s, e) for s, e in zip(st, en) if e - s >= cfg["trim_pauses_over"]]
pad = cfg["pad"]; fx = cfg["face_center_x"]; cx = int(1280 * fx)
segs = []; total = 0.0
for i, b in enumerate(cfg["beats"]):
    a0, b0 = b["src"]; parts = []; t = a0
    for s, e in sil:
        if s <= a0 or e >= b0: continue
        parts.append((t, s + pad)); t = e - pad
    parts.append((t, b0)); parts = [(x, y) for x, y in parts if y - x > 0.2]
    n = len(parts); f = ""; 
    for k, (x, y) in enumerate(parts):
        f += f"[0:v]trim={x:.3f}:{y:.3f},setpts=PTS-STARTPTS[v{k}];[0:a]atrim={x:.3f}:{y:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.03,afade=t=out:st={max(0, y - x - 0.03):.3f}:d=0.03[a{k}];"
    f += "".join(f"[v{k}][a{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[v][a]"
    clip = tmp / f"{b['id']}_src.mp4"
    run(base + ["-i", SRC, "-filter_complex", f, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "14", "-preset", "veryfast", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", str(clip)])
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(clip)], capture_output=True, text=True).stdout)
    art = R / "assets" / "scenes" / f"{b['art']}.png"; seg = tmp / f"{b['id']}.mp4"
    if b["type"] == "face":
        x0 = max(0, min(1280 - 576, cx - 288))
        fc = f"[0:v]crop=576:720:{x0}:0,scale={W}:{H}:flags=lanczos,format=yuv420p[bg];[1:v]scale={W}:{H}[ov];[bg][ov]overlay,format=yuv420p[v]"
        run(base + ["-i", str(clip), "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(art), "-filter_complex", fc, "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-t", f"{dur:.3f}", str(seg)])
    else:
        x0 = max(0, min(1280 - 720, cx - 360))
        zoom = f"scale=1620:2025,scale=w='trunc(1620*(1+0.04*t/{dur:.3f})/2)*2':h=-2:eval=frame,crop=1620:2025:(iw-1620)/2:(ih-2025)*0.40,scale={W}:{H}"
        fc = (f"[1:v]{zoom},fps={FPS}[z];[0:v]crop=720:720:{x0}:0,scale=250:250,format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lte(hypot(X-125,Y-125),125),255,0)'[fc];"
              f"[2:v]scale=250:250[r];[z][fc]overlay=790:1060[a1];[a1][r]overlay=790:1060,format=yuv420p[v]")
        run(base + ["-i", str(clip), "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(art), "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(R / "assets" / "placeholders" / "ring.png"),
                    "-filter_complex", fc, "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-t", f"{dur:.3f}", str(seg)])
    segs.append(seg); total += dur; print(f"{b['id']:<12} {dur:5.1f}s  ({n} cut{'s' if n > 1 else ''})")
lst = tmp / "list.txt"; lst.write_text("".join(f"file '{s}'\n" for s in segs))
run(base + ["-f", "concat", "-safe", "0", "-i", str(lst), "-vf", f"fade=t=in:d=0.4,fade=t=out:st={total - 0.5:.2f}:d=0.5,format=yuv420p", "-af", f"afade=t=in:d=0.2,afade=t=out:st={total - 0.4:.2f}:d=0.4",
            "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", a.out])
shutil.rmtree(tmp); print(f"wrote {a.out}  ({total:.1f}s)")
