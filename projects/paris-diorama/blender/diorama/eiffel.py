"""Eiffelturm als echtes Stahlfachwerk (tausende Einzelstäbe).

Maßstab: Originalmaße in Metern * scale. Profil nach den realen Kennwerten
(Basis 125 m, 1. Etage 57 m, 2. Etage 116 m, 3. Etage 276 m, Spitze ~300 m).
"""
import math
from mathutils import Vector
from .meshkit import MeshBuilder

# (Höhe m, halbe Außenbreite m)
# Reale Kennwerte am Fuß; der Schaft oberhalb der 2. Etage ist - wie in der Vorlage - etwas schlanker.
PROFILE = [(0, 62.0), (20, 52.0), (40, 43.0), (57.6, 36.0), (80, 27.5), (115.7, 17.5),
           (150, 13.2), (200, 10.2), (240, 8.8), (276, 7.6), (300, 5.0)]


def half_width(z):
    for (z0, w0), (z1, w1) in zip(PROFILE, PROFILE[1:]):
        if z <= z1:
            t = (z - z0) / (z1 - z0)
            # leichte Krümmung zwischen den Stützstellen (Hermite mit geschätzten Steigungen)
            return w0 + (w1 - w0) * (t * t * (3 - 2 * t) * 0.35 + t * 0.65)
    return PROFILE[-1][1]


def leg_inner(z):
    """Innenkante der vier Pfeiler (0 = Pfeiler verschmolzen)."""
    if z >= 115.7:
        return 0.0
    w = half_width(z)
    legw = 24 - 6.5 * (z / 115.7) ** 1.5
    return max(0.0, w - legw)


