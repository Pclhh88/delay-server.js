"""Timeline „Der See, der niemandem gehört" (Bodensee), Stil map_doc.

Timing kommt aus der Sprachaufnahme (analysis/transcript_asr.json, Segmente).
Loop: das letzte Bild entspricht dem ersten (Europa-Ansicht), der letzte Satz führt in den ersten.

python3 projects/bodensee/build_timeline.py
"""
import json
import math
import os
import re
import subprocess
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from shortsfactory.assets_gen import figures as F  # noqa: E402

P = os.path.join(ROOT, "projects", "bodensee")
A = os.path.join(P, "assets")
VEC = json.load(open(os.path.join(A, "maps", "vectors.json")))
DUR = 73.9
AXIS = VEC["axis_deg"]          # Achse Obersee (Grad über Ost), ca. -24
ROT = -36.0                      # Kartendrehung in den See-Szenen (See liegt schräg im Hochformat)


def ll(lon, lat):
    from pyproj import Transformer
    x, y = Transformer.from_crs("EPSG:4326", "EPSG:32632", always_xy=True).transform(lon, lat)
    return [round(x, 1), round(y, 1)]


def K(t, **kw):
    d = {"t": round(t, 3)}
    d.update(kw)
    return d


def cam(t, lon, lat, mpp, rot=ROT, tilt=0.0, ease="inout"):
    x, y = ll(lon, lat)
    return K(t, cx=x, cy=y, mpp=mpp, rot=rot, tilt=tilt, ease=ease)


# --------------------------------------------------------------------------- Untertitel
SEG_PHRASES = [
    ["Mitten in Europa", "liegt ein See,", "bei dem bis heute", "niemand weiß,", "wem er eigentlich gehört."],
    ["Das ist", "der Bodensee."],
    ["Drei Länder", "liegen an seinem Ufer:"],
    ["Deutschland,", "Österreich", "und die Schweiz."],
    ["Aber eine Grenze", "im See?"],
    ["Gibt es nicht."],
    ["Wie kann das sein?"],
    ["Früher", "brauchte man keine."],
    ["Rund um den See", "herrschten Fürsten,", "Klöster", "und Reichsstädte,"],
    ["alle unter dem Dach", "des Heiligen", "Römischen Reichs."],
    ["Der See", "war einfach der See."],
    ["Doch dann", "geht die Schweiz", "eigene Wege."],
    ["Das Reich zerfällt."],
    ["Und plötzlich", "teilen sich", "mehrere Staaten", "das Ufer."],
    ["Für den kleinen Untersee", "zieht man 1854", "eine Grenze."],
    ["Für den großen", "Obersee?"],
    ["Nie."],
    ["Und so hat heute", "jedes Land", "seine eigene Meinung."],
    ["Die Schweiz sagt:"],
    ["*Ganz klar,"],
    ["*d'Gränze gaht genau", "*i de Mitti dure."],
    ["Österreich sagt:"],
    ["*Geh bitte,", "*der See g'hört uns", "*doch olle zsamm."],
    ["Und Deutschland?"],
    ["*Dazu können wir", "*zum jetzigen Zeitpunkt", "*leider keine Aussage", "*treffen."],
    ["Das Verrückte:"],
    ["Es funktioniert", "trotzdem."],
    ["Fischerei,", "Schifffahrt,", "Wasserschutz,"],
    ["alles regeln", "die drei Länder", "gemeinsam."],
    ["Nur die eine Frage", "klären sie nie."],
    ["Millionen Menschen", "trinken Wasser", "aus diesem See."],
    ["Und trotzdem", "gilt bis heute:"],
]


def _syll(s):
    return max(1, len(re.findall(r"[aeiouäöüy]+", s.lower())))


def _energy(path, hop=0.01):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    n = int(16000 * hop)
    e = np.array([np.sqrt((a[i:i + n] ** 2).mean()) for i in range(0, len(a) - n, n)])
    return e, hop


