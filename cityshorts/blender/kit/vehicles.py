"""Fahrzeuge (Kleinwagen, Bus) + Animation entlang von Straßen-Polylinien."""
import math

import bpy

from .mesh import MeshBuilder

CAR_COLORS = ["car_red", "car_blue", "car_cream", "car_yellow", "car_green", "car_grey"]


def make_car(color):
    mb = MeshBuilder()
    mb.box_on(0, 0, 0.1, 0.9, 0.45, 0.22, color)
    mb.box_on(-0.05, 0, 0.32, 0.5, 0.4, 0.18, color)
    mb.box_on(-0.05, 0, 0.34, 0.52, 0.36, 0.13, "glass")
    for x in (-0.28, 0.28):
        for y in (-0.21, 0.21):
            mb.cyl((x, y, 0.1), 0.1, 0.07, "rubber", seg=10, rx=math.pi / 2)
    for y in (-0.15, 0.15):
        mb.box((0.455, y, 0.22), (0.02, 0.08, 0.05), "headlight")
    return mb


def make_bus(color="bus_orange"):
    mb = MeshBuilder()
    mb.box_on(0, 0, 0.12, 2.0, 0.55, 0.62, color)
    mb.box_on(0, 0, 0.42, 2.02, 0.57, 0.2, "glass")
    mb.box_on(0, 0, 0.74, 1.9, 0.5, 0.04, "white")
    for x in (-0.65, 0.65):
        for y in (-0.25, 0.25):
            mb.cyl((x, y, 0.12), 0.12, 0.07, "rubber", seg=10, rx=math.pi / 2)
    return mb


class Path:
    """Polylinie mit Bogenlängen-Parametrisierung (geschlossen oder offen)."""

    def __init__(self, pts, closed=True):
        self.pts = list(pts) + ([pts[0]] if closed else [])
        self.closed = closed
        self.cum = [0.0]
        for a, b in zip(self.pts, self.pts[1:]):
            self.cum.append(self.cum[-1] + math.dist(a, b))
        self.length = self.cum[-1]

    def at(self, s):
        if self.closed:
            s %= self.length
        else:
            s = max(0.0, min(s, self.length))
        lo, hi = 0, len(self.cum) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.cum[mid] <= s:
                lo = mid
            else:
                hi = mid
        a, b = self.pts[lo], self.pts[hi]
        seg = max(self.cum[hi] - self.cum[lo], 1e-9)
        u = (s - self.cum[lo]) / seg
        return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u), math.atan2(b[1] - a[1], b[0] - a[0])


def animate_along(ob, path, s0, speed, lane, f0, f1, fps, z=0.0, step=2):
    """Fahrzeug fährt mit `speed` Einheiten/s; lane = seitlicher Versatz (Rechtsverkehr)."""
    prev = None
    for f in range(f0, f1 + 1, step):
        s = s0 + speed * (f - f0) / fps
        (x, y), ang = path.at(s)
        nx, ny = math.sin(ang), -math.cos(ang)
        if prev is not None:  # Winkel stetig halten
            while ang - prev > math.pi:
                ang -= 2 * math.pi
            while ang - prev < -math.pi:
                ang += 2 * math.pi
        prev = ang
        px, py = x + nx * lane, y + ny * lane
        ob.location = (px, py, z(px, py) if callable(z) else z)
        ob.rotation_euler = (0, 0, ang)
        ob.keyframe_insert("location", frame=f)
        ob.keyframe_insert("rotation_euler", index=2, frame=f)
