"""Builds every image asset of the Mary Celeste short (collage style).

    python3 projects/mary-celeste/build/build_assets.py
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PROJ))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "projects", "amelia-earhart", "build"))

from shortsfactory.collage import graphics as g  # noqa: E402
from shortsfactory.collage.sticker import sticker_file  # noqa: E402
from shortsfactory.collage.vmap import THEMES, VintageMap  # noqa: E402
import build_assets as AB  # noqa: E402  (glass_window helper)

CUT = os.path.join(PROJ, "assets", "cutouts")
AME = os.path.join(ROOT, "projects", "amelia-earhart", "assets", "cutouts")
OUT = os.path.join(HERE, "assets")

STICKERS = {
    "ship": (CUT, "A1_mary_celeste.png"),
    "briggs": (CUT, "A2_briggs.png"),
    "sarah": (CUT, "A3_sarah_sophia.png"),
    "gibraltar": (CUT, "A4_gibraltar.png"),
    "barrel": (CUT, "B1_fass.png"),
    "boat": (CUT, "B2_rettungsboot.png"),
    "sword": (CUT, "B3_schwert.png"),
    "suitcase": (CUT, "B4_koffer.png"),
    "logbook": (CUT, "B5_logbuch.png"),
    "coins": (CUT, "B6_geldsack.png"),
    "microscope": (CUT, "B7_mikroskop.png"),
    "bow": (CUT, "B8_bug.png"),
    "sextant": (AME, "B2_sextant.png"),
    "doctor": (AME, "B9_arzt.png"),
    "magnifier": (AME, "B11_lupe.png"),
    "cloud1": (AME, "B12_wolke1.png"),
    "cloud2": (AME, "B12b_wolke2.png"),
}

PLACES = {
    "new_york": (-74.0, 40.7),
    "azores": (-28.0, 38.6),
    "found": (-17.7, 38.3),       # ~400 miles east of the Azores
    "gibraltar": (-5.35, 36.14),
    "genoa": (8.93, 44.4),
}

MAP_LABELS = [
    dict(text="ATLANTISCHER OZEAN", lon=-45, lat=28, size=2.6, spacing=0.3),
    dict(text="NORDAMERIKA", lon=-95, lat=45, size=2.2, style="serif"),
    dict(text="EUROPA", lon=8, lat=50, size=2.2, style="serif"),
    dict(text="AFRIKA", lon=5, lat=18, size=2.4, style="serif"),
    dict(text="Azoren", lon=-28, lat=40.3, size=1.0, spacing=0.15),
]


def save(name, arr, meta, **extra):
    Image.fromarray(arr, "RGBA").save(os.path.join(OUT, name + ".png"))
    meta[name] = dict(w=arr.shape[1], h=arr.shape[0], **extra)


def main():
    os.makedirs(OUT, exist_ok=True)
    meta = {}
    for i, (name, (d, src)) in enumerate(STICKERS.items()):
        meta[f"st_{name}"] = sticker_file(os.path.join(d, src), os.path.join(OUT, f"st_{name}.png"), seed=i)
        print("sticker", name)
    AB.glass_window(os.path.join(OUT, "st_magnifier.png"), meta["st_magnifier"], (340, 420), 262)

    m = VintageMap(-110, 30, 72, -6, ppd=26)
    img = m.render(labels=MAP_LABELS, theme=THEMES["retro_teal"], folds=(3, 2),
                   roses=[(-50, 12, 4), (-20, 52, 3)])
    save("map", img, meta, proj=m.params(), places={k: list(m.xy(*v)) for k, v in PLACES.items()})
    print("map", img.shape)

    L = [("lbl_mary", "Mary", "black", 130), ("lbl_celeste", "Celeste", "orange", 130),
         ("lbl_niemand", "Niemand an Bord", "petrol", 100), ("lbl_1872", "Dezember 1872", "black", 110),
         ("lbl_6monate", "6 Monate Essen", "petrol", 95), ("lbl_newyork", "New York", "black", 110),
         ("lbl_7", "+ 7 Seeleute", "petrol", 95), ("lbl_faesser", "1.701 Fässer Alkohol", "orange", 95),
         ("lbl_4wochen", "4 Wochen später", "black", 100), ("lbl_deigratia", "Dei Gratia", "petrol", 110),
         ("lbl_azoren", "Azoren", "orange", 100), ("lbl_gibraltar", "Gibraltar", "black", 110),
         ("lbl_bergelohn", "Bergelohn", "orange", 110), ("lbl_keinblut", "Kein Blut", "petrol", 130),
         ("lbl_rost", "Rost?", "orange", 150), ("lbl_10", "10 Menschen", "black", 120)]
    for i, (n, t, c, s) in enumerate(L):
        save(n, g.label(t, c, s, seed=20 + i), meta)
    save("stamp_mord", g.stamp("MORD?", seed=3), meta)
    save("rust", g.halftone_burst(300, cell=11, color=(150, 70, 40), seed=5), meta)
    save("tape_x", g.tape_x(600, seed=3), meta)
    save("ocean_strip", g.ocean_strip(1300, 430, seed=4), meta)
    save("dot", g.dot_marker(26, "orange"), meta)
    save("page", g.page_overlay(), meta)
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=1)
    print("done ->", OUT)


if __name__ == "__main__":
    main()
