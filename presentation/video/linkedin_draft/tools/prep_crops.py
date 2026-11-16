"""Crop the phone screenshots (status bars, nav bars, floating dev button removed) into scene-ready images.
Input: the original phone screenshots (not stored in the repo). Output: assets/crops/*.png.
Coordinates are in a 923x2000 reference frame and scaled to the real image size."""
from PIL import Image
import sys, pathlib
SRC = pathlib.Path(sys.argv[1])        # folder holding the screenshots
OUT = pathlib.Path(__file__).resolve().parent.parent / "assets" / "crops"
JOBS = {
  # name: (file, x0, y0, x1, y1)
  "banner_84":  ("51167bcd-image.jpg",  18, 268, 884, 782),   # venue, fielding badge, 84/4 (17.0 overs)
  "score_199":  ("51167bcd-image.jpg",  20, 1050, 880, 1312), # Predicted final score 199/7, range
  "banner_171": ("0acc9b41-image.jpg",  28, 284, 894, 798),   # 171/9 (37.3 overs)
  "score_183":  ("0acc9b41-image.jpg",  30, 1076, 890, 1336), # 183/10, range
  "live_home":  ("559ca574-image.jpg",  20, 575, 905, 1262),  # Live & Upcoming: NZ vs IND, Predict
}
for name, (f, x0, y0, x1, y1) in JOBS.items():
    im = Image.open(SRC / f); s = im.size[1] / 2000
    im.crop((int(x0*s), int(y0*s), int(x1*s), int(y1*s))).save(OUT / f"{name}.png")
    print(name, "ok")
