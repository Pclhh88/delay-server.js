"""Diorama-Kachel wie im Referenzbild (B2): abgerundete Insel mit Ringstraße,
Gehwegen, einem Häuserblock mit individuellen Gebäuden und dem Wahrzeichen
als Mittelpunkt. Ein Video kann aus mehreren solcher Kacheln bestehen
(eine pro Sehenswürdigkeit) – alles hier ist stadtunabhängig.
"""
import math
import random

import bpy

from . import details
from .house_detail import build_house, footprint, random_spec
from .mesh import MeshBuilder, rounded_rect
from .vehicles import Path

CAR_COLORS = ["car_red", "car_blue", "car_cream", "car_grey", "car_green", "car_yellow", "white", "dark"]


class Diorama:
    def __init__(self, col, family="rome", seed=3, half=14.0, corner=5.5, road_w=2.2, block_half=10.9,
                 hero_ellipse=(8.0, 7.0), skip_corners=(3,), front_rows_floors=(3, 3)):
        self.col = col
        self.family = family
        self.rng = random.Random(seed)
        self.half, self.corner, self.road_w = half, corner, road_w
        self.block_half = block_half
        self.hero = hero_ellipse  # Freifläche für das Wahrzeichen (Halbachsen)
        self.skip_corners = skip_corners
        self.front_floors = front_rows_floors
        self.n_house = 0
        self.footprints = []

    # ------------------------------------------------------------------
    def build(self):
        self._base_and_roads()
        self._block()
        self._street_furniture()
        self._traffic()
        return self

    def _base_and_roads(self):
        h, c = self.half, self.corner
        mb = MeshBuilder()
        mb.polygon_prism(rounded_rect(2 * h, 2 * h, c, 12), -0.45, 0.45, "sidewalk")        # Sockel
        rc = self.half - 1.0 - self.road_w / 2                                                # Straßenmitte
        self.ring = rounded_rect(2 * rc, 2 * rc, c - 1.6, 12)
        mb.strip(self.ring, self.road_w, 0.005, "asphalt", closed=True)
        # Bordsteine
        for off in (self.road_w / 2 + 0.06, -self.road_w / 2 - 0.06):
            pts = rounded_rect(2 * (rc + off), 2 * (rc + off), c - 1.6 + off, 12)
            mb.strip(pts, 0.12, 0.09, "stone_light", thickness=0.09, closed=True)
        # Innerer Block (Gehweg) leicht erhöht
        bh = self.block_half
        mb.polygon_prism(rounded_rect(2 * bh, 2 * bh, c - 3.2, 12), 0.0, 0.09, "sidewalk")
        mb.polygon_prism(rounded_rect(2 * (bh - 1.0), 2 * (bh - 1.0), c - 4.0, 12), 0.09, 0.01, "plaza")
        # Fahrbahnmarkierung (gestrichelt + Rand)
        path = Path(self.ring, True)
        s = 0.3
        while s < path.length:
            (x, y), a = path.at(s)
            mb.box((x, y, 0.012), (0.42, 0.05, 0.01), "road_line", rz=a)
            s += 0.95
        for off in (self.road_w / 2 - 0.12, -self.road_w / 2 + 0.12):
            pts = rounded_rect(2 * (rc + off), 2 * (rc + off), c - 1.6 + off, 12)
            mb.strip(pts, 0.035, 0.011, "road_line", closed=True)
        # Zebrastreifen an zwei Seiten
        for (x, y, a) in [(0, -rc, 0), (rc, 0, math.pi / 2)]:
            for k in range(7):
                o = -self.road_w / 2 + 0.2 + k * (self.road_w - 0.4) / 6
                dx, dy = (-math.sin(a) * o, math.cos(a) * o)
                mb.box((x + dx + 2.5 * math.cos(a), y + dy + 2.5 * math.sin(a), 0.012), (0.9, 0.14, 0.01),
                       "road_line", rz=a)
        self.base = mb.build("diorama_base", self.col, bevel=0.03)
        self.road_center = rc

    # ------------------------------------------------------------------
    def _house(self, pts, rot, cx, cy, blind, floors=None):
        rng = self.rng
        spec = random_spec(self.family, rng)
        if floors:
            spec["floors"] = rng.randint(*floors)
            spec["tops"] = (spec["tops"] + ["flat"] * 6)[:spec["floors"]]
        self.n_house += 1
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self.footprints.append((cx, cy, 0.5 * math.hypot(max(xs) - min(xs), max(ys) - min(ys))))
        ob, H = build_house(pts, spec, blind=blind, seed=rng.randint(0, 9999),
                            name=f"house_{self.n_house:02d}", collection=self.col)
        ob.location = (cx, cy, 0.09)
        ob.rotation_euler = (0, 0, math.radians(rot))
        return ob

    def _free(self, cx, cy, w, d, rot):
        """Prüft, ob die Grundfläche die Wahrzeichen-Ellipse freilässt."""
        a, b = self.hero
        ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        for u in (-w / 2, 0, w / 2):
            for v in (-d / 2, 0, d / 2):
                x, y = cx + u * ca - v * sa, cy + u * sa + v * ca
                if (x / a) ** 2 + (y / b) ** 2 < 1:
                    return False
        return True

    def _block(self):
        F = self.block_half - 0.25  # Bauflucht
        C = 3.3                     # Eckhaus-Größe
        rng = self.rng
        # Seiten: (Rotation, Funktion t -> Mittelpunkt) ; 0 = vorne (-y)
        sides = [(0, lambda t, d: (t, -F + d / 2)), (90, lambda t, d: (F - d / 2, t)),
                 (180, lambda t, d: (-t, F - d / 2)), (270, lambda t, d: (-F + d / 2, -t))]
        corners = [(F - C / 2, -F + C / 2, 0), (F - C / 2, F - C / 2, 90), (-F + C / 2, F - C / 2, 180),
                   (-F + C / 2, -F + C / 2, 270)]
        for k, (cx, cy, rot) in enumerate(corners):
            if k in self.skip_corners:
                continue
            pts = footprint(C, C, rng.choice(["round", "chamfer", "round"]), which=(0,), r=rng.uniform(0.6, 1.0))
            n = len(pts)
            self._house(pts, rot, cx, cy, blind=[n - 2, n - 1])
        for si, (rot, place) in enumerate(sides):
            t = -F + C
            end = F - C
            front = si in (0, 3)
            # an der übersprungenen Ecke offen enden (Sichtachse aufs Wahrzeichen)
            if si == 3 and 3 in self.skip_corners:
                end = F - C - 2.5
            if si == 0 and 3 in self.skip_corners:
                t = -F + C + 2.5
            lots = []
            while t < end - 1.0:
                w = min(rng.uniform(2.2, 3.4), end - t)
                lots.append((t, w))
                t += w
            park = 3 in self.skip_corners
            for i, (t, w) in enumerate(lots):
                d = rng.uniform(2.4, 3.0)
                cxy = place(t + w / 2, d)
                if not self._free(cxy[0], cxy[1], w, d, rot):
                    self._trees_at(cxy[0], cxy[1], 2)
                    continue
                blind = [1, 3]
                if park and si == 0 and i == 0:
                    blind.remove(3)   # Giebel zum Park hin mit Fenstern
                if park and si == 3 and i == len(lots) - 1:
                    blind.remove(1)
                self._house(footprint(w, d), rot, cxy[0], cxy[1], blind, self.front_floors if front else None)
        # Park in der freien Ecke (vorne links) mit Hecken, Bänken, Bäumen
        if 3 in self.skip_corners:
            px, py = -F + 2.6, -F + 2.6
            for k in range(5):
                a = rng.uniform(0, 2 * math.pi)
                self._tree(px + 1.9 * math.cos(a) * rng.random(), py + 1.9 * math.sin(a) * rng.random())
            hd = details.hedge("hedge_park", self.col, 4.0, h=0.28)
            hd.location = (px + 0.4, -F + 0.35, 0.1)
            hd2 = details.hedge("hedge_park2", self.col, 4.0, h=0.28)
            hd2.location = (-F + 0.35, py + 0.4, 0.1)
            hd2.rotation_euler = (0, 0, math.pi / 2)
            mb = MeshBuilder()
            details.bench(mb, px + 0.8, py - 0.8, 0.1, math.pi / 4)
            details.bench(mb, px - 0.6, py + 0.9, 0.1, -math.pi / 4)
            mb.build("park_furniture", self.col)

    def fill_greenery(self, n=40, avoid_ellipse=None, pines=0):
        """Bäume in freie Flächen des Blocks streuen (Plätze, Höfe)."""
        rng = self.rng
        lim = self.block_half - 0.9
        placed = 0
        tries = 0
        trees = list(self.footprints)
        while placed < n and tries < n * 40:
            tries += 1
            x, y = rng.uniform(-lim, lim), rng.uniform(-lim, lim)
            if avoid_ellipse and (x / avoid_ellipse[0]) ** 2 + (y / avoid_ellipse[1]) ** 2 < 1:
                continue
            if any(math.hypot(x - fx, y - fy) < fr + 0.45 for fx, fy, fr in trees):
                continue
            if placed < pines:
                t = details.fluffy_tree(f"pine_{placed}", self.col, rng.randint(0, 9999), "leaf_dark",
                                        size=rng.uniform(1.0, 1.3), shape="umbrella")
                t.location = (x, y, 0.1)
            else:
                self._tree(x, y)
            trees.append((x, y, 0.75))
            placed += 1
        return placed

    def _tree(self, x, y, leaf=None, size=None):
        rng = self.rng
        leaf = leaf or rng.choice(["leaf", "leaf", "leaf_light", "leaf_dark", "leaf_autumn", "leaf_olive"])
        ob = details.fluffy_tree(f"tree_{rng.randint(0, 1 << 30)}", self.col, rng.randint(0, 9999), leaf,
                                 size or rng.uniform(0.85, 1.25))
        ob.location = (x, y, 0.1)
        return ob

    def _trees_at(self, x, y, n):
        for _ in range(n):
            self._tree(x + self.rng.uniform(-0.8, 0.8), y + self.rng.uniform(-0.8, 0.8))

    def _street_furniture(self):
        rng = self.rng
        mb = MeshBuilder()
        outer = self.road_center + self.road_w / 2 + 0.45
        inner = self.road_center - self.road_w / 2 - 0.45
        for rc, every in ((outer, 3.6), (inner, 4.2)):
            pts = rounded_rect(2 * rc, 2 * rc, self.corner - 1.6 + (rc - self.road_center), 12)
            path = Path(pts, True)
            s = rng.uniform(0, 1)
            k = 0
            while s < path.length:
                (x, y), a = path.at(s)
                if k % 3 == 1 and rc == outer:
                    self._tree(x, y, size=rng.uniform(0.8, 1.1),
                               leaf=rng.choice(["leaf", "leaf_autumn", "leaf_light", "leaf_blossom"]))
                else:
                    details.lamp(mb, x, y, 0.09)
                for o in (-0.6, 0.6):
                    (bx, by), _ = path.at(s + o)
                    details.bollard(mb, bx, by, 0.09)
                s += every
                k += 1
        mb.build("street_furniture", self.col)
        # Hecke vorne am Rand (wie im Referenzbild)
        hd = details.hedge("hedge_front", self.col, 6.0, h=0.32, w=0.35)
        hd.location = (2.0, -self.half + 0.45, 0.0)

    def _traffic(self):
        rng = self.rng
        path = Path(self.ring, True)
        self.cars = []
        for k in range(9):
            s = path.length * (k + rng.uniform(0, 0.5)) / 9
            (x, y), a = path.at(s)
            lane = self.road_w * 0.24 * (1 if k % 2 else -1)
            nx, ny = math.sin(a), -math.cos(a)
            kind = rng.choice(["hatch", "hatch", "sedan", "van"])
            c = details.car(f"car_{k}", self.col, rng.choice(CAR_COLORS), kind)
            c.location = (x + nx * lane, y + ny * lane, 0.0)
            c.rotation_euler = (0, 0, a + (0 if lane < 0 else math.pi))
            self.cars.append(c)
