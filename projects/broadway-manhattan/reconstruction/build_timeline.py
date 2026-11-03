"""Baut timeline.json der Broadway-Rekonstruktion (Stil map_doc).

Eingaben: assets/maps/* (build_maps.py), analysis/camera_track.json (track_camera.py),
analysis/captions.json, analysis/timeline_analysis.json (Szenen/SFX).

python3 projects/broadway-manhattan/reconstruction/build_timeline.py
"""
import json
import math
import os
import sys

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
from shortsfactory.assets_gen import figures as F  # noqa: E402

P = os.path.join(ROOT, "projects", "broadway-manhattan")
A = os.path.join(P, "assets")
DUR = 78.27
VEC = json.load(open(os.path.join(A, "maps", "vectors.json")))
BW = np.array(VEC["broadway"], float)
MH = np.array(VEC["manhattan"], float)
AXIS_DEG = 68.8  # Hauptachse Manhattan (Grad über Ost)


def lonlat(lon, lat):
    from pyproj import Transformer
    x, y = Transformer.from_crs("EPSG:4326", "EPSG:32618", always_xy=True).transform(lon, lat)
    return [round(x, 1), round(y, 1)]


def bw(f, off=0.0):
    """Punkt auf Broadway bei Bogenlängen-Anteil f (0 = Südspitze, 1 = Norden), off = Meter nach Westen(+)."""
    seg = np.hypot(*np.diff(BW, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    u = f * s[-1]
    x, y = np.interp(u, s, BW[:, 0]), np.interp(u, s, BW[:, 1])
    i = min(len(BW) - 2, np.searchsorted(s, u))
    d = BW[i + 1] - BW[i]
    d /= np.linalg.norm(d) + 1e-9
    nrm = np.array([-d[1], d[0]])  # links der Laufrichtung = Westen (bei Nordlauf)
    p = np.array([x, y]) + nrm * off
    return [round(float(p[0]), 1), round(float(p[1]), 1)]


def bw_section(f0, f1):
    seg = np.hypot(*np.diff(BW, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)]) / (seg.sum())
    m = (s >= f0) & (s <= f1)
    return BW[m].round().astype(int).tolist()


_CAM = None


def cam_at(t):
    from shortsfactory.render.keyframes import props_at
    return props_at(_CAM, t)


def mpp_at(t):
    return cam_at(t)["mpp"]


def scr(t, x720, y1280):
    """Bildpunkt im Original (720x1280) zum Zeitpunkt t -> Weltkoordinate (über die vermessene Kamera)."""
    from shortsfactory.render.maplayer import camera_matrix
    H = camera_matrix(cam_at(t), 1.0, 1.0)
    q = np.linalg.inv(H) @ [x720 * 1.5, y1280 * 1.5, 1.0]
    return [round(float(q[0] / q[2]), 1), round(float(q[1] / q[2]), 1)]


def K(t, **kw):
    d = {"t": round(t, 3)}
    d.update(kw)
    return d


# --------------------------------------------------------------------------- assets
def save(img, name):
    path = os.path.join(A, "gen", name + ".png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    return {"path": f"assets/gen/{name}.png", "license": "own (procedural, shortsfactory.assets_gen)"}


def build_assets():
    import random
    a = {}
    for k in ("lenape", "dutch", "british"):
        a["fig_" + k] = save(F.figure(k, 240, 420), "fig_" + k)
    a["tipi"] = save(F.tipi(300, 340), "tipi")
    for i in range(3):
        a[f"tree{i}"] = save(F.tree(200, 380, seed=i), f"tree{i}")
    a["rocks"] = save(F.rocks(320, 220), "rocks")
    a["cliff"] = save(F.cliff(260, 340), "cliff")
    a["swamp"] = save(F.swamp(480, 320), "swamp")
    a["foot_l"] = save(F.footprint(36, 60), "foot_l")
    a["foot_r"] = save(F.footprint(36, 60, flip=True), "foot_r")
    a["sign"] = save(F.sign(w=520, h=600), "sign")
    a["barrel"] = save(F.barrel(140, 172), "barrel")
    a["crate"] = save(F.crate(160, 140), "crate")
    a["ruler"] = save(F.ruler(1800, 220), "ruler")
    a["pencil"] = save(F.pencil(1040, 80), "pencil")
    a["question"] = save(F.question(320), "question")
    a["ellipse"] = save(F.ellipse_stroke(300, 900), "ellipse")
    a["ring"] = save(F.ellipse_stroke(120, 120, gap_deg=0, width=6), "ring")
    a["new_amsterdam"] = save(new_amsterdam_patch(), "new_amsterdam")
    a["commissioners"] = save(commissioners_map(), "commissioners")
    # Fotokarten: Platzhalter aus dem Sentinel-Bild (eigene Aufbereitung freier Daten)
    sat = cv2.imread(os.path.join(A, "maps", "sat.jpg"))
    sm = json.load(open(os.path.join(A, "maps", "sat.json")))
    ta, _, tc, _, te, tf = sm["transform"]
    for nm, (lo, la) in SQUARES.items():
        x, y = lonlat(lo, la)
        px, py = int((x - tc) / ta), int((y - tf) / te)
        crop = sat[py - 30:py + 30, px - 42:px + 42]
        crop = cv2.resize(crop, (588, 420), interpolation=cv2.INTER_CUBIC)
        crop = cv2.detailEnhance(crop, sigma_s=8, sigma_r=0.15)
        a["card_" + nm.split()[0].lower()] = save(F.photo_card(crop, nm, 300, 210), "card_" + nm.split()[0].lower())
    a["glowdot"] = save(glow_dot(), "glowdot")
    return a


SQUARES = {"Times Square": (-73.9855, 40.7580), "Herald Square": (-73.9877, 40.7497),
           "Union Square": (-73.9906, 40.7359), "Madison Square": (-73.9880, 40.7420)}
CROSSINGS = [(-73.9819, 40.7681), (-73.9822, 40.7736), (-73.9817, 40.7795), (-73.9855, 40.7580),
             (-73.9877, 40.7497), (-73.9880, 40.7420), (-73.9906, 40.7359), (-73.9690, 40.7990)]


def glow_dot(sz=160):
    from PIL import Image
    yy, xx = np.mgrid[0:sz, 0:sz]
    d = np.hypot(xx - sz / 2, yy - sz / 2) / (sz / 2)
    a = np.clip(np.exp(-d * d * 6) * 1.2, 0, 1)
    core = np.clip(1 - d * 6, 0, 1)
    rgb = np.stack([255 + 0 * d, 210 + 45 * core, 60 + 195 * core], -1)
    return Image.fromarray(np.dstack([rgb, a * 255]).astype(np.uint8), "RGBA")


def new_amsterdam_patch():
    """Alter Stadtplan an der Südspitze: olivgrüne Fläche mit dunklen Straßen, schwarz umrandet.
    Wird auf der Karte platziert (Weltkoordinaten = Bild-px * 4 m)."""
    from PIL import Image, ImageDraw
    x0, y0 = MH[:, 0].min(), MH[:, 1].min()
    res = 4.0
    W, H = int(2600 / res), int(2600 / res)
    def px(p):
        return [((x - x0) / res, H - (y - y0) / res) for x, y in p]
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon(px(MH.tolist()), fill=255)
    cut = Image.new("L", (W, H), 0)
    # nur die Südspitze (unterhalb ~Chambers Street)
    cy = y0 + 1700
    ImageDraw.Draw(cut).polygon([(0, H - (cy - y0) / res - 200), (W, H - (cy - y0) / res + 260), (W, H), (0, H)], fill=255)
    from PIL import ImageChops
    m = ImageChops.multiply(mask, cut)
    fill = Image.new("RGBA", (W, H), (118, 128, 92, 255))
    im.paste(fill, (0, 0), m)
    lines = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lines)
    for l in VEC["grid"]:
        pts = px(l)
        dl.line(pts, fill=(44, 50, 34, 255), width=2)
    for l in VEC["grid"]:
        pts = px(l)
        dl.line(pts, fill=(196, 196, 170, 255), width=1)
    im.paste(lines, (0, 0), ImageChops.multiply(m, lines.getchannel("A")))
    edge = m.filter(__import__("PIL.ImageFilter", fromlist=["x"]).FIND_EDGES).point(lambda v: 255 if v > 40 else 0)
    from PIL import ImageFilter
    edge = edge.filter(ImageFilter.MaxFilter(5))
    im.paste(Image.new("RGBA", (W, H), (20, 20, 18, 255)), (0, 0), edge)
    bb = m.getbbox()
    im = im.crop(bb)
    json.dump({"origin": [x0 + bb[0] * res, y0 + (H - bb[3]) * res], "res": res, "size": im.size},
              open(os.path.join(A, "gen", "new_amsterdam.json"), "w"))
    return im


def commissioners_map():
    """Grafik 'Plan von 1811' im Kupferstich-Look aus den echten Straßendaten (eigene Grafik)."""
    from PIL import Image, ImageDraw, ImageFilter
    ang = math.radians(90 - AXIS_DEG)
    c, s = math.cos(ang), math.sin(ang)
    ctr = MH.mean(0)
    def rot(p):
        p = np.asarray(p, float) - ctr
        return np.stack([p[:, 0] * c - p[:, 1] * s, p[:, 0] * s + p[:, 1] * c], 1)
    m = rot(MH)
    lo, hi = m.min(0), m.max(0)
    res = (hi[1] - lo[1]) / 1500
    W, H = int((hi[0] - lo[0]) / res) + 160, 1500 + 120
    def px(p):
        q = rot(p)
        return [((x - lo[0]) / res + 80, H - 60 - (y - lo[1]) / res) for x, y in q]
    im = Image.new("RGBA", (W, H), (248, 246, 238, 255))
    d = ImageDraw.Draw(im)
    for k in range(0, 60):  # Wasser-Schraffur (Kupferstich)
        poly = px(MH.tolist())
        off = k * 3
        d.line([(x + off * 0.0, y) for x, y in poly][::1], fill=(60, 60, 60, int(140 * math.exp(-k / 6))), width=1)
    for l in VEC["grid"]:
        d.line(px(l), fill=(30, 30, 30, 255), width=2)
    d.line(px(MH.tolist()) + [px(MH.tolist())[0]], fill=(0, 0, 0, 255), width=5)
    f = F._font("playfair-display-latin-400", 34)
    d.text((W - 40, 90), "The Commissioners' Map", font=f, fill=(20, 20, 20, 255), anchor="rm")
    d.text((W - 40, 140), "of THE CITY OF NEW YORK", font=F._font("playfair-display-latin-700", 26), fill=(20, 20, 20, 255), anchor="rm")
    d.text((W - 40, 185), "1811", font=f, fill=(20, 20, 20, 255), anchor="rm")
    d.rectangle([2, 2, W - 3, H - 3], outline=(40, 40, 40, 255), width=4)
    return im.filter(ImageFilter.SMOOTH)


# --------------------------------------------------------------------------- camera
def camera_keys():
    tr = {}
    for fn in ("camera_track.json", "camera_track_a.json", "camera_track_a2.json", "camera_track_b.json", "camera_track_refine.json"):
        fp = os.path.join(P, "analysis", fn)
        if os.path.exists(fp):
            tr.update(json.load(open(fp)))
    # 13,8-16,6 s: Überblendung Satellit->Papier, Atlas-Treffer unzuverlässig -> interpolieren
    # 34,5-38,1 s: Zoom auf das Schild; Verkettung liefert Lage/Zoom brauchbar, Drehung nicht -> Drehung interpolieren
    SPECIAL = (34.5, 38.1)
    recs = sorted((int(k), v) for k, v in tr.items() if "cx" in v and not (13.8 < v["t"] < 16.6) and v["mpp"] > 0.5
                  and (v.get("err_px", 99) < 3 or (SPECIAL[0] < v["t"] < SPECIAL[1] and v.get("err_px", 99) < 40)))
    ts = np.array([(n - 1) / 30 for n, _ in recs])
    cx = np.array([v["cx"] for _, v in recs])
    cy = np.array([v["cy"] for _, v in recs])
    lm = np.log([v["mpp"] for _, v in recs])
    rot = np.radians([v["rot"] for _, v in recs])
    special = (ts > SPECIAL[0]) & (ts < SPECIAL[1])
    rot = np.unwrap(rot)
    rot[special] = np.interp(ts[special], ts[~special], rot[~special])
    rot = np.unwrap(rot)
    tilt = np.array([v["tilt"] for _, v in recs])
    # Ausreißer (Fehlzuordnungen) entfernen: Median-Abweichung
    def med(x, k=5):
        return np.array([np.median(x[max(0, i - k):i + k + 1]) for i in range(len(x))])
    # nur grobe Fehlzuordnungen verwerfen (Position springt / Drehung springt); Zoom darf schnell sein
    bad = (np.abs(cx - med(cx, 3)) > 150 * np.exp(lm)) | (np.abs(cy - med(cy, 3)) > 150 * np.exp(lm)) | \
          (np.abs(rot - med(rot, 3)) > 0.35)
    keep = ~bad
    ts, cx, cy, lm, rot, tilt = (a[keep] for a in (ts, cx, cy, lm, rot, tilt))
    def sm(x):
        k = np.array([1, 2, 1], float)
        k /= k.sum()
        return np.convolve(np.pad(x, 1, mode="edge"), k, "valid")
    cx, cy, lm, rot, tilt = sm(cx), sm(cy), sm(lm), sm(rot), sm(np.where(tilt < 4, 0, tilt))
    rot = np.degrees(rot)
    rot -= 360 * round(rot[0] / 360)
    # 68,3-73,2 s: Verkettung driftet im Zoom (Nahaufnahme, Satellit zu grob für den Atlas) ->
    # Zoom per Sichtvergleich korrigiert (Faktor 0,8, weich ein-/ausgeblendet)
    f = np.interp(ts, [68.3, 68.9, 72.6, 73.2], [1.0, 0.8, 0.8, 1.0])
    lm = lm + np.log(f)
    keys = []
    # 0-0,4 s: schneller Rückwärtszoom aus der Nahaufnahme (nicht trackbar, Riesenschrift im Bild)
    if ts[0] > 0.05:
        keys.append(K(0.0, cx=round(cx[0], 1), cy=round(cy[0], 1), mpp=1.6, rot=round(float(rot[0]), 3), tilt=0))
    for i, t in enumerate(ts):
        keys.append(K(t, cx=round(cx[i], 1), cy=round(cy[i], 1), mpp=round(math.exp(lm[i]), 4),
                      rot=round(rot[i], 3), tilt=round(tilt[i], 2), ease="linear"))
    if ts[0] > 0.05:
        keys[1]["ease"] = "out3"
    return keys


# --------------------------------------------------------------------------- scenes
GLOW_RED = [{"width": 150, "blur": 70, "color": [235, 20, 30], "strength": 0.75},
            {"width": 60, "blur": 22, "color": [255, 30, 40], "strength": 0.85},
            {"width": 14, "blur": 3, "color": [255, 50, 60], "strength": 1.0}]
WHITE_LABEL = dict(font="roboto-latin-700-normal", color=[255, 255, 255], shadow=[4, 5, 6, 0.65])


def items():
    I = []
    add = I.append
    # ---- Satellit (ganzes Video, unter dem Papier) -------------------------
    sat_keys = [K(0, value=1.0, out_value=0.42, out_sat=0.55, sat=0.95),
                K(2.2, value=1.0, out_value=0.42, out_sat=0.55),
                K(2.6, value=0.82, out_value=0.42, out_sat=0.55),
                K(4.4, value=0.82, out_value=0.42, out_sat=0.55),
                K(4.9, value=1.05, out_value=1.0, out_sat=0.9, sat=0.9),
                K(11.2, value=1.05, out_value=1.0, out_sat=0.9),
                K(11.8, value=0.62, out_value=0.62, out_sat=0.5, sat=0.5),
                K(66.0, value=0.62, out_value=0.62, out_sat=0.5, sat=0.5),
                K(67.0, value=1.05, out_value=1.05, out_sat=0.9, sat=0.9)]
    for src in ("sat_wide", "sat"):
        add({"kind": "raster", "src": src, "mask": "manhattan" if src == "sat" else None,
         "edge_feather": 0.04 if src == "sat" else 0,
             "mask_feather": 2, "keys": [dict(k, out_value=k.get("out_value", 1)) if src == "sat" else
                                         {"t": k["t"], "value": k.get("out_value", k["value"]), "sat": k.get("out_sat", 1)}
                                         for k in sat_keys]})
    # ---- Hook: Insel aufgehellt, Label --------------------------------------
    add({"kind": "polygon", "src": "manhattan", "start": 0, "end": 4.8, "fill": [238, 228, 170], "fill_mode": "lighten",
         "edge_width": 2.0, "edge_color": [255, 252, 235], "edge_glow": {"color": [255, 250, 220], "blur": 5, "strength": 1.2},
         "keys": [K(0, fill_opacity=0.55, edge_opacity=1), K(2.2, fill_opacity=0.55, edge_opacity=1),
                  K(2.5, fill_opacity=0.0, edge_opacity=0.6), K(4.4, fill_opacity=0, edge_opacity=0.6), K(4.8, edge_opacity=0)]})
    ctr = MH.mean(0)
    add({"kind": "label", "text": "Manhattan", "at": [round(ctr[0] - 900, 1), round(ctr[1] - 1500, 1)], "on_map": True,
         "height_m": 900, "angle": AXIS_DEG, "start": 0, "end": 2.6, **WHITE_LABEL,
         "keys": [K(0, opacity=1), K(2.2, opacity=1), K(2.5, opacity=0)]})
    # ---- Raster blau (2,3 - 4,7) und wieder 8,3 - 11,3 -----------------------
    add({"kind": "polygon", "src": "manhattan", "start": 2.2, "end": 11.6, "fill": [40, 130, 230],
         "keys": [K(2.2, fill_opacity=0), K(2.6, fill_opacity=0.25), K(4.5, fill_opacity=0.25), K(4.9, fill_opacity=0),
                  K(8.1, fill_opacity=0), K(8.5, fill_opacity=0.28), K(11.0, fill_opacity=0.28), K(11.5, fill_opacity=0)]})
    add({"kind": "lines", "src": "grid", "start": 2.2, "end": 11.6, "width": 1.4, "color": [215, 240, 255],
         "glow": {"color": [60, 170, 255], "width": 5, "strength": 2.2}, "reveal_dir": [0.36, 0.93],
         "keys": [K(2.2, reveal=0, opacity=1), K(3.1, reveal=1), K(4.5, opacity=1), K(4.9, opacity=0),
                  K(8.1, opacity=0), K(8.5, opacity=1), K(11.0, opacity=1), K(11.5, opacity=0)]})
    # ---- weißes Raster auf hellem Satellit (4,6 - 8,4 und 64,5 - Ende) --------
    for src, al in (("grid", 0.9), ("grid_outer", 0.75)):
        add({"kind": "lines", "src": src, "start": 4.5, "end": 8.6, "width": 1.6, "color": [255, 255, 255], "alpha": al,
             "width_zoom": 0.5, "ref_mpp": 10, "keys": [K(4.5, opacity=0), K(4.8, opacity=1), K(8.1, opacity=1), K(8.5, opacity=0)]})
    # ---- Broadway rot (5 - 13,8) ----------------------------------------------
    add({"kind": "path", "src": "broadway", "start": 4.9, "end": 12.6, "reverse": True, "core_width": 3.5,
         "glows": GLOW_RED, "keys": [K(4.9, progress=0, opacity=1), K(8.0, progress=1, ease="inout"),
                                     K(11.3, opacity=1), K(12.4, opacity=0)]})
    add({"kind": "label", "text": "Broadway", "on_path": "broadway", "dx": -70, "size": 30, "start": 5.6, "end": 11.4,
         "glow": [255, 30, 40, 10, 0.9], **WHITE_LABEL,
         "keys": [K(5.6, scale=0.3, opacity=0, pos=0.78), K(5.9, scale=1, opacity=1, ease="back_out"),
                  K(7.3, pos=0.55, ease="inout"), K(11.0, opacity=1), K(11.3, opacity=0)]})
    # ---- Frage: gelbe Ellipse + Fragezeichen ----------------------------------
    ell = []
    c0 = MH.mean(0)
    ax = np.array([math.cos(math.radians(AXIS_DEG)), math.sin(math.radians(AXIS_DEG))])
    nx = np.array([-ax[1], ax[0]])
    for i in range(121):
        a = math.radians(-80 + i / 120 * 330)
        p = c0 - ax * 600 + ax * math.sin(a) * 12000 + nx * math.cos(a) * 2700
        ell.append([round(p[0]), round(p[1])])
    add({"kind": "path", "points": ell, "start": 9.9, "end": 11.5, "core_width": 5, "core_color": [250, 228, 40],
         "keys": [K(9.9, progress=0), K(10.5, progress=1, ease="out"), K(11.1, opacity=1), K(11.4, opacity=0)]})
    for j, (f, off, t0) in enumerate(((0.75, 2400, 10.25), (0.88, -900, 10.45), (0.55, -2600, 10.6))):
        add({"kind": "sprite", "asset": "question", "at": bw(f, off), "size": 190, "start": t0, "end": 11.4,
             "keys": [K(t0, scale=0.2, opacity=0), K(t0 + 0.2, scale=1, opacity=1, ease="back_out"), K(11.0, opacity=1), K(11.3, opacity=0)]})
    # ---- Älteste Straße: gestrichelt + Handschrift ---------------------------
    add({"kind": "path", "src": "broadway", "start": 11.6, "end": 15.8, "core_width": 8, "dash": [26, 18],
         "keys": [K(11.6, opacity=0), K(12.0, opacity=1), K(15.2, opacity=1), K(15.7, opacity=0)]})
    add({"kind": "label", "text": "Oldest", "at": bw(0.5, -1500), "dy": -55, "size": 100, "font": "great-vibes-latin-400", "render_px": 200,
         "color": [255, 255, 255], "shadow": [3, 4, 5, 0.5], "start": 11.9, "end": 14.0,
         "keys": [K(11.9, opacity=0), K(12.2, opacity=1), K(13.6, opacity=1), K(13.9, opacity=0)]})
    add({"kind": "label", "text": "Street", "at": bw(0.5, -1500), "dx": 45, "dy": 45, "size": 100, "font": "great-vibes-latin-400", "render_px": 200,
         "color": [255, 255, 255], "shadow": [3, 4, 5, 0.5], "start": 12.1, "end": 14.0,
         "keys": [K(12.1, opacity=0), K(12.4, opacity=1), K(13.6, opacity=1), K(13.9, opacity=0)]})
    # ---- Papier (13,9 - 67,4) -------------------------------------------------
    pk = [K(13.7, opacity=0), K(14.9, opacity=1, ease="inout")]
    pk = pk + [K(66.9, opacity=1, dissolve=1.0), K(67.8, dissolve=0.0, ease="in")]
    pk[0]["dissolve"] = 1.0
    add({"kind": "raster", "src": "paper_wide", "start": 13.7, "end": 68.2, "keys": pk, "dissolve_center": [700, 600],
         "extend": True})
    add({"kind": "raster", "src": "paper", "start": 13.7, "end": 68.2, "keys": pk, "dissolve_center": [700, 600],
         "edge_feather": 0.08})
    add({"kind": "label", "text": "~1000 BCE", "at": bw(0.62, -900), "size": 60, "font": "playfair-display-latin-700",
         "render_px": 140, "color": [62, 44, 34], "start": 14.0, "end": 16.6,
         "keys": [K(14.0, opacity=0), K(14.4, opacity=1), K(16.1, opacity=1), K(16.5, opacity=0)]})
    # ---- Lenape (Positionen im Original abgelesen: scr(t, x720, y1280)) -------
    def pop(t0, t1, fade=0.3, **extra):
        return [K(t0, scale=0.2, opacity=0, **extra), K(t0 + 0.22, scale=1, opacity=1, ease="back_out"),
                K(t1 - fade, opacity=1), K(t1, opacity=0)]

    FILL = {"fig_lenape": 0.72, "fig_dutch": 0.80, "fig_british": 0.80, "tipi": 0.92, "sign": 0.92, "swamp": 0.9,
            "rocks": 0.85, "cliff": 0.9, "tree0": 0.85, "tree1": 0.85, "tree2": 0.85}

    def fig(asset, t, x, y, w720, t0, t1, anchor=(0.5, 0.95), keys=None, **kw):
        add({"kind": "sprite", "asset": asset, "at": scr(t, x, y), "size": round(w720 * 1.5 / FILL.get(asset, 1.0)),
             "anchor": list(anchor),
             "size_zoom": 1.0, "ref_mpp": round(mpp_at(t), 3), "start": t0, "end": t1,
             "keys": keys or pop(t0, t1), **kw})

    for (x, y), t0 in zip(((288, 712), (344, 728), (384, 696))[::-1], (16.25, 16.6, 16.95)):
        fig("fig_lenape", 17.0, x, y, 70, t0, 21.0)
    add({"kind": "label", "text": "The Lenape", "at": scr(17.0, 376, 424), "size": 80, "font": "great-vibes-latin-400",
         "render_px": 200, "color": [255, 255, 255], "shadow": [3, 4, 5, 0.45], "start": 16.9, "end": 19.4,
         "size_zoom": 1.0, "ref_mpp": round(mpp_at(17.0), 3),
         "keys": [K(16.9, opacity=0), K(17.2, opacity=1), K(19.0, opacity=1), K(19.3, opacity=0)]})
    add({"kind": "path", "points": [scr(17.0, 410, 470), scr(17.0, 395, 520), scr(17.0, 372, 548)], "core_width": 2.5,
         "start": 17.0, "end": 19.4, "keys": [K(17.0, progress=0), K(17.4, progress=1), K(19.0, opacity=1), K(19.3, opacity=0)]})
    # ---- Siedlungen (22,3 s abgelesen) ----------------------------------------
    tip = [((357, 360), 19.85), ((421, 520), 20.0), ((224, 605), 21.4), ((344, 704), 21.55), ((170, 840), 21.75),
           ((208, 872), 21.9), ((139, 960), 22.0), ((365, 1088), 22.1)]
    for (x, y), t0 in tip:
        fig("tipi", 22.3, x, y, 88, t0, 26.5)
    fig("fig_lenape", 22.3, 152, 896, 26, 19.9, 23.4)
    # ---- leichtester Weg (24,5 / 25,3 / 27,5 / 28,6 s abgelesen) ---------------
    fig("tipi", 24.5, 560, 600, 300, 23.6, 26.5, keys=[K(23.6, opacity=0), K(23.8, opacity=1), K(26.2, opacity=1), K(26.5, opacity=0)])
    walk = [[(328, 605), (384, 392)], [(349, 781), (384, 576)], [(349, 860), (384, 824)]]
    for j, (a0, a1) in enumerate(walk):
        p0, p1 = scr(24.5, *a0), scr(25.3, *a1)
        p2 = scr(27.5, 384, 536 + 120 * j)
        p3 = scr(28.6, 368, 528 + 110 * j)
        add({"kind": "sprite", "asset": "fig_lenape", "at": p0, "size": 96 * 1.5 / 0.72, "anchor": [0.5, 0.95], "size_zoom": 1.0,
             "ref_mpp": round(mpp_at(24.5), 3), "start": 23.6, "end": 31.0,
             "keys": [K(23.6, at=p0, opacity=0), K(23.9, opacity=1), K(25.3, at=p1), K(27.5, at=p2), K(28.6, at=p3),
                      K(30.4, at=scr(28.6, 368, 200 + 110 * j), opacity=1), K(30.9, opacity=0)]})
    obst = [("swamp", 27.5, 512, 260, 288, 24.85), ("rocks", 27.5, 264, 350, 112, 25.6), ("rocks", 27.5, 424, 345, 112, 25.75),
            ("cliff", 27.5, 528, 528, 140, 26.1), ("tree0", 27.5, 330, 1040, 200, 27.25), ("tree1", 27.5, 380, 1000, 210, 27.35),
            ("tree2", 27.5, 300, 940, 190, 27.45)]
    for a_, t, x, y, w, t0 in obst:
        fig(a_, t, x, y, w, t0, 31.0, anchor=(0.5, 0.9))
    for i in range(40):  # Fußspuren entlang der Laufrichtung
        f = i / 39
        wx, wy = scr(27.5, 230 - 70 * f, 520 - 520 * f) if f < 0.5 else scr(28.6, 368, 330 - 600 * (f - 0.5))
        t0 = 24.3 + 5.5 * f
        add({"kind": "sprite", "asset": "foot_l" if i % 2 else "foot_r", "at": [wx + (12 if i % 2 else -12), wy], "size": 22,
             "size_zoom": 1.0, "ref_mpp": round(mpp_at(27.5), 3), "start": t0, "end": 33.0,
             "keys": [K(t0, opacity=0), K(t0 + 0.15, opacity=0.9), K(31.0, opacity=0.9), K(32.6, opacity=0)]})
    # ---- Trail (braune Linie) und Schild --------------------------------------
    add({"kind": "path", "src": "broadway", "start": 30.3, "end": 68.2, "core_color": [96, 32, 20],
         "glows": [{"width": 4, "blur": 1.5, "color": [60, 20, 10], "strength": 0.6}], "width_zoom": 1.0,
         "ref_mpp": round(mpp_at(34.8), 3),
         "keys": [K(30.3, progress=0, core_width=4), K(33.2, progress=1, ease="inout"), K(41.9, core_width=4),
                  K(42.6, core_width=8, ease="out"), K(54.1, opacity=1), K(54.5, opacity=0)]})
    fig("sign", 34.8, 363, 688, 300, 34.15, 55.0, keys=[K(34.15, dy=-500, opacity=1), K(34.45, dy=0, ease="out3"),
                                                     K(54.0, opacity=1), K(54.4, opacity=0)])
    fig("fig_lenape", 34.8, 224, 736, 184, 33.6, 36.0)
    # ---- Holländer 1624 ------------------------------------------------------
    add({"kind": "label", "text": "1624", "at": "camera", "dy": 185, "size": 78, "font": "playfair-display-latin-400",
         "render_px": 200, "color": [250, 250, 250], "shadow": [3, 4, 6, 0.4], "start": 36.3, "end": 37.6,
         "keys": [K(36.3, opacity=0), K(36.5, opacity=1), K(37.2, opacity=1), K(37.5, opacity=0)]})
    fig("fig_dutch", 41.0, 424, 691, 144, 36.2, 45.6,
        keys=[K(36.2, scale=0.2, opacity=0, at=scr(36.5, 547, 677)), K(36.4, scale=1, opacity=1, ease="back_out"),
              K(39.0, at=scr(36.5, 547, 677)), K(40.0, at=scr(41.0, 424, 691), ease="inout"), K(44.7, dx=0),
              K(45.4, dx=500, opacity=0, ease="in")])
    na = json.load(open(os.path.join(A, "gen", "new_amsterdam.json")))
    w, h = na["size"]
    add({"kind": "sprite", "asset": "new_amsterdam", "on_map": True, "size_m": w * na["res"],
         "at": [na["origin"][0], na["origin"][1] + h * na["res"]], "anchor": [0, 0], "start": 37.7, "end": 54.6,
         "keys": [K(37.7, opacity=0), K(38.0, opacity=1), K(54.1, opacity=1), K(54.5, opacity=0)]})
    lab = dict(font="playfair-display-latin-700", render_px=120, color=[255, 255, 255], shadow=[2, 3, 4, 0.6],
               size_zoom=1.0, ref_mpp=round(mpp_at(38.5), 3))
    add({"kind": "label", "text": "New Amsterdam", "at": scr(38.5, 208, 571), "size": 29, "start": 38.0, "end": 50.7, **lab,
         "keys": [K(38.0, opacity=0), K(38.2, opacity=1), K(50.4, opacity=1), K(50.7, opacity=0)]})
    add({"kind": "path", "points": [scr(50.0, 152, 662), scr(50.0, 262, 664)], "core_width": 3, "core_color": [220, 30, 30],
         "start": 49.6, "end": 50.7, "keys": [K(49.6, progress=0), K(49.9, progress=1), K(50.4, opacity=1), K(50.7, opacity=0)]})
    add({"kind": "label", "text": "New York", "at": scr(50.0, 190, 659), "size": 29, "start": 50.5, "end": 54.6, **lab,
         "keys": [K(50.5, opacity=0), K(50.7, opacity=1), K(54.2, opacity=1), K(54.6, opacity=0)]})
    # ---- Briten ---------------------------------------------------------------
    fig("fig_british", 48.0, 280, 632, 136, 44.7, 55.0, keys=pop(44.7, 54.4))
    fig("fig_british", 48.0, 328, 552, 136, 46.4, 55.0, keys=pop(46.4, 54.4))
    for txt, f, off, t0 in (("Broad", 0.55, 1100, 52.9), ("way", 0.62, -700, 53.35)):
        add({"kind": "label", "text": txt, "at": bw(f, off), "size": 40, "font": "playfair-display-latin-700", "render_px": 160,
             "color": [255, 255, 255], "shadow": [2, 3, 4, 0.5], "start": t0, "end": 54.6,
             "keys": [K(t0, opacity=0, scale=0.6), K(t0 + 0.2, opacity=1, scale=1, ease="back_out"), K(54.2, opacity=1), K(54.5, opacity=0)]})
    # ---- 1811, Plan, Lineal --------------------------------------------------
    add({"kind": "label", "text": "1811", "at": "camera", "size": 90, "font": "playfair-display-latin-400", "render_px": 260,
         "color": [252, 252, 250], "shadow": [3, 4, 8, 0.35], "start": 54.4, "end": 56.0,
         "keys": [K(54.4, scale=6, opacity=0), K(54.55, opacity=1), K(55.0, scale=1, ease="out3"), K(55.6, opacity=1), K(55.95, opacity=0)]})
    add({"kind": "sprite", "asset": "commissioners", "at": "camera", "size": 640, "start": 55.6, "end": 57.2,
         "keys": [K(55.6, dx=900, rot=-8), K(56.0, dx=0, rot=-4, ease="out3"), K(56.8, dx=0), K(57.15, dx=-1000, ease="in")]})
    add({"kind": "sprite", "asset": "ruler", "at": "camera", "size": 150, "start": 56.8, "end": 60.4,
         "keys": [K(56.8, dx=700, dy=0, rot=-10), K(57.1, dx=180, rot=-12, ease="out3"), K(57.9, dx=150, rot=-14),
                  K(58.3, dx=60, dy=200, rot=-62, ease="inout"), K(59.6, dx=80, dy=520, rot=-70), K(60.3, dx=-900, ease="in")]})
    add({"kind": "sprite", "asset": "pencil", "at": "camera", "size": 420, "start": 56.9, "end": 60.4,
         "keys": [K(56.9, dx=-700, dy=200, rot=-25), K(57.2, dx=-150, dy=140, rot=-25, ease="out3"), K(57.6, dx=-40, dy=-260),
                  K(57.9, dx=-60, dy=120), K(58.2, dx=-20, dy=-250), K(58.6, dx=30, dy=60, rot=-60), K(59.2, dx=40, dy=-200),
                  K(60.3, dx=-900, dy=-300, ease="in")]})
    # ---- Lebensader: rot getönt, Neon, Fässer ----------------------------------
    for src in ("paper_wide", "paper"):
        pass
    add({"kind": "polygon", "points": [[540000, 4470000], [640000, 4470000], [640000, 4570000], [540000, 4570000]],
         "start": 58.8, "end": 68.2, "fill": [255, 120, 110], "fill_mode": "multiply",
         "keys": [K(58.8, fill_opacity=0), K(59.6, fill_opacity=0.18), K(62.0, fill_opacity=0.3), K(66.9, fill_opacity=0.3), K(67.3, fill_opacity=0)]})
    add({"kind": "path", "src": "broadway", "start": 59.0, "end": 67.3, "core_width": 3.2, "glows": GLOW_RED,
         "keys": [K(59.0, opacity=0), K(59.6, opacity=1)]})
    add({"kind": "path", "src": "broadway", "start": 67.0, "end": 78.27, "core_width": 3.0,
         "glows": [{"width": 46, "blur": 18, "color": [255, 30, 40], "strength": 0.65},
                   {"width": 10, "blur": 2, "color": [255, 50, 60], "strength": 1.0}]})
    # Lineal-Linien bleiben als Raster stehen
    add({"kind": "lines", "src": "grid", "start": 57.6, "end": 64.6, "width": 1.2, "color": [255, 255, 255], "alpha": 0.7,
         "reveal_dir": [0.93, -0.36], "keys": [K(57.6, reveal=0), K(59.3, reveal=1), K(64.2, opacity=1), K(64.6, opacity=0)]})
    add({"kind": "ink", "start": 66.8, "end": 67.8, "dissolve_center": [520, 1000],
         "keys": [K(66.95, grow=0, opacity=0.95), K(67.25, grow=0.55, ease="out"), K(67.3, opacity=0.95), K(67.55, opacity=0)]})
    for j in range(6):
        t0 = 60.6 + 0.5 * j
        add({"kind": "sprite", "asset": "barrel" if j % 2 == 0 else "crate", "on_path": "broadway", "size": 46,
             "anchor": [0.5, 0.8], "size_zoom": 1.0, "ref_mpp": 14, "start": t0, "end": 64.8,
             "keys": [K(t0, pos=0.05 + 0.02 * j, opacity=0), K(t0 + 0.2, opacity=1), K(64.4, pos=0.5 + 0.08 * j, opacity=1), K(64.8, opacity=0)]})
    # ---- Raster drüber, Rückkehr zum Satellit ----------------------------------
    add({"kind": "lines", "src": "grid", "start": 64.5, "end": 78.27, "width": 1.6, "color": [255, 255, 255], "alpha": 0.9,
         "width_zoom": 0.5, "ref_mpp": 10, "reveal_dir": [0.36, 0.93], "keys": [K(64.5, reveal=0), K(66.6, reveal=1, ease="inout")]})
    add({"kind": "lines", "src": "grid_outer", "start": 64.8, "end": 78.27, "width": 1.4, "color": [255, 255, 255], "alpha": 0.7,
         "width_zoom": 0.5, "ref_mpp": 10, "keys": [K(64.8, opacity=0), K(66.4, opacity=1)]})
    # Kreuzungen
    for j, (lo, la) in enumerate(CROSSINGS):
        t0 = 69.0 + 0.25 * j
        add({"kind": "sprite", "asset": "ring", "at": lonlat(lo, la), "size": 70, "size_zoom": 1.0, "ref_mpp": round(mpp_at(70.0), 3),
             "start": t0, "end": 72.6, "keys": [K(t0, scale=0.2, opacity=0), K(t0 + 0.2, scale=1, opacity=1, ease="back_out"),
                                                K(72.2, opacity=1), K(72.5, opacity=0)]})
    for j, (nm, t0) in enumerate((("Times Square", 73.05), ("Herald Square", 74.25), ("Union Square", 75.3), ("Madison Square", 76.9))):
        lo, la = SQUARES[nm]
        add({"kind": "sprite", "asset": "glowdot", "at": lonlat(lo, la), "size": 60, "start": t0 - 0.3, "end": DUR, "blend": "add",
             "keys": [K(t0 - 0.3, opacity=0), K(t0, opacity=1)]})
        side = [(151, -714), (-216, -542), (-152, 172), (237, -152)][j]
        add({"kind": "sprite", "asset": "card_" + nm.split()[0].lower(), "at": "camera", "dx": side[0], "dy": side[1],
             "size": 360, "start": t0, "end": DUR,
             "keys": [K(t0, scale=0.3, opacity=0, dx=side[0], dy=side[1]), K(t0 + 0.2, scale=1, opacity=1, ease="back_out")]})
    z = {"raster": 0, "ink": 2}
    I.sort(key=lambda it: z.get(it["kind"], 1))  # stabil: Karten unten, Grafiken darüber
    return I


def audio():
    an = json.load(open(os.path.join(P, "analysis", "timeline_analysis.json")))["audio"]
    out = [{"id": "voice", "src": "audio/voice_reference_proxy.flac", "start": 0.0, "gain_db": 0.0}]
    # Musikbett mit Pausen bei den Figuren-Zitaten
    t = 0.0
    for a, b in an["music_dropouts"] + [[DUR, DUR]]:
        if a > t:
            out.append({"id": f"music_{t:.1f}", "src": "audio/music_bed.wav", "start": t, "trim": [t, a],
                        "gain_db": -17.0, "fade_out": 0.08})
        t = b
    pops = {16.25, 16.6, 16.95, 19.85, 21.4, 21.75, 24.85, 25.6, 26.1, 27.25, 10.25, 44.7, 34.5, 36.3, 50.65, 53.0}
    clicks = {73.05, 74.25, 75.3, 76.0, 76.9, 68.3}
    for s in an["sfx_peaks_s"]:
        if s in pops:
            src, g = "@sfx/pop", -14
        elif s in clicks:
            src, g = "@sfx/click", -16
        else:
            src, g = "@sfx/soft_whoosh", -20
        out.append({"id": f"sfx_{s}", "src": src, "start": round(s - 0.03, 3), "gain_db": g})
    return out


def captions():
    cap = json.load(open(os.path.join(P, "analysis", "captions.json")))
    return {"style": {"font": "roboto-latin-700-normal", "size": 50, "y": 1366, "fill": [236, 236, 228],
                      "stroke_w": 0, "uppercase": False, "fade_in": 0.1,
                      "shadow": {"dx": 2, "dy": 3, "blur": 3.0, "color": [0, 0, 0], "alpha": 0.6},
                      "variants": {"quote_italic": {"font": "roboto-latin-700-italic"}}},
            "words": [{"text": w["text"], "start": w["start"], "end": w["end"], **({"style": w["style"]} if w.get("style") else {})}
                      for w in cap["words"]]}


def main():
    global _CAM
    mb = os.path.join(P, "audio", "music_bed.wav")
    if not os.path.exists(mb):  # eigenes Musikbett (nicht im Git, wird erzeugt)
        from shortsfactory.audio import sfx
        sfx.write_wav(mb, sfx.ambient_bed(DUR + 1))
    _CAM = camera_keys()
    assets = build_assets()
    tl = {
        "meta": {"fps": 30, "width": 1080, "height": 1920, "duration": DUR, "style_profile": "map_doc",
                 "attribution": ["Contains modified Copernicus Sentinel data 2024",
                                 "© OpenStreetMap contributors, Overture Maps Foundation (ODbL)",
                                 "Terrain: AWS Terrain Tiles (SRTM, USGS 3DEP)"]},
        "assets": assets,
        "maps": {"nyc": {"rasters": {"sat": "assets/maps/sat.json", "sat_wide": "assets/maps/sat_wide.json",
                                     "paper": "assets/maps/paper.json", "paper_wide": "assets/maps/paper_wide.json"},
                         "masks": {"manhattan": "assets/maps/sat_manhattan_mask.png"},
                         "vectors": "assets/maps/vectors.json"}},
        "layers": [{"id": "map", "type": "map", "map": "nyc", "start": 0, "end": DUR, "keys": _CAM, "items": items()}],
        "captions": captions(),
        "audio": audio(),
    }
    json.dump(tl, open(os.path.join(P, "reconstruction", "timeline.json"), "w"), indent=None, separators=(",", ":"))
    print("layers ok, items", len(tl["layers"][0]["items"]), "camera keys", len(tl["layers"][0]["keys"]))


if __name__ == "__main__":
    main()
