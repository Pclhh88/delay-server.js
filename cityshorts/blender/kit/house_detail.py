"""Detaillierte Miniatur-Häuser im Look des Referenzbilds.

Statt aufgeklebter Fenster-Kästchen wird jede Fassade aus Pfeilern und
Brüstungsbändern aufgebaut, sodass Fenster echte Laibungen haben. Dazu
Rahmen mit Sprossen, Gesimse, durchgehende schmiedeeiserne Balkone,
Ladenzone mit Markisen, Mansarddach mit Gauben und Kaminen.

Ein Haus = Grundriss (konvexes Polygon, gegen den Uhrzeigersinn) + Stil.
Kanten in `blind` (Index) sind Brandwände zum Nachbarhaus (ohne Fenster).
"""
import math
import random

from .mesh import MeshBuilder, inset_polygon

STYLES = {
    "haussmann": {
        "wall": "stone_cream", "trim": "stone_light", "roof": "zinc_blue", "roof_shape": "mansard",
        "ground_h": 0.95, "floor_h": 0.62, "floors": 4, "bay": 0.5, "win_w": 0.25, "win_h": 0.68,
        "balcony_floors": [1, 4], "shutters": None, "hoods": [1], "awnings": ["awning_red", "awning_green"],
    },
    "haussmann_red": {
        "wall": "stone_warm", "trim": "stone_light", "roof": "zinc_red", "roof_shape": "mansard",
        "ground_h": 0.95, "floor_h": 0.6, "floors": 3, "bay": 0.5, "win_w": 0.25, "win_h": 0.66,
        "balcony_floors": [1], "shutters": None, "hoods": [1, 2], "awnings": ["awning_red"],
    },
    "roman": {
        "wall": "stone_ochre", "trim": "stone_light", "roof": "tile_terracotta", "roof_shape": "hip",
        "ground_h": 0.9, "floor_h": 0.6, "floors": 3, "bay": 0.55, "win_w": 0.22, "win_h": 0.6,
        "balcony_floors": [1], "shutters": "shutter_green", "hoods": [1], "awnings": ["awning_red"],
    },
}


class Facade:
    """Lokales Koordinatensystem einer Fassadenkante: u entlang, v nach außen."""

    def __init__(self, mb, p0, p1):
        self.mb = mb
        self.p0 = p0
        self.L = math.dist(p0, p1)
        self.ux, self.uy = (p1[0] - p0[0]) / self.L, (p1[1] - p0[1]) / self.L
        self.nx, self.ny = self.uy, -self.ux  # rechts = außen (CCW)
        self.rz = math.atan2(self.uy, self.ux)

    def box(self, u0, u1, v0, v1, z0, z1, mat):
        if u1 - u0 <= 1e-4 or z1 - z0 <= 1e-4:
            return
        u, v = (u0 + u1) / 2, (v0 + v1) / 2
        x = self.p0[0] + self.ux * u + self.nx * v
        y = self.p0[1] + self.uy * u + self.ny * v
        self.mb.box((x, y, (z0 + z1) / 2), (u1 - u0, v1 - v0, z1 - z0), mat, rz=self.rz)



REC = 0.06  # Tiefe der Fensterlaibung


