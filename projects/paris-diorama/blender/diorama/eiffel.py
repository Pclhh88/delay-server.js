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


def build_eiffel_measured(materials, collection, location, prof, name='EiffelTower'):
    """Fachwerk-Turm nach einem im Bild gemessenen Profil (Einheiten der Szene, nicht Meter).

    prof: {Marke: (z, halbe Breite)} aus blockout.tower_profile(). Der Turm der Vorlage hat keine
    realen Proportionen (1. Etage hoch, oberer Schaft gestreckt) – nachgebaut wird das Bild.
    """
    M, D = 'tower_bronze', 'tower_dark'
    chord, brace = 0.11, 0.045
    zL1a, zL1b = prof['etage1_unten'][0], prof['etage1_oben'][0]
    zL2 = prof['etage2'][0]
    zL3a, zL3b = prof['etage3_unten'][0], prof['etage3_oben'][0]
    samples = sorted([(0.0, prof['fuss'][1]), (zL1a, prof['etage1_unten'][1] * 0.93),
                      (prof['zwischen_1_2'][0], prof['zwischen_1_2'][1]), (zL2, prof['etage2'][1] * 0.95)] +
                     [prof[k] for k in ('schaft_720', 'schaft_650', 'schaft_550', 'schaft_450', 'schaft_350',
                                        'schaft_280')] + [(zL3a, prof['schaft_280'][1])])

    def half(z):
        for (z0, a0), (z1, a1) in zip(samples, samples[1:]):
            if z <= z1:
                t = (z - z0) / max(1e-6, z1 - z0)
                return a0 + (a1 - a0) * t
        return samples[-1][1]

    def legw(z):
        return 0.78 + (half(zL2) - 0.78) * min(1.0, z / zL2)

    mb = MeshBuilder()
    V = Vector
    # ---- vier Pfeiler (Fuß -> 2. Etage) ----
    zs = [zL2 * k / 22 for k in range(23)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            secs = []
            for z in zs:
                w = half(z)
                a = max(w - legw(z), 0.04)
                secs.append([V((sx * a, sy * a, z)), V((sx * w, sy * a, z)), V((sx * w, sy * w, z)), V((sx * a, sy * w, z))])
            for k in range(len(secs) - 1):
                A, B = secs[k], secs[k + 1]
                for c in range(4):
                    d = (c + 1) % 4
                    mb.beam(A[c], B[c], chord, M)
                    mb.beam(A[c], B[d], brace, M)
                    mb.beam(A[d], B[c], brace, M)
                    if k % 2 == 0:
                        mb.beam(B[c], B[d], brace, M)
            w0, a0 = half(0), half(0) - legw(0)
            c0 = (w0 + a0) / 2
            mb.box((sx * c0, sy * c0, 0.06), (legw(0) + 0.12, legw(0) + 0.12, 0.12), 'stone_beige')
    # ---- Zierbögen auf allen vier Seiten (Fuß -> unter der 1. Etage) ----
    apex = zL1a - 0.95
    for side in range(4):
        ang = side * math.pi / 2
        ca, sa = math.cos(ang), math.sin(ang)

        def R(u, v, z):
            return V((u * ca - v * sa, u * sa + v * ca, z))
        span = half(0.35) - legw(0.35)
        outer, inner = [], []
        for k in range(21):
            t = math.pi * k / 20
            u = -math.cos(t) * span
            z = 0.35 + math.sin(t) * (apex - 0.35)
            v = -(half(z) - 0.02)
            outer.append(R(u, v, z))
            inner.append(R(u * 0.9, v + 0.01, 0.35 + math.sin(t) * (apex - 0.35) + 0.22))
        for p0, p1 in zip(outer, outer[1:]):
            mb.beam(p0, p1, chord * 1.1, D)
        for p0, p1 in zip(inner, inner[1:]):
            mb.beam(p0, p1, brace * 1.3, D)
        for p0, p1 in zip(outer[1:-1:2], inner[1:-1:2]):
            mb.beam(p0, p1, brace, D)
        # Bogenzwickel bis zur Etage: senkrechte Stäbe + Rauten
        for k in range(1, 20, 2):
            u = -math.cos(math.pi * k / 20) * span
            z0 = 0.35 + math.sin(math.pi * k / 20) * (apex - 0.35) + 0.22
            v = -(half(zL1a) - 0.03)
            mb.beam(R(u * 0.9, v, z0), R(u * 0.95, v, zL1a), brace, D)
    # ---- 1. Etage: Kastenträger-Ring mit Fries und Geländer ----
    wP = prof['etage1_oben'][1]
    hole = half(zL1b) - legw(zL1b) - 0.05
    hP = zL1b - zL1a
    for sgn in (-1, 1):
        mb.box((0, sgn * (wP + hole) / 2, zL1a + hP / 2), (2 * wP, wP - hole, hP), D)
        mb.box((sgn * (wP + hole) / 2, 0, zL1a + hP / 2), (wP - hole, 2 * hole, hP), D)
    n = 14
    for k in range(n + 1):  # Friespfosten + Rundbogenfelder angedeutet
        u = -wP + 2 * wP * k / n
        for (x, y) in ((u, -wP - 0.015), (u, wP + 0.015), (-wP - 0.015, u), (wP + 0.015, u)):
            mb.box((x, y, zL1a + hP / 2), (0.05, 0.05, hP * 0.9), M)
    for (x0, y0, x1, y1) in ((-wP, -wP, wP, -wP), (wP, -wP, wP, wP), (wP, wP, -wP, wP), (-wP, wP, -wP, -wP)):
        mb.beam((x0, y0, zL1b + 0.16), (x1, y1, zL1b + 0.16), 0.03, M)
        mb.beam((x0, y0, zL1a + 0.06), (x1, y1, zL1a + 0.06), 0.06, M)
        for k in range(13):
            t = k / 12
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            mb.beam((x, y, zL1b), (x, y, zL1b + 0.16), 0.02, M)
    # ---- 2. Etage ----
    w2 = prof['etage2'][1]
    mb.box((0, 0, zL2 - 0.08), (2 * w2, 2 * w2, 0.18), D)
    for (x0, y0, x1, y1) in ((-w2, -w2, w2, -w2), (w2, -w2, w2, w2), (w2, w2, -w2, w2), (-w2, w2, -w2, -w2)):
        mb.beam((x0, y0, zL2 + 0.12), (x1, y1, zL2 + 0.12), 0.025, M)
        for k in range(9):
            t = k / 8
            mb.beam((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, zL2 + 0.01),
                    (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, zL2 + 0.12), 0.018, M)
    # ---- Schaft: jede Ecke ein eigener Gitterstiel, dazwischen Rauten ----
    zs2 = [zL2 + (zL3a - zL2) * k / 26 for k in range(27)]
    secs = [[V((-half(z), -half(z), z)), V((half(z), -half(z), z)), V((half(z), half(z), z)), V((-half(z), half(z), z))]
            for z in zs2]
    for k in range(len(secs) - 1):
        A, B = secs[k], secs[k + 1]
        for c in range(4):
            d = (c + 1) % 4
            mb.beam(A[c], B[c], chord * 0.9, M)
            mb.beam(A[c], B[d], brace * 0.9, M)
            mb.beam(A[d], B[c], brace * 0.9, M)
            ia, ib = A[c] * 0.8, B[c] * 0.8
            ia.z, ib.z = A[c].z, B[c].z
            mb.beam(ia, ib, brace * 0.8, M)
            if k % 3 == 0:
                mb.beam(B[c], B[d], brace, M)
    # ---- 3. Etage, Laterne, Kuppel, Antenne, Fahne ----
    w3 = prof['etage3_oben'][1]
    mb.box((0, 0, (zL3a + zL3b) / 2), (2 * w3, 2 * w3, zL3b - zL3a), D)
    for (x0, y0, x1, y1) in ((-w3, -w3, w3, -w3), (w3, -w3, w3, w3), (w3, w3, -w3, w3), (-w3, w3, -w3, -w3)):
        mb.beam((x0, y0, zL3b + 0.06), (x1, y1, zL3b + 0.06), 0.02, M)
    zk = prof['kuppel'][0]
    rk = prof['kuppel'][1]
    mb.cylinder((0, 0, zL3b), rk * 0.92, (zk - zL3b) * 0.55, M, seg=16, r_top=rk * 0.88)
    mb.cylinder((0, 0, zL3b + (zk - zL3b) * 0.55), rk, 0.05, D, seg=16)
    mb.sphere((0, 0, zL3b + (zk - zL3b) * 0.6), rk * 0.85, M, seg=16, rings=10, scale=(1, 1, 0.75))
    zt = prof['fahne'][0]
    mb.cylinder((0, 0, zk), 0.07, 0.25, D, seg=8, r_top=0.05)
    mb.cylinder((0, 0, zk + 0.25), 0.03, zt - zk - 0.3, D, seg=6, r_top=0.018)
    mb.box((0.12, 0, zt - 0.06), (0.22, 0.015, 0.11), 'gold')
    return mb.build(name, materials, collection, location=location)
