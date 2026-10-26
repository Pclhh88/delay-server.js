"""Bäume und Hecken: Stamm + Äste + aus vielen verformten Kugeln gebaute Krone."""
import math
import random
from mathutils import Vector, noise
from .meshkit import MeshBuilder

TREE_TYPES = {
    #           Laub          Kronen-Radius  Stammhöhe  Büschel  Form
    'round':   ('leaf_green',  1.0,  1.1, 14, (1.0, 1.0, 1.05)),
    'dark':    ('leaf_dark',   1.0,  1.1, 14, (1.0, 1.0, 1.1)),
    'tall':    ('leaf_green',  1.15, 2.4, 18, (1.0, 1.0, 1.25)),
    'orange':  ('leaf_orange', 1.1,  1.3, 18, (1.0, 1.0, 1.1)),
    'ochre':   ('leaf_ochre',  1.0,  1.2, 16, (1.0, 1.0, 1.1)),
    'blossom': ('leaf_white',  0.9,  1.2, 10, (1.0, 1.0, 0.9)),
    'small':   ('leaf_green',  0.6,  0.9, 8, (1.0, 1.0, 1.1)),
}


def crown_height(kind, size=1.0):
    """Höhe der Kronenmitte über dem Fußpunkt (für die Platzierung aus dem Bild)."""
    _, R, trunk_h, _, shape = TREE_TYPES[kind]
    return (trunk_h + R * shape[2] * 0.85) * size


def _jitter(seed, amp=0.18, freq=2.2):
    off = Vector((seed * 1.37, seed * 2.11, seed * 0.73))

    def f(p):
        return 1.0 + amp * noise.noise(p * freq + off) + 0.08 * noise.noise(p * freq * 3 + off)
    return f


def build_tree(name, kind, location, materials, collection, size=1.0, seed=0):
    leaf, R, trunk_h, nclumps, shape = TREE_TYPES[kind]
    rng = random.Random(seed)
    R *= size
    trunk_h *= size
    mb = MeshBuilder()
    tr = 0.07 * size + 0.03
    mb.cylinder((0, 0, 0), tr * 1.25, trunk_h + R * 0.5, 'bark', seg=8, r_top=tr * 0.7)
    cz = trunk_h + R * shape[2] * 0.85
    # Äste
    for k in range(4 if kind != 'blossom' else 7):
        a = rng.uniform(0, 2 * math.pi)
        z0 = trunk_h * rng.uniform(0.75, 1.0)
        L = R * rng.uniform(0.5, 0.9)
        p1 = Vector((math.cos(a) * L, math.sin(a) * L, z0 + L * rng.uniform(0.5, 0.9)))
        mb.beam((0, 0, z0), p1, tr * 0.6, 'bark')
        if kind == 'blossom':
            for j in range(3):
                a2 = a + rng.uniform(-0.8, 0.8)
                p2 = p1 + Vector((math.cos(a2) * L * 0.5, math.sin(a2) * L * 0.5, L * rng.uniform(0.2, 0.6)))
                mb.beam(p1, p2, tr * 0.3, 'bark')
    # Krone: Büschel auf einer Ellipsoid-Hülle + Kern
    mb.sphere((0, 0, cz), R * 0.78, leaf, seg=14, rings=10,
              scale=shape, jitter=_jitter(seed, 0.12))
    for k in range(nclumps):
        u = rng.uniform(-1, 1)
        a = rng.uniform(0, 2 * math.pi)
        rr = math.sqrt(1 - u * u)
        d = Vector((rr * math.cos(a), rr * math.sin(a), u * 0.8 + 0.1))
        r = R * rng.uniform(0.32, 0.5) * (0.75 if kind == 'blossom' else 1.0)
        c = Vector((d.x * R * 0.62 * shape[0], d.y * R * 0.62 * shape[1], cz + d.z * R * 0.6 * shape[2]))
        mb.sphere(c, r, leaf, seg=10, rings=7, jitter=_jitter(seed * 31 + k, 0.22, 3.0))
    return mb.build(name, materials, collection, location=location, rotation=rng.uniform(0, 6.28))


def build_hedge(name, points, materials, collection, height=0.45, width=0.55, seed=0):
    """Hecke entlang einer Punktliste (Weltkoordinaten), aus Blobs zusammengesetzt."""
    rng = random.Random(seed)
    mb = MeshBuilder()
    c0 = Vector(points[0])
    pts = [Vector(p) - c0 for p in points]
    for a, b in zip(pts, pts[1:]):
        L = (b - a).length
        n = max(1, int(L / (width * 0.6)))
        for k in range(n):
            p = a + (b - a) * (k / n)
            h = height * rng.uniform(0.8, 1.15)
            mb.sphere((p.x, p.y, h * 0.55), width * rng.uniform(0.5, 0.65), 'hedge', seg=10, rings=7,
                      scale=(1, 1, h / width * 1.1), jitter=_jitter(seed * 7 + k, 0.2, 3.0))
    return mb.build(name, materials, collection, location=(c0.x, c0.y, c0.z if len(c0) > 2 else 0))


def build_bush(name, location, materials, collection, r=0.35, seed=0, mat='hedge'):
    rng = random.Random(seed)
    mb = MeshBuilder()
    for k in range(4):
        mb.sphere((rng.uniform(-r, r) * 0.6, rng.uniform(-r, r) * 0.6, r * 0.6), r * rng.uniform(0.6, 0.9),
                  mat, seg=10, rings=7, jitter=_jitter(seed + k, 0.2, 3.0))
    return mb.build(name, materials, collection, location=location)
