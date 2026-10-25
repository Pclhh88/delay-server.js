"""Bäume als Bibliotheks-Varianten: Laubbaum, Pinie (Rom!), Zypresse, Herbstbaum."""
import math
import random

import bpy

from .mesh import MeshBuilder


def make_tree(kind, seed):
    rng = random.Random(seed)
    mb = MeshBuilder()
    if kind == "pine":  # Schirmpinie: hoher Stamm, flache breite Krone
        h = rng.uniform(2.2, 2.8)
        mb.cyl((0, 0, 0), 0.08, h, "trunk", seg=6, r2=0.05)
        for k in range(6):
            a = k / 6 * 6.283 + rng.uniform(-0.3, 0.3)
            r = rng.uniform(0.3, 0.6)
            mb.sphere((r * math.cos(a), r * math.sin(a), h + rng.uniform(-0.05, 0.1)),
                      rng.uniform(0.45, 0.6), "leaf_dark", s=(1, 1, 0.45), ico=2, smooth=True)
        mb.sphere((0, 0, h + 0.1), 0.7, "leaf_dark", s=(1, 1, 0.45), ico=2)
    elif kind == "cypress":
        h = rng.uniform(1.8, 2.6)
        mb.cyl((0, 0, 0), 0.05, 0.3, "trunk", seg=6)
        mb.sphere((0, 0, 0.25 + h / 2), 0.32, "leaf_dark", s=(1, 1, h / 0.64), ico=2)
    else:  # Laubbaum (auch Herbst): buschige Krone aus vielen kleinen Kugeln
        leafs = ["leaf_autumn", "leaf_autumn", "wall_ochre"] if kind == "autumn" else ["leaf", "leaf_light", "leaf"]
        h = rng.uniform(0.7, 1.0)
        mb.cyl((0, 0, 0), 0.06, h + 0.4, "trunk", seg=6, r2=0.035)
        cz = h + 0.55
        for k in range(34):
            u, v = rng.uniform(-1, 1), rng.uniform(0, 2 * math.pi)
            r = 0.5 * rng.random() ** 0.4
            x, y, z = r * math.sqrt(1 - u * u) * math.cos(v), r * math.sqrt(1 - u * u) * math.sin(v), r * u * 0.85
            mb.sphere((x, y, cz + z), rng.uniform(0.13, 0.22), rng.choice(leafs), ico=1, smooth=False)
    return mb


def build_library(kinds, per_kind, collection, seed=0):
    lib = {}
    for kind in kinds:
        lib[kind] = []
        for i in range(per_kind):
            sub = bpy.data.collections.new(f"LIB_tree_{kind}_{i}")
            collection.children.link(sub)
            make_tree(kind, seed * 100 + i + sum(map(ord, kind))).build(f"tree_{kind}_{i}", sub)
            lib[kind].append(sub)
    return lib
