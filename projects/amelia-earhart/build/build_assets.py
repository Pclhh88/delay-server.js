"""Builds every image asset of the Amelia Earhart short (collage style).

    python3 projects/amelia-earhart/build/build_assets.py

Inputs : assets/cutouts/*.png (user-supplied B/W cutouts), Natural Earth land.
Outputs: build/assets/*.png + build/assets/meta.json (anchors, sizes, map
projection, route points).  Generated files are not committed.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(PROJ)))

from shortsfactory.collage import graphics as g  # noqa: E402
from shortsfactory.collage.sticker import sticker_file  # noqa: E402
from shortsfactory.collage.vmap import THEMES, VintageMap  # noqa: E402

CUT = os.path.join(PROJ, "assets", "cutouts")
OUT = os.path.join(HERE, "assets")

STICKERS = {
    "portrait": "A1_earhart_portrait.png",
    "portrait2": "A1b_earhart_portrait2.png",
    "electra": "A2_electra.png",
    "itasca": "A3_itasca.png",
    "lexington": "A4_lexington.png",
    "colorado": "A5_colorado.png",
    "radio": "B1_funkgeraet.png",
    "sextant": "B2_sextant.png",
    "box_full": "B3_sextantkiste.png",
    "box_empty": "B3b_sextantkiste_leer.png",
    "shoe": "B4_frauenschuh.png",
    "compass": "B5_kompass.png",
    "watch": "B6_taschenuhr.png",
    "pancake": "B7_pfannkuchen.png",
    "phone": "B8_handy.png",
    "doctor": "B9_arzt.png",
    "folder": "B10_akte.png",
    "folder_open": "B10b_akte_offen.png",
    "magnifier": "B11_lupe.png",
    "cloud1": "B12_wolke1.png",
    "cloud2": "B12b_wolke2.png",
}

# 1937 world flight, eastbound (lon, lat)
ROUTE_FLOWN = [
    (-122.2, 37.7),   # Oakland
    (-80.3, 25.8),    # Miami
    (-66.0, 18.4),    # San Juan
    (-63.1, 10.1),    # Caripito
    (-55.2, 5.8),     # Paramaribo
    (-35.2, -5.8),    # Natal
    (-16.5, 16.0),    # Saint-Louis
    (-0.05, 16.3),    # Gao
    (15.0, 12.1),     # Fort Lamy
    (32.5, 15.6),     # Khartoum
    (42.7, 13.0),     # Assab
    (67.0, 24.9),     # Karachi
    (88.4, 22.6),     # Calcutta
    (96.2, 16.8),     # Rangoon
    (100.5, 13.8),    # Bangkok
    (103.8, 1.3),     # Singapore
    (107.6, -6.9),    # Bandung
    (123.6, -10.2),   # Kupang
    (130.8, -12.5),   # Darwin
    (147.0, -6.7),    # Lae
]
ROUTE_PLANNED = [(147.0, -6.7), (-176.6, 0.8), (-157.9, 21.3), (-122.2, 37.7)]
HOWLAND = (-176.6, 0.8)

MAP_LABELS = [
    dict(text="STILLER OZEAN", lon=200, lat=14, size=3.2, spacing=0.35),
    dict(text="AUSTRALIEN", lon=134, lat=-25, size=2.2, style="serif"),
    dict(text="NORDAMERIKA", lon=255, lat=45, size=2.2, style="serif"),
    dict(text="ASIEN", lon=105, lat=45, size=2.4, style="serif"),
    dict(text="SÜDAMERIKA", lon=297, lat=-15, size=2.0, style="serif"),
    dict(text="Äquator", lon=225, lat=1.2, size=1.1, spacing=0.15),
]


def save(name, arr, meta, **extra):
    Image.fromarray(arr, "RGBA" if arr.shape[2] == 4 else "RGB").save(os.path.join(OUT, name + ".png"))
    meta[name] = dict(w=arr.shape[1], h=arr.shape[0], **extra)


def glass_window(path, info, centre, radius):
    """Make the magnifier glass see-through (keep a faint tint + highlight)."""
    import cv2
    im = np.asarray(Image.open(path).convert("RGBA")).copy()
    f0, ox, oy = info["src_map"]
    cx, cy, r = centre[0] * f0 + ox, centre[1] * f0 + oy, radius * f0
    yy, xx = np.mgrid[0:im.shape[0], 0:im.shape[1]]
    d = np.hypot(xx - cx, yy - cy)
    inside = np.clip((r - d) / 3, 0, 1)
    hl = np.exp(-(((xx - (cx - r * 0.35)) ** 2 + (yy - (cy - r * 0.4)) ** 2) / (2 * (r * 0.22) ** 2)))
    a = im[..., 3].astype(np.float32)
    a = a * (1 - inside) + inside * (25 + 90 * hl)
    im[..., :3] = np.where(inside[..., None] > 0.5, (235, 238, 232), im[..., :3])
    im[..., 3] = np.clip(a, 0, 255).astype(np.uint8)
    Image.fromarray(im, "RGBA").save(path)
    info["lens"] = [cx / im.shape[1], cy / im.shape[0]]


def main():
    os.makedirs(OUT, exist_ok=True)
    meta = {}
    for i, (name, src) in enumerate(STICKERS.items()):
        info = sticker_file(os.path.join(CUT, src), os.path.join(OUT, f"st_{name}.png"), seed=i)
        meta[f"st_{name}"] = info
        print("sticker", name, info["w"], info["h"])

    # big Pacific map (camera background)
    m = VintageMap(90, 300, 60, -50, ppd=24)
    img = m.render(labels=MAP_LABELS, theme=THEMES["retro_teal"],
                   roses=[(205, -20, 5), (152, 28, 3.5), (250, 15, 3)])
    save("map_pacific", img, meta, proj=m.params(), howland=list(m.xy(*HOWLAND)),
         lae=list(m.xy(147.0, -6.7)))
    print("map_pacific", img.shape)

    # world card: small landscape map on torn paper with the flown route
    wm = VintageMap(-140, 220, 72, -50, ppd=6)
    card = wm.render(grid=30, folds=(4, 2), theme=THEMES["retro_teal"], labels=[
        dict(text="1937", lon=-100, lat=-38, size=6, style="serif", alpha=150)])
    a = g.torn_mask(card.shape[1], card.shape[0], depth=10, seed=4, soft=1.2)
    card[..., 3] = (a * 255).astype(np.uint8)
    card = g.add_shadow(card, dx=8, dy=12, blur=10, op=0.45, pad=40)
    flown = [(x + 40, y + 40) for x, y in wm.route_xy(ROUTE_FLOWN)]
    planned = [(x + 40, y + 40) for x, y in wm.route_xy(ROUTE_PLANNED)]
    save("world_card", card, meta, route=flown, planned=planned, proj=wm.params(), pad=40)

    save("lbl_amelia", g.label("Amelia", "black", 120, seed=1), meta)
    save("lbl_earhart", g.label("Earhart", "orange", 120, seed=2), meta)
    save("lbl_1937", g.label("1937", "black", 190, seed=3), meta)
    save("lbl_howland", g.label("Howland Island", "petrol", 105, seed=5), meta)
    save("burst_orange", g.halftone_burst(900, seed=1), meta)
    save("arc_orange", g.halftone_arc(600, width=0.22, span=110, cell=15), meta)
    glass_window(os.path.join(OUT, "st_magnifier.png"), meta["st_magnifier"], (340, 420), 262)
    save("newspaper", g.newspaper(headline="WOMAN FLIES\nATLANTIC ALONE", date="MAY 1932", seed=2), meta)
    save("dot", g.dot_marker(26, "orange"), meta)
    save("page", g.page_overlay(), meta)

    quote = "„Wir müssten über euch sein, aber wir sehen euch nicht. Das Benzin wird knapp.“"
    n = len(quote.split())
    for k in range(0, n + 1):
        save(f"quote_{k:02d}", g.typewriter_strip(quote, words_visible=k, seed=7), meta)
    meta["quote_words"] = n

    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=1)
    print("done ->", OUT)


if __name__ == "__main__":
    main()
