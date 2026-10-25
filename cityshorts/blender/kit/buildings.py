"""Parametrische Häuser in Architektur-Stilen.

Ein Stil ist nur ein Satz Parameter (Farben, Stockwerke, Dachformen, Details).
build_library() erzeugt pro Stil N Varianten einmalig; die Stadt platziert
davon nur Instanzen (Collection-Instances) -> schnell und wiederverwendbar.

Neue Stadt, neuer Look: Stil hier ergänzen oder in city.json "style" wählen.
"""
import math
import random

import bpy

from .mesh import MeshBuilder

STYLES = {
    # Rom / Mittelmeer: Ocker, Siena, Terrakotta-Walmdächer, grüne Läden, Dachterrassen
    "roman": {
        "walls": ["wall_ochre", "wall_sienna", "wall_cream", "wall_salmon", "wall_yellow", "wall_rose"],
        "roofs": ["roof_terracotta", "roof_terracotta2"],
        "roof_types": ["hip", "hip", "gable", "terrace"],
        "shutters": ["shutter_green", "shutter_green", "shutter_brown"],
        "floors": (2, 5), "floor_h": 0.62, "w": (2.2, 3.0), "d": (2.2, 2.9),
        "roof_pitch": 0.32, "awnings": ["awning_red", "awning_green"], "cornice": "wall_stone",
    },
    # Paris / Haussmann: Creme-Stein, blaugraue Mansarddächer, Kamine, Balkone
    "haussmann": {
        "walls": ["wall_cream", "wall_stone"],
        "roofs": ["roof_slate"],
        "roof_types": ["mansard"],
        "shutters": [],
        "floors": (5, 6), "floor_h": 0.6, "w": (2.8, 3.8), "d": (2.6, 3.4),
        "roof_pitch": 0.5, "awnings": ["awning_red"], "cornice": "white",
    },
    # neutral / Platzhalter für Städte ohne eigenen Stil
    "generic": {
        "walls": ["wall_cream", "wall_stone", "wall_salmon"],
        "roofs": ["roof_terracotta", "roof_slate"],
        "roof_types": ["gable", "hip", "flat"],
        "shutters": [],
        "floors": (2, 4), "floor_h": 0.62, "w": (2.4, 3.4), "d": (2.4, 3.2),
        "roof_pitch": 0.45, "awnings": [], "cornice": "white",
    },
}


def _facade_windows(mb, st, rng, w, d, floors, fh, shutter):
    """Fenster (+ Läden) auf allen vier Fassaden."""
    for side in range(4):
        along = w if side % 2 == 0 else d
        depth = d if side % 2 == 0 else w
        n = max(1, int(along / 0.75))
        for fl in range(floors):
            z = 0.28 + fl * fh + (0.08 if fl == 0 else 0)
            for i in range(n):
                u = -along / 2 + (i + 0.5) * along / n
                if fl == 0 and i == n // 2 and side == 0:
                    # Tür im Erdgeschoss
                    _place(mb, side, u, depth / 2, z - 0.2, 0.26, 0.42, "shutter_brown")
                    continue
                _place(mb, side, u, depth / 2, z, 0.2, 0.3, "glass")
                if shutter:
                    for s in (-1, 1):
                        _place(mb, side, u + s * 0.17, depth / 2 + 0.005, z, 0.1, 0.32, shutter)


def _place(mb, side, u, half_depth, z, ww, wh, mat, protrude=0.03):
    off = half_depth + protrude / 2 - 0.01
    if side == 0:
        mb.box((u, -off, z + wh / 2), (ww, protrude, wh), mat)
    elif side == 2:
        mb.box((-u, off, z + wh / 2), (ww, protrude, wh), mat)
    elif side == 1:
        mb.box((off, u, z + wh / 2), (protrude, ww, wh), mat)
    else:
        mb.box((-off, -u, z + wh / 2), (protrude, ww, wh), mat)


