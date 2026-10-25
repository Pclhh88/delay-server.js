"""Rom: Kolosseum, Trevi-Brunnen, Pantheon, Petersdom (prozedural, stilisiert).

Maße in Szenen-Einheiten (1 Haus ~ 3 Einheiten breit). Wahrzeichen sind
bewusst etwas überhöht – Miniatur-Look statt Maßstabstreue.
"""
import math
import random

import bpy

from ..kit import props
from ..kit.mesh import MeshBuilder
from . import register


def _ellipse_pt(a, b, t):
    return a * math.cos(t), b * math.sin(t)


def _tangent(a, b, t):
    return math.atan2(b * math.cos(t), -a * math.sin(t))


@register("rome.colosseum")
def colosseum(col, params):
    a, b = 8.0, 6.6
    mb = MeshBuilder()
    rng = random.Random(3)
    N = 64
    tiers = [(0.0, 1.35), (1.35, 1.25), (2.6, 1.25), (3.85, 1.05)]
    # Bruchkante: auf der Südwestseite fehlen die oberen Ränge
    def n_tiers(t):
        d = (math.degrees(t) - 215) % 360
        d = min(d, 360 - d)
        if d < 50:
            return 2
        if d < 62:
            return 3
        return 4
    per = 2 * math.pi * math.sqrt((a * a + b * b) / 2) / N
    for i in range(N):
        t = 2 * math.pi * i / N
        x, y = _ellipse_pt(a, b, t)
        rz = _tangent(a, b, t)
        nt = n_tiers(t)
        for k, (z0, h) in enumerate(tiers[:nt]):
            if k < 3:
                # Pfeiler + Halbsäule + Bogen-Sturz
                mb.box_on(x, y, z0, per * 0.42, 0.7, h, "travertine", rz=rz)
                mb.box((x, y, z0 + h * 0.86), (per * 1.02, 0.66, h * 0.28), "travertine", rz=rz)
                mb.box((x, y, z0 + h - 0.05), (per * 1.05, 0.78, 0.1), "travertine_dark", rz=rz)
            else:  # Attika: geschlossene Wand mit kleinen Fenstern
                mb.box_on(x, y, z0, per * 1.02, 0.66, h, "travertine", rz=rz)
                if i % 2 == 0:
                    nx, ny = math.cos(rz - math.pi / 2), math.sin(rz - math.pi / 2)
                    mb.box((x - nx * 0.34, y - ny * 0.34, z0 + h * 0.55), (per * 0.3, 0.04, 0.25), "dark", rz=rz)
        if nt < 4:  # unregelmäßige Bruchkante
            z0, h = tiers[nt]
            mb.box_on(x, y, z0, per * 1.02, 0.66, rng.uniform(0.1, 0.6), "travertine", rz=rz)
        # Bögen dunkel hinterlegen (Blick ins Innere)
        for k, (z0, h) in enumerate(tiers[:min(nt, 3)]):
            ix, iy = _ellipse_pt(a - 0.45, b - 0.45, t)
            mb.box_on(ix, iy, z0, per * 1.02, 0.15, h, "travertine_dark", rz=rz)
    # innerer Ring (sichtbar an der Bruchkante)
    mb.ring(a - 0.5, b - 0.5, a - 1.3, b - 1.3, 0, 3.6, "travertine_dark", n=N)
    # Zuschauerränge (cavea) – Stufenringe nach innen abfallend
    steps = 7
    for s in range(steps):
        f0 = s / steps
        ao, bo = a - 1.3 - f0 * 2.6, b - 1.3 - f0 * 2.6
        mb.ring(ao, bo, ao - 2.6 / steps, bo - 2.6 / steps, 0, 3.4 - s * 0.38,
                "travertine" if s % 2 else "stone_grey", n=N)
    ai, bi = a - 3.9, b - 3.9
    # Arena: halb Sandboden, halb offengelegte Unterbauten (Hypogäum)
    mb.polygon_prism([(ai * math.cos(t), bi * math.sin(t)) for t in [2 * math.pi * i / 40 for i in range(40)]],
                     0.0, 0.08, "travertine_dark")
    for gx in range(-8, 9):
        x = gx * ai / 8.5
        if x > 0.2:
            continue
        hh = bi * math.sqrt(max(0, 1 - (x / ai) ** 2)) * 0.92
        if hh > 0.1:
            mb.box_on(x, 0, 0.08, 0.08, 2 * hh, 0.45, "travertine")
    for gy in range(-3, 4):
        y = gy * bi / 3.6
        ww = ai * math.sqrt(max(0, 1 - (y / bi) ** 2)) * 0.92
        if ww > 0.1:
            mb.box_on(-ww / 2, y, 0.08, ww, 0.08, 0.45, "travertine")
    sand = [(ai * 0.95 * math.cos(t), bi * 0.95 * math.sin(t)) for t in [-math.pi / 2 + math.pi * i / 24 for i in range(25)]]
    mb.polygon_prism(sand, 0.08, 0.45, "sand")
    ob = mb.build("colosseum", col, bevel=0.02)
    # Platz rund ums Kolosseum
    plat = MeshBuilder()
    plat.ring(a + 1.6, b + 1.6, 0.01, 0.01, -0.02, 0.07, "plaza", n=48)
    pl = plat.build("colosseum_plaza", col)
    ppl = MeshBuilder()
    props.crowd(ppl, 0, -b - 0.9, 2.2, 14, 7)
    props.crowd(ppl, a + 0.8, 0, 1.0, 6, 8)
    people = ppl.build("colosseum_people", col)
    # Steine, die im "Steinbruch"-Gag herausfliegen (Animation im Szenen-Skript)
    stones = []
    for k in range(6):
        t = math.radians(215 + rng.uniform(-35, 35))
        x, y = _ellipse_pt(a, b, t)
        smb = MeshBuilder()
        smb.box((0, 0, 0), (0.5, 0.4, 0.35), "travertine")
        st = smb.build(f"colosseum_stone_{k}", col, bevel=0.03)
        st.location = (x, y, 2.6 + rng.uniform(0, 0.3))
        st.scale = (0, 0, 0)
        stones.append(st)
    return {"objects": [ob, pl, people], "height": 5.0, "radius": 8.5, "extras": {"stones": stones}}