def _window(f, u, z0, w, h, st, floor_idx, rng):
    t = 0.022
    f.box(u - w / 2, u + w / 2, -REC, -REC + 0.01, z0, z0 + h, "window_glass")
    for a, b, c, d in [(u - w / 2, u - w / 2 + t, z0, z0 + h), (u + w / 2 - t, u + w / 2, z0, z0 + h),
                       (u - w / 2, u + w / 2, z0 + h - t, z0 + h), (u - w / 2, u + w / 2, z0, z0 + t),
                       (u - t / 3, u + t / 3, z0, z0 + h), (u - w / 2, u + w / 2, z0 + h * 0.72, z0 + h * 0.72 + t * 0.7)]:
        f.box(a, b, -REC + 0.005, -REC + 0.025, c, d, "frame_white")
    for k in (0.33, 0.52):  # Quersprossen
        f.box(u - w / 2, u + w / 2, -REC + 0.008, -REC + 0.02, z0 + h * k, z0 + h * k + 0.008, "frame_white")
    f.box(u - w / 2 - 0.03, u + w / 2 + 0.03, -0.01, 0.035, z0 - 0.025, z0, st["trim"])  # Sims
    # Faschen (Rahmung) um die Öffnung
    for a, b in [(u - w / 2 - 0.035, u - w / 2), (u + w / 2, u + w / 2 + 0.035)]:
        f.box(a, b, 0.0, 0.012, z0, z0 + h, st["trim"])
    f.box(u - w / 2 - 0.035, u + w / 2 + 0.035, 0.0, 0.012, z0 + h, z0 + h + 0.035, st["trim"])
    if floor_idx in st["hoods"]:  # Verdachung
        f.box(u - w / 2 - 0.06, u + w / 2 + 0.06, 0.0, 0.05, z0 + h + 0.05, z0 + h + 0.085, st["trim"])
        f.box(u - w / 2 - 0.02, u + w / 2 + 0.02, 0.0, 0.03, z0 + h + 0.035, z0 + h + 0.05, st["trim"])
    if st["shutters"]:
        for s in (-1, 1):
            f.box(u + s * (w / 2 + 0.005) - (0.12 if s < 0 else 0), u + s * (w / 2 + 0.005) + (0.12 if s > 0 else 0),
                  0.0, 0.02, z0, z0 + h, st["shutters"])
            for k in range(6):  # Lamellen
                zz = z0 + 0.05 + k * (h - 0.1) / 5
                f.box(u + s * (w / 2 + 0.06) - 0.05, u + s * (w / 2 + 0.06) + 0.05, 0.02, 0.026, zz, zz + 0.008,
                      "dark")
    elif floor_idx not in st["balcony_floors"]:  # französischer Austritt (Brüstungsgitter)
        _railing(f, u - w / 2 - 0.01, u + w / 2 + 0.01, 0.015, z0, 0.15)


def _railing(f, u0, u1, v, z0, h, pitch=0.032):
    f.box(u0, u1, v, v + 0.012, z0 + h - 0.012, z0 + h, "iron")
    f.box(u0, u1, v, v + 0.01, z0 + 0.012, z0 + 0.022, "iron")
    n = max(2, int((u1 - u0) / pitch))
    for i in range(n + 1):
        u = u0 + (u1 - u0) * i / n
        f.box(u - 0.004, u + 0.004, v + 0.002, v + 0.008, z0, z0 + h, "iron")
        if i % 4 == 2:  # kleines Ornament
            f.box(u - 0.012, u + 0.012, v, v + 0.01, z0 + h * 0.45, z0 + h * 0.6, "iron")


def _bays(L, st):
    n = max(1, int(round(L / st["bay"])))
    return [(i + 0.5) * L / n for i in range(n)], L / n