def build_eiffel(materials, collection, location, scale, rotation=0.0, name='EiffelTower'):
    S = scale
    mb = MeshBuilder()
    M, D = 'tower_bronze', 'tower_dark'
    chord = 2.3 * S
    brace = 0.7 * S

    def P(x, y, z):
        return Vector((x * S, y * S, z * S))

    # ---- vier Pfeiler bis zur 2. Etage ----
    zs = [0, 4.5, 9, 14, 19, 24, 29, 34, 39, 44.5, 50, 57.6, 61, 64.6, 69, 73.5, 78, 83, 88, 93, 98, 103, 109, 115.7]
    for sx in (-1, 1):
        for sy in (-1, 1):
            secs = []
            for z in zs:
                w = half_width(z)
                a = leg_inner(z)
                a = max(a, 0.6)  # an der 2. Etage laufen die Pfeiler zusammen
                secs.append([(sx * a, sy * a, z), (sx * w, sy * a, z), (sx * w, sy * w, z), (sx * a, sy * w, z)])
            for k in range(len(secs) - 1):
                A, B = secs[k], secs[k + 1]
                for c in range(4):
                    mb.beam(P(*A[c]), P(*B[c]), chord, M)
                    d = (c + 1) % 4
                    mb.beam(P(*A[c]), P(*B[d]), brace, M)
                    mb.beam(P(*A[d]), P(*B[c]), brace, M)
                    mb.beam(P(*B[c]), P(*B[d]), brace, M)
            # Fundament-Sockel
            w0, a0 = half_width(0), leg_inner(0)
            c = ((w0 + a0) / 2 * sx, (w0 + a0) / 2 * sy)
            mb.box(P(c[0], c[1], 1.5), ((w0 - a0 + 4) * S, (w0 - a0 + 4) * S, 3 * S), 'stone_beige')

    # ---- Bögen zwischen den Pfeilern (je Seite) ----
    for side in range(4):
        ang = side * math.pi / 2
        ca, sa = math.cos(ang), math.sin(ang)

        def R(u, v, z):  # u entlang der Seite, v = Abstand nach außen
            return P(u * ca - v * sa, u * sa + v * ca, z)
        span = leg_inner(14) + 2
        for ring_off, wdt in ((0, chord * 1.2), (5, brace * 1.4)):
            pts = []
            for k in range(17):
                t = math.pi * k / 16
                u = -math.cos(t) * span
                z = 14 + math.sin(t) * (50 - 14 - ring_off)
                v = -half_width(z) + 2.0
                pts.append(R(u, -v, z))
            for p0, p1 in zip(pts, pts[1:]):
                mb.beam(p0, p1, wdt, D)
            if ring_off:
                arc_out = pts
            else:
                arc_in = pts
        for p0, p1 in zip(arc_in[1:-1:2], arc_out[1:-1:2]):
            mb.beam(p0, p1, brace, D)

    # ---- Plattformen ----
    def platform(z, w, h, hole):
        # vier Kastenträger als Rahmen (Mitte offen, man sieht hindurch)
        t = (w - hole)
        mb.box(P(0, -(w - t / 2), z + h / 2), (2 * w * S, t * S, h * S), D)
        mb.box(P(0, (w - t / 2), z + h / 2), (2 * w * S, t * S, h * S), D)
        mb.box(P(-(w - t / 2), 0, z + h / 2), (t * S, 2 * hole * S, h * S), D)
        mb.box(P((w - t / 2), 0, z + h / 2), (t * S, 2 * hole * S, h * S), D)
        # Fries: vorstehende Pfosten zwischen den Bogenfeldern
        n = int(w / 2.2)
        for k in range(-n, n + 1):
            u = k * (w / n) * 0.96
            for (x, y) in ((u, -w - 0.4), (u, w + 0.4), (-w - 0.4, u), (w + 0.4, u)):
                mb.box(P(x, y, z + h * 0.5), (1.0 * S, 1.0 * S, h * 0.9 * S), M)
        # Geländer oben
        for (x0, y0, x1, y1) in ((-w, -w, w, -w), (w, -w, w, w), (w, w, -w, w), (-w, w, -w, -w)):
            mb.beam(P(x0, y0, z + h + 3), P(x1, y1, z + h + 3), 0.8 * S, M)
            m = int(2 * w / 3)
            for k in range(m + 1):
                t2 = k / m
                x, y = x0 + (x1 - x0) * t2, y0 + (y1 - y0) * t2
                mb.beam(P(x, y, z + h), P(x, y, z + h + 3), 0.5 * S, M)
    platform(57.6, half_width(57.6) + 2.5, 7.0, 15)
    platform(115.7, half_width(115.7) + 2.0, 5.0, 6)

    # Galerie-Häuschen auf der 1. Etage (angedeutet)
    w1 = half_width(57.6)
    for (x, y, sx, sy) in ((0, -w1 + 3, 2 * w1 - 12, 4), (0, w1 - 3, 2 * w1 - 12, 4),
                           (-w1 + 3, 0, 4, 2 * w1 - 12), (w1 - 3, 0, 4, 2 * w1 - 12)):
        mb.box(P(x, y, 64.6 + 3), (sx * S, sy * S, 6 * S), M)

    # ---- Schaft von 2. Etage bis 3. Etage ----
    zs2 = [115.7, 122, 129, 136, 143, 150, 158, 166, 174, 182, 190, 199, 208, 217, 226, 235, 244, 253, 262, 270, 276]
    secs = []
    for z in zs2:
        w = half_width(z)
        secs.append([(-w, -w, z), (w, -w, z), (w, w, z), (-w, w, z)])
    for k in range(len(secs) - 1):
        A, B = secs[k], secs[k + 1]
        for c in range(4):
            d = (c + 1) % 4
            mb.beam(P(*A[c]), P(*B[c]), chord * 1.3, M)
            mb.beam(P(*A[c]), P(*B[d]), brace, M)
            mb.beam(P(*A[d]), P(*B[c]), brace, M)
            mb.beam(P(*B[c]), P(*B[d]), brace * 1.2, M)
            # innere Doppel-Kantenstäbe (jeder Eckstiel ist selbst ein Gitter)
    # ---- Spitze: 3. Etage, Laterne, Kuppel, Antenne ----
    w3 = half_width(276) + 1.5
    mb.box(P(0, 0, 276 + 2), (2 * w3 * S, 2 * w3 * S, 4 * S), D)
    mb.box(P(0, 0, 276 + 7), (2 * (w3 - 2) * S, 2 * (w3 - 2) * S, 6 * S), M)
    for (x0, y0, x1, y1) in ((-w3, -w3, w3, -w3), (w3, -w3, w3, w3), (w3, w3, -w3, w3), (-w3, w3, -w3, -w3)):
        mb.beam(P(x0, y0, 276 + 5), P(x1, y1, 276 + 5), 0.6 * S, M)
    mb.box(P(0, 0, 286), (2 * (w3 - 3) * S, 2 * (w3 - 3) * S, 2 * S), D)
    mb.cylinder(P(0, 0, 287), 6.5 * S, 7 * S, M, seg=16, r_top=5.0 * S)
    mb.cylinder(P(0, 0, 294), 4.2 * S, 1.5 * S, D, seg=12)
    mb.cylinder(P(0, 0, 295.5), 3.6 * S, 5 * S, M, seg=12, r_top=2.4 * S)
    mb.sphere(P(0, 0, 300.5), 4.0 * S, M, seg=16, rings=10, scale=(1, 1, 0.8))
    mb.cylinder(P(0, 0, 302.5), 0.9 * S, 18 * S, D, seg=8, r_top=0.4 * S)
    mb.cylinder(P(0, 0, 320), 0.45 * S, 14 * S, D, seg=6, r_top=0.25 * S)
    mb.box(P(1.6, 0, 331), (3.0 * S, 0.3 * S, 1.8 * S), 'gold')  # Fähnchen
    ob = mb.build(name, materials, collection, location=location, rotation=rotation)
    return ob
