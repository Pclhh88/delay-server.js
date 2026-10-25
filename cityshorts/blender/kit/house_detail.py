"""Detaillierte Miniatur-Häuser im Look des Referenzbilds (B2).

Jedes Haus entsteht aus Grundriss + Spezifikation. `random_spec()` würfelt
aus einer Stil-Familie (z. B. "paris", "rome") eine individuelle Variante:
Geschosszahl, Achsmaß, Fensterformen (gerade, Verdachung, Dreiecksgiebel,
Rundbogen), Balkone, Läden, Erdgeschoss (Läden, Arkaden, Rustika mit Portal),
Gliederung (Gesimse, Eckquader, Konsolen), Dach (Mansarde mit Gauben,
Walmdach mit Ziegeln, Flachdach mit Balustrade) und Dachlandschaft
(Kamine, Lüfter, Wassertanks, Antennen, Pflanzkübel, Pergola).

Fassaden werden aus Pfeilern und Bändern aufgebaut, sodass Fenster echte
Laibungen haben (keine aufgeklebten Kästchen).
"""
import math
import random

from .mesh import MeshBuilder, inset_polygon

REC = 0.06  # Tiefe der Fensterlaibung

FAMILIES = {
    "paris": {
        "walls": ["stone_cream", "stone_warm", "stone_tan", "stone_light", "stone_pinkish"],
        "roofs": [("mansard", "zinc_blue"), ("mansard", "zinc_dark"), ("mansard", "zinc_red"), ("flat", "rooftop_grey"),
                  ("hip", "zinc_dark")],
        "floors": (3, 6), "floor_h": (0.56, 0.64), "ground_h": (0.85, 1.0), "bay": (0.46, 0.56),
        "tops": ["flat", "hood", "hood", "pediment", "arch"], "shutters": [None],
        "grounds": ["shops", "shops", "arcade", "rustic"], "balconies": [[1], [1, 4], [1, 5], [2], []],
        "shops": ["shop_wood", "shop_green", "shop_red"], "awnings": ["awning_red", "awning_green", None],
    },
    "rome": {
        "walls": ["stone_ochre", "stone_sienna", "stone_salmon", "stone_yellow", "stone_cream", "stone_rose"],
        "roofs": [("hip", "tile_terracotta"), ("hip", "tile_terracotta"), ("gable", "tile_terracotta"),
                  ("gable", "tile_terracotta"), ("flat", "rooftop_grey"), ("mansard", "zinc_dark")],
        "floors": (2, 6), "floor_h": (0.56, 0.66), "ground_h": (0.85, 1.05), "bay": (0.5, 0.62),
        "tops": ["flat", "hood", "pediment", "arch", "flat"], "shutters": ["shutter_green", "shutter_green", "shutter_brown", None],
        "grounds": ["shops", "rustic", "arcade"], "balconies": [[1], [], [2], [1]],
        "shops": ["shop_wood", "shop_green"], "awnings": ["awning_red", "awning_green", None],
    },
}


def random_spec(family, rng, floors=None):
    """Würfelt ein individuelles Haus. `floors` (min, max) erlaubt Höhenzonen."""
    F = FAMILIES[family]
    shape, roof = rng.choice(F["roofs"])
    nf = rng.randint(*(floors or F["floors"]))
    facade = rng.choice(["classic", "classic", "plain", "painted"])
    tops = [rng.choice(F["tops"]) for _ in range(nf)]
    if rng.random() < 0.6:  # oberste Etage meist schlicht
        tops[-1] = "flat"
    if facade == "plain":
        tops = [t if t == "arch" and rng.random() < 0.5 else "flat" for t in tops]
    wall = rng.choice(F["walls"])
    return {
        "family": family, "wall": wall, "roof": roof, "roof_shape": shape,
        "trim": rng.choice(["stone_light", "stone_light", "frame_white", "stone_cream"]),
        "ground_wall": rng.choice(["stone_light", "travertine", "stone_tan"]) if rng.random() < 0.4 else wall,
        "floors": nf, "floor_h": rng.uniform(*F["floor_h"]), "ground_h": rng.uniform(*F["ground_h"]),
        "bay": rng.uniform(*F["bay"]), "win_w": rng.uniform(0.45, 0.64), "win_h": rng.uniform(0.56, 0.74),
        "bay_mode": rng.choice(["even", "even", "center", "pairs"]), "facade": facade,
        "tops": tops, "balcony_floors": rng.choice(F["balconies"]), "balconettes": rng.random() < 0.6,
        "shutters": rng.choice(F["shutters"]), "ground": rng.choice(F["grounds"]),
        "shop": rng.choice(F["shops"]), "awning": rng.choice(F["awnings"]),
        "quoins": rng.random() < 0.45, "strings": rng.random() < 0.65, "brackets": rng.random() < 0.55,
        "clutter": True, "balustrade": rng.random() < 0.5,
        # Details pro Fenster (vermeiden sichtbare Wiederholung)
        "p_closed": rng.uniform(0.0, 0.45), "p_flower": rng.uniform(0.0, 0.35),
        "p_balcony": rng.uniform(0.0, 0.22), "p_ac": rng.uniform(0.0, 0.12),
        "ivy": rng.random() < 0.25, "laundry": family == "rome" and rng.random() < 0.35,
        "loggia": rng.random() < 0.18, "setback": rng.random() < 0.22 and shape in ("flat", "hip"),
        "altana": rng.random() < 0.3,
    }


