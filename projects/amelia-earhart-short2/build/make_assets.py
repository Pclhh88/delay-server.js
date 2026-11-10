"""Assets of the teaser Short: everything from the long version (linked), plus a few new labels
and a 9:16 page overlay.   python3 projects/amelia-earhart-short2/build/make_assets.py"""
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(PROJ)))
from shortsfactory.collage import graphics as g  # noqa

LONG = os.path.join(os.path.dirname(PROJ), "amelia-earhart-long")
SRC = os.path.join(LONG, "build", "assets")
OUT = os.path.join(HERE, "assets")
os.makedirs(OUT, exist_ok=True)

LABELS = [("lbl_3jahre", "3 Jahre später", "black", 110), ("lbl_fall", "Fall erledigt", "black", 120),
          ("lbl_wasdas", "Was ist das?", "orange", 140), ("lbl_wo", "Wo ist sie?", "orange", 160),
          ("lbl_video", "Ganzes Video", "black", 130), ("lbl_kanal", "auf meinem Kanal", "petrol", 110),
          ("lbl_3theorien", "+ 3 weitere Theorien", "petrol", 100)]

meta = json.load(open(os.path.join(SRC, "meta.json")))
own = {n for n, *_ in LABELS} | {"page"}
for f in os.listdir(SRC):
    if f.endswith(".png") and f[:-4] not in own and not f.endswith("_orig.png"):
        dst = os.path.join(OUT, f)
        if not os.path.lexists(dst):
            os.symlink(os.path.join(SRC, f), dst)


def save(name, arr):
    Image.fromarray(arr, "RGBA").save(os.path.join(OUT, name + ".png"))
    meta[name] = dict(w=arr.shape[1], h=arr.shape[0])


for i, (n, t, c, s) in enumerate(LABELS):
    save(n, g.label(t, c, s, seed=500 + i))
save("page", g.page_overlay(1080, 1920, seed=5))
json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=1)
print("assets ->", OUT)