def captions():
    segs = json.load(open(os.path.join(P, "analysis", "transcript_asr.json")))
    segs = segs if isinstance(segs, list) else segs["segments"]
    assert len(segs) == len(SEG_PHRASES), (len(segs), len(SEG_PHRASES))
    e, hop = _energy(os.path.join(P, "audio", "voice.mp3"))
    words = []
    for s, phr in zip(segs, SEG_PHRASES):
        t0, t1 = s["start"], s["end"]
        w = np.array([_syll(p) for p in phr], float)
        bounds = t0 + (t1 - t0) * np.concatenate([[0], np.cumsum(w) / w.sum()])
        # innere Grenzen zur leisesten Stelle in ±0,15 s schieben (Sprechpausen)
        for i in range(1, len(bounds) - 1):
            a, b = int((bounds[i] - 0.15) / hop), int((bounds[i] + 0.15) / hop)
            bounds[i] = (a + int(np.argmin(e[a:b]))) * hop
        for i, p in enumerate(phr):
            it = p.startswith("*")
            d = {"text": p.lstrip("*"), "start": round(bounds[i] - 0.05, 3), "end": round(bounds[i + 1], 3)}
            if it:
                d["style"] = "quote_italic"
            words.append(d)
    for a, b in zip(words, words[1:]):  # bis zur nächsten Phrase stehen lassen (max. 0,6 s Lücke)
        if b["start"] - a["end"] < 0.6:
            a["end"] = b["start"]
    json.dump({"source": "Phrasen aus Skript, Zeiten aus ASR-Segmenten + Silbenverteilung", "words": words},
              open(os.path.join(P, "analysis", "captions.json"), "w"), indent=1, ensure_ascii=False)
    return {"style": {"font": "roboto-latin-700-normal", "size": 50, "y": 1366, "fill": [236, 236, 228],
                      "stroke_w": 0, "uppercase": False, "fade_in": 0.1,
                      "shadow": {"dx": 2, "dy": 3, "blur": 3.0, "color": [0, 0, 0], "alpha": 0.6},
                      "variants": {"quote_italic": {"font": "roboto-latin-700-italic"}}},
            "words": words}


