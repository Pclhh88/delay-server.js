"""Assets for the Bernsteinzimmer long video (16:9): Europe map with flag-filled countries,
'stage' look (dark newspaper collage, coloured paper shapes), stickers, labels, captions.

    python3 projects/bernsteinzimmer/build/build_assets.py [--only stickers|map|stage|labels]
"""
import argparse
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(PROJ)))
from shortsfactory.collage import PALETTE, font  # noqa: E402
from shortsfactory.collage import graphics as g  # noqa: E402
from shortsfactory.collage.sticker import make_sticker  # noqa: E402
from shortsfactory.collage.vmap import THEMES, VintageMap, fractal_noise  # noqa: E402

OUT = os.path.join(HERE, "assets")
CUT = os.path.join(PROJ, "assets", "cutouts")
GEO = os.path.join(PROJ, "assets", "geo")
BGS = os.path.join(PROJ, "assets", "backgrounds")
W, H = 1920, 1080

# map window and projection (equirectangular, x compressed by cos(57°) so Europe keeps its shape)
LON0, LON1, LAT1, LAT0, PPD, KX = -12.0, 50.0, 71.0, 43.0, 110, 0.56

PLACES = {"berlin": (13.40, 52.52), "st_petersburg": (30.31, 59.94), "zarskoje": (30.40, 59.72),
          "koenigsberg": (20.51, 54.71), "stockholm": (18.07, 59.33), "moskau": (37.62, 55.75),
          "warschau": (21.01, 52.23), "dziemiany": (17.82, 54.00), "danzig": (18.65, 54.35)}
CITY_NAMES = {"berlin": "Berlin", "st_petersburg": "St. Petersburg", "zarskoje": "Zarskoje Selo",
              "koenigsberg": "Königsberg", "stockholm": "Stockholm", "moskau": "Moskau", "warschau": "Warschau",
              "dziemiany": "Dziemiany", "danzig": "Danzig"}


def map_xy(lon, lat):
    return ((lon - LON0) * PPD * KX, (LAT1 - lat) * PPD)


def save(meta, name, arr, **extra):
    Image.fromarray(arr, "RGBA" if arr.shape[2] == 4 else "RGB").save(os.path.join(OUT, name + ".png"))
    meta[name] = dict(w=arr.shape[1], h=arr.shape[0], **extra)


# ------------------------------------------------------------------ flags
def _stripes(w, h, cols, vertical=False):
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    n = len(cols)
    for i, c in enumerate(cols):
        if vertical:
            d.rectangle([w * i / n, 0, w * (i + 1) / n, h], fill=c)
        else:
            d.rectangle([0, h * i / n, w, h * (i + 1) / n], fill=c)
    return img


def _nordic(w, h, bg, cross, cross2=None):
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    t = min(w, h) * 0.16
    cx = w * 0.38
    if cross2:
        d.rectangle([0, h / 2 - t * 0.8, w, h / 2 + t * 0.8], fill=cross2)
        d.rectangle([cx - t * 0.8, 0, cx + t * 0.8, h], fill=cross2)
    d.rectangle([0, h / 2 - t / 2, w, h / 2 + t / 2], fill=cross)
    d.rectangle([cx - t / 2, 0, cx + t / 2, h], fill=cross)
    return img


def _star(d, cx, cy, r, fill):
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.42
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)


