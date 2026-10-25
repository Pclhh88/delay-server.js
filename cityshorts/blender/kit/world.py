"""Diorama-Welt: Insel-Sockel, Straßen, Fluss, Brücken und automatische
Bebauung der freien Flächen mit Häusern und Bäumen aus der Bibliothek.

Eingabe ist city.json -> "world"; nur Wahrzeichen sind stadtspezifisch,
alles andere entsteht aus Regeln + Zufalls-Seed (reproduzierbar).
"""
import math
import random

import bpy

from . import buildings, vegetation
from .mesh import MeshBuilder, offset_polyline, rounded_rect
from .props import lamp
from .vehicles import Path


def _seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    u = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.hypot(p[0] - ax - u * dx, p[1] - ay - u * dy)


def poly_dist(p, pts, closed=False):
    segs = list(zip(pts, pts[1:])) + ([(pts[-1], pts[0])] if closed else [])
    return min(_seg_dist(p, a, b) for a, b in segs)


def _smooth(pts, iters=3):
    """Chaikin-Glättung für organische Flussläufe."""
    for _ in range(iters):
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]),
                    (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        out.append(pts[-1])
        pts = out
    return pts


class World:
    def __init__(self, cfg, collection, landmarks):
        self.cfg = cfg
        self.col = collection
        self.landmarks = landmarks  # [{"pos":(x,y), "rot":deg, "footprint":(hw,hd)}]
        self.half = cfg.get("half", 32)
        self.road_w = cfg.get("road_width", 2.2)
        self.rng = random.Random(cfg.get("seed", 1))
        inset = cfg.get("ring_inset", 2.4)
        self.ring = rounded_rect(2 * (self.half - inset), 2 * (self.half - inset), cfg.get("corner", 6) - 1.5, 6)
        self.streets = [[tuple(p) for p in s] for s in cfg.get("streets", [])]
        r = cfg.get("river")
        self.river = _smooth([tuple(p) for p in r["pts"]]) if r else None
        self.river_w = r.get("width", 4.0) if r else 0
        self.houses, self.trees, self.paths = [], [], []

    # ------------------------------------------------------------------
    def build(self, lib_col):
        self._base()
        self._roads()
        if self.river:
            self._river()
        self._fill(lib_col)
        self.paths.append(Path(self.ring, closed=True))
        for s in self.streets:
            self.paths.append(Path(s + s[-2:0:-1], closed=True))  # hin und zurück
        return self

    def _base(self):
        h = self.half
        outline = rounded_rect(2 * h, 2 * h, self.cfg.get("corner", 6), 10)
        mb = MeshBuilder()
        mb.polygon_prism(outline, -0.25, 0.25, "ground")
        mb.polygon_prism(rounded_rect(2 * h - 0.02, 2 * h - 0.02, self.cfg.get("corner", 6), 10), -1.6, 1.35, "soil")
        mb.polygon_prism(rounded_rect(2 * h - 0.3, 2 * h - 0.3, self.cfg.get("corner", 6), 10), -2.6, 1.0, "soil_dark")
        self.base = mb.build("island_base", self.col, bevel=0.15)

    def _roads(self):
        mb = MeshBuilder()
        w = self.road_w
        mb.strip(self.ring, w + 0.9, 0.05, "sidewalk", thickness=0.08, closed=True)
        mb.strip(self.ring, w, 0.07, "asphalt", closed=True)
        for s in self.streets:
            mb.strip(s, w + 0.9, 0.05, "sidewalk", thickness=0.08)
            mb.strip(s, w, 0.07, "asphalt")
        # Mittellinien (gestrichelt)
        for path in [Path(self.ring, True)] + [Path(s, False) for s in self.streets]:
            s = 0.5
            while s < path.length - 0.5:
                (x, y), a = path.at(s)
                if not (self.river and poly_dist((x, y), self.river) < self.river_w / 2 + 0.6):
                    mb.box((x, y, 0.075), (0.45, 0.06, 0.01), "road_line", rz=a)
                s += 1.1
        self.roads = mb.build("roads", self.col)

    def _river(self):
        mb = MeshBuilder()
        pts, w = self.river, self.river_w
        mb.strip(pts, w + 0.9, 0.02, "travertine_dark")              # Flussbett-Kante
        mb.strip(pts, w, 0.06, "water_river")
        for side in (-1, 1):                                           # Kaimauern
            mb.strip(offset_polyline(pts, side * (w / 2 + 0.22)), 0.44, 0.32, "travertine", thickness=0.3)
        river_ob = mb.build("river", self.col)
        # Brücken dort, wo Straßen den Fluss kreuzen
        bmb = MeshBuilder()
        for road in [self.ring + [self.ring[0]]] + self.streets:
            for a, b in zip(road, road[1:]):
                for t in [i / 40 for i in range(41)]:
                    p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                    if poly_dist(p, pts) < 0.3:
                        ang = math.atan2(b[1] - a[1], b[0] - a[0])
                        L = w + 2.2
                        bmb.box((p[0], p[1], 0.22), (L, self.road_w + 0.6, 0.22), "travertine", rz=ang)
                        bmb.box((p[0], p[1], 0.34), (L, self.road_w, 0.02), "asphalt", rz=ang)
                        for s in (-1, 1):
                            ox, oy = -math.sin(ang) * s * (self.road_w / 2 + 0.22), math.cos(ang) * s * (self.road_w / 2 + 0.22)
                            bmb.box((p[0] + ox, p[1] + oy, 0.45), (L, 0.15, 0.22), "travertine", rz=ang)
                        break
        if bmb.bm.verts:
            bmb.build("bridges", self.col, bevel=0.03)
        self.river_ob = river_ob

    # ------------------------------------------------------------------
    def road_z(self, x, y):
        """Fahrbahnhöhe (auf Brücken höher)."""
        if self.river and poly_dist((x, y), self.river) < self.river_w / 2 + 1.0:
            return 0.36
        return 0.08

    def _blocked(self, x, y, r):
        h = self.half - 2.4 - self.road_w / 2 - 0.5
        if abs(x) > h - r or abs(y) > h - r:
            return True
        clear = self.road_w / 2 + 0.4 + r
        for s in self.streets:
            if poly_dist((x, y), s) < clear:
                return True
        if self.river and poly_dist((x, y), self.river) < self.river_w / 2 + 0.45 + r:
            return True
        for lm in self.landmarks:
            lx, ly = lm["pos"]
            a = math.radians(-lm.get("rot", 0))
            dx, dy = x - lx, y - ly
            u, v = dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)
            hw, hd = lm["footprint"]
            ox, oy = lm.get("fp_center", (0, 0))
            u, v = u - ox, v - oy
            if abs(u) < hw + r and abs(v) < hd + r:
                return True
        return False

    def _nearest_road_angle(self, x, y):
        best, ang = 1e9, 0.0
        for road in [self.ring + [self.ring[0]]] + self.streets:
            for a, b in zip(road, road[1:]):
                d = _seg_dist((x, y), a, b)
                if d < best:
                    best = d
                    ang = math.atan2(b[1] - a[1], b[0] - a[0])
                    # Fassade (lokal -y) zur Straße drehen
                    cx = (a[0] + b[0]) / 2 - x
                    cy = (a[1] + b[1]) / 2 - y
                    side = (-math.sin(ang) * cx + math.cos(ang) * cy)
                    ang = ang if side < 0 else ang + math.pi
        return round(ang / (math.pi / 2)) * (math.pi / 2), best

    def _fill(self, lib_col):
        style = self.cfg.get("style", "generic")
        houses = buildings.build_library(style, self.cfg.get("house_variants", 14), lib_col, self.cfg.get("seed", 1))
        kinds = self.cfg.get("tree_kinds", ["round", "pine", "cypress"])
        trees = vegetation.build_library(kinds, 3, lib_col, self.cfg.get("seed", 1))
        step = self.cfg.get("lot_spacing", 3.3)
        park_ratio = self.cfg.get("park_ratio", 0.12)
        n = int(self.half / step) + 1
        rng = self.rng
        lamps = MeshBuilder()
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                x = i * step + rng.uniform(-0.25, 0.25)
                y = j * step + rng.uniform(-0.25, 0.25)
                if self._blocked(x, y, 1.3):
                    # Restflächen: einzelne Bäume, wenn wenigstens dafür Platz ist
                    if not self._blocked(x, y, 0.5) and rng.random() < 0.6:
                        self._tree(trees, kinds, x, y)
                    continue
                if rng.random() < park_ratio:
                    for _ in range(rng.randint(2, 4)):
                        self._tree(trees, kinds, x + rng.uniform(-1.3, 1.3), y + rng.uniform(-1.3, 1.3))
                    continue
                sub, dims = rng.choice(houses)
                ang, _ = self._nearest_road_angle(x, y)
                ob = bpy.data.objects.new(f"house_{i}_{j}", None)
                ob.instance_type = "COLLECTION"
                ob.instance_collection = sub
                ob.location = (x, y, 0)
                ob.rotation_euler = (0, 0, ang)
                self.col.objects.link(ob)
                self.houses.append(ob)
        # Straßenbäume + Laternen entlang des Rings
        ring = Path(self.ring, True)
        s = 0.0
        while s < ring.length:
            (x, y), a = ring.at(s)
            nx, ny = -math.sin(a), math.cos(a)
            px, py = x + nx * (self.road_w / 2 + 0.75), y + ny * (self.road_w / 2 + 0.75)
            if not (self.river and poly_dist((px, py), self.river) < self.river_w / 2 + 1):
                if int(s / 3.2) % 2 == 0:
                    self._tree(trees, kinds[:1] + ["autumn"] if "autumn" in kinds else kinds[:1], px, py, force=True)
                else:
                    lamp(lamps, px, py, 0.13)
            s += 3.2
        if lamps.bm.verts:
            lamps.build("lamps", self.col)

    def _tree(self, lib, kinds, x, y, force=False):
        if not force and self._blocked(x, y, 0.4):
            return
        kind = self.rng.choice(kinds)
        ob = bpy.data.objects.new(f"tree_{len(self.trees)}", None)
        ob.instance_type = "COLLECTION"
        ob.instance_collection = self.rng.choice(lib[kind])
        ob.location = (x, y, 0.1)
        ob.rotation_euler = (0, 0, self.rng.uniform(0, 6.28))
        s = self.rng.uniform(0.85, 1.15)
        ob.scale = (s, s, s)
        self.col.objects.link(ob)
        self.trees.append(ob)
