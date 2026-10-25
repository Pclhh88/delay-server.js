"""Diorama-Kachel (Referenz B2) mit organisch gewachsenem Stadtteil.

Aufbau:
  * Kachel als abgerundetes Rechteck (Hochformat-Kachel passt zu 9:16),
    Ringstraße mit Bordsteinen, Markierung, Zebrastreifen.
  * Freiflächen: Wahrzeichen (Ellipse, frei positionierbar), Piazza mit
    Brunnen, gewundene Gasse, kleiner Park.
  * Bebauung in zwei Phasen:
      1. Randbebauung entlang der Straße mit wechselnden Breiten, Tiefen,
         Rücksprüngen, leichten Verdrehungen und gelegentlichen Durchgängen,
      2. Innenbebauung: kleinere Häuser, zufällig gepackt (Kollisionstest),
         dazwischen Höfe und Gassen.
  * Höhenzonen: vorne (zur Kamera) niedrig, hinten hoch -> Wahrzeichen
    bleibt sichtbar, Stadt wirkt gestaffelt.
  * Brandwände werden automatisch erkannt (Nachbar direkt an der Kante).
  * Jedes Haus, jeder Baum, jede Laterne, jede Person und jedes Auto ist ein
    eigenes Objekt (gleiche Requisiten teilen sich Mesh-Daten) -> einzeln
    animierbar (Aufbau-Animationen, Hervorheben, Fahren ...).
"""
import math
import random

import bpy

from . import details, props, specials
from .house_detail import build_house, footprint, random_spec
from .mesh import MeshBuilder, rounded_rect
from .vehicles import Path

CAR_COLORS = ["car_red", "car_blue", "car_cream", "car_grey", "car_green", "car_yellow", "white", "dark"]


# --- Geometrie-Helfer ------------------------------------------------------
def rect_corners(cx, cy, w, d, ang):
    c, s = math.cos(ang), math.sin(ang)
    return [(cx + u * c - v * s, cy + u * s + v * c) for u, v in ((-w / 2, -d / 2), (w / 2, -d / 2),
                                                                     (w / 2, d / 2), (-w / 2, d / 2))]


def _proj(poly, ax):
    vals = [p[0] * ax[0] + p[1] * ax[1] for p in poly]
    return min(vals), max(vals)


def overlap(a, b, margin=0.0):
    """SAT-Test zweier konvexer Polygone (margin > 0 verlangt Abstand)."""
    for poly in (a, b):
        n = len(poly)
        for i in range(n):
            x0, y0 = poly[i]
            x1, y1 = poly[(i + 1) % n]
            ax = (-(y1 - y0), x1 - x0)
            L = math.hypot(*ax) or 1
            ax = (ax[0] / L, ax[1] / L)
            a0, a1 = _proj(a, ax)
            b0, b1 = _proj(b, ax)
            if a1 + margin <= b0 or b1 + margin <= a0:
                return False
    return True


def inside(poly, x, y):
    n = len(poly)
    sign = 0
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        c = (x1 - x0) * (y - y0) - (y1 - y0) * (x - x0)
        if c != 0:
            if sign == 0:
                sign = 1 if c > 0 else -1
            elif (c > 0) != (sign > 0):
                return False
    return True


def _seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    u = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - a[0] - u * dx, p[1] - a[1] - u * dy)


class Prop:
    """Requisit mit geteilten Mesh-Daten: jede Platzierung ist ein eigenes Objekt
    (einzeln animierbar), das Mesh existiert nur einmal (speicherschonend)."""

    def __init__(self, col, name, build_fn):
        self.col, self.name, self.build_fn = col, name, build_fn
        self.mesh = None
        self.n = 0

    def place(self, x, y, z=0.0, rz=0.0, s=1.0):
        if self.mesh is None:
            mb = MeshBuilder()
            self.build_fn(mb)
            ob = mb.build(f"{self.name}_001", self.col)
            self.mesh = ob.data
        else:
            ob = bpy.data.objects.new(f"{self.name}_{self.n + 1:03d}", self.mesh)
            self.col.objects.link(ob)
        self.n += 1
        ob.location = (x, y, z)
        ob.rotation_euler = (0, 0, rz)
        ob.scale = (s, s, s)
        return ob


