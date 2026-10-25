"""Sonderbauten als Akzente im Stadtbild: Barockkirche mit Kuppel, Campanile.
Lokaler Ursprung = Mitte der Grundfläche, Hauptfassade nach -y."""
import math
import random

from .house_detail import Facade
from .mesh import MeshBuilder


def church(name, col, seed=0, wall="stone_cream", w=3.2, d=5.0):
    rng = random.Random(seed)
    mb = MeshBuilder()
    trim = "stone_light"
    h = 2.6 + rng.uniform(0, 0.4)
    mb.box_on(0, 0, 0, w, d, h, wall)                                   # Schiff
    mb.prism(0, 0, h, d + 0.1, w, 0.75, "tile_terracotta", rz=math.pi / 2, overhang=0.12)
    mb.box_on(0, -d / 2 + 0.1, h, w, 0.2, 0.05, trim)
    # Fassade: zwei Ordnungen mit Pilastern, Giebel, Voluten
    fy = -d / 2
    f = Facade(mb, (-w / 2 - 0.15, fy), (w / 2 + 0.15, fy))
    W = f.L
    f.box(0, W, -0.2, 0.05, 0, h * 0.55, wall)
    f.box(W * 0.18, W * 0.82, -0.2, 0.05, h * 0.55, h + 0.5, wall)
    for z0, z1, us in [(0, h * 0.55, (0.05, 0.3, W - 0.3, W - 0.05)), (h * 0.55 + 0.1, h + 0.4, (W * 0.2, W * 0.8))]:
        for u in us:
            f.box(u - 0.07, u + 0.07, 0.05, 0.1, z0, z1, trim)
        f.box(-0.02 if z0 == 0 else W * 0.16, W + 0.02 if z0 == 0 else W * 0.84, 0.05, 0.14, z1, z1 + 0.1, trim)
    f.pediment(W / 2, h + 0.5, W * 0.7, 0.45, 0.16, trim)
    for s in (-1, 1):  # Voluten (Viertelzylinder angedeutet)
        x, y = f.w(W / 2 + s * W * 0.36, 0.05)
        mb.cyl((x, y, h * 0.55 + 0.1), 0.22, 0.1, trim, seg=12, rx=math.pi / 2, rz=f.rz)
    f.box(W / 2 - 0.28, W / 2 + 0.28, -0.25, -0.2, 0, 0.95, "shop_wood")      # Portal
    f.arch_fill(W / 2 - 0.28, W / 2 + 0.28, 0.95, -0.2, 0.06, wall)
    f.arch_ring(W / 2 - 0.28, W / 2 + 0.28, 0.95, 0.06, trim)
    f.pediment(W / 2, 1.35, 0.8, 0.18, 0.12, trim)
    x, y = f.w(W / 2, 0.06)
    mb.cyl((x, y, h * 0.55 + 0.75), 0.2, 0.04, "window_glass", seg=16, rx=math.pi / 2, rz=f.rz)  # Rosette
    mb.cyl((x, y, h * 0.55 + 0.75), 0.24, 0.03, trim, seg=16, rx=math.pi / 2, rz=f.rz)
    for k in (-1, 1):  # Seitenfenster
        x, y = f.w(W / 2 + k * W * 0.33, 0.06)
        mb.box((x, y, h * 0.3), (0.22, 0.03, 0.45), "window_glass", rz=f.rz)
    # Kuppel über der Vierung
    cy = d * 0.18
    mb.cyl((0, cy, h), 1.0, 0.25, trim, seg=24)
    mb.cyl((0, cy, h + 0.25), 0.9, 0.7, wall, seg=24)
    for k in range(8):
        a = 2 * math.pi * k / 8
        mb.box((0.91 * math.cos(a), cy + 0.91 * math.sin(a), h + 0.6), (0.18, 0.04, 0.32), "window_glass", rz=a + math.pi / 2)
        mb.box((0.95 * math.cos(a + 0.39), cy + 0.95 * math.sin(a + 0.39), h + 0.6), (0.08, 0.08, 0.7), trim,
               rz=a + 0.39)
    mb.cyl((0, cy, h + 0.95), 0.98, 0.1, trim, seg=24)
    mb.sphere((0, cy, h + 1.05), 0.9, "lead_dome", seg=32, rings=16, s=(1, 1, 1.15), zmin=0)
    for k in range(12):  # Rippen
        a = 2 * math.pi * k / 12
        for j in range(6):
            phi = (j + 0.5) / 6 * math.pi / 2 * 0.9
            r = 0.91 * math.cos(phi)
            z = h + 1.05 + 0.91 * 1.15 * math.sin(phi)
            mb.box((r * math.cos(a), cy + r * math.sin(a), z), (0.04, 0.05, 0.2), trim, rz=a,
                   ry=-math.atan2(math.sin(phi), 1.15 * math.cos(phi)))
    lz = h + 1.05 + 0.9 * 1.15
    mb.cyl((0, cy, lz - 0.05), 0.2, 0.32, trim, seg=12)
    mb.cyl((0, cy, lz + 0.27), 0.22, 0.2, "lead_dome", seg=12, r2=0.03)
    mb.sphere((0, cy, lz + 0.52), 0.05, "gold", seg=8, rings=6)
    mb.box((0, cy, lz + 0.66), (0.02, 0.02, 0.2), "gold")
    mb.box((0, cy, lz + 0.7), (0.1, 0.02, 0.02), "gold")
    ob = mb.build(name, col, bevel=0.008)
    return ob, lz + 0.7