# ---------------------------------------------------------------------------
class Facade:
    """Lokales Koordinatensystem einer Fassadenkante: u entlang, v nach außen."""

    def __init__(self, mb, p0, p1):
        self.mb = mb
        self.p0 = p0
        self.L = math.dist(p0, p1)
        self.ux, self.uy = (p1[0] - p0[0]) / self.L, (p1[1] - p0[1]) / self.L
        self.nx, self.ny = self.uy, -self.ux  # rechts = außen (CCW)
        self.rz = math.atan2(self.uy, self.ux)

    def w(self, u, v):
        return (self.p0[0] + self.ux * u + self.nx * v, self.p0[1] + self.uy * u + self.ny * v)

    def box(self, u0, u1, v0, v1, z0, z1, mat):
        if u1 - u0 <= 1e-4 or z1 - z0 <= 1e-4 or v1 - v0 <= 1e-5:
            return
        x, y = self.w((u0 + u1) / 2, (v0 + v1) / 2)
        self.mb.box((x, y, (z0 + z1) / 2), (u1 - u0, v1 - v0, z1 - z0), mat, rz=self.rz)

    def pediment(self, u, z, width, height, depth, mat):
        x, y = self.w(u, depth / 2)
        self.mb.prism(x, y, z, depth, width, height, mat, rz=self.rz + math.pi / 2)

    def arch_fill(self, a, b, zs, v0, v1, mat, seg=10):
        """Füllt [a,b] x [zs, zs+r] außerhalb eines Halbkreises (Bogenzwickel)."""
        bm = self.mb.bm
        r, c = (b - a) / 2, (a + b) / 2
        arc = [(c - r * math.cos(math.pi * i / seg), zs + r * math.sin(math.pi * i / seg)) for i in range(seg + 1)]
        # äußere Randpunkte: linke Kante hoch, oben quer, rechte Kante runter
        outer = []
        for i in range(seg + 1):
            t = i / seg
            if t < 0.25:
                outer.append((a, zs + r * t / 0.25))
            elif t < 0.75:
                outer.append((a + (b - a) * (t - 0.25) / 0.5, zs + r))
            else:
                outer.append((b, zs + r * (1 - (t - 0.75) / 0.25)))
        verts = []

        def V(u, z, v):
            x, y = self.w(u, v)
            vv = bm.verts.new((x, y, z))
            verts.append(vv)
            return vv
        fa = [V(u, z, v1) for u, z in arc]
        fo = [V(u, z, v1) for u, z in outer]
        ba = [V(u, z, v0) for u, z in arc]
        bo = [V(u, z, v0) for u, z in outer]
        for i in range(seg):
            for quad in ((fa[i], fa[i + 1], fo[i + 1], fo[i]), (bo[i], bo[i + 1], ba[i + 1], ba[i]),
                         (ba[i], ba[i + 1], fa[i + 1], fa[i])):
                try:
                    bm.faces.new(quad)
                except ValueError:
                    pass
        self.mb._tag(verts, mat, False)

    def arch_ring(self, a, b, zs, v, mat, t=0.03, seg=12):
        """Archivolte: Profilring um einen Rundbogen."""
        r, c = (b - a) / 2 + t / 2, (a + b) / 2
        for i in range(seg):
            a0, a1 = math.pi * i / seg, math.pi * (i + 1) / seg
            am = (a0 + a1) / 2
            u, z = c - r * math.cos(am), zs + r * math.sin(am)
            x, y = self.w(u, v + 0.01)
            ln = r * math.pi / seg * 1.08
            self.mb.box((x, y, z), (ln, 0.02, t), mat, rz=self.rz, ry=am - math.pi / 2)
            if i == seg // 2:  # Schlussstein
                self.mb.box((x, y, z), (0.05, 0.03, 0.07), mat, rz=self.rz)


