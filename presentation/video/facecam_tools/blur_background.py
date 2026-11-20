#!/usr/bin/env python3
"""Blur the background behind a speaker and apply a natural colour/audio grade.

  python3 blur_background.py INPUT.mp4 OUTPUT.mp4 [--blur 14]
Uses MediaPipe's selfie segmentation model (selfie.tflite, Apache-2.0) to separate the person from the background,
smooths the mask over time to avoid flicker, blurs only the background, then ffmpeg applies a light grade
(brightness, warmth, sharpen, denoise) and audio clean-up (noise reduction, compression, -16 LUFS).
No face reshaping, skin smoothing or generated imagery is applied."""
import argparse, subprocess, pathlib, cv2, numpy as np, mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision
ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("dst"); ap.add_argument("--blur", type=float, default=14)
a = ap.parse_args(); here = pathlib.Path(__file__).resolve().parent
seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
    base_options=mpt.BaseOptions(model_asset_path=str(here / "selfie.tflite")), running_mode=vision.RunningMode.IMAGE, output_confidence_masks=True, output_category_mask=False))
cap = cv2.VideoCapture(a.src); W = int(cap.get(3)); H = int(cap.get(4)); FPS = cap.get(5) or 30
vf = "hqdn3d=1.5:1.5:4:4,eq=brightness=0.035:contrast=1.07:saturation=1.08:gamma=1.06,colorbalance=rm=0.025:bm=-0.02:rh=0.015,unsharp=5:5:0.45:3:3:0.0,vignette=PI/8"
af = "highpass=f=80,afftdn=nr=12,acompressor=threshold=-24dB:ratio=3:attack=10:release=150,loudnorm=I=-16:TP=-1.5:LRA=9"
ff = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", a.src,
    "-map", "0:v", "-map", "1:a", "-vf", vf, "-af", af, "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", a.dst], stdin=subprocess.PIPE)
prev = None; n = 0
while True:
    ok, f = cap.read()
    if not ok: break
    m = seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(f, cv2.COLOR_BGR2RGB))).confidence_masks[0].numpy_view().astype(np.float32)
    m = np.clip((m - 0.3) / 0.4, 0, 1)
    prev = m if prev is None else 0.55 * m + 0.45 * prev          # temporal smoothing against flicker
    mm = cv2.GaussianBlur(prev, (0, 0), 3)[..., None]
    bg = cv2.GaussianBlur(f, (0, 0), a.blur)
    ff.stdin.write((f * mm + bg * (1 - mm)).astype(np.uint8).tobytes()); n += 1
ff.stdin.close(); ff.wait(); print("frames", n, "->", a.dst)
