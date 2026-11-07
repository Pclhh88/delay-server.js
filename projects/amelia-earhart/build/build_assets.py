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
    "bones": "B13_knochen.png",
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
HOWLAND = (-176.6168, 0.8047)        # island centroid (OpenStreetMap)
NIKUMARORO = (-174.5185, -4.6789)    # atoll centroid (OpenStreetMap)

MAP_LABELS = [
    dict(text="STILLER OZEAN", lon=200, lat=14, size=3.2, spacing=0.35),
    dict(text="AUSTRALIEN", lon=134, lat=-25, size=2.2, style="serif"),
    dict(text="NORDAMERIKA", lon=255, lat=45, size=2.2, style="serif"),
    dict(text="ASIEN", lon=105, lat=45, size=2.4, style="serif"),
    dict(text="SÜDAMERIKA", lon=297, lat=-15, size=2.0, style="serif"),
    dict(text="NORDAMERIKA", lon=-100, lat=45, size=2.2, style="serif"),
    dict(text="AFRIKA", lon=20, lat=5, size=2.4, style="serif"),
    dict(text="EUROPA", lon=15, lat=50, size=2.0, style="serif"),
    dict(text="ATLANTISCHER OZEAN", lon=-38, lat=28, size=2.2, spacing=0.3),
    dict(text="INDISCHER OZEAN", lon=78, lat=-22, size=2.4, spacing=0.3),
    dict(text="Äquator", lon=225, lat=1.2, size=1.1, spacing=0.15),
]


def chaikin(pts, n=3):
    pts = np.asarray(pts, np.float64)
    for _ in range(n):
        q = []
        for a, b in zip(pts, np.roll(pts, -1, 0)):
            q += [0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b]
        pts = np.array(q)
    return pts


