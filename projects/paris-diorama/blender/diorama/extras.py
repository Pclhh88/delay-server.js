"""Dachaufbauten und Kleinbauten: Kuppeltürmchen, Dachpavillon, Lüfter, Pavillon."""
import math
import random
from .meshkit import MeshBuilder


def build_cupola(name, location, materials, collection, s=1.0):
    """Weißes Türmchen mit Kuppel und Spitze (Dach des hinteren Hauses)."""
    mb = MeshBuilder()
    oct_ = [(math.cos(a) * 0.55 * s, math.sin(a) * 0.55 * s) for a in [math.pi / 8 + k * math.pi / 4 for k in range(8)]]
    mb.prism(oct_, 0, 1.3 * s, 'stone_light')
    for k in range(8):  # schmale Fenster
        a = k * math.pi / 4
        mb.box((math.cos(a) * 0.52 * s, math.sin(a) * 0.52 * s, 0.75 * s), (0.12 * s, 0.12 * s, 0.5 * s), 'glass', rot=a)
    mb.cylinder((0, 0, 1.3 * s), 0.62 * s, 0.1 * s, 'trim_white', seg=16)
    rings = []
    for k in range(9):
        t = k / 8 * math.pi / 2
        r = 0.55 * s * math.cos(t) + 0.02
        rings.append(([(math.cos(a) * r, math.sin(a) * r) for a in [j * math.pi / 8 for j in range(16)]],
                      1.4 * s + 0.9 * s * math.sin(t) ** 0.8 + 0.4 * s * (k / 8) ** 3))
    mb.loft(rings, 'zinc_light', smooth=True)
    mb.cylinder((0, 0, 2.6 * s), 0.12 * s, 0.35 * s, 'stone_light', seg=8)
    mb.cylinder((0, 0, 2.95 * s), 0.03 * s, 0.5 * s, 'gold', seg=6, r_top=0.005)
    # Sockelbau mit Fenstern
    mb.box((0.7 * s, 0, 0.4 * s), (1.2 * s, 1.3 * s, 0.8 * s), 'stone_light')
    mb.box((1.31 * s, 0, 0.45 * s), (0.02, 0.5 * s, 0.4 * s), 'glass')
    return mb.build(name, materials, collection, location=location)


def build_kiosk(name, location, materials, collection, s=1.0):
    """Dachpavillon mit grünem Kupferdach (rechtes Kuppelhaus)."""
    mb = MeshBuilder()
    mb.box((0, 0, 0.35 * s), (1.2 * s, 1.0 * s, 0.7 * s), 'stone_beige')
    for x in (-0.4, 0, 0.4):
        mb.box((x * s, -0.505 * s, 0.38 * s), (0.2 * s, 0.02, 0.4 * s), 'glass')
    rings = [([(-0.75 * s, -0.65 * s), (0.75 * s, -0.65 * s), (0.75 * s, 0.65 * s), (-0.75 * s, 0.65 * s)], 0.7 * s),
             ([(-0.55 * s, -0.45 * s), (0.55 * s, -0.45 * s), (0.55 * s, 0.45 * s), (-0.55 * s, 0.45 * s)], 0.95 * s)]
    mb.loft(rings, 'copper_green')
    for k in range(-4, 5):  # Rippen
        mb.beam((k * 0.15 * s, -0.66 * s, 0.71 * s), (k * 0.12 * s, -0.46 * s, 0.96 * s), 0.025, 'trim_white')
    return mb.build(name, materials, collection, location=location)


def build_roof_clutter(name, location, materials, collection, area=(2.0, 1.5), n=6, seed=0):
    """Lüftungskästen, Rohre, Satellitenschüsseln."""
    rng = random.Random(seed)
    mb = MeshBuilder()
    for k in range(n):
        x, y = rng.uniform(-area[0] / 2, area[0] / 2), rng.uniform(-area[1] / 2, area[1] / 2)
        t = rng.random()
        if t < 0.4:
            mb.box((x, y, 0.12), (rng.uniform(0.15, 0.35), rng.uniform(0.15, 0.3), 0.24), 'zinc_light')
        elif t < 0.7:
            mb.cylinder((x, y, 0), 0.04, rng.uniform(0.3, 0.6), 'zinc_light', seg=8)
            mb.cylinder((x, y, 0.55), 0.07, 0.04, 'zinc_light', seg=8)
        else:
            mb.cylinder((x, y, 0), 0.02, 0.2, 'iron_black', seg=6)
            mb.sphere((x, y, 0.28), 0.12, 'frame_white', seg=10, rings=6, scale=(1, 1, 0.35))
    return mb.build(name, materials, collection, location=location)


def build_pavilion(name, location, size, materials, collection, rot=0.0):
    """Niedriger Hofbau mit dunkelblauem Pultdach."""
    mb = MeshBuilder()
    w, d, h = size
    mb.box((0, 0, h / 2), (w, d, h), 'stone_beige')
    for k in range(int(w / 0.5)):
        mb.box((-w / 2 + 0.25 + k * 0.5, -d / 2 - 0.005, h * 0.5), (0.25, 0.02, h * 0.5), 'glass')
    mb.loft([([(-w / 2 - 0.1, -d / 2 - 0.1), (w / 2 + 0.1, -d / 2 - 0.1), (w / 2 + 0.1, d / 2 + 0.1), (-w / 2 - 0.1, d / 2 + 0.1)], h),
             ([(-w / 2 + 0.2, -d / 2 + 0.3), (w / 2 - 0.2, -d / 2 + 0.3), (w / 2 - 0.2, d / 2 - 0.1), (-w / 2 + 0.2, d / 2 - 0.1)], h + 0.4)],
            'zinc_blue')
    return mb.build(name, materials, collection, location=location, rotation=rot)