@register("rome.trevi")
def trevi(col, params):
    mb = MeshBuilder()
    W, D, H = 11.0, 3.0, 5.4
    y0 = 1.8
    # Palazzo Poli
    mb.box_on(0, y0, 0, W, D, H, "wall_cream")
    mb.box_on(0, y0, H - 0.1, W + 0.25, D + 0.25, 0.25, "marble")
    mb.hip(0, y0, H + 0.15, W, D, 0.7, "roof_terracotta", overhang=0.1)
    for fl in range(3):
        for i in range(12):
            x = -W / 2 + 0.45 + i * (W - 0.9) / 11
            if abs(x) < 2.1:
                continue
            z = 1.4 + fl * 1.25
            mb.box((x, y0 - D / 2 - 0.02, z), (0.38, 0.06, 0.6), "marble")
            mb.box((x, y0 - D / 2 - 0.04, z), (0.26, 0.06, 0.48), "glass")
            mb.box((x, y0 - D / 2 - 0.05, z + 0.4), (0.46, 0.1, 0.08), "marble")
    for x in (-5.3, -2.3, 2.3, 5.3):  # Pilaster
        mb.box_on(x, y0 - D / 2 - 0.05, 0.9, 0.3, 0.12, H - 1.0, "marble")
    # Triumphbogen-Mitte
    mb.box_on(0, y0 - D / 2 - 0.4, 0, 4.2, 0.9, H + 0.6, "marble")
    mb.box_on(0, y0 - D / 2 - 0.45, H + 0.6, 3.6, 0.8, 0.9, "marble")  # Attika
    for k in range(4):
        x = -1.2 + k * 0.8
        props.person(mb, x, y0 - D / 2 - 0.5, H + 1.5, random.Random(k), scale=1.4)
    for x in (-1.85, -0.95, 0.95, 1.85):  # Säulen
        mb.cyl((x, y0 - D / 2 - 0.95, 0.9), 0.17, 3.8, "marble", seg=12)
        mb.box((x, y0 - D / 2 - 0.95, 4.8), (0.42, 0.42, 0.18), "marble")
    mb.box((0, y0 - D / 2 - 0.95, 5.0), (4.3, 0.5, 0.35), "marble")
    # Nische mit Oceanus
    mb.box_on(0, y0 - D / 2 - 0.86, 0.9, 1.3, 0.1, 3.0, "travertine_dark")
    mb.sphere((0, y0 - D / 2 - 0.85, 3.9), 0.65, "travertine_dark", s=(1, 0.15, 0.7), zmin=0)
    mb.cyl((0, y0 - D / 2 - 1.2, 1.0), 0.28, 1.4, "white", seg=12, r2=0.2)
    mb.sphere((0, y0 - D / 2 - 1.2, 2.55), 0.2, "white", seg=12, rings=8)
    for s in (-1, 1):  # Seitenfiguren + Seepferde
        mb.cyl((s * 1.4, y0 - D / 2 - 1.05, 1.6), 0.18, 1.0, "white", seg=10)
        mb.sphere((s * 1.4, y0 - D / 2 - 1.05, 2.75), 0.15, "white", seg=10, rings=6)
        mb.sphere((s * 0.9, y0 - D / 2 - 1.9, 0.9), 0.35, "white", s=(1.4, 0.8, 0.9), ico=2)
        mb.sphere((s * 1.25, y0 - D / 2 - 2.1, 1.25), 0.18, "white", ico=2)
    # Felsen
    rng = random.Random(11)
    for k in range(38):
        x = rng.uniform(-4.6, 4.6)
        mb.sphere((x, y0 - D / 2 - rng.uniform(0.6, 1.8), rng.uniform(0.0, 0.9) * (1 - abs(x) / 6)),
                  rng.uniform(0.35, 0.7), "travertine", ico=1, smooth=False, s=(1.2, 1, 0.8))
    # Kaskaden
    for x in (-2.2, -0.9, 0, 0.9, 2.2):
        mb.box((x, y0 - D / 2 - 1.85, 0.75), (0.5 if x else 1.0, 0.06, 0.9), "foam")
    # Becken (Halbellipse) + Wasser
    cy = y0 - D / 2 - 1.6
    mb.ring(5.6, 3.6, 5.2, 3.2, 0, 0.45, "marble", n=36, th0=math.pi, th1=2 * math.pi, c=(0, cy))
    water_pts = [(5.25 * math.cos(t), cy + 3.25 * math.sin(t)) for t in [math.pi + math.pi * i / 36 for i in range(37)]]
    wmb = MeshBuilder()
    wmb.polygon_prism(water_pts, 0.0, 0.32, "water")
    water = wmb.build("trevi_water", col)
    # Stufen + Platz
    mb.ring(6.6, 4.6, 5.6, 3.6, 0, 0.12, "travertine", n=36, th0=math.pi, th1=2 * math.pi, c=(0, cy))
    mb.box_on(0, cy - 2.0, -0.02, W + 3, 6, 0.08, "plaza")
    ob = mb.build("trevi", col, bevel=0.02)
    ppl = MeshBuilder()
    props.crowd(ppl, 0, cy - 4.3, 3.2, 26, 5, avoid=lambda x, y: (x / 6.6) ** 2 + ((y - cy) / 4.6) ** 2 < 1)
    people = ppl.build("trevi_people", col)
    # Münzen (Animation im Szenen-Skript)
    coins = []
    for k in range(7):
        cmb = MeshBuilder()
        cmb.cyl((0, 0, -0.02), 0.13, 0.04, "gold", seg=12, rx=0)
        c = cmb.build(f"trevi_coin_{k}", col)
        c.scale = (0, 0, 0)
        coins.append(c)
    return {"objects": [ob, water, people], "height": 6.5, "radius": 7.0,
            "extras": {"coins": coins, "basin": (0, cy - 1.5, 0.35), "throw_from": (0, cy - 4.4, 0.7)}}