# --- Diorama ---------------------------------------------------------------
class Diorama:
    def __init__(self, col, family="rome", seed=3, hx=13.0, hy=17.0, corner=5.0, road_w=2.2,
                 hero=None, plazas=(), alleys=(), park=None, camera_dir=(-0.35, -1.0), specials_spec=()):
        """hero = {"pos": (x, y), "ellipse": (a, b), "rot": grad}
        plazas = [(x, y, r)], alleys = [[(x, y), ...], breite], park = (x, y, r)."""
        self.col = col
        self.family = family
        self.rng = random.Random(seed)
        self.hx, self.hy, self.corner, self.road_w = hx, hy, corner, road_w
        self.hero = hero
        self.plazas = list(plazas)
        self.alleys = list(alleys)
        self.park = park
        L = math.hypot(*camera_dir)
        self.cam = (camera_dir[0] / L, camera_dir[1] / L)
        self.specials_spec = specials_spec
        self.polys = []          # belegte Grundflächen (Polygone in Weltkoordinaten)
        self.houses = []         # (objekt, höhe)
        self.trees, self.people, self.cars, self.objects = [], [], [], []
        self.n_house = 0

    @property
    def footprints(self):  # Kompatibilität (Mittelpunkt, Radius)
        out = []
        for p in self.polys:
            cx = sum(q[0] for q in p) / len(p)
            cy = sum(q[1] for q in p) / len(p)
            out.append((cx, cy, max(math.hypot(q[0] - cx, q[1] - cy) for q in p)))
        return out

    def build(self):
        self._base_and_roads()
        self._paving()
        self._specials()
        self._perimeter()
        self._interior()
        self._make_houses()
        self._greenery()
        self._street_furniture()
        self._people()
        self._traffic()
        return self

    # ------------------------------------------------------------------
    def _rr(self, off, n=12):
        """Abgerundetes Rechteck, um `off` gegenüber dem Kachelrand nach innen versetzt."""
        return rounded_rect(2 * (self.hx - off), 2 * (self.hy - off), max(0.3, self.corner - off), n)

    def _base_and_roads(self):
        mb = MeshBuilder()
        mb.polygon_prism(self._rr(0), -0.45, 0.45, "sidewalk")
        off_c = 1.0 + self.road_w / 2
        self.ring = self._rr(off_c)
        mb.strip(self.ring, self.road_w, 0.005, "asphalt", closed=True)
        for d in (self.road_w / 2 + 0.06, -self.road_w / 2 - 0.06):
            mb.strip(self._rr(off_c - d), 0.12, 0.09, "stone_light", thickness=0.09, closed=True)
        self.block_off = off_c + self.road_w / 2 + 0.12
        mb.polygon_prism(self._rr(self.block_off), 0.0, 0.09, "sidewalk")
        path = Path(self.ring, True)
        s = 0.3
        while s < path.length:
            (x, y), a = path.at(s)
            mb.box((x, y, 0.012), (0.42, 0.05, 0.01), "road_line", rz=a)
            s += 0.95
        for d in (self.road_w / 2 - 0.12, -self.road_w / 2 + 0.12):
            mb.strip(self._rr(off_c - d), 0.035, 0.011, "road_line", closed=True)
        for frac in (0.08, 0.6):  # Zebrastreifen
            (x, y), a = path.at(path.length * frac)
            for k in range(7):
                o = -self.road_w / 2 + 0.2 + k * (self.road_w - 0.4) / 6
                mb.box((x - math.sin(a) * o, y + math.cos(a) * o, 0.012), (0.9, 0.14, 0.01), "road_line", rz=a)
        self.base = mb.build("diorama_base", self.col, bevel=0.03)
        self.objects.append(self.base)
        self.inner = self._rr(self.block_off + 0.9)   # Bauflucht-Linie

    def _paving(self):
        """Platzflächen (Pflaster) für Piazza, Gasse, Wahrzeichen-Umfeld."""
        mb = MeshBuilder()
        mb.polygon_prism(self._rr(self.block_off + 0.6), 0.09, 0.012, "plaza")
        for pts, w in self.alleys:
            mb.strip(pts, w, 0.105, "plaza")
        self.paving = mb.build("paving", self.col)

    # ------------------------------------------------------------------
    def _free(self, poly, margin=0.0):
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        pts = list(poly) + [(cx, cy)] + [((p[0] + cx) / 2, (p[1] + cy) / 2) for p in poly]
        bound = self._rr(self.block_off + 0.35)
        if not all(inside(bound, *p) for p in poly):
            return False
        if self.hero:
            hx, hy = self.hero["pos"]
            a, b = self.hero["ellipse"]
            r = math.radians(self.hero.get("rot", 0))
            for x, y in pts:
                u = (x - hx) * math.cos(r) + (y - hy) * math.sin(r)
                v = -(x - hx) * math.sin(r) + (y - hy) * math.cos(r)
                if (u / a) ** 2 + (v / b) ** 2 < 1:
                    return False
        for px, py, pr in self.plazas + ([self.park] if self.park else []):
            if any(math.hypot(x - px, y - py) < pr for x, y in pts):
                return False
        for apts, w in self.alleys:
            for x, y in pts:
                if min(_seg_dist((x, y), a, b) for a, b in zip(apts, apts[1:])) < w / 2 + 0.1:
                    return False
        return not any(overlap(poly, q, margin) for q in self.polys)

    def _zone_floors(self, x, y):
        """Höhenzone nach Lage zur Kamera: vorne niedrig, hinten hoch."""
        depth = -(x * self.cam[0] + y * self.cam[1]) / max(self.hx, self.hy)  # +1 hinten, -1 vorne
        if depth < -0.45:
            return (2, 3)
        if depth < 0.1:
            return (3, 4)
        if depth < 0.5:
            return (3, 5)
        return (4, 6)

    def _specials(self):
        self.special_objs = []
        for sp in self.specials_spec:
            x, y, rot = sp["pos"][0], sp["pos"][1], math.radians(sp.get("rot", 0))
            if sp["type"] == "church":
                ob, h = specials.church("church", self.col, seed=self.rng.randint(0, 999),
                                        wall=sp.get("wall", "stone_cream"))
                poly = rect_corners(x, y, 3.6, 5.2, rot)
            else:
                ob, h = specials.campanile("campanile", self.col, seed=self.rng.randint(0, 999), s=sp.get("scale", 1.0))
                poly = rect_corners(x, y, 1.1, 1.1, rot)
            ob.location = (x, y, 0.1)
            ob.rotation_euler = (0, 0, rot)
            self.polys.append(poly)
            self.houses.append((ob, h))
            self.special_objs.append(ob)

    def _perimeter(self):
        """Randbebauung entlang der Bauflucht: Breiten, Tiefen, Rücksprünge,
        Verdrehungen und Durchgänge variieren."""
        rng = self.rng
        path = Path(self.inner, True)
        self.plots = []
        s = rng.uniform(0, 2)
        while s < path.length - 1.5:
            if rng.random() < 0.09:  # Durchgang / Gasse
                s += rng.uniform(0.5, 1.0)
                continue
            w = rng.uniform(1.5, 3.3)
            d = rng.uniform(1.9, 3.6)
            setback = rng.uniform(0.0, 0.3) if rng.random() < 0.5 else 0.0
            (x0, y0), a0 = path.at(s)
            (x1, y1), a1 = path.at(s + w)
            ang = math.atan2(y1 - y0, x1 - x0) + math.radians(rng.uniform(-2.5, 2.5))
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            nx, ny = -math.sin(ang), math.cos(ang)  # nach innen (Pfad gegen Uhrzeigersinn)
            ww = math.hypot(x1 - x0, y1 - y0)
            placed = False
            for shrink in (1.0, 0.8, 0.62, 0.5):
                dd = max(1.3, d * shrink)
                cx, cy = mx + nx * (setback + dd / 2), my + ny * (setback + dd / 2)
                poly = rect_corners(cx, cy, ww, dd, ang)
                if self._free(poly, margin=-0.04):
                    self.polys.append(poly)
                    corner_curv = abs(((a1 - a0 + math.pi) % (2 * math.pi)) - math.pi) > 0.35
                    self.plots.append({"poly": poly, "c": (cx, cy), "w": ww, "d": dd, "ang": ang,
                                       "corner": corner_curv, "front": True})
                    placed = True
                    break
            if not placed:
                self.plots.append({"tree": (mx + nx * 1.2, my + ny * 1.2)})
            s += w

    def _interior(self, n=60):
        rng = self.rng
        bx, by = self.hx - self.block_off - 1.0, self.hy - self.block_off - 1.0
        for _ in range(n * 25):
            if sum(1 for p in self.plots if "poly" in p and not p["front"]) >= n:
                break
            x, y = rng.uniform(-bx, bx), rng.uniform(-by, by)
            w, d = rng.uniform(1.4, 2.9), rng.uniform(1.4, 2.7)
            # Ausrichtung grob am nächsten Rand, mit Abweichung
            ang = (0 if abs(x) / bx < abs(y) / by else math.pi / 2) + math.radians(rng.uniform(-9, 9))
            ang += rng.choice((0, math.pi))
            poly = rect_corners(x, y, w, d, ang)
            if self._free(poly, margin=0.18 if rng.random() < 0.45 else -0.03):
                self.polys.append(poly)
                self.plots.append({"poly": poly, "c": (x, y), "w": w, "d": d, "ang": ang, "corner": False,
                                   "front": False})

    def _blind_edges(self, poly_world, own):
        """Kante ist Brandwand, wenn direkt davor ein anderes Gebäude steht."""
        blind = []
        n = len(poly_world)
        for e in range(n):
            (x0, y0), (x1, y1) = poly_world[e], poly_world[(e + 1) % n]
            L = math.hypot(x1 - x0, y1 - y0) or 1
            nx, ny = (y1 - y0) / L, -(x1 - x0) / L  # außen (CCW)
            hits = 0
            for t in (0.25, 0.5, 0.75):
                px, py = x0 + (x1 - x0) * t + nx * 0.18, y0 + (y1 - y0) * t + ny * 0.18
                if any(inside(q, px, py) for q in self.polys if q is not own):
                    hits += 1
            if hits >= 2:
                blind.append(e)
        return blind

    def _make_houses(self):
        rng = self.rng
        for p in self.plots:
            if "tree" in p:
                continue
            cx, cy = p["c"]
            spec = random_spec(self.family, rng, floors=self._zone_floors(cx, cy))
            if not p["front"]:  # Innenhäuser: eher Wohnhäuser, keine Läden
                spec["ground"] = rng.choice(["rustic", "rustic", "shops"])
                spec["awning"] = None if rng.random() < 0.6 else spec["awning"]
            w, d = p["w"], p["d"]
            if p["corner"] and rng.random() < 0.75:
                pts = footprint(w, d, rng.choice(["round", "chamfer"]), which=(rng.choice((0, 3)),),
                                r=min(0.9, 0.3 * min(w, d)))
            else:
                pts = footprint(w, d)
            # lokales Polygon in Welt -> Brandwände bestimmen (Kanten-Reihenfolge wie footprint)
            ca, sa = math.cos(p["ang"]), math.sin(p["ang"])
            world = [(cx + u * ca - v * sa, cy + u * sa + v * ca) for u, v in pts]
            blind = self._blind_edges(world, p["poly"])
            if len(blind) >= len(pts) - 1:
                blind = blind[:len(pts) - 2]
            self.n_house += 1
            ob, H = build_house(pts, spec, blind=blind, seed=rng.randint(0, 99999),
                                name=f"house_{self.n_house:02d}", collection=self.col)
            ob.location = (cx, cy, 0.1)
            ob.rotation_euler = (0, 0, p["ang"])
            self.houses.append((ob, H))

    # ------------------------------------------------------------------
    def tree(self, x, y, leaf=None, size=None, shape="round"):
        rng = self.rng
        leaf = leaf or rng.choice(["leaf", "leaf", "leaf_light", "leaf_dark", "leaf_autumn", "leaf_olive",
                                   "leaf_blossom"])
        ob = details.fluffy_tree(f"tree_{len(self.trees):03d}", self.col, rng.randint(0, 99999), leaf,
                                 size or rng.uniform(0.8, 1.25), shape=shape)
        ob.location = (x, y, 0.1)
        self.trees.append(ob)
        return ob

    def _tree_free(self, x, y, r=0.45):
        return (inside(self._rr(self.block_off + 0.5), x, y)
                and not any(inside(q, x, y) or min(_seg_dist((x, y), q[i], q[(i + 1) % len(q)])
                                                   for i in range(len(q))) < r for q in self.polys))

    def _greenery(self, n_inner=34, pines=7):
        rng = self.rng
        for p in self.plots:
            if "tree" in p and self._tree_free(*p["tree"]):
                self.tree(*p["tree"])
        bx, by = self.hx - self.block_off - 0.8, self.hy - self.block_off - 0.8
        placed, tries = 0, 0
        spots = []
        while placed < n_inner and tries < n_inner * 60:
            tries += 1
            x, y = rng.uniform(-bx, bx), rng.uniform(-by, by)
            if self.hero:
                hx, hy = self.hero["pos"]
                a, b = self.hero["ellipse"]
                r = math.radians(self.hero.get("rot", 0))
                u = (x - hx) * math.cos(r) + (y - hy) * math.sin(r)
                v = -(x - hx) * math.sin(r) + (y - hy) * math.cos(r)
                if (u / (a - 0.6)) ** 2 + (v / (b - 0.6)) ** 2 < 1:
                    continue
            if any(math.hypot(x - px, y - py) < pr * 0.75 for px, py, pr in self.plazas):
                continue
            if any(math.hypot(x - sx, y - sy) < 0.8 for sx, sy in spots) or not self._tree_free(x, y):
                continue
            spots.append((x, y))
            if placed < pines:
                self.tree(x, y, "leaf_dark", rng.uniform(1.0, 1.3), shape="umbrella")
            else:
                self.tree(x, y)
            placed += 1
        if self.park:  # Park: Bäume, Hecken, Bänke
            px, py, pr = self.park
            for k in range(6):
                a, rr = rng.uniform(0, 2 * math.pi), pr * math.sqrt(rng.random()) * 0.8
                self.tree(px + rr * math.cos(a), py + rr * math.sin(a))
            for k in range(3):
                a = rng.uniform(0, 2 * math.pi)
                hd = details.hedge(f"hedge_park_{k}", self.col, rng.uniform(1.5, 2.6), seed=k, h=0.26)
                hd.location = (px + pr * 0.7 * math.cos(a), py + pr * 0.7 * math.sin(a), 0.1)
                hd.rotation_euler = (0, 0, a + math.pi / 2)
        for px, py, pr in self.plazas:  # Piazza-Brunnen
            fo = specials.fountain_piazza(f"fountain_{px:.0f}_{py:.0f}", self.col, r=min(0.8, pr * 0.35))
            fo.location = (px, py, 0.1)
            self.objects.append(fo)

    def _street_furniture(self):
        rng = self.rng
        lamp = Prop(self.col, "lamp", lambda mb: details.lamp(mb, 0, 0, 0))
        bollard = Prop(self.col, "bollard", lambda mb: details.bollard(mb, 0, 0, 0))
        bench = Prop(self.col, "bench", lambda mb: details.bench(mb, 0, 0, 0, 0))
        off_c = 1.0 + self.road_w / 2
        for off, every, trees in ((off_c - self.road_w / 2 - 0.45, 3.4, True), (self.block_off + 0.3, 4.0, False)):
            path = Path(self._rr(off), True)
            s = rng.uniform(0, 1)
            k = 0
            while s < path.length:
                (x, y), a = path.at(s)
                if trees and k % 3 == 1:
                    self.tree(x, y, size=rng.uniform(0.75, 1.05),
                              leaf=rng.choice(["leaf", "leaf_autumn", "leaf_light", "leaf_blossom"]))
                elif trees or self._tree_free(x, y, 0.2):
                    self.objects.append(lamp.place(x, y, 0.09))
                for o in (-0.6, 0.6):
                    (bx, by), _ = path.at(s + o)
                    if trees or self._tree_free(bx, by, 0.1):
                        self.objects.append(bollard.place(bx, by, 0.09))
                s += every * rng.uniform(0.85, 1.15)
                k += 1
        for px, py, pr in self.plazas + ([self.park] if self.park else []):
            for k in range(3):
                a = rng.uniform(0, 2 * math.pi)
                x, y = px + pr * 0.6 * math.cos(a), py + pr * 0.6 * math.sin(a)
                if self._tree_free(x, y, 0.2):
                    self.objects.append(bench.place(x, y, 0.1, a + math.pi / 2))
        # Hecke vorne am Kachelrand (wie im Referenzbild)
        hd = details.hedge("hedge_front", self.col, 6.0, h=0.32, w=0.35)
        hd.location = (1.5, -self.hy + 0.45, 0.0)
        self.objects.append(hd)

    def _people(self, n=90):
        """Passanten als eigene Objekte (6 Varianten, geteilte Meshes)."""
        rng = self.rng
        variants = []
        for k in range(6):
            r = random.Random(k)
            variants.append(Prop(self.col, f"person{k}", lambda mb, r=r: props.person(mb, 0, 0, 0, r)))
        spots = [(px, py, pr) for px, py, pr in self.plazas]
        if self.hero:
            hx, hy = self.hero["pos"]
            spots.append((hx, hy, max(self.hero["ellipse"]) + 1.5))
        for _ in range(n * 10):
            if len(self.people) >= n:
                break
            px, py, pr = rng.choice(spots)
            a, rr = rng.uniform(0, 2 * math.pi), pr * math.sqrt(rng.random())
            x, y = px + rr * math.cos(a), py + rr * math.sin(a)
            if self.hero:
                hx, hy = self.hero["pos"]
                ea, eb = self.hero["ellipse"]
                r = math.radians(self.hero.get("rot", 0))
                u = (x - hx) * math.cos(r) + (y - hy) * math.sin(r)
                v = -(x - hx) * math.sin(r) + (y - hy) * math.cos(r)
                if (u / (ea - 0.9)) ** 2 + (v / (eb - 0.9)) ** 2 < 1:
                    continue
            if not self._tree_free(x, y, 0.12):
                continue
            self.people.append(rng.choice(variants).place(x, y, 0.1, rng.uniform(0, 6.28)))

    def _traffic(self, n=9):
        rng = self.rng
        path = Path(self.ring, True)
        for k in range(n):
            s = path.length * (k + rng.uniform(0, 0.6)) / n
            (x, y), a = path.at(s)
            lane = self.road_w * 0.24 * (1 if k % 2 else -1)
            nx, ny = math.sin(a), -math.cos(a)
            c = details.car(f"car_{k}", self.col, rng.choice(CAR_COLORS), rng.choice(["hatch", "hatch", "sedan", "van"]))
            c.location = (x + nx * lane, y + ny * lane, 0.0)
            c.rotation_euler = (0, 0, a + (0 if lane < 0 else math.pi))
            self.cars.append(c)