def make_house(style_name, seed):
    st = STYLES[style_name]
    rng = random.Random(seed)
    mb = MeshBuilder()
    w = rng.uniform(*st["w"])
    d = rng.uniform(*st["d"])
    floors = rng.randint(*st["floors"])
    fh = st["floor_h"]
    h = floors * fh + 0.2
    wall = rng.choice(st["walls"])
    roof = rng.choice(st["roofs"])
    shutter = rng.choice(st["shutters"]) if st["shutters"] else None
    mb.box_on(0, 0, 0, w, d, h, wall)
    # Sockel + Gesims
    mb.box_on(0, 0, 0, w + 0.04, d + 0.04, 0.22, "wall_stone" if wall != "wall_stone" else "stone_grey")
    mb.box_on(0, 0, h - 0.06, w + 0.12, d + 0.12, 0.1, st["cornice"])
    _facade_windows(mb, st, rng, w, d, floors, fh, shutter)
    rt = rng.choice(st["roof_types"])
    pitch = st["roof_pitch"]
    if rt == "hip":
        mb.hip(0, 0, h + 0.04, w, d, min(w, d) * pitch, roof, overhang=0.12)
    elif rt == "gable":
        if w >= d:
            mb.prism(0, 0, h + 0.04, w, d, d * pitch, roof, overhang=0.1)
        else:
            mb.prism(0, 0, h + 0.04, d, w, w * pitch, roof, rz=math.pi / 2, overhang=0.1)
    elif rt == "mansard":
        mb.box_on(0, 0, h + 0.04, w - 0.1, d - 0.1, 0.5, roof)
        mb.hip(0, 0, h + 0.54, w - 0.5, d - 0.5, 0.25, roof)
        for i in range(max(2, int(w / 0.8))):
            x = -w / 2 + 0.4 + i * (w - 0.8) / max(1, int(w / 0.8) - 1)
            mb.box((x, -d / 2 + 0.1, h + 0.32), (0.22, 0.12, 0.28), "white")  # Gauben
        for s in (-1, 1):
            mb.box_on(s * (w / 2 - 0.5), d * 0.15, h + 0.5, 0.25, 0.4, 0.55, "wall_sienna")  # Kamine
    else:  # terrace / flat
        mb.box_on(0, 0, h + 0.04, w + 0.02, d + 0.02, 0.06, "roof_flat")
        mb.box_on(0, 0, h + 0.1, w, 0.06, 0.18, wall)  # Brüstung
        if rt == "terrace":
            # kleines Dachhäuschen + Kübelpflanzen + Sonnenschirm-Pergola
            mb.box_on(w * 0.2, d * 0.15, h + 0.1, w * 0.35, d * 0.35, 0.5, wall)
            mb.hip(w * 0.2, d * 0.15, h + 0.6, w * 0.35, d * 0.35, 0.15, roof, overhang=0.05)
            for k in range(rng.randint(2, 4)):
                px, py = rng.uniform(-w / 2 + 0.3, 0), rng.uniform(-d / 2 + 0.3, d / 2 - 0.3)
                mb.cyl((px, py, h + 0.1), 0.08, 0.1, "roof_terracotta", seg=8)
                mb.sphere((px, py, h + 0.27), 0.13, rng.choice(["leaf", "leaf_light"]), ico=1, smooth=False)
    # Markise im Erdgeschoss (Café-Look)
    if st["awnings"] and rng.random() < 0.45:
        aw = rng.choice(st["awnings"])
        mb.box((0, -d / 2 - 0.18, 0.62), (w * 0.7, 0.36, 0.04), aw)
        mb.box((0, -d / 2 - 0.36, 0.56), (w * 0.7, 0.02, 0.12), aw)
    return mb, (w, d, h)


def build_library(style_name, count, collection, seed=0):
    """Erzeugt `count` Hausvarianten als eigene Collections (für Instanzen)."""
    lib = []
    for i in range(count):
        mb, dims = make_house(style_name, seed * 1000 + i)
        sub = bpy.data.collections.new(f"LIB_{style_name}_{i:02d}")
        collection.children.link(sub)
        mb.build(f"house_{style_name}_{i:02d}", sub, bevel=0.025)
        lib.append((sub, dims))
    return lib
