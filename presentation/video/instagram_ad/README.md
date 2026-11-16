# CricPredict Instagram ad (Reel, 9:16, 1080x1920, ~31 s)

Output: `../CricPredict_Instagram_Ad_Draft.mp4` (H.264 High, 30 fps, AAC, original synthesised music at about -15 LUFS).
A separate piece from the LinkedIn drafts and `storyboard_preview_silent.mp4`; none of those were touched.

## Files
* `ad.html`: the whole edit. Every scene, text overlay and animation (timed in beats at 128 BPM, one beat = 0.46875 s). Edit text, order, timings here.
* `assets/ui/`: genuine CricPredict interface crops (cropped from your phone screenshots of the live site and from the product running locally).
* `assets/captures/`: element screenshots of the product used to make those crops.
* `assets/music_original.wav`: original track, synthesised by `tools/make_music.py` (no samples, no AI model, no third-party music).
* `tools/render_frames.js` (HTML to frames), `tools/build_ad.py` (frames + music to MP4), `tools/make_music.py`.
* `voiceover_script.md` and `captions.srt`: the lines to record and ready-made subtitles that match the video timing.

## Rebuild
```bash
node tools/render_frames.js frames 30 4        # needs Playwright/Chromium; Inter font
python3 tools/build_ad.py frames               # needs ffmpeg
python3 tools/build_ad.py frames --no-music    # silent, for adding Instagram's licensed music in the app
python3 tools/build_ad.py frames --voiceover vo.wav          # your voiceover; music ducks underneath
python3 tools/build_ad.py frames --facecam take.mp4 --face-start 12.0   # circular face-cam window over the call-to-action
```
Face camera: none is included and none is generated. By default the video has no face footage and no placeholder.

## Layout rules used
Reels UI covers roughly the top 220 px and bottom 420 px and the right-hand button column, so all text and numbers sit between y 250 and y 1500 and inside x 60-960. Headlines are 100-250 px, secondary text at least 32 px.

## What is real and what is a labelled sample
| On screen | Source |
|---|---|
| NZ v IND: 84/4 (17.0 overs) -> 199/7, range 170-228; 171/9 (37.3 overs) -> 183, range 162-204; finished 185 all out | Your screenshots of the live site, numbers verified by you |
| "Live & Upcoming" card (NZ v IND, Predict button) | Your phone screenshot of the live site |
| "Build your own match" form | Your phone screenshot of the live site (84/4 entered) |
| Third Umpire AI card | The site's Third Umpire AI page, header only |
| Wickets to fall (1 more), next over (5 runs), win probability (17%) | The product's own output on a **made-up** Men's ODI, entered locally. Labelled "SAMPLE SCENARIO · NOT A REAL MATCH" on screen |
| Fielding | Not featured. The "India fielding 92%" badge is visible in the real screenshots but is not called out or claimed as a feature |

## Before you post
* Check the Reels safe zones in the Instagram app preview and add the link as a link sticker or "link in bio"; the video only shows the URL.
* The music is original and royalty-free, but I could not listen to it. Play it once; swap for Instagram's licensed audio if you prefer (`--no-music`).
* "Wickets to fall" and "win probability" use a sample scenario; replace with live captures when a match is on if you want all-real footage.