def atoll(raw, rim=0.0034, passage=((-174.5405, -4.6655), 0.0017), k=40000):
    """Atoll from a coarse outline: outer shore = smoothed hull of the OSM points,
    lagoon = shore offset inwards by the land-rim width, plus one passage to the sea
    (Nikumaroro: Tatiman Passage on the west side).  Simplified, not survey-exact."""
    import cv2
    pts = np.asarray(raw, np.float64)
    hull = chaikin(cv2.convexHull(pts.astype(np.float32)).reshape(-1, 2).astype(np.float64), 3)
    lon0, lat1 = hull[:, 0].min() - 0.01, hull[:, 1].max() + 0.01
    W = int((hull[:, 0].max() + 0.01 - lon0) * k)
    H = int((lat1 - hull[:, 1].min() + 0.01) * k)
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.round(np.c_[(hull[:, 0] - lon0) * k, (lat1 - hull[:, 1]) * k]).astype(np.int32)], 255)
    r = int(rim * k)
    lag = cv2.erode(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    cs, _ = cv2.findContours(lag, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cs, key=cv2.contourArea).reshape(-1, 2).astype(np.float64)
    lagoon = chaikin(np.c_[c[:, 0] / k + lon0, lat1 - c[:, 1] / k][::4], 2)
    # passage: thin channel from the lagoon centre-west to the given shore point
    (px, py), wdt = passage
    cx, cy = lagoon[:, 0].mean() - 0.006, lagoon[:, 1].mean() + 0.003
    d = np.array([px - cx, py - cy])
    n = np.array([-d[1], d[0]]) / np.linalg.norm(d) * wdt / 2
    ext = np.array([px, py]) + d / np.linalg.norm(d) * 0.005
    channel = np.array([[cx, cy] + n, ext + n, ext - n, [cx, cy] - n])
    return [hull, (lagoon, True), (channel, True)]


def load_islands():
    """Howland + Nikumaroro (positions/size/orientation from OpenStreetMap, ODbL).
    Returns {name: [rings]} – a ring may be (ring, True) for water inside the land."""
    gj = json.load(open(os.path.join(PROJ, "assets", "geo", "islands_osm.geojson"), encoding="utf-8"))
    out = {}
    for f in gj["features"]:
        ring = f["geometry"]["coordinates"][0][:-1]
        out[f["properties"]["name"]] = atoll(ring) if f["properties"]["name"] == "Nikumaroro" else [chaikin(ring, 3)]
    return out


# zoom tiles: (name, centre lon, centre lat, ppd, w, h) – all share the overview's style scale
TILES = [
    ("tile_mid", -175.5, -2.0, 120, 2400, 3600),
    ("tile_h1", HOWLAND[0], HOWLAND[1], 600, 1800, 2700),
    ("tile_h2", HOWLAND[0], HOWLAND[1], 3000, 1800, 2700),
    ("tile_h25", HOWLAND[0], HOWLAND[1], 6000, 1800, 2700),
    ("tile_h3", HOWLAND[0], HOWLAND[1], 15000, 1500, 2400),
    ("tile_n1", NIKUMARORO[0], NIKUMARORO[1], 600, 1800, 2700),
    ("tile_n2", NIKUMARORO[0], NIKUMARORO[1], 3000, 1800, 2700),
    ("tile_n3", NIKUMARORO[0], NIKUMARORO[1], 7500, 1500, 2400),
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

    # big map (camera background): once around the world (430° so the 1937 route
    # Oakland -> ... -> Lae -> Howland stays continuous), Pacific in the middle-right
    m = VintageMap(-155, 300, 72, -72, ppd=24)
    img = m.render(labels=MAP_LABELS, theme=THEMES["retro_teal"], folds=(6, 2),
                   roses=[(205, -20, 5), (152, 28, 3.5), (250, 15, 3), (-30, -25, 4), (65, 5, 3.5)])
    save("map_pacific", img, meta, proj=m.params(), howland=list(m.xy(*HOWLAND)),
         lae=list(m.xy(147.0, -6.7)), nikumaroro=list(m.xy(*NIKUMARORO)),
         route=[list(p) for p in m.route_xy(ROUTE_FLOWN + [HOWLAND])], route_lae_index=len(ROUTE_FLOWN) - 1)
    print("map_pacific", img.shape)

    # detail tiles (real island outlines), placed in overview-map pixels
    islands = load_islands()
    extra = [r for rings in islands.values() for r in rings]
    for name, lon, lat, ppd, tw, th in TILES:
        hw, hh = tw / 2 / ppd, th / 2 / ppd
        tm = VintageMap(lon - hw, lon + hw, lat + hh, lat - hh, ppd=ppd, style_ppd=40, extra_land=extra)
        timg = tm.render(theme=THEMES["retro_teal"], grid=15, folds=(1, 1), feather=0.14, seed=11)
        x0, y0 = m.xy(lon - hw, lat + hh)
        save(name, timg, meta, pos=[x0, y0], design_scale=m.ppd / ppd, ppd=ppd)
        print(name, timg.shape)

    save("lbl_amelia", g.label("Amelia", "black", 120, seed=1), meta)
    save("lbl_earhart", g.label("Earhart", "orange", 120, seed=2), meta)
    save("lbl_1937", g.label("1937", "black", 190, seed=3), meta)
    save("lbl_howland", g.label("Howland Island", "petrol", 105, seed=5), meta)
    save("lbl_2wochen", g.label("2 Wochen", "black", 130, seed=6), meta)
    save("lbl_kein_flugzeug", g.label("Kein Flugzeug", "black", 110, seed=7), meta)
    save("lbl_kein_wrack", g.label("Kein Wrack", "orange", 110, seed=8), meta)
    save("lbl_nichts", g.label("Nichts.", "petrol", 170, seed=9), meta)
    save("lbl_1940", g.label("1940", "black", 190, seed=10), meta)
    save("lbl_nikumaroro", g.label("Nikumaroro", "petrol", 100, seed=11), meta)
    save("lbl_2018", g.label("2018", "orange", 190, seed=12), meta)
    save("stamp_mann", g.stamp("MANN", seed=1), meta)
    save("lbl_25km", g.label("2,3 km", "petrol", 90, seed=13), meta)
    save("lbl_stiller", g.label("Stiller Ozean", "black", 110, seed=15), meta)
    save("lbl_4000km", g.label("4.000 km", "orange", 95, seed=14), meta)
    save("bone1", g.bone(520, seed=1), meta)
    save("bone2", g.bone(380, seed=2), meta)
    save("star", g.star(150), meta)
    save("tape_x", g.tape_x(700, seed=3), meta)
    save("ocean_strip", g.ocean_strip(1300, 430, seed=4), meta)
    save("scribble", g.scribble_note(seed=5), meta)
    save("smoke", g.halftone_burst(320, cell=17, seed=7), meta)
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