# ---------------------------------------------------------------------------
def _bays(L, spec):
    """Fensterachsen: gleichmäßig, mit betonter Mittelachse oder paarweise."""
    if L < 0.34:
        return [], L
    mode = spec.get("bay_mode", "even")
    n = max(1, int(round(L / spec["bay"])))
    if mode == "pairs" and L > 1.6:
        npair = max(1, int(round(L / (2.1 * spec["bay"]))))
        g = spec["bay"] * 0.36
        us = []
        for i in range(npair):
            c = (i + 0.5) * L / npair
            us += [c - g, c + g]
        return us, 2 * g
    if mode == "center" and n >= 3:
        if n % 2 == 0:
            n += 1
        w = [1.0] * n
        w[n // 2] = 1.35
        tot = sum(w)
        us, acc = [], 0.0
        for x in w:
            us.append((acc + x / 2) * L / tot)
            acc += x
        return us, L / tot
    return [(i + 0.5) * L / n for i in range(n)], L / n


def _railing(f, u0, u1, v, z0, h, pitch=0.03):
    f.box(u0, u1, v, v + 0.014, z0 + h - 0.014, z0 + h, "iron")
    f.box(u0, u1, v, v + 0.01, z0 + 0.015, z0 + 0.025, "iron")
    n = max(2, int((u1 - u0) / pitch))
    for i in range(n + 1):
        u = u0 + (u1 - u0) * i / n
        f.box(u - 0.0035, u + 0.0035, v + 0.002, v + 0.008, z0, z0 + h, "iron")
        if i % 3 == 1:
            f.box(u - 0.01, u + 0.01, v + 0.001, v + 0.009, z0 + h * 0.5, z0 + h * 0.62, "iron")


def _skin(f, cuts, L, o0, o1, z0, z1, mat):
    """Wandhaut eines Geschosses [z0,z1] mit Öffnungen [o0,o1] an `cuts`."""
    if o0 > z0:
        f.box(0, L, -REC, 0, z0, o0, mat)
    if z1 > o1:
        f.box(0, L, -REC, 0, o1, z1, mat)
    edges = [0.0] + [c for cut in cuts for c in cut] + [L]
    for a, b in zip(edges[0::2], edges[1::2]):
        f.box(a, b, -REC, 0, o0, o1, mat)


def _rustic(f, cuts, L, z0, z1, o1, mat):
    """Rustika-Erdgeschoss: Steinlagen mit tiefen Fugen."""
    edges = [0.0] + [c for cut in cuts for c in cut] + [L]
    z = z0
    k = 0
    while z < z1 - 1e-4:
        zz = min(z + 0.09, z1)
        if zz <= o1:
            for a, b in zip(edges[0::2], edges[1::2]):
                f.box(a, b, -REC, 0.012, z + 0.01, zz, mat)
        else:
            f.box(0, L, -REC, 0.012, max(z, o1) + 0.01, zz, mat)
        f.box(0, L, -REC, 0.0, z, z + 0.01, mat)  # Fuge (zurückliegend)
        z = zz
        k += 1


def _window(f, u, z0, w, h, spec, top, floor_idx, wall, rng=None):
    rng = rng or random.Random(0)
    t = 0.02
    trim = spec["trim"]
    facade = spec.get("facade", "classic")
    arch = top == "arch"
    hr = h - w / 2 if arch else h
    f.box(u - w / 2, u + w / 2, -REC, -REC + 0.008, z0, z0 + h, "window_glass")
    if rng.random() < 0.3:  # Vorhang/Innenraum hinter dem Glas
        f.box(u - w / 2 + 0.02, u + (rng.uniform(-0.1, 0.4)) * w / 2, -REC - 0.004, -REC + 0.002, z0 + 0.03,
              z0 + hr - 0.03, rng.choice(["white", "stone_cream", "wall_rose"]))
    for a, b, c, d in [(u - w / 2, u - w / 2 + t, z0, z0 + hr), (u + w / 2 - t, u + w / 2, z0, z0 + hr),
                       (u - w / 2, u + w / 2, z0, z0 + t), (u - t / 3, u + t / 3, z0, z0 + h - 0.01),
                       (u - w / 2, u + w / 2, z0 + hr * 0.7, z0 + hr * 0.7 + t * 0.7)]:
        f.box(a, b, -REC + 0.004, -REC + 0.022, c, d, "frame_white")
    f.box(u - w / 2, u + w / 2, -REC + 0.006, -REC + 0.018, z0 + hr * 0.36, z0 + hr * 0.36 + 0.007, "frame_white")
    if arch:
        f.box(u - w / 2, u + w / 2, -REC + 0.004, -REC + 0.022, z0 + hr - t, z0 + hr, "frame_white")
        f.arch_fill(u - w / 2, u + w / 2, z0 + hr, -REC, 0.0, wall)
        if facade != "plain":
            f.arch_ring(u - w / 2, u + w / 2, z0 + hr, 0.0, trim)
    # Sohlbank
    f.box(u - w / 2 - 0.035, u + w / 2 + 0.035, -0.01, 0.04, z0 - 0.028, z0, trim)
    if not arch and facade == "classic":  # plastische Faschen
        for a, b in [(u - w / 2 - 0.03, u - w / 2), (u + w / 2, u + w / 2 + 0.03)]:
            f.box(a, b, 0.0, 0.012, z0, z0 + h, trim)
        f.box(u - w / 2 - 0.03, u + w / 2 + 0.03, 0.0, 0.012, z0 + h, z0 + h + 0.03, trim)
    elif not arch and facade == "painted":  # aufgemalte, flache Rahmung
        f.box(u - w / 2 - 0.05, u + w / 2 + 0.05, 0.0, 0.003, z0 - 0.03, z0 + h + 0.05, trim)
    if facade != "plain":
        if top == "hood":
            f.box(u - w / 2 - 0.06, u + w / 2 + 0.06, 0.0, 0.055, z0 + h + 0.045, z0 + h + 0.08, trim)
            for s in (-1, 1):
                f.box(u + s * (w / 2 + 0.045) - 0.012, u + s * (w / 2 + 0.045) + 0.012, 0.0, 0.04, z0 + h - 0.05,
                      z0 + h + 0.045, trim)
        elif top == "pediment":
            f.box(u - w / 2 - 0.05, u + w / 2 + 0.05, 0.0, 0.05, z0 + h + 0.04, z0 + h + 0.065, trim)
            f.pediment(u, z0 + h + 0.065, w + 0.12, 0.09, 0.05, trim)
    single_balcony = floor_idx not in spec["balcony_floors"] and rng.random() < spec.get("p_balcony", 0)
    if spec["shutters"] and not arch:
        state = rng.random()
        pc = spec.get("p_closed", 0)
        for s in (-1, 1):
            closed = state < pc or (state < pc * 1.6 and s < 0)
            if closed:  # Laden geschlossen: liegt vor dem Glas
                a, b = (u - w / 2, u) if s < 0 else (u, u + w / 2)
                f.box(a, b, -REC + 0.022, -REC + 0.04, z0, z0 + h, spec["shutters"])
                for k in range(7):
                    zz = z0 + 0.04 + k * (h - 0.08) / 6
                    f.box(a + 0.01, b - 0.01, -REC + 0.04, -REC + 0.046, zz, zz + 0.008, "dark")
            else:
                u0 = u + s * (w / 2 + 0.01)
                a, b = (u0 - 0.13, u0) if s < 0 else (u0, u0 + 0.13)
                f.box(a, b, 0.0, 0.018, z0, z0 + h, spec["shutters"])
                for k in range(7):
                    zz = z0 + 0.04 + k * (h - 0.08) / 6
                    f.box(a + 0.015, b - 0.015, 0.018, 0.024, zz, zz + 0.01, "dark")
    elif spec["balconettes"] and floor_idx not in spec["balcony_floors"] and not single_balcony:
        _railing(f, u - w / 2 - 0.02, u + w / 2 + 0.02, 0.012, z0, 0.15)
    if single_balcony:  # einzelner Balkon mit Konsolen
        f.box(u - w / 2 - 0.1, u + w / 2 + 0.1, 0.0, 0.18, z0 - 0.035, z0, spec["trim"])
        for s in (-1, 1):
            f.box(u + s * (w / 2 + 0.06) - 0.015, u + s * (w / 2 + 0.06) + 0.015, 0.0, 0.15, z0 - 0.09, z0 - 0.035,
                  spec["trim"])
        _railing(f, u - w / 2 - 0.1, u + w / 2 + 0.1, 0.165, z0, 0.16)
        for s in (-1, 1):
            f.box(u + s * (w / 2 + 0.095) - 0.006, u + s * (w / 2 + 0.095) + 0.006, 0.0, 0.17, z0, z0 + 0.16, "iron")
    elif rng.random() < spec.get("p_flower", 0):  # Blumenkasten
        f.box(u - w / 2, u + w / 2, 0.035, 0.09, z0 + 0.0, z0 + 0.05, "chimney_pot")
        for k in range(4):
            uu = u - w / 2 + (k + 0.5) * w / 4
            x, y = f.w(uu, 0.065)
            f.mb.sphere((x, y, z0 + 0.07), 0.04, rng.choice(["hedge", "leaf_light"]), ico=1, smooth=False)
            if rng.random() < 0.6:
                f.mb.sphere((x, y + 0.0, z0 + 0.1), 0.018, rng.choice(["car_red", "wall_rose", "white", "car_yellow"]),
                            ico=1, smooth=False)
    if rng.random() < spec.get("p_ac", 0):  # Klimagerät neben dem Fenster
        side = rng.choice((-1, 1))
        uu = u + side * (w / 2 + 0.12)
        f.box(uu - 0.07, uu + 0.07, 0.0, 0.07, z0 + 0.02, z0 + 0.12, "metal")


def _ground(f, us, bw, L, spec, rng):
    gh = spec["ground_h"]
    kind = spec["ground"]
    wall, trim = spec.get("ground_wall", spec["wall"]), spec["trim"]
    door = len(us) // 2 if len(us) >= 3 else (0 if us and rng.random() < 0.4 else -1)
    if kind == "shops":
        sw = min(bw * 0.8, 0.52)
        oh = gh * 0.74
        cuts = [(u - sw / 2, u + sw / 2) for u in us]
        _rustic(f, cuts, L, 0, gh - 0.08, oh, wall)
        for i, u in enumerate(us):
            if i == door:
                f.box(u - sw / 2, u + sw / 2, -REC, -REC + 0.02, 0, oh, "shop_wood")
                f.box(u - 0.008, u + 0.008, -REC + 0.02, -REC + 0.028, 0, oh * 0.92, "dark")
                f.box(u - sw / 2 + 0.03, u + sw / 2 - 0.03, -REC + 0.02, -REC + 0.026, oh * 0.78, oh * 0.95, "window_glass")
                continue
            sm = spec["shop"]
            f.box(u - sw / 2, u + sw / 2, -REC, -REC + 0.008, 0.1, oh - 0.12, "window_glass")
            f.box(u - sw / 2, u + sw / 2, -REC, -REC + 0.035, 0, 0.1, sm)
            f.box(u - sw / 2, u + sw / 2, -REC, -REC + 0.04, oh - 0.12, oh, sm)  # Ladenschild
            f.box(u - sw / 4, u + sw / 4, -REC + 0.04, -REC + 0.046, oh - 0.095, oh - 0.025, "stone_light")
            for k in (1, 2):
                uu = u - sw / 2 + sw * k / 3
                f.box(uu - 0.007, uu + 0.007, -REC + 0.004, -REC + 0.026, 0.1, oh - 0.12, sm)
            if spec["awning"]:
                _awning(f, u - sw / 2 - 0.02, u + sw / 2 + 0.02, oh - 0.12, spec["awning"])
    else:
        arch = kind == "arcade"
        sw = min(bw * (0.7 if arch else 0.42), 0.5)
        oh = gh * (0.8 if arch else 0.62)
        cuts = [(u - sw / 2, u + sw / 2) for u in us]
        _rustic(f, cuts, L, 0, gh - 0.08, oh, wall)
        for i, u in enumerate(us):
            if arch or i == door:
                ww = sw if arch else min(bw * 0.6, 0.42)
                zs = oh - ww / 2
                f.box(u - ww / 2, u + ww / 2, -REC - 0.04, -REC - 0.03, 0, oh, "shop_wood" if i == door else "dark")
                f.arch_fill(u - ww / 2, u + ww / 2, zs, -REC, 0.012, wall)
                f.arch_ring(u - ww / 2, u + ww / 2, zs, 0.012, trim)
                if arch and i != door:
                    f.box(u - ww / 2, u + ww / 2, -REC - 0.03, -REC - 0.022, 0.08, zs, "window_glass")
            else:  # vergitterte Fenster
                z0 = gh * 0.25
                f.box(u - sw / 2, u + sw / 2, -REC, -REC + 0.008, z0, oh, "window_glass")
                for k in range(5):
                    uu = u - sw / 2 + sw * (k + 0.5) / 5
                    f.box(uu - 0.005, uu + 0.005, -REC + 0.01, -REC + 0.02, z0, oh, "iron")
    # Füllen über Öffnungen bis zum Gurtgesims
    f.box(0, L, -REC, 0.0, gh - 0.08, gh - 0.06, wall)
    f.box(-0.02, L + 0.02, 0, 0.05, gh - 0.07, gh, trim)


def _awning(f, u0, u1, z, mat):
    for k in range(6):
        a = k / 6
        f.box(u0, u1, 0.03 + a * 0.22, 0.03 + (a + 1 / 6) * 0.22, z - 0.03 - a * 0.12, z - a * 0.12, mat)
    for k in range(int((u1 - u0) / 0.05)):  # gewellte Kante
        uu = u0 + 0.025 + k * 0.05
        f.box(uu - 0.02, uu + 0.02, 0.245, 0.26, z - 0.2, z - 0.12, mat)


# ---------------------------------------------------------------------------
def footprint(w, d, corner="square", which=(1,), r=0.6, seg=4):
    """Rechteck (CCW, Front = Kante 0 bei -y) mit abgeschrägten/runden Ecken.
    which: Ecken 0=(+x,-y) 1=(+x,+y) 2=(-x,+y) 3=(-x,-y)."""
    corners = [(w / 2, -d / 2, 0), (w / 2, d / 2, 90), (-w / 2, d / 2, 180), (-w / 2, -d / 2, 270)]
    pts = []
    for k, (x, y, a0) in enumerate([corners[3]] + corners[:3]):
        idx = (k + 3) % 4
        if idx not in which or corner == "square":
            pts.append((x, y))
            continue
        sx, sy = (1 if x > 0 else -1), (1 if y > 0 else -1)
        cx, cy = x - sx * r, y - sy * r
        # Bogen von der vorherigen Kante zur nächsten (CCW)
        ang0 = {0: -90, 1: 0, 2: 90, 3: 180}[idx]
        n = 1 if corner == "chamfer" else seg
        for i in range(n + 1):
            a = math.radians(ang0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def build_house(pts, spec, blind=(), seed=0, name="house", collection=None):
    rng = random.Random(seed)
    mb = MeshBuilder()
    gh, fh, nf = spec["ground_h"], spec["floor_h"], spec["floors"]
    H = gh + nf * fh
    wall, trim = spec["wall"], spec["trim"]
    mb.polygon_prism(inset_polygon(pts, REC), 0, H, wall)
    n = len(pts)
    for e in range(n):
        f = Facade(mb, pts[e], pts[(e + 1) % n])
        L = f.L
        if e in blind:
            f.box(0, L, -REC, 0, 0, H, wall)
            continue
        us, bw = _bays(L, spec)
        if not us:  # schmale Kante (Rundung): glatte Wand mit Gesimsen
            f.box(0, L, -REC, 0, 0, H, wall)
            for k in range(nf):
                f.box(-0.01, L + 0.01, 0, 0.03, gh + k * fh - 0.02, gh + k * fh + 0.02, trim)
            f.box(-0.06, L + 0.06, 0, 0.1, H, H + 0.05, trim)
            continue
        ww = min(spec["win_w"] * bw, 0.3)
        if spec["ground"] != "none":
            _ground(f, us, bw, L, spec, rng)
        for k in range(nf):
            z = gh + k * fh
            top = spec["tops"][k]
            wh = fh * spec["win_h"]
            sill = z + (fh - wh) * 0.42
            cuts = [(u - ww / 2, u + ww / 2) for u in us]
            if not (spec.get("loggia") and k == nf - 1 and len(us) >= 2):
                _skin(f, cuts, L, sill, sill + wh, z, z + fh, wall)
            if spec.get("loggia") and k == nf - 1 and len(us) >= 2:
                _loggia(f, us, bw, L, z, fh, spec)
                continue
            for u in us:
                _window(f, u, sill, ww, wh, spec, top, k + 1, wall, rng)
            if (k + 1) in spec["balcony_floors"]:
                f.box(-0.01, L + 0.01, 0, 0.16, sill - 0.035, sill, trim)
                for i in range(len(us) + 1):
                    uc = min(max(i * bw, 0.03), L - 0.03)
                    f.box(uc - 0.018, uc + 0.018, 0.0, 0.14, sill - 0.09, sill - 0.035, trim)
                _railing(f, 0.0, L, 0.145, sill, 0.17)
            if spec["strings"] and k < nf - 1:
                f.box(-0.01, L + 0.01, 0, 0.025, z + fh - 0.02, z + fh + 0.015, trim)
        # Hauptgesims (evtl. mit Konsolen)
        f.box(-0.04, L + 0.04, 0, 0.06, H - 0.06, H, trim)
        f.box(-0.08, L + 0.08, 0, 0.13, H, H + 0.045, trim)
        f.box(-0.1, L + 0.1, 0, 0.16, H + 0.045, H + 0.075, trim)
        if spec["brackets"]:
            for i in range(int(L / 0.12) + 1):
                uu = 0.04 + i * (L - 0.08) / max(1, int(L / 0.12))
                f.box(uu - 0.015, uu + 0.015, 0.0, 0.12, H - 0.05, H, trim)
        if spec["quoins"]:
            for side in (0, 1):
                z = gh
                k = 0
                while z < H - 0.08:
                    ln = 0.16 if k % 2 else 0.1
                    a, b = (0, ln) if side == 0 else (L - ln, L)
                    f.box(a, b, 0, 0.014, z + 0.008, z + 0.1, trim)
                    z += 0.11
                    k += 1
        if spec.get("ivy") and rng.random() < 0.5:
            _ivy(f, rng.uniform(0.2, L - 0.2), min(H, rng.uniform(1.0, H)), rng)
        if spec.get("laundry") and len(us) >= 2 and rng.random() < 0.6:
            k = rng.randrange(nf)
            _laundry(f, us[0], us[1], gh + k * fh + fh * 0.2, rng)
    if spec.get("setback") and spec["floors"] >= 2:
        _setback(mb, pts, H + 0.075, spec, rng)
    else:
        _roof(mb, pts, H + 0.075, spec, blind, rng)
    ob = mb.build(name, collection, bevel=0.005) if collection else mb
    return ob, H


def _loggia(f, us, bw, L, z, fh, spec):
    """Oberstes Geschoss als offene Bogen-Loggia."""
    wall = spec["wall"]
    ow = bw * 0.72
    zs = z + fh * 0.88 - ow / 2
    cuts = [(u - ow / 2, u + ow / 2) for u in us]
    _skin(f, cuts, L, z + 0.06, zs + ow / 2, z, z + fh, wall)
    for u in us:
        f.box(u - ow / 2, u + ow / 2, -0.35, -0.3, z, z + fh, "travertine_dark")      # Rückwand (Schatten)
        f.arch_fill(u - ow / 2, u + ow / 2, zs, -REC, 0.0, wall)
        f.arch_ring(u - ow / 2, u + ow / 2, zs, 0.0, spec["trim"])
        _railing(f, u - ow / 2, u + ow / 2, -0.02, z + 0.06, 0.15)
    for i in range(len(us) - 1):  # Säulchen zwischen den Bögen
        uc = (us[i] + us[i + 1]) / 2
        x, y = f.w(uc, -0.02)
        f.mb.cyl((x, y, z + 0.06), 0.03, zs - z - 0.06, spec["trim"], seg=8)


def _ivy(f, u, h, rng):
    """Efeu/Kletterpflanze an der Fassade."""
    for k in range(int(30 * h)):
        zz = h * rng.random() ** 1.6
        spread = 0.08 + 0.25 * (1 - zz / h)
        uu = u + rng.uniform(-spread, spread)
        x, y = f.w(min(max(uu, 0.05), f.L - 0.05), 0.03)
        f.mb.sphere((x, y, zz + 0.05), rng.uniform(0.04, 0.08), rng.choice(["hedge", "leaf_dark", "leaf"]),
                    ico=1, smooth=False)


def _laundry(f, u0, u1, z, rng):
    """Wäscheleine zwischen zwei Fenstern (römisches Detail)."""
    f.box(u0, u1, 0.1, 0.104, z + 0.18, z + 0.184, "dark")
    for k in range(rng.randint(3, 5)):
        uu = u0 + (k + 0.5) * (u1 - u0) / 5 + rng.uniform(-0.03, 0.03)
        hh = rng.uniform(0.06, 0.12)
        f.box(uu - 0.03, uu + 0.03, 0.098, 0.106, z + 0.18 - hh, z + 0.18,
              rng.choice(["white", "car_blue", "car_red", "car_yellow", "wall_rose"]))


def _setback(mb, pts, z, spec, rng):
    """Zurückgesetztes Dachgeschoss mit umlaufender Terrasse."""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    inset = min(0.5, 0.2 * min(max(xs) - min(xs), max(ys) - min(ys)))
    mb.polygon_prism(inset_polygon(pts, 0.05), z - 0.02, 0.03, "rooftop_grey")
    n = len(pts)
    for e in range(n):
        f = Facade(mb, pts[e], pts[(e + 1) % n])
        _railing(f, 0.05, f.L - 0.05, -0.06, z, 0.17)
    sub = dict(spec, floors=1, ground="none", ground_h=0.0, setback=False, loggia=False, ivy=False,
               laundry=False, quoins=False, brackets=False, balcony_floors=[], balconettes=False,
               tops=["flat"], bay_mode="even", roof_shape=rng.choice(["hip", "flat"]))
    if sub["roof_shape"] == "hip" and spec["family"] == "rome":
        sub["roof"] = "tile_terracotta"
    smb, _ = build_house(inset_polygon(pts, inset), sub, blind=(), seed=rng.randint(0, 999))
    import mathutils
    mb.merge(smb, mathutils.Matrix.Translation((0, 0, z)))
    # Pflanzkübel auf der Terrasse
    for k in range(rng.randint(2, 5)):
        e = rng.randrange(n)
        p, q = pts[e], pts[(e + 1) % n]
        t = rng.uniform(0.2, 0.8)
        x, y = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
        cx, cy = sum(xs) / n, sum(ys) / n
        L = math.hypot(cx - x, cy - y) or 1
        x, y = x + (cx - x) / L * 0.25, y + (cy - y) / L * 0.25
        mb.box((x, y, z + 0.05), (0.12, 0.12, 0.1), "chimney_pot")
        mb.sphere((x, y, z + 0.17), 0.1, rng.choice(["leaf", "hedge", "leaf_light"]), ico=2)


# ---------------------------------------------------------------------------
def _roof(mb, pts, z, spec, blind, rng):
    roof = spec["roof"]
    n = len(pts)
    shape = spec["roof_shape"]
    if shape == "gable" and len(pts) == 4:
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        w, d = max(xs) - min(xs), max(ys) - min(ys)
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        along_x = w >= d
        span = d if along_x else w
        hgt = span * rng.uniform(0.22, 0.32)
        rz = 0.0 if along_x else math.pi / 2
        L1, L2 = (w, d) if along_x else (d, w)
        mb.prism(cx, cy, z, L1 + 0.1, L2, hgt, roof, rz=rz, overhang=0.18)
        # Giebeldreiecke in Wandfarbe
        for sgn in (-1, 1):
            ox, oy = (sgn * (L1 / 2 - 0.02), 0) if along_x else (0, sgn * (L1 / 2 - 0.02))
            mb.prism(cx + ox, cy + oy, z - 0.01, 0.04, L2 - 0.02, hgt - 0.03, spec["wall"], rz=rz)
        _chimneys(mb, pts, z + hgt * 0.3, blind, rng, 0.6)
        return
    if shape == "hip":
        out = inset_polygon(pts, -0.22)
        mb.loft(out, z - 0.02, out, z + 0.02, "shop_wood")  # Traufbrett
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        mid = inset_polygon(pts, min(0.75, 0.42 * min(max(xs) - min(xs), max(ys) - min(ys))))
        hgt = 0.5 + rng.uniform(0, 0.15)
        mb.loft(out, z + 0.02, mid, z + hgt, roof, cap_top=True, cap_bottom=True)
        if spec.get("altana") and len(pts) == 4:  # römische Dachterrasse (Altana)
            cx = sum(p[0] for p in mid) / len(mid)
            cy = sum(p[1] for p in mid) / len(mid)
            mb.box((cx, cy, z + hgt + 0.12), (0.9, 0.7, 0.24), spec["wall"])
            mb.box((cx, cy, z + hgt + 0.25), (0.96, 0.76, 0.03), "stone_light")
            f = Facade(mb, (cx - 0.48, cy - 0.38), (cx + 0.48, cy - 0.38))
            _railing(f, 0, 0.96, 0.0, z + hgt + 0.26, 0.14)
            for k in range(3):
                mb.sphere((cx - 0.3 + k * 0.3, cy + 0.2, z + hgt + 0.33), 0.08, "leaf_light", ico=2)
            for dx in (-0.4, 0.4):
                mb.box((cx + dx, cy - 0.3, z + hgt + 0.45), (0.02, 0.02, 0.4), "shop_wood")
            mb.box((cx, cy - 0.1, z + hgt + 0.66), (0.9, 0.5, 0.015), "shop_wood")
        _chimneys(mb, pts, z + hgt * 0.4, blind, rng, 0.75)
        return
    if shape == "flat":
        inner = inset_polygon(pts, 0.1)
        mb.polygon_prism(inner, z - 0.02, 0.03, roof)
        for e in range(n):
            if e in blind:
                continue
            f = Facade(mb, pts[e], pts[(e + 1) % n])
            if spec["balustrade"]:
                f.box(0.0, f.L, -0.08, 0.0, z, z + 0.035, "stone_light")
                f.box(0.0, f.L, -0.09, 0.01, z + 0.2, z + 0.235, "stone_light")
                for i in range(int(f.L / 0.06)):
                    uu = 0.04 + i * 0.06
                    x, y = f.w(uu, -0.04)
                    mb.cyl((x, y, z + 0.035), 0.016, 0.165, "stone_light", seg=6, r2=0.01)
            else:
                f.box(0.0, f.L, -0.1, 0.0, z, z + 0.16, spec["wall"])
                f.box(-0.01, f.L + 0.01, -0.11, 0.01, z + 0.16, z + 0.19, "stone_light")
        _clutter(mb, inner, z + 0.01, rng, rich=True)
        _chimneys(mb, pts, z, blind, rng, 0.25)
        return
    # Mansarde: steiler Brisis + flacher Terrasson + Gauben
    h1 = 0.6 + rng.uniform(-0.05, 0.08)
    a = inset_polygon(pts, -0.02)
    b = inset_polygon(pts, 0.17)
    c = inset_polygon(pts, 0.55)
    mb.loft(a, z, b, z + h1, roof)
    mb.loft(b, z + h1, c, z + h1 + 0.15, roof, cap_top=True)
    mb.loft(inset_polygon(pts, 0.15), z + h1 - 0.015, inset_polygon(pts, 0.2), z + h1 + 0.02, "frame_white")
    gtype = rng.choice(["pediment", "segment", "flat"])
    for e in range(n):
        if e in blind:
            continue
        f = Facade(mb, pts[e], pts[(e + 1) % n])
        us, bw = _bays(f.L, spec)
        for i, u in enumerate(us):
            _dormer(f, u, z, spec, gtype)
    _clutter(mb, c, z + h1 + 0.15, rng, rich=False)
    _chimneys(mb, pts, z + h1 * 0.6, blind, rng, 0.35)


def _dormer(f, u, z, spec, gtype):
    w, h = 0.22, 0.32
    v0, v1 = -0.035, -0.36
    z0 = z + 0.08
    trim = spec["trim"]
    f.box(u - w / 2, u + w / 2, v1, v0, z0, z0 + h, spec["wall"])
    f.box(u - w / 2 - 0.02, u - w / 2 + 0.02, v1, v0 + 0.012, z0, z0 + h, trim)
    f.box(u + w / 2 - 0.02, u + w / 2 + 0.02, v1, v0 + 0.012, z0, z0 + h, trim)
    f.box(u - w / 2 + 0.02, u + w / 2 - 0.02, v0 - 0.02, v0 - 0.012, z0 + 0.04, z0 + h - 0.03, "window_glass")
    f.box(u - 0.006, u + 0.006, v0 - 0.012, v0, z0 + 0.04, z0 + h - 0.03, "frame_white")
    f.box(u - w / 2 + 0.02, u + w / 2 - 0.02, v0 - 0.012, v0, z0 + h * 0.55, z0 + h * 0.55 + 0.01, "frame_white")
    f.box(u - w / 2 - 0.02, u + w / 2 + 0.02, v1, v0 + 0.02, z0 + h, z0 + h + 0.025, trim)
    top = z0 + h + 0.025
    x, y = f.w(u, (v0 + v1) / 2)
    if gtype == "pediment":
        f.mb.prism(x, y, top, abs(v1 - v0) + 0.03, w + 0.06, 0.12, spec["roof"], rz=f.rz + math.pi / 2)
    elif gtype == "segment":
        x2, y2 = f.w(u, v1)
        f.mb.cyl((x2, y2, top - 0.06), w / 2 + 0.04, abs(v1 - v0) + 0.05, spec["roof"], seg=12,
                 rx=math.pi / 2, rz=f.rz, smooth=False)
        f.box(u - w / 2 - 0.02, u + w / 2 + 0.02, v1, v1 + 0.02, top - 0.07, top, spec["roof"])
    else:
        f.box(u - w / 2 - 0.03, u + w / 2 + 0.03, v1 - 0.02, v0 + 0.035, top, top + 0.03, spec["roof"])


def _chimneys(mb, pts, z, blind, rng, inset):
    n = len(pts)
    cen = (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n)
    edges = list(blind) or [rng.randrange(n)]
    for e in edges:
        p, q = pts[e], pts[(e + 1) % n]
        for t in (0.28, 0.72) if math.dist(p, q) > 1.6 else (0.5,):
            x = p[0] + (q[0] - p[0]) * t
            y = p[1] + (q[1] - p[1]) * t
            x += (cen[0] - x) * inset / max(math.dist((x, y), cen), 1e-6)
            y += (cen[1] - y) * inset / max(math.dist((x, y), cen), 1e-6)
            ang = math.atan2(q[1] - p[1], q[0] - p[0])
            if rng.random() < 0.35:
                continue
            hh = 0.4 + rng.uniform(0, 0.18)
            mb.box((x, y, z + hh / 2), (0.32, 0.16, hh), "brick", rz=ang)
            mb.box((x, y, z + hh + 0.015), (0.35, 0.19, 0.04), "stone_light", rz=ang)
            for k in range(rng.randint(2, 3)):
                o = -0.1 + k * 0.1
                mb.cyl((x + math.cos(ang) * o, y + math.sin(ang) * o, z + hh + 0.035), 0.024,
                       0.07 + rng.uniform(0, 0.05), "chimney_pot", seg=8)


def _clutter(mb, poly, z, rng, rich):
    """Dachlandschaft: Lüfter, Wassertank, Antennen, Kübel, Aufzugshaus, Pergola."""
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    x0, x1, y0, y1 = min(xs) + 0.2, max(xs) - 0.2, min(ys) + 0.2, max(ys) - 0.2
    if x1 <= x0 or y1 <= y0:
        return

    def P():
        return rng.uniform(x0, x1), rng.uniform(y0, y1)
    for _ in range(rng.randint(2, 4)):  # Lüftungshauben
        x, y = P()
        mb.cyl((x, y, z), 0.04, 0.12, "metal", seg=8)
        mb.cyl((x, y, z + 0.12), 0.07, 0.04, "metal", seg=8, r2=0.02)
    if rng.random() < 0.6:
        x, y = P()
        mb.box((x, y, z + 0.035), (0.22, 0.14, 0.07), "metal")  # Klimagerät
    if rng.random() < 0.5:
        x, y = P()
        mb.cyl((x, y, z), 0.008, 0.45, "iron", seg=4)  # Antenne
        mb.box((x, y, z + 0.4), (0.2, 0.012, 0.012), "iron")
        mb.box((x, y, z + 0.32), (0.14, 0.012, 0.012), "iron")
    if rich:
        if rng.random() < 0.7:  # Treppenhaus-Aufbau
            x, y = P()
            mb.box((x, y, z + 0.2), (0.5, 0.4, 0.4), "stone_light")
            mb.box((x, y, z + 0.42), (0.56, 0.46, 0.04), "rooftop_grey")
            mb.box((x, y - 0.2, z + 0.15), (0.14, 0.01, 0.3), "shop_wood")
        if rng.random() < 0.5:  # Wassertank
            x, y = P()
            mb.cyl((x, y, z), 0.15, 0.3, "metal", seg=12)
            mb.cyl((x, y, z + 0.3), 0.16, 0.06, "metal", seg=12, r2=0.02)
        for _ in range(rng.randint(2, 6)):  # Pflanzkübel
            x, y = P()
            mb.box((x, y, z + 0.04), (0.12, 0.12, 0.08), "chimney_pot")
            mb.sphere((x, y, z + 0.14), 0.09, rng.choice(["leaf", "leaf_light", "hedge"]), ico=2)
        if rng.random() < 0.35:  # Pergola mit Sonnenschirm
            x, y = P()
            for dx in (-0.25, 0.25):
                for dy in (-0.2, 0.2):
                    mb.box((x + dx, y + dy, z + 0.15), (0.02, 0.02, 0.3), "shop_wood")
            for k in range(6):
                mb.box((x - 0.25 + k * 0.1, y, z + 0.31), (0.015, 0.46, 0.015), "shop_wood")
