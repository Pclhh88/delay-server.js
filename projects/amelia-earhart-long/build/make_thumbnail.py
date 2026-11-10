"""YouTube thumbnail (1280x720) in the video's collage style, from the built assets."""
import os, sys
import numpy as np
from PIL import Image, ImageFilter
from shortsfactory.collage.graphics import label

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "..", "output", "thumbnail.png")
W, H = 1280, 720


def load(n):
    return Image.open(os.path.join(A, n + ".png")).convert("RGBA")


def put(canvas, im, cx, cy, width=None, height=None, rot=0.0):
    if width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    elif height:
        im = im.resize((round(im.width * height / im.height), height), Image.LANCZOS)
    if rot:
        im = im.rotate(rot, Image.BICUBIC, expand=True)
    canvas.alpha_composite(im, (round(cx - im.width / 2), round(cy - im.height / 2)))


# background: ocean paper of the zoom tile (map lines + grain), slightly darkened at the edges
bg = load("tile_n1").convert("RGB")
bw = bg.width // 2
bg = bg.crop((0, 0, bw, round(bw * H / W))).resize((W, H), Image.LANCZOS)
yy, xx = np.mgrid[0:H, 0:W]
vig = 1 - 0.45 * (((xx - W * 0.6) / W) ** 2 + ((yy - H / 2) / H) ** 2)
canvas = Image.fromarray((np.asarray(bg, np.float32) * vig[..., None]).clip(0, 255).astype(np.uint8)).convert("RGBA")

# island glow so it pops against the ocean
isl = load("isl_nikumaroro")
put(canvas, isl, 850, 430, width=780, rot=12)
put(canvas, load("st_bones"), 870, 450, width=560, rot=-10)
put(canvas, load("st_crab"), 1150, 620, width=250, rot=8)
put(canvas, load("st_portrait"), 255, 410, height=640, rot=-3)

t1 = Image.fromarray(label("Nur 13 Knochen", "orange", size=150, seed=3))
put(canvas, t1, 870, 105, width=760, rot=2)
t2 = Image.fromarray(label("Wo ist sie?", "black", size=120, seed=5))
put(canvas, t2, 300, 655, width=430, rot=-3)

canvas.convert("RGB").save(OUT)
print("thumbnail ->", os.path.normpath(OUT))