@register("rome.pantheon")
def pantheon(col, params):
    mb = MeshBuilder()
    R, H = 3.2, 3.0
    mb.cyl((0, 0, 0), R, H, "wall_sienna", seg=48)
    for k, (dr, dz) in enumerate([(0.05, 0.25), (-0.08, 0.25), (-0.22, 0.22)]):
        mb.cyl((0, 0, H + k * 0.25), R + dr, dz, "stone_grey", seg=48)
    mb.cyl((0, 0, 1.2), R + 0.04, 0.12, "stone_grey", seg=48)
    zd = H + 0.72
    mb.sphere((0, 0, zd), R - 0.2, "lead_dome", seg=48, rings=24, s=(1, 1, 0.62), zmin=0, zmax=0.975)
    mb.ring(0.8, 0.8, 0.66, 0.66, zd + (R - 0.2) * 0.6, 0.08, "stone_grey", n=24)  # Oculus-Rand
    # Zwischenbau + Vorhalle
    mb.box_on(0, -R - 0.2, 0, 4.6, 1.8, 3.8, "wall_sienna")
    mb.prism(0, -R - 0.2, 3.8, 1.8, 4.6, 0.95, "stone_grey", rz=math.pi / 2, overhang=0.05)
    py = -R - 2.0
    mb.box_on(0, py, 0, 6.6, 3.2, 0.3, "travertine")  # Stufen-Sockel
    for row, yy in enumerate((py - 1.25, py - 0.25, py + 0.75)):
        xs = [-2.7 + i * 5.4 / 7 for i in range(8)] if row == 0 else [-2.7, -0.95, 0.95, 2.7]
        for x in xs:
            mb.cyl((x, yy, 0.3), 0.21, 2.55, "stone_grey", seg=12)
            mb.box((x, yy, 2.92), (0.5, 0.5, 0.14), "marble")
    mb.box_on(0, py - 0.25, 2.95, 6.3, 3.0, 0.55, "marble")
    mb.box((0, py - 1.76, 3.22), (3.0, 0.04, 0.18), "dark")  # Inschrift-Band (M·AGRIPPA)
    mb.prism(0, py - 0.25, 3.5, 3.0, 6.5, 1.05, "marble", rz=math.pi / 2, overhang=0.08)
    mb.prism(0, py - 0.25, 3.56, 3.0, 6.1, 0.92, "lead_dome", rz=math.pi / 2)  # Dachfläche (Blei)
    # Piazza della Rotonda: Brunnen mit Obelisk + Cafés
    props.fountain(mb, 0, py - 4.0, 0.0, r=1.0)
    props.obelisk(mb, 0, py - 4.0, 0.25, h=1.8)
    props.cafe(mb, -3.5, py - 4.2, 0.0, 5, 3)
    props.cafe(mb, 3.6, py - 4.0, 0.0, 5, 4, "awning_green")
    mb.box_on(0, py - 3.0, -0.02, 10, 7, 0.06, "plaza")
    ob = mb.build("pantheon", col, bevel=0.02)
    ppl = MeshBuilder()
    props.crowd(ppl, 0, py - 3.0, 3.0, 22, 9, avoid=lambda x, y: math.hypot(x, y - (py - 4.0)) < 1.15)
    people = ppl.build("pantheon_people", col)
    # Regenwolke + Tropfen (Gag: "dann regnet es eben rein")
    cmb = MeshBuilder()
    rng = random.Random(5)
    for k in range(9):
        cmb.sphere((rng.uniform(-1.2, 1.2), rng.uniform(-0.6, 0.6), rng.uniform(-0.2, 0.3)),
                   rng.uniform(0.55, 0.9), "cloud", ico=2)
    cloud = cmb.build("pantheon_cloud", col)
    cloud.location = (0, 0, zd + 4.2)
    cloud.scale = (0, 0, 0)
    drops = []
    for k in range(14):
        dmb = MeshBuilder()
        dmb.sphere((0, 0, 0), 0.06, "rain", seg=8, rings=6, s=(1, 1, 3))
        d = dmb.build(f"pantheon_drop_{k}", col)
        d.scale = (0, 0, 0)
        drops.append(d)
    return {"objects": [ob, people], "height": 6.0, "radius": 5.5,
            "extras": {"cloud": cloud, "drops": drops, "oculus": (0, 0, zd + 1.9)}}


