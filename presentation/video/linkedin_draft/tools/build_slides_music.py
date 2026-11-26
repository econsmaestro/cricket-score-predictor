#!/usr/bin/env python3
"""Build the 90-second slides-and-music LinkedIn cut (no voice, no face) from slides_music.json.
  python3 tools/build_slides_music.py [--out FILE] [--no-music]
Static slides, soft cross-fades, a thin progress bar along the bottom, and the original synthesised track under it."""
import argparse, json, pathlib, subprocess
R = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(R.parent / "CricPredict_LinkedIn_90s_Music.mp4")); ap.add_argument("--no-music", action="store_true"); a = ap.parse_args()
c = json.load(open(R / "slides_music.json")); W, H = c["size"]; FPS = c["fps"]; X = c["crossfade"]; sc = c["scenes"]
total = sum(s["dur"] for s in sc) - X * (len(sc) - 1)
cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
for s in sc: cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{s['dur'] + X:.3f}", "-i", str(R / "assets" / "scenes" / f"{s['art']}.png")]
cmd += ["-f", "lavfi", "-i", f"color=c=0x34C26B:s={W}x6:r={FPS}"]
if not a.no_music: cmd += ["-i", str(R / c["music"])]
f = "".join(f"[{i}:v]scale={W}:{H},setsar=1,fps={FPS},format=yuv420p[v{i}];" for i in range(len(sc)))
last = "[v0]"; t = 0.0
for i in range(1, len(sc)):
    t += sc[i - 1]["dur"]; off = t - X * i
    f += f"{last}[v{i}]xfade=transition=fade:duration={X}:offset={off:.3f}[x{i}];"; last = f"[x{i}]"
f += f"{last}[{len(sc)}:v]overlay=x='-{W}+{W}*t/{total:.2f}':y={H - 8}:eof_action=pass,fade=t=in:d=0.4,fade=t=out:st={total - 0.6:.2f}:d=0.6,format=yuv420p[v]"
if not a.no_music: f += f";[{len(sc) + 1}:a]loudnorm=I=-15:TP=-1.5:LRA=7,afade=t=in:d=0.3,afade=t=out:st={total - 1.6:.2f}:d=1.6[aout]"
cmd += ["-filter_complex", f, "-map", "[v]"] + ([] if a.no_music else ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]) + (["-an"] if a.no_music else [])
cmd += ["-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-movflags", "+faststart", a.out]
subprocess.run(cmd, check=True); print(f"wrote {a.out} ({total:.1f}s)")
