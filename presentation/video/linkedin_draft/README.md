# CricPredict LinkedIn draft (4:5, 1080x1350)

Updated, mobile-first version of the silent storyboard. The original `../storyboard_preview_silent.mp4` is untouched.

## Files
* `scenes.html`: every scene as editable HTML/CSS (same palette and fonts as the original frames).
* `scenes.json`: scene order, durations, cross-fade length, face-camera picture-in-picture position.
* `assets/crops/`: crops of the phone screenshots (status bars, nav bars, floating dev button removed).
* `assets/scenes/`, `assets/placeholders/`: rendered 2160x2700 scene art and the face-camera placeholders.
* `tools/prep_crops.py` (crops), `tools/render_scenes.js` (HTML to PNG), `tools/build_video.py` (PNG to MP4).
* `facecam_layout_guide.png`: where your face goes in each scene.

## Rebuild
```bash
node tools/render_scenes.js                 # after editing scenes.html
python3 tools/build_video.py                # silent draft with placeholders
python3 tools/build_video.py --facecam take.mp4 --face-x 0.5 --audio   # with your footage and its audio
```
Needs ffmpeg and Playwright (Chromium). Fonts: Carlito and Caladea.

## Face camera
* Scenes `s01_open` and `s08_cta` are full-screen face camera with text overlaid. All other scenes are the product with a 250 px circular face-cam window at bottom-right (x 790, y 1060), which never covers screenshots or statistics.
* The build uses footage on the same timeline as the video (scene start = footage time). Set `fc_start` on a scene in `scenes.json` to pick a different point in the footage, or edit the scene durations to match your speech.
* Record at 1080p or better in landscape, face centred, head and shoulders. The 4:5 crop uses only the middle 45% of a 16:9 frame, so 720p footage will look soft. Phone vertical (4:5 or 9:16) works too.
* Do not add captions in the lower-left text zone; it already carries the one-line takeaway. Auto-captions from your editor can go just above the face-cam circle or replace the takeaway text.

## What stays fixed (accuracy)
Numbers are unchanged from the deck, the backtest report and your two prediction screenshots: 16.6 / 21.1 / 38.3 / 41.5 MAE, Men's ODI report metrics 46.8%, 3.11, −2.98, 199/7 (170–228), 183 (162–204), 185 all out. Fielding research is labelled "Not in production" and "Proposed research"; live predictions use only the hand-assigned team rating.