# --------------------------------------------------------------------------- Grafiken
def save(img, name):
    path = os.path.join(A, "gen", name + ".png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    return {"path": f"assets/gen/{name}.png", "license": "own (procedural)"}


def build_assets():
    a = {}
    for k in ("swiss", "austrian", "german"):
        a["fig_" + k] = save(F.country_figure(k, 240, 420), "fig_" + k)
    a["castle"] = save(F.castle(260, 260), "castle")
    a["church"] = save(F.church(220, 280), "church")
    a["town"] = save(F.town(300, 220), "town")
    a["fish"] = save(F.fish(260, 140), "fish")
    a["ship"] = save(F.ship(320, 210), "ship")
    a["drop"] = save(F.drop(150, 210), "drop")
    a["stamp"] = save(F.stamp("KEINE AUSSAGE", 760, 230), "stamp")
    a["question"] = save(F.question(320), "question")
    a["ruler"] = save(F.ruler(1800, 220), "ruler")
    a["pencil"] = save(F.pencil(1040, 80), "pencil")
    return a


def hatch_lines(spacing=750.0, ang_deg=40.0):
    """Schraffur über den ganzen See in den drei Landesfarben (für 'gehört uns allen')."""
    import shapely
    from shapely.ops import unary_union
    lake = unary_union([shapely.Polygon(p) for p in VEC["lake_parts"]]).buffer(0)
    x0, y0, x1, y1 = lake.bounds
    a = math.radians(ang_deg)
    d = np.array([math.cos(a), math.sin(a)])
    n = np.array([-d[1], d[0]])
    c = np.array([(x0 + x1) / 2, (y0 + y1) / 2])
    L = math.hypot(x1 - x0, y1 - y0)
    groups = [[], [], []]
    for k, off in enumerate(np.arange(-L / 2, L / 2, spacing)):
        p = c + n * off
        ln = shapely.LineString([p - d * L, p + d * L]).intersection(lake)
        for g in getattr(ln, "geoms", [ln]):
            if g.geom_type == "LineString" and g.length > 200:
                groups[k % 3].append(np.round(np.asarray(g.coords)).astype(int).tolist())
    return groups


# --------------------------------------------------------------------------- Kamera
def camera():
    E = (9.40, 47.62, 2300.0, 0.0)      # Europa-Ansicht (Anfang = Ende, Loop)
    keys = [
        cam(0.0, *E[:3], rot=0, ease="linear"),
        cam(1.2, 9.40, 47.62, 1900.0, rot=0, ease="linear"),
        cam(3.0, 9.36, 47.63, 75.0, ease="inout"),       # „liegt ein See" – Zoom hinein
        cam(5.4, 9.38, 47.625, 64.0),
        cam(6.0, 9.38, 47.625, 60.0),
        cam(7.5, 9.38, 47.63, 62.0),
        cam(12.2, 9.38, 47.62, 78.0),                     # drei Länder
        cam(13.6, 9.44, 47.59, 50.0),                     # Grenze im See?
        cam(15.2, 9.44, 47.59, 46.0),
        cam(16.4, 9.42, 47.60, 62.0),                     # Wie kann das sein?
        cam(18.4, 9.38, 47.64, 110.0),                    # Fürsten, Klöster, Städte
        cam(22.4, 9.38, 47.64, 120.0),
        cam(24.6, 9.40, 47.70, 330.0, rot=-15),          # Heiliges Römisches Reich
        cam(26.0, 9.38, 47.63, 85.0),                     # Der See war einfach der See
        cam(27.5, 9.38, 47.63, 80.0),
        cam(29.6, 9.30, 47.52, 170.0, rot=-25),          # Schweiz geht eigene Wege
        cam(31.4, 9.32, 47.58, 150.0, rot=-30),
        cam(33.0, 9.38, 47.62, 80.0),                     # mehrere Staaten
        cam(34.6, 9.30, 47.65, 70.0),
        cam(36.0, 9.00, 47.685, 24.0, rot=-12),          # Untersee 1854
        cam(38.8, 9.01, 47.68, 22.0, rot=-12),
        cam(40.2, 9.44, 47.59, 52.0),                     # Obersee? Nie.
        cam(41.6, 9.44, 47.59, 50.0),
        cam(44.0, 9.42, 47.60, 62.0),                     # jedes Land eigene Meinung
        cam(45.6, 9.40, 47.565, 34.0),                    # Schweiz
        cam(47.6, 9.44, 47.585, 48.0),
        cam(49.2, 9.46, 47.59, 52.0),
        cam(50.4, 9.68, 47.52, 32.0),                     # Österreich
        cam(52.4, 9.50, 47.59, 58.0),
        cam(53.6, 9.50, 47.59, 58.0),
        cam(55.0, 9.46, 47.665, 28.0),                    # Deutschland
        cam(58.4, 9.46, 47.66, 26.0),
        cam(60.0, 9.40, 47.62, 68.0),                     # Es funktioniert trotzdem
        cam(64.0, 9.42, 47.61, 60.0),
        cam(66.4, 9.40, 47.62, 72.0),
        cam(68.8, 9.40, 47.62, 66.0),
        cam(71.6, 9.30, 47.95, 330.0, rot=-15),          # Trinkwasser nach Norden
        cam(72.3, 9.32, 47.90, 360.0, rot=-12),
        cam(DUR - 0.15, *E[:3], rot=0, ease="in3"),       # zurück zur Europa-Ansicht (Loop)
        cam(DUR, *E[:3], rot=0, ease="linear"),
    ]
    return keys


# --------------------------------------------------------------------------- Szenen
WHITE = dict(font="roboto-latin-700-normal", color=[255, 255, 255], shadow=[4, 5, 6, 0.65])
SERIF = dict(font="playfair-display-latin-700", render_px=140, color=[60, 42, 32])


def pop(t0, t1, fade=0.3):
    return [K(t0, scale=0.2, opacity=0), K(t0 + 0.22, scale=1, opacity=1, ease="back_out"), K(t1 - fade, opacity=1), K(t1, opacity=0)]


def fade(t0, t1, d=0.3, op=1.0, **extra):
    return [K(t0, opacity=0, **extra), K(t0 + d, opacity=op), K(t1 - d, opacity=op), K(t1, opacity=0)]


def items():
    I = []
    add = I.append
    # ---- Karten (unten) -------------------------------------------------------
    add({"kind": "raster", "src": "europe", "extend": True})
    add({"kind": "raster", "src": "region", "edge_feather": 0.06,
         "keys": [K(0, opacity=0), K(1.6, opacity=0), K(2.4, opacity=1), K(72.6, opacity=1), K(73.4, opacity=0)]})
    sat_k = [K(0, opacity=0), K(2.2, opacity=0), K(2.9, opacity=1), K(69.6, opacity=1), K(70.6, opacity=0)]
    add({"kind": "raster", "src": "sat_wide", "mask": "valid_wide", "mask_alpha": True, "mask_feather": 6, "keys": sat_k})
    add({"kind": "raster", "src": "sat", "mask": "valid", "mask_alpha": True, "mask_feather": 6, "edge_feather": 0.04, "keys": sat_k})
    pk = [K(16.6, opacity=0), K(17.5, opacity=1, ease="inout"), K(58.7, opacity=1), K(59.6, opacity=0)]
    add({"kind": "raster", "src": "paper_wide", "start": 16.6, "end": 59.7, "extend": True, "keys": pk})
    add({"kind": "raster", "src": "paper", "start": 16.6, "end": 59.7, "edge_feather": 0.12, "keys": pk})

    # ---- Hook: Europa, See leuchtet ------------------------------------------
    add({"kind": "lines", "src": "europe_borders", "width": 1.2, "color": [255, 255, 255], "alpha": 0.55,
         "keys": [K(0, opacity=1), K(1.4, opacity=1), K(2.2, opacity=0), K(73.0, opacity=0), K(73.6, opacity=1)]})
    add({"kind": "polygon", "src": "lake_parts", "fill": [80, 190, 255], "fill_mode": "lighten",
         "edge_width": 2.5, "edge_color": [220, 245, 255], "edge_glow": {"color": [90, 200, 255], "blur": 10, "strength": 1.6},
         "keys": [K(0, fill_opacity=0.9, edge_opacity=1, opacity=1), K(2.0, fill_opacity=0.9), K(3.4, fill_opacity=0.22),
                  K(5.2, fill_opacity=0.22, edge_opacity=1), K(7.2, fill_opacity=0.0, edge_opacity=0.0),
                  K(72.6, fill_opacity=0, edge_opacity=0), K(73.5, fill_opacity=0.9, edge_opacity=1)]})
    for j, (lo, la, t0) in enumerate(((9.30, 47.66, 4.15), (9.55, 47.57, 4.35), (9.42, 47.52, 4.55))):
        add({"kind": "sprite", "asset": "question", "at": ll(lo, la), "size": 120, "start": t0, "end": 6.2, "keys": pop(t0, 6.2)})
    add({"kind": "label", "text": "Bodensee", "at": ll(9.36, 47.63), "on_map": True, "height_m": 3200, "angle": AXIS,
         "start": 5.8, "end": 7.9, **WHITE, "keys": [K(5.8, opacity=0, scale=1.25), K(6.15, opacity=1, scale=1, ease="out3"),
                                                     K(7.5, opacity=1), K(7.9, opacity=0)]})
    # ---- drei Länder -----------------------------------------------------------
    cols = {"DE": [255, 206, 0], "AT": [235, 40, 45], "CH": [255, 255, 255]}
    times = {"DE": 9.75, "AT": 10.55, "CH": 11.35}
    labels = {"DE": ("Deutschland", (9.40, 47.80)), "AT": ("Österreich", (9.88, 47.56)), "CH": ("Schweiz", (9.22, 47.50))}
    for c in ("DE", "AT", "CH"):
        t0 = times[c]
        add({"kind": "polygon", "src": "near_" + c, "fill": cols[c], "feather": 25, "start": t0 - 0.1, "end": 14.8,
             "keys": [K(t0 - 0.1, fill_opacity=0), K(t0 + 0.25, fill_opacity=0.14), K(14.2, fill_opacity=0.14), K(14.8, fill_opacity=0)]})
        add({"kind": "lines", "src": "shore_" + c, "width": 4, "color": cols[c],
             "glow": {"color": cols[c], "width": 10, "strength": 1.4}, "start": t0 - 0.1, "end": 15.0,
             "keys": [K(t0 - 0.1, opacity=0), K(t0 + 0.25, opacity=1), K(14.4, opacity=1), K(15.0, opacity=0)]})
        txt, (lo, la) = labels[c]
        add({"kind": "label", "text": txt, "at": ll(lo, la), "size": 46, "start": t0, "end": 14.6, **WHITE,
             "glow": [0, 0, 0, 10, 0.35], "keys": pop(t0, 14.6)})
    # Grenze im See? – gestrichelte Linie zeichnet sich, zerfällt
    add({"kind": "path", "src": "midline", "start": 12.9, "end": 15.0, "core_width": 7, "core_color": [255, 60, 60],
         "dash": [26, 16], "glows": [{"width": 16, "blur": 6, "color": [255, 40, 40], "strength": 0.6}],
         "keys": [K(12.9, progress=0, opacity=1), K(13.9, progress=1, ease="inout"), K(14.3, opacity=1),
                  K(14.35, opacity=0.2), K(14.45, opacity=0.9), K(14.55, opacity=0.1), K(14.7, opacity=0)]})
    add({"kind": "sprite", "asset": "question", "at": "camera", "size": 330, "start": 15.3, "end": 16.8, "keys": pop(15.3, 16.8)})
    # ---- Früher: Burgen, Klöster, Städte (Papier) --------------------------------
    sites = [("castle", 9.08, 47.78, 19.25), ("castle", 9.62, 47.70, 19.45), ("castle", 9.25, 47.48, 19.6),
             ("church", 9.30, 47.66, 20.15), ("church", 9.05, 47.70, 20.3), ("church", 9.55, 47.46, 20.45),
             ("town", 9.17, 47.66, 21.0), ("town", 9.68, 47.55, 21.15), ("town", 9.16, 47.77, 21.3), ("town", 9.48, 47.65, 21.45)]
    for a_, lo, la, t0 in sites:
        add({"kind": "sprite", "asset": a_, "at": ll(lo, la), "size": 150, "anchor": [0.5, 0.9], "size_zoom": 0.7,
             "ref_mpp": 115, "start": t0, "end": 27.2, "keys": pop(t0, 27.2)})
    reich = [ll(*p) for p in ((6.0, 46.3), (13.5, 46.0), (14.5, 50.5), (5.5, 50.8), (4.8, 48.0))]
    add({"kind": "polygon", "points": reich, "start": 22.4, "end": 31.4, "fill": [140, 70, 170], "feather": 40,
         "keys": [K(22.4, fill_opacity=0), K(23.2, fill_opacity=0.3), K(29.9, fill_opacity=0.3), K(30.5, fill_opacity=0.12),
                  K(30.6, fill_opacity=0.25), K(31.3, fill_opacity=0)]})
    add({"kind": "label", "text": "Heiliges Römisches Reich", "at": ll(9.40, 48.15), "size": 54, "start": 23.0, "end": 26.0,
         **SERIF, "color": [70, 30, 90], "keys": fade(23.0, 26.0)})
    add({"kind": "polygon", "src": "lake_parts", "fill": [120, 200, 255], "fill_mode": "lighten", "start": 25.4, "end": 27.6,
         "keys": [K(25.4, fill_opacity=0), K(26.0, fill_opacity=0.5), K(26.6, fill_opacity=0.2), K(27.1, fill_opacity=0.5), K(27.6, fill_opacity=0)]})
    # ---- Schweiz geht eigene Wege, Reich zerfällt --------------------------------
    add({"kind": "polygon", "src": "country_CH", "fill": [220, 40, 40], "feather": 20, "start": 28.0, "end": 34.6,
         "keys": [K(28.0, fill_opacity=0), K(28.6, fill_opacity=0.3), K(31.4, fill_opacity=0.3), K(32.4, fill_opacity=0.12),
                  K(34.0, fill_opacity=0.12), K(34.6, fill_opacity=0)]})
    add({"kind": "label", "text": "Schweiz", "at": ll(9.02, 47.47), "dy": -130, "size": 54, "start": 28.3, "end": 31.2, **SERIF,
         "color": [150, 20, 20], "keys": pop(28.3, 31.2)})
    add({"kind": "sprite", "asset": "fig_swiss", "at": ll(9.38, 47.40), "size": 130, "anchor": [0.5, 0.95], "start": 28.2,
         "end": 31.3, "keys": [K(28.2, scale=0.2, opacity=0), K(28.45, scale=1, opacity=1, ease="back_out"),
                               K(29.6, dy=0), K(30.8, dy=60, opacity=1), K(31.2, opacity=0)]})
    # ---- mehrere Staaten -------------------------------------------------------
    states = [("Baden", 9.02, 47.79, 32.6), ("Württemberg", 9.47, 47.70, 32.9), ("Bayern", 9.70, 47.60, 33.15),
              ("Österreich", 9.80, 47.46, 33.4), ("Schweiz", 9.30, 47.53, 33.65)]
    for txt, lo, la, t0 in states:
        add({"kind": "label", "text": txt, "at": ll(lo, la), "size": 44, "start": t0, "end": 35.2, **SERIF, "keys": pop(t0, 35.2)})
    # ---- Untersee 1854: Lineal + Bleistift zeichnen die Grenze Strich für Strich -------
    add({"kind": "path", "src": "border_untersee", "start": 35.7, "end": 40.0, "core_width": 5, "core_color": [180, 30, 30],
         "keys": [K(35.7, progress=0), K(38.6, progress=1, ease="inout"), K(39.5, opacity=1), K(40.0, opacity=0)]})
    add({"kind": "sprite", "asset": "ruler", "at": "camera", "dx": 40, "dy": 250, "size": 140, "rot": 0, "start": 35.0, "end": 39.4,
         "keys": [K(35.0, dx=900, dy=230, rot=-90), K(35.5, dx=0, ease="out3"), K(38.7, dx=0), K(39.3, dx=-1100, ease="in")]})
    add({"kind": "sprite", "asset": "pencil", "on_path": "border_untersee", "size": 380, "anchor": [0.0, 0.5], "start": 35.3, "end": 39.6,
         "keys": [K(35.3, pos=0, opacity=0, rot=-35, dy=-200), K(35.7, pos=0, opacity=1, dy=0, ease="out3"),
                  K(38.6, pos=1, ease="inout"), K(39.0, dy=0, opacity=1), K(39.5, dy=-500, opacity=0, ease="in")]})
    add({"kind": "label", "text": "1854", "at": ll(9.02, 47.705), "size": 78, "font": "playfair-display-latin-400",
         "render_px": 200, "color": [60, 42, 32], "start": 36.6, "end": 39.6, "keys": pop(36.6, 39.6)})
    # Obersee: Bleistift kommt, zögert, fliegt weg
    add({"kind": "sprite", "asset": "pencil", "at": ll(9.44, 47.59), "size": 380, "anchor": [0.0, 0.5], "start": 39.7, "end": 41.9,
         "keys": [K(39.7, dx=600, dy=-300, rot=-35, opacity=1), K(40.3, dx=40, dy=-40, ease="out3"), K(40.7, dx=60, dy=-60),
                  K(40.95, dx=40, dy=-40, rot=-32), K(41.5, dx=900, dy=-700, rot=20, ease="in")]})
    # ---- drei Meinungen ----------------------------------------------------------
    figs = {"swiss": (9.37, 47.555, 42.3), "austrian": (9.74, 47.495, 42.6), "german": (9.47, 47.665, 42.9)}
    for k, (lo, la, t0) in figs.items():
        add({"kind": "sprite", "asset": "fig_" + k, "at": ll(lo, la), "size": 190, "anchor": [0.5, 0.95],
             "size_zoom": 0.6, "ref_mpp": 50, "start": t0, "end": 59.2, "keys": pop(t0, 59.2)})
    # Schweiz: Grenze genau in der Mitte (rot, zeichnet sich)
    add({"kind": "path", "src": "midline", "start": 46.9, "end": 59.0, "core_width": 5, "core_color": [220, 30, 30],
         "glows": [{"width": 14, "blur": 5, "color": [255, 40, 40], "strength": 0.5}],
         "keys": [K(46.9, progress=0), K(48.9, progress=1, ease="inout"), K(50.6, opacity=1), K(51.2, opacity=0.25), K(58.4, opacity=0.25), K(59.0, opacity=0)]})
    # Österreich: See gehört allen -> Schraffur in drei Farben
    hcol = [[255, 206, 0], [235, 40, 45], [255, 255, 255]]
    for g, col in zip(hatch_lines(), hcol):
        add({"kind": "lines", "points": g, "start": 51.0, "end": 59.0, "width": 4, "color": col, "alpha": 0.6,
             "reveal_dir": [1.0, -0.4],
             "keys": [K(51.0, reveal=0, opacity=1), K(52.6, reveal=1, ease="inout"), K(54.2, opacity=1), K(54.8, opacity=0.15),
                      K(58.4, opacity=0.15), K(59.0, opacity=0)]})
    # Deutschland: Stempel
    add({"kind": "sprite", "asset": "stamp", "at": "camera", "dy": 260, "size": 560, "start": 57.0, "end": 59.4,
         "keys": [K(57.0, scale=2.6, opacity=0, rot=-14), K(57.25, scale=1, opacity=1, ease="in"), K(58.9, opacity=1), K(59.4, opacity=0)]})
    # ---- es funktioniert trotzdem: Fisch, Schiff, Wasser, Verbindungen -------------
    for a_, lo, la, t0 in (("fish", 9.33, 47.63, 62.0), ("ship", 9.46, 47.60, 62.75), ("drop", 9.58, 47.56, 63.55)):
        add({"kind": "sprite", "asset": a_, "at": ll(lo, la), "size": 175, "start": t0, "end": 66.6, "keys": pop(t0, 66.6)})
    tri = [ll(9.37, 47.555), ll(9.74, 47.495), ll(9.47, 47.665), ll(9.37, 47.555)]
    for k, (lo, la, t0) in figs.items():
        add({"kind": "sprite", "asset": "fig_" + k, "at": ll(lo, la), "size": 150, "anchor": [0.5, 0.95], "start": 64.3,
             "end": 66.6, "keys": pop(64.3, 66.6)})
    add({"kind": "path", "points": tri, "start": 64.6, "end": 66.6, "core_width": 4, "core_color": [255, 230, 80], "dash": [20, 12],
         "keys": [K(64.6, progress=0), K(65.8, progress=1, ease="inout"), K(66.2, opacity=1), K(66.6, opacity=0)]})
    add({"kind": "sprite", "asset": "question", "at": "camera", "size": 420, "start": 67.1, "end": 69.2, "keys": pop(67.1, 69.2)})
    # ---- Trinkwasser: Leitungen leuchten nach Norden ------------------------------
    for j, pts in enumerate(VEC["pipes"]):
        add({"kind": "path", "points": pts, "start": 69.3, "end": 72.9, "core_width": 3, "core_color": [210, 240, 255],
             "glows": [{"width": 18, "blur": 8, "color": [60, 170, 255], "strength": 1.0}],
             "keys": [K(69.3 + 0.12 * j, progress=0), K(71.2 + 0.12 * j, progress=1, ease="out"), K(72.3, opacity=1), K(72.9, opacity=0)]})
    add({"kind": "polygon", "src": "lake_parts", "fill": [80, 190, 255], "fill_mode": "lighten", "start": 69.2, "end": 72.8,
         "keys": [K(69.2, fill_opacity=0), K(69.7, fill_opacity=0.5), K(72.2, fill_opacity=0.5), K(72.8, fill_opacity=0)]})
    z = {"raster": 0}
    I.sort(key=lambda it: z.get(it["kind"], 1))
    return I


def audio():
    out = [{"id": "voice", "src": "audio/voice.mp3", "start": 0.0, "gain_db": 0.0}]
    drops = [[46.0, 49.3], [50.6, 53.6], [55.0, 58.6]]  # Musik pausiert bei den Zitaten
    t = 0.0
    for a, b in drops + [[DUR, DUR]]:
        if a > t:
            out.append({"id": f"music_{t:.1f}", "src": "audio/music_bed.wav", "start": t, "trim": [t, a],
                        "gain_db": -18.0, "fade_out": 0.1})
        t = b
    pops = [4.15, 4.35, 4.55, 9.75, 10.55, 11.35, 15.3, 19.25, 19.45, 19.6, 20.15, 20.3, 20.45, 21.0, 21.15, 21.3, 21.45,
            28.2, 32.6, 32.9, 33.15, 33.4, 33.65, 36.6, 42.3, 42.6, 42.9, 62.0, 62.75, 63.55, 64.3, 67.1]
    for s in pops:
        out.append({"src": "@sfx/pop", "start": round(s - 0.02, 3), "gain_db": -15})
    for s in (1.4, 16.7, 24.0, 35.0, 39.8, 59.2, 72.2):
        out.append({"src": "@sfx/soft_whoosh", "start": s, "gain_db": -19})
    out.append({"src": "@sfx/impact_low", "start": 57.22, "gain_db": -12})
    out.append({"src": "@sfx/click", "start": 57.22, "gain_db": -12})
    return out


def main():
    mb = os.path.join(P, "audio", "music_bed.wav")
    if not os.path.exists(mb):
        from shortsfactory.audio import sfx
        sfx.write_wav(mb, sfx.ambient_bed(DUR + 1, seed=11))
    tl = {
        "meta": {"fps": 30, "width": 1080, "height": 1920, "duration": DUR, "style_profile": "map_doc",
                 "attribution": ["Contains modified Copernicus Sentinel data 2024/2025",
                                 "© OpenStreetMap contributors, Overture Maps Foundation (ODbL)",
                                 "Terrain: AWS Terrain Tiles (SRTM, USGS 3DEP)"]},
        "assets": build_assets(),
        "maps": {"bs": {"rasters": {k: f"assets/maps/{k}.json" for k in ("europe", "region", "sat", "sat_wide", "paper", "paper_wide")},
                        "masks": {"valid": "assets/maps/sat_valid_mask.png", "lake": "assets/maps/sat_lake_mask.png",
                                  "valid_wide": "assets/maps/sat_wide_valid_mask.png"},
                        "vectors": "assets/maps/vectors.json"}},
        "layers": [{"id": "map", "type": "map", "map": "bs", "start": 0, "end": DUR, "keys": camera(), "items": items()}],
        "captions": captions(),
        "audio": audio(),
    }
    os.makedirs(os.path.join(P, "build"), exist_ok=True)
    json.dump(tl, open(os.path.join(P, "build", "timeline.json"), "w"), separators=(",", ":"), ensure_ascii=False)
    print("items", len(tl["layers"][0]["items"]), "captions", len(tl["captions"]["words"]))


if __name__ == "__main__":
    main()