@register("rome.st_peters")
def st_peters(col, params):
    """Petersdom, Fassade nach -y, Petersplatz mit Kolonnaden davor."""
    mb = MeshBuilder()
    # Kirchenschiff + Querhaus + Apsis
    mb.box_on(0, -2.6, 0, 4.6, 8.2, 3.5, "travertine")
    mb.box_on(0, 1.2, 0, 9.0, 4.0, 3.5, "travertine")
    mb.cyl((0, 3.2, 0), 2.2, 3.5, "travertine", seg=24)
    for x in (-4.5, 4.5):
        mb.cyl((x, 1.2, 0), 2.0, 3.5, "travertine", seg=24)
    mb.box_on(0, -2.6, 3.5, 4.8, 8.4, 0.25, "marble")
    mb.box_on(0, 1.2, 3.5, 9.2, 4.2, 0.25, "marble")
    mb.prism(0, -2.6, 3.75, 8.4, 4.4, 0.9, "lead_dome", rz=math.pi / 2)
    # Tambour + Kuppel + Laterne
    cz = 3.75
    mb.cyl((0, 1.2, cz), 2.25, 0.35, "marble", seg=32)
    mb.cyl((0, 1.2, cz + 0.35), 2.0, 1.4, "travertine", seg=32)
    for k in range(16):
        t = 2 * math.pi * k / 16
        for dd in (-0.09, 0.09):
            tt = t + dd / 2.1
            mb.cyl((2.12 * math.cos(tt), 1.2 + 2.12 * math.sin(tt), cz + 0.35), 0.07, 1.25, "marble", seg=6)
    mb.cyl((0, 1.2, cz + 1.75), 2.2, 0.22, "marble", seg=32)
    dz = cz + 1.95
    mb.sphere((0, 1.2, dz), 2.0, "lead_dome", seg=40, rings=20, s=(1, 1, 1.32), zmin=0)
    for k in range(16):  # Rippen
        t = 2 * math.pi * k / 16
        for j in range(9):
            phi = (j + 0.5) / 9 * (math.pi / 2) * 0.93
            r = 2.01 * math.cos(phi)
            z = dz + 2.01 * 1.32 * math.sin(phi)
            tilt = -math.atan2(math.sin(phi), 1.32 * math.cos(phi))
            mb.box((r * math.cos(t), 1.2 + r * math.sin(t), z), (0.07, 0.09, 0.4), "marble", rz=t, ry=tilt)
    lz = dz + 2.0 * 1.32 - 0.05
    mb.cyl((0, 1.2, lz), 0.42, 0.7, "marble", seg=16)
    mb.cyl((0, 1.2, lz + 0.7), 0.45, 0.45, "lead_dome", seg=16, r2=0.06)
    mb.sphere((0, 1.2, lz + 1.25), 0.12, "gold", seg=10, rings=6)
    mb.box((0, 1.2, lz + 1.5), (0.04, 0.04, 0.35), "gold")
    mb.box((0, 1.2, lz + 1.55), (0.18, 0.04, 0.04), "gold")
    for x in (-3.3, 3.3):  # Nebenkuppeln
        mb.cyl((x, -0.9, 3.75), 0.7, 0.6, "travertine", seg=20)
        mb.sphere((x, -0.9, 4.35), 0.7, "lead_dome", seg=20, rings=10, s=(1, 1, 1.3), zmin=0)
        mb.cyl((x, -0.9, 5.2), 0.12, 0.35, "marble", seg=8)
    # Fassade
    fy = -6.9
    mb.box_on(0, fy, 0, 9.6, 0.8, 4.2, "travertine")
    mb.box_on(0, fy, 4.2, 9.8, 0.9, 0.3, "marble")
    mb.box_on(0, fy, 4.5, 9.0, 0.7, 0.55, "travertine")
    for i in range(8):
        x = -4.1 + i * 8.2 / 7
        mb.cyl((x, fy - 0.45, 0.4), 0.2, 3.7, "marble", seg=12)
    for i in range(13):
        props.person(mb, -4.2 + i * 0.7, fy, 5.05, random.Random(i), scale=1.3)
    mb.prism(0, fy - 0.1, 4.2, 0.9, 3.4, 0.7, "marble", rz=math.pi / 2)
    for i in range(5):  # Fensterreihe
        x = -3.5 + i * 1.75
        mb.box((x, fy - 0.42, 3.0), (0.45, 0.05, 0.7), "glass")
    mb.box_on(0, fy - 0.9, 0, 9.0, 1.1, 0.4, "travertine")  # Treppe
    # Petersplatz: Trapez + Ellipse mit Kolonnaden
    pcy = fy - 7.5
    mb.box_on(0, fy - 2.4, -0.02, 9.0, 3.6, 0.07, "plaza")
    sq = MeshBuilder()
    sq.ring(6.0, 5.0, 0.01, 0.01, -0.02, 0.07, "plaza", n=48)
    for k in range(16):  # Pflaster-Strahlen
        t = 2 * math.pi * k / 16
        mb.box((2.8 * math.cos(t), pcy + 2.3 * math.sin(t), 0.06), (5.0, 0.06, 0.02), "travertine", rz=t)
    sqo = sq.build("st_peters_square", col)
    sqo.location = (0, pcy, 0)
    for side in (-1, 1):
        th0, th1 = (math.radians(20), math.radians(160)) if side < 0 else (math.radians(200), math.radians(340))
        th0, th1 = th0 - math.pi / 2, th1 - math.pi / 2  # Öffnung nach vorn/hinten (±y)
        for row in range(3):
            ra, rb = 6.0 + row * 0.38, 5.0 + row * 0.38
            for i in range(19):
                t = th0 + (th1 - th0) * i / 18
                mb.cyl((ra * math.cos(t), pcy + rb * math.sin(t), 0.05), 0.09, 1.05, "travertine", seg=6)
        mb.ring(6.95, 5.95, 5.8, 4.8, 1.1, 0.3, "travertine", n=24, th0=th0, th1=th1, c=(0, pcy))
        for i in range(10):
            t = th0 + (th1 - th0) * i / 9
            props.person(mb, 6.4 * math.cos(t), pcy + 5.4 * math.sin(t), 1.4, random.Random(i + 40))
        # Verbindungsflügel zur Fassade
        xw = -side * 4.85
        mb.box_on(xw, fy - 2.4, 0, 0.9, 4.0, 1.4, "travertine")
    props.obelisk(mb, 0, pcy, 0.05, h=2.4)
    for x in (-2.6, 2.6):
        props.fountain(mb, x, pcy, 0.05, r=0.6)
    ob = mb.build("st_peters", col, bevel=0.02)
    ppl = MeshBuilder()
    props.crowd(ppl, 0, pcy, 4.2, 40, 12, avoid=lambda x, y: math.hypot(x, y - pcy) < 0.6
                or min(math.hypot(x - 2.6, y - pcy), math.hypot(x + 2.6, y - pcy)) < 0.7)
    people = ppl.build("st_peters_people", col)
    return {"objects": [ob, sqo, people], "height": 10.5, "radius": 9.0,
            "extras": {"dome_top": (0, 1.2, lz + 1.6)}}
