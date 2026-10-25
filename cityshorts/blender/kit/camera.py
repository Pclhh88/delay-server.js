"""Kamera-Bewegungsbibliothek.

Jede Einstellung (Shot) ist eine parametrische Bahn um ein Ziel:
  az  (Azimut, Grad)   el (Höhe, Grad)   dist (Abstand, in Ziel-Radien)
jeweils als [Start, Ende]. Benannte Presets (MOVES) machen daraus
wiederverwendbare Kamerafahrten, die für jede Stadt/jedes Wahrzeichen
funktionieren, weil sie relativ zur Größe des Ziels skaliert sind.

Zwischen zwei Shots fliegt die Kamera in `transition` Sekunden weich
(Smootherstep + leichter Bogen nach oben) zum nächsten Motiv -> eine
durchgehende Fahrt statt harter Schnitte.
"""
import math

from mathutils import Vector

MOVES = {
    # Totale: ganze Insel, langsame Kreisfahrt
    "overview_orbit": {"az": [-120, -70], "el": [50, 42], "dist": [3.4, 2.9], "lens": 35, "fstop": 2.2},
    # Ranfahrt aufs Motiv mit leichter Drehung
    "push_in": {"az": [-80, -60], "el": [36, 26], "dist": [4.6, 3.0], "lens": 40, "fstop": 0.9},
    # halbe Umrundung (Kreisfahrt / 180°)
    "orbit": {"az": [-140, -20], "el": [32, 30], "dist": [3.4, 3.1], "lens": 40, "fstop": 0.9},
    # volle 360°-Runde
    "orbit360": {"az": [0, 360], "el": [34, 34], "dist": [3.4, 3.4], "lens": 40, "fstop": 0.9},
    # Kran: von unten nach oben über das Motiv steigen
    "crane_up": {"az": [-30, -10], "el": [12, 50], "dist": [3.4, 4.2], "lens": 35, "fstop": 0.9},
    # tiefer Vorbeiflug auf Straßenhöhe
    "low_flyby": {"az": [-150, -60], "el": [10, 16], "dist": [3.0, 2.7], "lens": 30, "fstop": 0.6},
    # Detail von oben (Draufsicht, z. B. Kuppel mit Oculus)
    "top_down": {"az": [-90, -40], "el": [70, 80], "dist": [3.6, 2.8], "lens": 45, "fstop": 0.9},
    # Abschluss: rausziehen und drehen
    "pullback_360": {"az": [20, 200], "el": [30, 55], "dist": [1.4, 3.6], "lens": 35, "fstop": 2.2},
}


def smootherstep(u):
    u = max(0.0, min(1.0, u))
    return u * u * u * (u * (6 * u - 15) + 10)


def ease_inout(u):
    u = max(0.0, min(1.0, u))
    return 0.5 - 0.5 * math.cos(math.pi * u)


def _lerp(a, b, u):
    return a + (b - a) * u


class Shot:
    def __init__(self, t0, t1, target, radius, spec):
        self.t0, self.t1 = t0, t1
        self.target = Vector(target)
        self.radius = radius
        self.p = dict(MOVES[spec.get("move", "orbit")])
        self.p.update({k: v for k, v in spec.items() if k in ("az", "el", "dist", "lens", "fstop")})
        self.az_offset = spec.get("az_offset", 0)

    def pose(self, t):
        u = (t - self.t0) / max(self.t1 - self.t0, 1e-6)
        # leicht gedämpfter Anfang/Ende, aber nie Stillstand
        u = 0.15 * u + 0.85 * ease_inout(u)
        p = self.p
        az = math.radians(_lerp(*p["az"], u) + self.az_offset)
        el = math.radians(_lerp(*p["el"], u))
        d = _lerp(*p["dist"], u) * self.radius
        off = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))) * d
        return self.target + off, self.target.copy(), p["lens"], p["fstop"]


def camera_track(shots, fps, n_frames, transition=0.8):
    """-> Liste pro Frame: (pos, look, lens, fstop)"""
    out = []
    for f in range(n_frames):
        t = f / fps
        k = 0
        while k + 1 < len(shots) and t >= shots[k + 1].t0:
            k += 1
        cur = shots[k]
        pos, look, lens, fstop = cur.pose(t)
        if k > 0 and t < cur.t0 + transition:
            prev = shots[k - 1]
            p0, l0, lens0, f0 = prev.pose(t)  # vorheriger Shot läuft weiter ...
            w = smootherstep((t - cur.t0) / transition)
            arc = math.sin(math.pi * w) * 0.25 * (p0 - pos).length  # ... Bogen über die Stadt
            pos = p0.lerp(pos, w) + Vector((0, 0, arc))
            look = l0.lerp(look, w)
            lens = _lerp(lens0, lens, w)
            fstop = _lerp(f0, fstop, w)
        out.append((pos, look, lens, fstop))
    return out