def build_house(pts, style="haussmann", blind=(), seed=0, name="house", collection=None, floors=None):
    st = dict(STYLES[style])
    if floors:
        st["floors"] = floors
    rng = random.Random(seed)
    mb = MeshBuilder()
    gh, fh, nf = st["ground_h"], st["floor_h"], st["floors"]
    H = gh + nf * fh
    # Kern (zurückgesetzt um die Laibungstiefe)
    mb.polygon_prism(inset_polygon(pts, REC), 0, H, st["wall"])
    n = len(pts)
    for e in range(n):
        f = Facade(mb, pts[e], pts[(e + 1) % n])
        L = f.L
        if e in blind:
            f.box(0, L, -REC, 0, 0, H, st["wall"])
            continue
        us, bw = _bays(L, st)
        ww = min(st["win_w"], bw * 0.6)
        # --- Erdgeschoss: Läden, Tür, Rustika ---
        door = len(us) // 2 if len(us) > 2 else -1
        sw = min(bw * 0.78, 0.5)
        oh = gh * 0.72
        cuts = [(u - sw / 2, u + sw / 2) for u in us]
        _skin(f, cuts, L, 0, oh, gh, st["wall"], rustic=True)
        for i, u in enumerate(us):
            if i == door:
                f.box(u - sw / 2, u + sw / 2, -REC, -REC + 0.02, 0, oh, "shop_wood")
                f.box(u - 0.01, u + 0.01, -REC + 0.02, -REC + 0.03, 0, oh * 0.9, "dark")
                continue
            f.box(u - sw / 2, u + sw / 2, -REC, -REC + 0.01, 0.12, oh - 0.02, "window_glass")
            f.box(u - sw / 2, u + sw / 2, -REC, -REC + 0.03, 0, 0.12, "shop_wood")
            f.box(u - sw / 2, u + sw / 2, -REC, -REC + 0.03, oh - 0.1, oh, "shop_wood")
            for k in (1, 2):
                uu = u - sw / 2 + sw * k / 3
                f.box(uu - 0.008, uu + 0.008, -REC + 0.005, -REC + 0.025, 0.12, oh - 0.1, "shop_wood")
        if st["awnings"] and rng.random() < 0.8:
            aw = rng.choice(st["awnings"])
            for i, u in enumerate(us):
                if i != door:
                    _awning(f, u - sw / 2 - 0.02, u + sw / 2 + 0.02, oh, aw)
        f.box(-0.02, L + 0.02, 0, 0.05, gh - 0.06, gh, st["trim"])  # Gurtgesims
        # --- Obergeschosse ---
        for k in range(nf):
            z = gh + k * fh
            sill = z + 0.1
            wh = fh * 0.66
            cuts = [(u - ww / 2, u + ww / 2) for u in us]
            _skin(f, cuts, L, sill, sill + wh, fh, st["wall"], z0=z)
            for u in us:
                _window(f, u, sill, ww, wh, st, k + 1, rng)
            if (k + 1) in st["balcony_floors"]:
                f.box(-0.01, L + 0.01, 0, 0.16, sill - 0.035, sill, st["trim"])  # Balkonplatte
                for i in range(len(us) + 1):  # Konsolen
                    uc = min(max(i * bw, 0.03), L - 0.03)
                    f.box(uc - 0.02, uc + 0.02, 0.0, 0.14, sill - 0.08, sill - 0.035, st["trim"])
                _railing(f, 0.0, L, 0.145, sill, 0.17)
            if k == nf - 1:
                f.box(-0.04, L + 0.04, 0, 0.06, z + fh - 0.05, z + fh, st["trim"])
        # Hauptgesims
        f.box(-0.06, L + 0.06, 0, 0.1, H, H + 0.05, st["trim"])
        f.box(-0.08, L + 0.08, 0, 0.13, H + 0.05, H + 0.085, st["trim"])
        # Eck-Lisenen
        f.box(0, 0.05, 0, 0.012, gh, H, st["trim"])
        f.box(L - 0.05, L, 0, 0.012, gh, H, st["trim"])
    _roof(mb, pts, H + 0.085, st, blind, rng)
    ob = mb.build(name, collection, bevel=0.006) if collection else mb
    return ob, H


def _skin(f, cuts, L, o0, o1, h, mat, rustic=False, z0=None):
    """Wandhaut eines Geschosses mit Öffnungen [o0,o1] an den Stellen `cuts`."""
    z0 = o0 if z0 is None else z0
    top = z0 + h
    base = z0
    if o0 > base:
        f.box(0, L, -REC, 0, base, o0, mat)
    f.box(0, L, -REC, 0, o1, top, mat)
    edges = [0.0] + [c for cut in cuts for c in cut] + [L]
    for a, b in zip(edges[0::2], edges[1::2]):
        if not rustic:
            f.box(a, b, -REC, 0, o0, o1, mat)
            continue
        z = base
        while z < o1 - 1e-4:  # Rustika: Steinlagen mit Fugen
            z1 = min(z + 0.1, o1)
            f.box(a, b, -REC, 0.0 if int(z * 100) % 20 else 0.008, z + 0.008, z1, mat)
            f.box(a, b, -REC, -0.008, z, z + 0.008, mat)
            z = z1