def campanile(name, col, seed=0, wall="brick", s=1.0):
    """Romanischer Glockenturm (z. B. wie Santa Maria in Cosmedin)."""
    rng = random.Random(seed)
    mb = MeshBuilder()
    w = 1.0 * s
    levels = rng.randint(5, 6)
    lh = 0.62 * s
    mb.box_on(0, 0, 0, w, w, 1.2 * s, wall)
    z = 1.2 * s
    for k in range(levels):
        mb.box_on(0, 0, z, w, w, lh, wall)
        mb.box_on(0, 0, z + lh - 0.04, w + 0.08, w + 0.08, 0.05, "stone_light")
        for e in range(4):
            pts = [(-w / 2, -w / 2), (w / 2, -w / 2), (w / 2, w / 2), (-w / 2, w / 2)]
            f = Facade(mb, pts[e], pts[(e + 1) % 4])
            n = 1 if k < 2 else (2 if k < levels - 1 else 3)
            ow = f.L / (n + 1) * 0.8
            zs = z + lh * 0.62 - ow / 2
            for i in range(n):
                u = (i + 1) * f.L / (n + 1)
                f.box(u - ow / 2, u + ow / 2, -0.12, -0.08, z + 0.08, zs + ow / 2, "dark")
                f.arch_fill(u - ow / 2, u + ow / 2, zs, -0.08, 0.005, wall, seg=8)
                f.box(u - ow / 2 - 0.005, u - ow / 2, -0.08, 0.005, z + 0.08, zs, wall)
            for i in range(n - 1):
                x, y = f.w((i + 1.5) * f.L / (n + 1), -0.04)
                mb.cyl((x, y, z + 0.08), 0.025, zs - z - 0.08, "stone_light", seg=6)
        z += lh
    mb.cyl((0, 0, z), w * 0.75, 0.6 * s, "tile_terracotta", seg=4, r2=0.02, rz=math.pi / 4, smooth=False)
    mb.box((0, 0, z + 0.7 * s), (0.02, 0.02, 0.22), "iron")
    ob = mb.build(name, col, bevel=0.006)
    return ob, z + 0.8 * s


def fountain_piazza(name, col, r=0.8):
    mb = MeshBuilder()
    mb.ring(r, r, r - 0.1, r - 0.1, 0, 0.18, "travertine", n=24)
    mb.cyl((0, 0, 0), r - 0.1, 0.14, "water", seg=24)
    mb.cyl((0, 0, 0), 0.1, 0.5, "travertine", seg=10)
    mb.cyl((0, 0, 0.45), 0.3, 0.06, "travertine", seg=16)
    mb.sphere((0, 0, 0.6), 0.1, "foam", seg=10, rings=6, s=(1, 1, 1.5))
    return mb.build(name, col, bevel=0.01)