def flag(kind, w, h, star_at=None):
    red, white, blue = (178, 46, 40), (238, 232, 218), (40, 70, 140)
    if kind in ("prussia", "brandenburg"):          # Prussian black-white
        n = max(2, int(h / 60))
        return _stripes(w, h, [white, (34, 32, 30)] * (n // 2 + 1))
    if kind == "russia_old" or kind == "russia":     # white-blue-red (Peter the Great's tricolour)
        return _stripes(w, h, [white, blue, red])
    if kind == "sweden":
        return _nordic(w, h, (36, 86, 150), (236, 190, 40))
    if kind == "finland":
        return _nordic(w, h, white, (30, 70, 140))
    if kind == "denmark":
        return _nordic(w, h, red, white)
    if kind == "poland_lith":                          # red field, white band
        return _stripes(w, h, [red, white, red])
    if kind == "poland":
        return _stripes(w, h, [white, (196, 40, 50)])
    if kind == "germany":
        return _stripes(w, h, [(30, 30, 30), (200, 30, 30), (240, 196, 40)])
    if kind == "germany_ww2":                          # field grey + Balkenkreuz (Wehrmacht insignia)
        img = Image.new("RGB", (w, h), (112, 116, 104))
        d = ImageDraw.Draw(img)
        cx, cy, s = w / 2, h / 2, min(w, h) * 0.22
        for col, k in ((white, 1.0), ((24, 24, 24), 0.62)):
            a, b = s * k, s * k * 0.36
            d.rectangle([cx - a, cy - b, cx + a, cy + b], fill=col)
            d.rectangle([cx - b, cy - a, cx + b, cy + a], fill=col)
        return img
    if kind == "ussr":
        img = Image.new("RGB", (w, h), (176, 30, 30))
        sx, sy = star_at or (w * 0.25, h * 0.3)
        _star(ImageDraw.Draw(img), sx, sy, 150, (236, 190, 40))
        return img
    if kind == "lithuania":
        return _stripes(w, h, [(240, 190, 30), (20, 110, 60), (190, 40, 40)])
    if kind == "latvia":
        return _stripes(w, h, [(150, 30, 40), white, (150, 30, 40)])
    if kind == "estonia":
        return _stripes(w, h, [(40, 100, 180), (20, 20, 20), white])
    if kind == "belarus":
        return _stripes(w, h, [(190, 40, 40), (190, 40, 40), (40, 130, 60)])
    if kind == "ukraine":
        return _stripes(w, h, [(40, 100, 190), (240, 200, 40)])
    raise KeyError(kind)


FLAG_OF = {"1715": {"prussia": "prussia", "brandenburg": "brandenburg", "russia": "russia_old", "sweden": "sweden",
                    "poland": "poland_lith"},
           "1938": {"germany": "germany_ww2", "ussr": "ussr", "poland": "poland", "sweden": "sweden",
                    "finland": "finland", "lithuania": "lithuania", "latvia": "latvia", "estonia": "estonia",
                    "denmark": "denmark"},
           "2010": {"poland": "poland", "germany": "germany", "russia": "russia", "russia_k": "russia",
                    "lithuania": "lithuania", "sweden": "sweden", "denmark": "denmark", "belarus": "belarus",
                    "latvia": "latvia", "estonia": "estonia", "finland": "finland", "ukraine": "ukraine"}}


def country_masks(year, mw, mh):
    gj = json.load(open(os.path.join(GEO, f"countries_{year}.geojson")))
    masks, seen = {}, set()
    for f in gj["features"]:
        key, name = f["properties"]["key"], f["properties"]["NAME"]
        key = {"germany_ep": "germany", "ussr2": "ussr", "sweden_fin": "sweden", "russia2": "sweden"}.get(key, key)
        if (key, name) in seen:
            continue
        seen.add((key, name))
        m = masks.setdefault(key, np.zeros((mh, mw), np.uint8))
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            for i, ring in enumerate(poly):
                r = np.array(ring, np.float64)
                x = (r[:, 0] - LON0) * PPD * KX
                y = (LAT1 - r[:, 1]) * PPD
                cv2.fillPoly(m, [np.round(np.c_[x, y] * 4).astype(np.int32)], 0 if i else 255, cv2.LINE_AA, shift=2)
    if year == "1715":
        # by 1716 Russia held Ingria, Estonia and Livonia (St. Petersburg!) – the dataset still shows Sweden
        yy, xx = np.mgrid[0:mh, 0:mw]
        lon = xx / (PPD * KX) + LON0
        lat = LAT1 - yy / PPD
        moved = (masks["sweden"] > 0) & (lat < 60.35) & (lon > 21.5)
        masks["russia"] = np.maximum(masks["russia"], np.where(moved, masks["sweden"], 0)).astype(np.uint8)
        masks["sweden"][moved] = 0
    return masks


def build_map(meta):
    m = VintageMap(LON0, LON1, LAT1, LAT0, ppd=PPD)
    labels = [dict(text="OSTSEE", lon=19.0, lat=56.3, size=0.75, spacing=0.35),
              dict(text="NORDSEE", lon=3.5, lat=56.5, size=0.75, spacing=0.35)]
    img = m.render(labels=labels, theme=THEMES["retro_teal"], folds=(4, 2), roses=[(-6, 60, 3.0)], seed=7)
    land = m.land_mask()
    mw = int(round(m.W * KX))
    img = cv2.resize(img, (mw, m.H), interpolation=cv2.INTER_AREA)
    land = cv2.resize(land, (mw, m.H), interpolation=cv2.INTER_AREA)
    save(meta, "map_europe", img, proj=dict(lon0=LON0, lat1=LAT1, ppd=PPD, kx=KX, w=mw, h=m.H))
    print("map_europe", img.shape)
    rng = np.random.default_rng(3)
    paper = fractal_noise(m.H, mw, 21)
    for year, flags in FLAG_OF.items():
        masks = country_masks(year, mw, m.H)
        for key, kind in flags.items():
            if key not in masks:
                print("  missing", year, key)
                continue
            mk = (masks[key].astype(np.float32) / 255) * land          # only on land
            ys, xs = np.nonzero(mk > 0.05)
            if len(xs) == 0:
                continue
            pad = 12
            x0, x1 = max(0, xs.min() - pad), min(mw, xs.max() + pad)
            y0, y1 = max(0, ys.min() - pad), min(m.H, ys.max() + pad)
            a = mk[y0:y1, x0:x1]
            # cut-paper edge: slightly ragged, thin dark outline
            jag = cv2.GaussianBlur(rng.random(a.shape).astype(np.float32), (0, 0), 3)
            a2 = np.clip((cv2.GaussianBlur(a, (0, 0), 2.0) - 0.5 + 0.25 * (jag - 0.5)) * 6 + 0.5, 0, 1)
            edge = np.clip(a2 - cv2.erode(a2, np.ones((7, 7), np.uint8)), 0, 1)
            fw, fh = x1 - x0, y1 - y0
            mx, my = map_xy(36.0, 56.5)
            fl = np.asarray(flag(kind, fw, fh, star_at=(mx - x0, my - y0))).astype(np.float32) / 255
            pn = paper[y0:y1, x0:x1, None]
            fl = fl * (0.84 + 0.22 * pn)
            fl = fl * (1 - 0.55 * edge[..., None])
            out = np.dstack([np.clip(fl * 255, 0, 255), a2 * 255 * 0.8]).astype(np.uint8)
            save(meta, f"flag_{year}_{key}", out, pos=[int(x0), int(y0)])
        print("flags", year, list(flags))
    meta["places"] = {k: list(map_xy(*v)) for k, v in PLACES.items()}
    for k, name in CITY_NAMES.items():
        arr, anc = g.city_label(name, size=46)
        save(meta, f"city_{k}", arr, anchor=list(anc))
    save(meta, "dot", g.dot_marker(22))
    save(meta, "arc_orange", g.halftone_arc(600, width=0.22, span=110, cell=15))


# ------------------------------------------------------------------ stage look
def dark_collage(seed=0):
    r = np.random.default_rng(seed)
    base = Image.new("RGB", (W, H), (24, 24, 22))
    heads = ["DAS ZIMMER\nIST WEG", "SCHATZ\nGESUCHT", "KÖNIGSBERG\nBRENNT", "BERNSTEIN\nGEFUNDEN?"]
    sheets = [Image.fromarray(g.newspaper(900, 1200, headline=h, date="1945", seed=s)).convert("L")
              for s, h in enumerate(heads)]
    for i in range(90):
        sh = sheets[i % len(sheets)]
        w, h = int(r.uniform(150, 520)), int(r.uniform(120, 420))
        x0, y0 = int(r.uniform(0, sh.width - w)), int(r.uniform(0, sh.height - h))
        crop = np.asarray(sh.crop((x0, y0, x0 + w, y0 + h))).astype(np.float32)
        crop = cv2.GaussianBlur(crop, (0, 0), 0.8) * r.uniform(0.07, 0.17) + r.uniform(8, 20)
        rgb = np.dstack([crop, crop * 0.98, crop * 0.93]).clip(0, 255).astype(np.uint8)
        m = (g.torn_mask(w, h, depth=6, seed=int(r.integers(1e6))) * 255).astype(np.uint8)
        piece = Image.fromarray(np.dstack([rgb, m]), "RGBA").rotate(r.uniform(-25, 25), Image.BICUBIC, expand=True)
        base.paste(piece, (int(r.uniform(-150, W)), int(r.uniform(-150, H))), piece)
    a = np.asarray(base).astype(np.float32)
    a *= (1 + 0.15 * fractal_noise(H, W, seed)[..., None] - 0.07)
    yy, xx = np.mgrid[0:H, 0:W]
    a *= (1 - 0.35 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 2)[..., None]
    return a.clip(0, 255).astype(np.uint8)


def blob(size, seed, fill_rgb=None, texture=None, circle=False):
    """coloured paper shape (or photo-filled circle) with creases, cream rim and drop shadow"""
    S = size
    pad = int(S * 0.08)
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:S + 2 * pad, 0:S + 2 * pad].astype(np.float32)
    cx = cy = S / 2 + pad
    if circle:
        m = (np.hypot(xx - cx, yy - cy) < S * 0.46).astype(np.uint8) * 255
    else:
        th = np.linspace(0, 2 * np.pi, 400, endpoint=False)
        rad = S * 0.44 * (1 + sum(r.uniform(0.03, 0.08) * np.sin(k * th + r.uniform(0, 6.3)) for k in (2, 3, 4)))
        pts = np.stack([cx + rad * np.cos(th), cy + rad * np.sin(th)], 1).astype(np.int32)
        m = np.zeros(xx.shape, np.uint8)
        cv2.fillPoly(m, [pts], 255, cv2.LINE_AA)
    hh, ww = m.shape
    if texture is not None:
        t = Image.open(texture).convert("RGB")
        sc = max(ww / t.width, hh / t.height)
        t = t.resize((int(t.width * sc) + 1, int(t.height * sc) + 1), Image.LANCZOS)
        ox, oy = (t.width - ww) // 2, (t.height - hh) // 2
        col = np.asarray(t.crop((ox, oy, ox + ww, oy + hh))).astype(np.float32)
    else:
        n = fractal_noise(hh, ww, seed + 9)
        col = np.array(fill_rgb, np.float32)[None, None] * (0.86 + 0.24 * n[..., None])
    cr = np.zeros((hh, ww), np.float32)
    for _ in range(10):
        p0 = r.uniform(0, [ww, hh])
        p1 = p0 + r.uniform(-S * 0.5, S * 0.5, 2)
        cv2.line(cr, tuple(p0.astype(int)), tuple(p1.astype(int)), 1.0, 2, cv2.LINE_AA)
    col = col * (1 - 0.12 * cv2.GaussianBlur(cr, (0, 0), 1.2)[..., None])
    a = m.astype(np.float32) / 255
    rim = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))).astype(np.float32) / 255
    cream = np.array(PALETTE["cream"], np.float32)
    rgb = col * a[..., None] + cream * (1 - a[..., None])
    sh = cv2.GaussianBlur(rim, (0, 0), S * 0.02)
    sh = np.roll(np.roll(sh, int(S * 0.02), 0), int(S * 0.012), 1) * 0.5
    out_a = rim + sh * (1 - rim)
    out_rgb = (rgb * rim[..., None] + np.array([20, 22, 20]) * sh[..., None] * (1 - rim[..., None])) / np.maximum(out_a[..., None], 1e-4)
    return np.dstack([out_rgb.clip(0, 255), out_a * 255]).astype(np.uint8)