def _awning(f, u0, u1, z, mat):
    for k in range(6):  # schräge Markise in Streifen
        a = k / 6
        f.box(u0, u1, 0.03 + a * 0.22, 0.03 + (a + 1 / 6) * 0.22, z - 0.03 - a * 0.12, z - a * 0.12, mat)
    f.box(u0, u1, 0.24, 0.26, z - 0.2, z - 0.12, mat)


def _roof(mb, pts, z, st, blind, rng):
    roof = st["roof"]
    if st["roof_shape"] == "hip":
        out = inset_polygon(pts, -0.18)
        mid = inset_polygon(pts, 0.9)
        mb.loft(out, z, mid, z + 0.55, roof, cap_top=True, cap_bottom=True)
        return
    # Mansarde: steiler Brisis-Teil + flacher Terrasson
    a = inset_polygon(pts, -0.02)
    b = inset_polygon(pts, 0.2)
    c = inset_polygon(pts, 0.6)
    h1 = 0.62
    mb.loft(a, z, b, z + h1, roof)
    mb.loft(b, z + h1, c, z + h1 + 0.16, roof, cap_top=True)
    mb.polygon_prism(inset_polygon(pts, 0.04), z, 0.02, "stone_light")
    mb.loft(inset_polygon(pts, 0.17), z + h1 - 0.02, inset_polygon(pts, 0.23), z + h1 + 0.02, "frame_white")  # Zinkleiste
    n = len(pts)
    for e in range(n):
        if e in blind:
            continue
        f = Facade(mb, pts[e], pts[(e + 1) % n])
        us, bw = _bays(f.L, st)
        for i, u in enumerate(us):
            if f.L > 1.2 and (i == 0 or i == len(us) - 1):
                continue
            _dormer(f, u, z, st)
    # Kamine auf den Brandwänden / im Dachfirst
    cen = (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n)
    for e in (list(blind) or [0]):
        p, q = pts[e], pts[(e + 1) % n]
        for t in (0.3, 0.7):
            x = p[0] + (q[0] - p[0]) * t
            y = p[1] + (q[1] - p[1]) * t
            x += (cen[0] - x) * 0.12
            y += (cen[1] - y) * 0.12
            mb.box((x, y, z + 0.55), (0.32, 0.18, 0.6), "brick")
            mb.box((x, y, z + 0.86), (0.36, 0.22, 0.04), "stone_light")
            for k in range(3):
                mb.cyl((x - 0.1 + k * 0.1, y, z + 0.88), 0.03, 0.09, "chimney_pot", seg=8)


def _dormer(f, u, z, st):
    w, h = 0.24, 0.36
    v0, v1 = -0.035, -0.4
    z += 0.04
    f.box(u - w / 2, u + w / 2, v1, v0, z, z + h, st["trim"])
    f.box(u - w / 2 + 0.04, u + w / 2 - 0.04, v0, v0 + 0.006, z + 0.06, z + h - 0.05, "window_glass")
    f.box(u - 0.006, u + 0.006, v0, v0 + 0.012, z + 0.06, z + h - 0.05, "frame_white")
    f.box(u - w / 2 + 0.04, u + w / 2 - 0.04, v0, v0 + 0.012, z + h * 0.55, z + h * 0.55 + 0.01, "frame_white")
    # Segmentbogen-Dach der Gaube
    x = f.p0[0] + f.ux * u + f.nx * v1
    y = f.p0[1] + f.uy * u + f.ny * v1
    f.mb.cyl((x, y, z + h), w / 2 + 0.03, abs(v1 - v0) + 0.04, st["roof"], seg=12,
             rx=math.pi / 2, rz=f.rz, smooth=False)
    f.box(u - w / 2 - 0.02, u + w / 2 + 0.02, v0, v0 + 0.03, z + h - 0.02, z + h + 0.02, st["trim"])
