#!/usr/bin/env python3
"""Encode the ad from rendered frames plus the original music.

  node tools/render_frames.js FRAMES_DIR 30 4          # 1) render frames from ad.html
  python3 tools/build_ad.py FRAMES_DIR                 # 2) silent visuals + music  -> ../CricPredict_Instagram_Ad_Draft.mp4
Options:
  --no-music              visuals only
  --music FILE            use your own track instead of assets/music_original.wav
  --voiceover FILE        your recorded voiceover; music is ducked underneath it
  --facecam FILE          circular face-cam window over the call-to-action (last 4.5 s); read from footage time --face-start (s)
Nothing is generated for the face camera: without --facecam the draft has no face footage at all."""
import argparse, pathlib, subprocess
R = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(); ap.add_argument("frames"); ap.add_argument("--out", default=str(R.parent / "CricPredict_Instagram_Ad_Draft.mp4"))
ap.add_argument("--no-music", action="store_true"); ap.add_argument("--music", default=str(R / "assets" / "music_original.wav"))
ap.add_argument("--voiceover"); ap.add_argument("--facecam"); ap.add_argument("--face-start", type=float, default=0.0)
a = ap.parse_args(); FR = 30; DUR = 31.0; CTA = 55 * 0.46875
cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(FR), "-i", f"{a.frames}/f%05d.jpg"]
idx = 1; af = []; vf = "[0:v]format=yuv420p[v]"
if a.facecam:
    cmd += ["-ss", str(a.face_start), "-t", str(DUR - CTA), "-i", a.facecam]; fi = idx; idx += 1
    vf = (f"[{fi}:v]crop=ih:ih:(iw-ih)/2:0,scale=170:170,format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lte(hypot(X-85,Y-85),85),255,0)',setpts=PTS+{CTA}/TB[fc];"
          f"[0:v][fc]overlay=60:1335:enable='gte(t,{CTA})',format=yuv420p[v]")
if not a.no_music:
    cmd += ["-i", a.music]; mi = idx; idx += 1
    music = f"[{mi}:a]loudnorm=I=-15:TP=-1.5:LRA=7,afade=t=in:d=0.2,afade=t=out:st={DUR-1.3}:d=1.3"
    if a.voiceover:
        cmd += ["-i", a.voiceover]; vi = idx; idx += 1
        af = [f"{music},volume=0.6[m]", f"[{vi}:a]highpass=f=80,loudnorm=I=-16:TP=-1.5[vo]", "[m][vo]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[md]", "[md][vo]amix=inputs=2:duration=longest:normalize=0[aout]"]
    else:
        af = [f"{music}[aout]"]
fc = ";".join([vf] + af)
cmd += ["-filter_complex", fc, "-map", "[v]"] + (["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"] if af else ["-an"])
cmd += ["-t", str(DUR), "-r", str(FR), "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart", a.out]
subprocess.run(cmd, check=True); print("wrote", a.out)