BLOBS = {"blob_gold": dict(fill_rgb=(206, 146, 40)), "blob_orange": dict(fill_rgb=(214, 92, 42)),
         "blob_petrol": dict(fill_rgb=(46, 112, 116)), "blob_red": dict(fill_rgb=(168, 40, 36)),
         "blob_grey": dict(fill_rgb=(112, 116, 104)), "blob_blue": dict(fill_rgb=(52, 82, 140)),
         "circ_amber": dict(texture="H6_bernstein_a.png", circle=True),
         "circ_amber2": dict(texture="H6_bernstein_b.png", circle=True),
         "circ_sky": dict(texture="H1_himmel.png", circle=True), "circ_forest": dict(texture="H5_wald_a.png", circle=True),
         "circ_earth": dict(texture="H9_erde.png", circle=True), "circ_fire": dict(texture="H2_feuer.png", circle=True),
         "circ_snow": dict(texture="H8_schnee.png", circle=True), "circ_sea": dict(texture="H3_ostsee_a.png", circle=True),
         "circ_night": dict(texture="H7_nachthimmel.png", circle=True)}


def caption(text, size=86):
    """big serif sentence: white with black outline (key sentences on the stage)"""
    f = ImageFont.truetype(font("serif"), size)
    bb = f.getbbox(text, stroke_width=7)
    img = Image.new("RGBA", (bb[2] - bb[0] + 40, bb[3] - bb[1] + 40), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((20 - bb[0], 20 - bb[1]), text, font=f, fill=(255, 255, 255, 255),
                             stroke_width=7, stroke_fill=(16, 16, 16, 255))
    return g.add_shadow(np.asarray(img), dx=4, dy=6, blur=5, op=0.5)


CAPTIONS = {"cap_zimmer": "Nach einem Zimmer.", "cap_wie": "Wie verliert man ein ganzes Zimmer?",
            "cap_wunder": "Das achte Weltwunder", "cap_puzzle": "wie ein riesiges Puzzle",
            "cap_soldatenkoenig": "Der Soldatenkönig", "cap_gold": "wie flüssiges Gold",
            "cap_krieg": "Dann kommt der Krieg.", "cap_groesser": "viel größer"}
LABELS = [("lbl_2025", "Sommer 2025", "black", 120), ("lbl_genehmigung", "Genehmigung", "petrol", 100),
          ("lbl_ss", "Ehem. SS-Übungsplatz", "black", 100), ("lbl_radar", "Bodenradar", "orange", 110),
          ("lbl_hohlraum", "Hohlraum!", "orange", 130), ("lbl_6t", "6 Tonnen Bernstein", "orange", 110),
          ("lbl_1945", "1945", "black", 150), ("lbl_spurlos", "Spurlos verschwunden", "black", 110),
          ("lbl_1701", "1701", "black", 150), ("lbl_friedrich", "Friedrich I.", "petrol", 100),
          ("lbl_schlueter", "Andreas Schlüter", "petrol", 100), ("lbl_wolfram", "Gottfried Wolfram", "petrol", 100),
          ("lbl_fw", "Friedrich Wilhelm I.", "petrol", 100), ("lbl_keinekunst", "Keine Kunst", "black", 120),
          ("lbl_soldaten", "Soldaten!", "orange", 130), ("lbl_1716", "1716", "black", 150),
          ("lbl_peter", "Peter der Große", "petrol", 100), ("lbl_buendnis", "Bündnis gegen Schweden", "black", 100),
          ("lbl_geschenk", "Ein Geschenk", "orange", 120), ("lbl_55", "55 Grenadiere", "orange", 120),
          ("lbl_gross", "Alle besonders groß", "black", 100), ("lbl_jahrzehnte", "Jahrzehntelang", "black", 110),
          ("lbl_elisabeth", "Zarin Elisabeth", "petrol", 100), ("lbl_1755", "1755", "black", 150),
          ("lbl_katharinen", "Katharinenpalast", "petrol", 100), ("lbl_rastrelli", "Rastrelli", "petrol", 100),
          ("lbl_55qm", "über 55 m²", "orange", 130), ("lbl_200", "Fast 200 Jahre", "black", 120),
          ("lbl_juni41", "Juni 1941", "black", 130)]


def build_stage(meta):
    save(meta, "stage_bg", dark_collage(5))
    for i, (name, kw) in enumerate(BLOBS.items()):
        kw = dict(kw)
        if "texture" in kw:
            kw["texture"] = os.path.join(BGS, kw["texture"])
        save(meta, name, blob(1000, 40 + i, **kw))
    for name, text in CAPTIONS.items():
        save(meta, name, caption(text))
    for i, (n, t, c, s) in enumerate(LABELS):
        save(meta, n, g.label(t, c, s, seed=300 + i))
    save(meta, "page", g.page_overlay(W, H, seed=3))
    save(meta, "tape_x", g.tape_x(700, seed=2))
    print("stage assets ok")


# ------------------------------------------------------------------ stickers (every cutout)
def build_stickers(meta):
    for i, f in enumerate(sorted(os.listdir(CUT))):
        if not f.lower().endswith((".png", ".jpg")):
            continue
        name = "st_" + os.path.splitext(f)[0].lower()
        dst = os.path.join(OUT, name + ".png")
        src = os.path.join(CUT, f)
        if name in meta and os.path.exists(dst) and os.path.getmtime(dst) > os.path.getmtime(src):
            continue
        rgba = np.asarray(Image.open(src).convert("RGBA"))
        colour = f.startswith(("F0", "A1_", "A10_"))
        if f.endswith(".jpg"):          # rectangular photo: keep it, add a white border
            rgba = cv2.copyMakeBorder(rgba[..., :3], 18, 18, 18, 18, cv2.BORDER_CONSTANT, value=(244, 240, 228))
            rgba = np.dstack([rgba, np.full(rgba.shape[:2], 255, np.uint8)])
        out, anc = make_sticker(rgba, tone=0.12 if colour else 0.35, seed=i, max_side=1400)
        Image.fromarray(out, "RGBA").save(dst)
        meta[name] = dict(w=out.shape[1], h=out.shape[0], anchor=[round(anc[0], 4), round(anc[1], 4)])
    print("stickers:", sum(1 for k in meta if k.startswith("st_")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    mp = os.path.join(OUT, "meta.json")
    meta = json.load(open(mp)) if os.path.exists(mp) else {}
    for step, fn in (("map", build_map), ("stage", build_stage), ("stickers", build_stickers)):
        if a.only in (None, step):
            fn(meta)
            json.dump(meta, open(mp, "w"), indent=1)
    print("meta ->", mp)


if __name__ == "__main__":
    main()
