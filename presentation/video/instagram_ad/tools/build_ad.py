#!/usr/bin/env python3
"""Encode the ad from rendered frames plus the original music.

  node tools/render_frames.js FRAMES_DIR 30 4          # 1) render frames from ad.html
  python3 tools/build_ad.py FRAMES_DIR                 # 2) visuals + music  -> ../CricPredict_Instagram_Ad_Draft.mp4
Options:
  --no-music              visuals only
  --music FILE            use your own track instead of assets/music_original.wav
  --voiceover FILE        a separate voiceover recording; music is ducked underneath it
  --facecam FILE          short real face-cam clip shown in a circular window over the call-to-action, with its own audio
  --face-start S          where in FILE the clip starts (seconds); --face-dur D its length; --face-at T when it appears in the ad
  --face-x X              horizontal face position in the footage, 0..1 (default 0.55)
Nothing is generated for the face camera: without --facecam the ad has no face footage."""
import argparse, pathlib, subprocess
R = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(); ap.add_argument("frames"); ap.add_argument("--out", default=str(R.parent / "CricPredict_Instagram_Ad_Draft.mp4"))
ap.add_argument("--no-music", action="store_true"); ap.add_argument("--music", default=str(R / "assets" / "music_original.wav"))
ap.add_argument("--voiceover"); ap.add_argument("--facecam"); ap.add_argument("--face-start", type=float, default=0.0)
ap.add_argument("--face-dur", type=float, default=2.2); ap.add_argument("--face-at", type=float, default=27.0); ap.add_argument("--face-x", type=float, default=0.55)
a = ap.parse_args(); FR = 30; DUR = 31.0
cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(FR), "-i", f"{a.frames}/f%05d.jpg"]
idx = 1; af = []; vf = "[0:v]format=yuv420p[v]"; vo = None
if a.facecam:
    cmd += ["-ss", str(a.face_start), "-t", str(a.face_dur), "-i", a.facecam]; fi = idx; idx += 1
    x0 = max(0, min(1280 - 500, int(1280 * a.face_x) - 250)); S = 170
    vf = (f"[{fi}:v]crop=500:500:{x0}:40,scale={S}:{S},format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lte(hypot(X-{S/2},Y-{S/2}),{S/2}),255,0)',setpts=PTS-STARTPTS+{a.face_at}/TB[fc];"
          f"[0:v][fc]overlay=60:1335:enable='between(t,{a.face_at},{a.face_at + a.face_dur})',format=yuv420p[v]")
    vo = f"[{fi}:a]highpass=f=80,loudnorm=I=-16:TP=-1.5,adelay={int(a.face_at * 1000)}|{int(a.face_at * 1000)}[vo]"
if a.voiceover:
    cmd += ["-i", a.voiceover]; vi = idx; idx += 1; vo = f"[{vi}:a]highpass=f=80,loudnorm=I=-16:TP=-1.5[vo]"
if not a.no_music:
    cmd += ["-i", a.music]; mi = idx; idx += 1
    music = f"[{mi}:a]loudnorm=I=-15:TP=-1.5:LRA=7,afade=t=in:d=0.2,afade=t=out:st={DUR-1.3}:d=1.3"
    if vo: af = [vo, f"{music},volume=0.6[m]", "[vo]asplit=2[vo1][vo2]", "[m][vo1]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[md]", "[md][vo2]amix=inputs=2:duration=longest:normalize=0[aout]"]
    else: af = [f"{music}[aout]"]
elif vo:
    af = [vo, "[vo]apad[aout]"]
fc = ";".join([vf] + af)
cmd += ["-filter_complex", fc, "-map", "[v]"] + (["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"] if af else ["-an"])
cmd += ["-t", str(DUR), "-r", str(FR), "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart", a.out]
subprocess.run(cmd, check=True); print("wrote", a.out)
