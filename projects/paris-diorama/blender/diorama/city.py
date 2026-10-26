"""Parametrischer Hausgenerator in Benchmark-Qualität (Techniken wie landmark.py / Gebäude F).

Ein Haus wird in „Designeinheiten“ gebaut (Obergeschoss = 1,0 hoch) und über das Elternobjekt auf
die vermessene Größe skaliert; so haben alle Häuser gleich feine, maßstäbliche Details.

Bauteile je Haus (Kinder des Elternobjekts): Wände (Boolean-Öffnungen), Innenraum, Gesimse/Bänder,
Fenster, Ornament/Balkone, Dach, Gauben, Dachaufbauten.
"""
import math
import random
from dataclasses import dataclass, field

import bpy
from mathutils import Vector

from . import landmark as LM
from .landmark import (Frame, Cutters, MeshBuilder, g_box, g_extrude_dz, g_extrude_sz, g_molding, g_revolve,
                       g_tube, ring, sweep, window, lambrequin, festoon, chimney_pot, _finish, _boolean, _stone,
                       _plain, T_WALL)


@dataclass
class House:
    name: str
    lx: float                         # Designeinheiten (Grundriss lokal, Ursprung = vordere Ecke)
    ly: float
    rad: dict
    floors: int
    gh: float                         # Erdgeschosshöhe
    stone: tuple                      # (hell, dunkel) Fassadenfarbe
    roof_kind: str = 'mansard'        # mansard | curved | bell | low | attic
    roof_h: float = 1.6
    roof_in: float = 0.7
    roof_mat: str = 'zinc'
    dormer: str = 'gable'             # gable | arch | oeil | none
    dormer_per_face: dict = field(default_factory=dict)  # {'right': n, ...}; fehlt -> automatisch
    bay: float = 1.0
    faces: tuple = ('right', 'left', 'east', 'north')
    blind: tuple = ()                 # Brandwände (keine Öffnungen)
    balconies: tuple = (2,)           # Geschosse mit durchlaufendem Gussbalkon
    rails: bool = True                # französische Gitter vor den übrigen Fenstern
    shutters: str = ''                # Material der Fensterläden ('' = keine)
    ground: str = 'shop'              # shop | arch
    doors: dict = field(default_factory=dict)   # {face: [bay, ...]}
    door_mat: str = 'wood'
    corner_windows: bool = False
    balustrade: bool = False          # Steinbalustrade auf dem Hauptgesims
    lambrequins: bool = False
    chimneys: list = field(default_factory=list)  # [(x, y, w, d, h, pots)] lokal, Designeinheiten
    attic_in: float = 0.5             # nur roof_kind == 'attic'
    attic_h: float = 0.9
    seed: int = 1


# ----------------------------------------------------------------------------- Materialien
_SHARED = {}


def shared_materials():
    if not _SHARED:
        base = LM.make_materials()
        base.update({
            'wood': _plain('CT_wood', '#3B2A20', 0.5, var=0.12, scale=60),
            'wood_green': _plain('CT_wood_green', '#2E4F3A', 0.45, var=0.08, scale=40),
            'shutter': _plain('CT_shutter', '#7A4A2E', 0.55, var=0.1, scale=40),
            'zinc_light': _plain('CT_zinc_light', '#AEB3B5', 0.4, metal=0.45, var=0.08, scale=5),
            'roof_red': _plain('CT_roof_red', '#9A5446', 0.45, metal=0.25, var=0.1, scale=5),
            'terracotta': _plain('CT_terracotta', '#B5643F', 0.75, var=0.15, scale=30),
            'brick': _plain('CT_brick', '#A9674C', 0.85, var=0.15, scale=40),
            'shop_glass': _plain('CT_shop_glass', '#2A2723', 0.08, coat=0.4),
            'sign': _plain('CT_sign', '#2D3A33', 0.5),
            'stone_white': _stone('CT_stone_white', '#ECE6DA', '#D6CEBE', grime='#8C8273', streak=0.15),
        })
        _SHARED.update(base)
    return _SHARED


def house_materials(h):
    M = dict(shared_materials())
    c1, c2 = h.stone
    M['stone'] = _stone(f'{h.name}_stone', c1, c2, grime='#6B5B4B', streak=0.2)
    M['trim'] = _stone(f'{h.name}_trim', _lighten(c1, 0.08), _lighten(c2, 0.06), grime='#776654', ao_dist=0.15,
                       streak=0.2, bump=0.15)
    return M


def _lighten(hexc, f):
    h = hexc.lstrip('#')
    c = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    c = [min(255, int(v + (255 - v) * f)) for v in c]
    return '#%02X%02X%02X' % tuple(c)


# ----------------------------------------------------------------------------- Fassaden-Bauteile
def shutters(fr, mb, s, w, zb, zt):
    """Geöffnete Lamellenläden links und rechts des Fensters (Rahmen + 9 Lamellen je Flügel)."""
    for sx in (-1, 1):
        a = s + sx * (w / 2 + 0.07)
        b = a + sx * w * 0.5
        s0, s1 = min(a, b), max(a, b)
        fr.put(mb, g_box(s0, s1, 0.004, 0.02, zb, zt), 'shutter')
        for z0, z1 in ((zb, zb + 0.03), (zt - 0.03, zt), ((zb + zt) / 2 - 0.015, (zb + zt) / 2 + 0.015)):
            fr.put(mb, g_box(s0, s1, 0.02, 0.034, z0, z1), 'shutter')
        for x0, x1 in ((s0, s0 + 0.03), (s1 - 0.03, s1)):
            fr.put(mb, g_box(x0, x1, 0.02, 0.034, zb, zt), 'shutter')
        for k in range(1, 10):
            z = zb + (zt - zb) * k / 10
            fr.put(mb, g_extrude_dz([(0.02, z - 0.012), (0.028, z - 0.012), (0.036, z + 0.008), (0.028, z + 0.012)],
                                    s0 + 0.03, s1 - 0.03), 'shutter')


def shopfront(fr, mb, cut, s, w, z0, z1, door=False, mat='wood'):
    """Ladenfront/Tür: Öffnung, Rahmen mit Pfosten, Sockelpaneel, Oberlicht, Schild."""
    cut.append(fr, g_box(s - w / 2, s + w / 2, -T_WALL - 0.05, 0.06, z0, z1))
    dg = -0.07
    fw = 0.04
    for a, b, c0, c1 in ((s - w / 2, s - w / 2 + fw, z0, z1), (s + w / 2 - fw, s + w / 2, z0, z1),
                         (s - w / 2, s + w / 2, z1 - fw, z1), (s - w / 2, s + w / 2, z0, z0 + fw)):
        fr.put(mb, g_box(a, b, dg - 0.03, dg + 0.03, c0, c1), mat)
    ztr = z1 - (z1 - z0) * 0.2
    fr.put(mb, g_box(s - w / 2, s + w / 2, dg - 0.025, dg + 0.025, ztr - 0.02, ztr + 0.02), mat)
    if door:
        for sx in (-1, 1):  # zwei Flügel mit Kassetten
            a, b = (s - w / 2 + fw, s - 0.01) if sx < 0 else (s + 0.01, s + w / 2 - fw)
            fr.put(mb, g_box(a, b, dg - 0.02, dg + 0.01, z0 + fw, ztr - 0.02), mat)
            for zz0, zz1 in ((z0 + 0.1, z0 + (ztr - z0) * 0.45), (z0 + (ztr - z0) * 0.52, ztr - 0.1)):
                fr.put(mb, g_box(a + 0.04, b - 0.04, dg + 0.01, dg + 0.025, zz0, zz1), mat)
        fr.put(mb, g_box(s - w / 2 + fw, s + w / 2 - fw, dg - 0.004, dg + 0.002, ztr + 0.02, z1 - fw), 'glass')
    else:
        fr.put(mb, g_box(s - w / 2 + fw, s + w / 2 - fw, dg - 0.01, dg + 0.03, z0 + fw, z0 + 0.28), mat)  # Sockel
        fr.put(mb, g_box(s - w / 2 + fw, s + w / 2 - fw, dg - 0.004, dg + 0.002, z0 + 0.28, z1 - fw), 'shop_glass')
        for k in (1, 2):
            x = s - w / 2 + w * k / 3
            fr.put(mb, g_box(x - 0.014, x + 0.014, dg - 0.02, dg + 0.02, z0 + 0.28, ztr), mat)
        # Auslage (Andeutung von Waren/Regalen)
        fr.put(mb, g_box(s - w / 2 + 0.08, s + w / 2 - 0.08, dg - 0.2, dg - 0.12, z0 + 0.28, z0 + 0.36), 'curtain')
    # Schildband
    fr.put(mb, g_box(s - w / 2 - 0.05, s + w / 2 + 0.05, 0.0, 0.05, z1 + 0.03, z1 + 0.15), 'sign')
    fr.put(mb, g_box(s - w / 2 - 0.07, s + w / 2 + 0.07, 0.0, 0.07, z1 + 0.15, z1 + 0.18), 'trim')


def _ring_walk(d, step):
    """Gleichabständige Punkte (Position, Tangente) auf dem Grundriss-Ring mit Versatz d."""
    rg = ring(d)
    out, acc, nxt = [], 0.0, step / 2
    for i in range(len(rg)):
        p, q = Vector((*rg[i], 0.0)), Vector((*rg[(i + 1) % len(rg)], 0.0))
        L = (q - p).length
        while L > 1e-9 and nxt <= acc + L:
            t = (nxt - acc) / L
            out.append((p + (q - p) * t, (q - p).normalized()))
            nxt += step
        acc += L
    return out


def iron_balcony_ring(mb, z, depth=0.3, h=0.32, skip=None):
    """Durchlaufender Gussbalkon rund um das Haus: Platte (Sweep), Konsolen, Gitter mit Kreismotiv."""
    sweep(mb, [(-0.02, z - 0.08), (depth - 0.02, z - 0.08), (depth + 0.01, z - 0.05), (depth + 0.01, z),
               (-0.02, z)], 'trim')
    for p, t in _ring_walk(0.0, 0.42):
        if skip and skip(p):
            continue
        n = Vector((t.y, -t.x, 0))
        fr = Frame((p.x, p.y), (t.x, t.y), (n.x, n.y))
        fr.put(mb, g_extrude_dz([(0, z - 0.3), (0.035, z - 0.3), (0.08, z - 0.18), (depth * 0.8, z - 0.09),
                                 (depth * 0.8, z - 0.08), (0, z - 0.08)], -0.025, 0.025), 'trim')
    dr = depth - 0.03
    sweep(mb, [(dr - 0.012, z + h - 0.02), (dr + 0.012, z + h - 0.02), (dr + 0.012, z + h), (dr - 0.012, z + h)],
          'iron')
    sweep(mb, [(dr - 0.008, z + 0.03), (dr + 0.008, z + 0.03), (dr + 0.008, z + 0.045), (dr - 0.008, z + 0.045)],
          'iron')
    for i, (p, t) in enumerate(_ring_walk(dr, 0.045)):
        if skip and skip(p):
            continue
        mb.box((p.x, p.y, z + h / 2), (0.009, 0.009, h), 'iron')
        if i % 6 == 0:
            n = Vector((t.y, -t.x, 0))
            pts = [p + t * 0.06 * math.cos(a) + Vector((0, 0, z + h * 0.55 + 0.06 * math.sin(a))) for a in
                   [2 * math.pi * k / 12 for k in range(13)]]
            pts = [(q.x, q.y, q.z) for q in pts]
            v, f = g_tube(pts, 0.005, seg=4)
            mb.add(v, f, 'iron')


def stone_balustrade_ring(mb, z, d=0.02, h=0.38, step=0.13):
    """Steinbalustrade auf dem Hauptgesims: Sockel, gedrechselte Docken, Handlauf (Sweeps)."""
    sweep(mb, [(d - 0.07, z), (d + 0.07, z), (d + 0.07, z + 0.06), (d - 0.07, z + 0.06)], 'trim')
    sweep(mb, [(d - 0.08, z + h - 0.06), (d + 0.08, z + h - 0.06), (d + 0.09, z + h - 0.03), (d + 0.08, z + h),
               (d - 0.08, z + h)], 'trim')
    prof = [(0.0, z + 0.06), (0.04, z + 0.06), (0.04, z + 0.09), (0.03, z + 0.1), (0.055, z + 0.17), (0.045, z + 0.22),
            (0.022, z + h - 0.12), (0.03, z + h - 0.1), (0.04, z + h - 0.08), (0.04, z + h - 0.06), (0.0, z + h - 0.06)]
    for p, t in _ring_walk(d, step):
        v, f = g_revolve(prof, seg=10)
        mb.add([(x + p.x, y + p.y, zz) for x, y, zz in v], f, 'trim', True)


def dormer_window(fr, mb, s, w, style, mat_body, roof_mat):
    """Gaube mit echtem Fenster: Wangen, Front mit Rahmen/Flügeln/Glas, Giebel- oder Rundbogenverdachung."""
    d, z, _ = LM.roof_point(0.18)
    h = w * 1.35
    zb = z
    df = d + 0.06                                  # Frontebene
    back = d - 0.9
    # Körper (taucht ins Dach)
    fr.put(mb, g_box(s - w / 2 - 0.05, s - w / 2, back, df, zb, zb + h), mat_body)
    fr.put(mb, g_box(s + w / 2, s + w / 2 + 0.05, back, df, zb, zb + h), mat_body)
    fr.put(mb, g_box(s - w / 2, s + w / 2, back, df - 0.08, zb, zb + h), 'interior')
    # Fenster
    fw = 0.03
    for a, b, c0, c1 in ((s - w / 2, s - w / 2 + fw, zb, zb + h), (s + w / 2 - fw, s + w / 2, zb, zb + h),
                         (s - w / 2, s + w / 2, zb, zb + fw), (s - 0.01, s + 0.01, zb, zb + h)):
        fr.put(mb, g_box(a, b, df - 0.06, df - 0.03, c0, c1), 'frame')
    for k in (1, 2):
        zz = zb + h * k / 3
        fr.put(mb, g_box(s - w / 2, s + w / 2, df - 0.06, df - 0.04, zz - 0.006, zz + 0.006), 'frame')
    fr.put(mb, g_box(s - w / 2 + fw, s + w / 2 - fw, df - 0.05, df - 0.048, zb + fw, zb + h), 'glass')
    # Pilaster der Front + Sohlbank
    for sx in (-1, 1):
        fr.put(mb, g_box(s + sx * (w / 2 + 0.025) - 0.04, s + sx * (w / 2 + 0.025) + 0.04, df - 0.03, df + 0.02, zb,
                         zb + h), mat_body)
    fr.put(mb, g_box(s - w / 2 - 0.08, s + w / 2 + 0.08, df - 0.1, df + 0.04, zb - 0.04, zb + 0.02), mat_body)
    top = zb + h
    fr.put(mb, g_box(s - w / 2 - 0.08, s + w / 2 + 0.08, back, df + 0.04, top, top + 0.05), mat_body)
    if style == 'arch':
        r = w / 2 + 0.08
        prof = [(s + r * math.cos(a), top + 0.05 + r * 0.85 * math.sin(a)) for a in [math.pi * i / 12 for i in range(13)]]
        v, f = [], []
        for dd in (back, df + 0.04):
            v += [(ss, dd, zz) for ss, zz in prof]
        n = len(prof)
        f = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
        f += [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
        fr.put(mb, (v, f), roof_mat, True)
        arc = [(s + (r - 0.03) * math.cos(a), df + 0.05, top + 0.05 + (r - 0.03) * 0.85 * math.sin(a))
               for a in [math.pi * i / 12 for i in range(13)]]
        fr.put(mb, g_tube(arc, 0.025, seg=6), mat_body, True)
    elif style == 'gable':
        apex = top + 0.05 + w * 0.42
        fr.put(mb, g_extrude_sz([(s - w / 2 - 0.1, top + 0.05), (s + w / 2 + 0.1, top + 0.05), (s, apex)], back,
                                df + 0.04), mat_body)
        for sx in (-1, 1):  # Dachflächen der Gaube
            fr.put(mb, g_extrude_sz([(s, apex + 0.03), (s + sx * (w / 2 + 0.14), top + 0.03),
                                     (s + sx * (w / 2 + 0.14), top + 0.07), (s, apex + 0.07)][::sx], back, df + 0.06),
                   roof_mat)
    else:
        fr.put(mb, g_box(s - w / 2 - 0.1, s + w / 2 + 0.1, back, df + 0.08, top + 0.05, top + 0.1), roof_mat)


def chimney_stack(mb, x, y, z, w, d, h, pots, M_stone='brick'):
    """Kaminstock mit Abdeckplatte und Tonaufsätzen (Pots)."""
    mb.box((x, y, z + h / 2), (w, d, h), M_stone)
    mb.box((x, y, z + h + 0.03), (w + 0.07, d + 0.07, 0.06), 'trim')
    mb.box((x, y, z + h * 0.8), (w + 0.04, d + 0.04, 0.04), 'trim')
    for k in range(pots):
        px = x - w / 2 + w * (k + 0.5) / pots
        chimney_pot(mb, px, y, z + h + 0.06, h=0.2 + 0.05 * (k % 2), r=min(0.045, w / pots * 0.38), mat='terracotta')


def cupola(mb, x, y, z, s=1.0):
    """Weißes Kuppeltürmchen: achteckiger Tambour mit Rundbogenfenstern, Rippenkuppel, Laterne, Spitze."""
    prof = [(0.0, z), (0.5 * s, z), (0.5 * s, z + 0.08 * s), (0.44 * s, z + 0.1 * s), (0.44 * s, z + 0.75 * s),
            (0.5 * s, z + 0.78 * s), (0.5 * s, z + 0.86 * s), (0.0, z + 0.86 * s)]
    v, f = g_revolve(prof, seg=8)
    mb.add([(a + x, b + y, c) for a, b, c in v], f, 'stone_white')
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        cx, cy = x + 0.43 * s * math.cos(a), y + 0.43 * s * math.sin(a)
        mb.box((cx, cy, z + 0.42 * s), (0.04 * s, 0.16 * s, 0.4 * s), 'glass', rot=a)
        pts = [(cx - math.sin(a) * 0.09 * s * math.cos(t), cy + math.cos(a) * 0.09 * s * math.cos(t),
                z + 0.62 * s + 0.09 * s * math.sin(t)) for t in [math.pi * i / 8 for i in range(9)]]
        v, f = g_tube(pts, 0.018 * s, seg=6)
        mb.add([(p[0] + math.cos(a) * 0.02, p[1] + math.sin(a) * 0.02, p[2]) for p in v], f, 'stone_white', True)
    dome = [(0.46 * s * math.cos(t), z + 0.86 * s + 0.55 * s * math.sin(t) ** 0.9) for t in
            [math.pi / 2 * i / 12 for i in range(13)]]
    v, f = g_revolve(dome, seg=24)
    mb.add([(a + x, b + y, c) for a, b, c in v], f, 'zinc_light', True)
    for k in range(8):
        a = 2 * math.pi * k / 8
        rib = [(x + 0.47 * s * math.cos(t) * math.cos(a), y + 0.47 * s * math.cos(t) * math.sin(a),
                z + 0.86 * s + 0.56 * s * math.sin(t) ** 0.9) for t in [math.pi / 2 * i / 10 for i in range(10)]]
        v, f = g_tube(rib, 0.018 * s, seg=6)
        mb.add(v, f, 'stone_white', True)
    lant = [(0.0, z + 1.38 * s), (0.12 * s, z + 1.38 * s), (0.12 * s, z + 1.6 * s), (0.15 * s, z + 1.62 * s),
            (0.06 * s, z + 1.75 * s), (0.03 * s, z + 1.9 * s), (0.008 * s, z + 2.2 * s), (0.0, z + 2.22 * s)]
    v, f = g_revolve(lant, seg=12)
    mb.add([(a + x, b + y, c) for a, b, c in v], f, 'stone_white', True)


# ----------------------------------------------------------------------------- Haus
def build_house(h, coll, location, rotation, scale):
    """Baut das Haus in Designeinheiten; Elternobjekt trägt Lage, Drehung und Maßstab (1/k)."""
    M = house_materials(h)
    rng = random.Random(h.seed)
    eave = h.gh + h.floors * 1.0
    LM.configure(h.lx, h.ly, h.rad, eave, h.roof_h, h.roof_in, 'mansard' if h.roof_kind == 'attic' else h.roof_kind)
    root = bpy.data.objects.new(h.name, None)
    root.empty_display_type = 'CUBE'
    coll.objects.link(root)
    F = LM.edge_frames()
    cut = Cutters()
    z_corn = eave - 0.25

    # ---------- Wandkörper (Rustika-Fugen im EG)
    wall = MeshBuilder()
    prof = [(0.0, 0.0)]
    for zz in [0.16 + 0.2 * k for k in range(int((h.gh - 0.3) / 0.2))]:
        prof += [(0.0, zz - 0.014), (-0.012, zz - 0.008), (-0.012, zz + 0.008), (0.0, zz + 0.014)]
    prof += [(0.0, z_corn + 0.05), (-T_WALL, z_corn + 0.05), (-T_WALL, 0.0)]
    sweep(wall, prof, 'stone', closed_profile=True, mats=['stone'] * (len(prof) - 2) + ['interior', 'interior'])
    walls_ob = wall.build(h.name + '_Walls', M, coll)

    win, orn = MeshBuilder(), MeshBuilder()

    def floor_z(f):
        return h.gh + (f - 1) * 1.0

    def windows_column(fr, s, w, face, k):
        for f in range(1, h.floors + 1):
            z0 = floor_z(f)
            top = f == h.floors
            bal = f in h.balconies
            zb = z0 + (0.08 if bal else 0.17)
            zt = z0 + (0.72 if top else 0.8)
            cap = ('pediment' if k % 2 == 0 else 'segment') if f == 1 else ('cornice' if f == 2 else None)
            window(fr, win, cut, s, zb, zt, w, cap=cap, rail=(h.rails and not bal), keystone=f <= 3, ear=(f == 2),
                   sill=not bal)
            if h.shutters:
                shutters(fr, win, s, w, zb, zt)
            if h.lambrequins and top:
                lambrequin(fr, orn, s - w / 2 - 0.04, s + w / 2 + 0.04, zb - 0.06, h=0.2)

    for face in h.faces:
        fr, L = F[face], F[face + '_len']
        if face in h.blind or L < 0.6:
            continue
        nb = max(1, int(round(L / h.bay)))
        bw = L / nb
        w = min(bw * 0.48, 0.44)
        for k in range(nb):
            s = (k + 0.5) * bw
            door = k in h.doors.get(face, [])
            if h.ground == 'shop':
                shopfront(fr, win, cut, s, min(bw * 0.7, 0.8), 0.12, h.gh - 0.32, door=door,
                          mat=h.door_mat if door else 'wood')
            else:
                window(fr, win, cut, s, 0.2, h.gh - 0.28, min(bw * 0.5, 0.42), kind='arch', sill=False)
            windows_column(fr, s, w, face, k)
        for k in range(nb + 1):  # Lisenen zwischen den Achsen in den Obergeschossen
            s = k * bw
            fr.put(orn, g_box(s - 0.045, s + 0.045, 0, 0.018, h.gh + 0.12, z_corn - 0.05), 'trim')

    # Fenster auf großen Eckrundungen (z. B. Eckhaus vorne)
    if h.corner_windows and h.rad['SW'] > 0.4:
        R = h.rad['SW']
        a = math.radians(225)
        o = (R + R * math.cos(a), R + R * math.sin(a))
        fr = Frame(o, (-math.sin(a), math.cos(a)), (math.cos(a), math.sin(a)))
        door = 'corner' in h.doors
        shopfront(fr, win, cut, 0.0, min(0.6, R * 0.9), 0.12, h.gh - 0.32, door=door, mat=h.door_mat)
        windows_column(fr, 0.0, min(0.4, R * 0.55), 'corner', 0)

    _boolean(walls_ob, cut.mb, M, coll)
    walls_ob.parent = root

    inner = MeshBuilder()
    for z in [0.0, h.gh] + [floor_z(f) + 1.0 for f in range(1, h.floors)] + [z_corn]:
        inner.prism(ring(-T_WALL - 0.005), z - 0.04, z, 'interior', cap_bottom=True)
    _finish(inner, h.name + '_Interior', M, coll, root)

    # ---------- Gesimse, Bänder, Balkone
    cor = MeshBuilder()
    sweep(cor, [(-0.02, -0.02), (0.05, -0.02), (0.05, 0.1), (0.035, 0.12), (0.035, 0.14), (-0.02, 0.14)], 'trim')
    g = h.gh
    sweep(cor, [(-0.01, g - 0.04), (0.04, g - 0.04), (0.07, g), (0.07, g + 0.05), (0.09, g + 0.07), (0.09, g + 0.12),
                (-0.01, g + 0.12)], 'trim')
    for f in range(2, h.floors + 1):
        if f in h.balconies:
            continue
        z = floor_z(f)
        sweep(cor, [(-0.01, z - 0.02), (0.025, z - 0.02), (0.03, z), (0.025, z + 0.02), (-0.01, z + 0.02)], 'trim')
    z = z_corn
    sweep(cor, [(-0.01, z - 0.02), (0.03, z - 0.02), (0.03, z + 0.03), (0.05, z + 0.04), (0.05, z + 0.07),
                (0.09, z + 0.09), (0.12, z + 0.12), (0.12, z + 0.15), (0.2, z + 0.18), (0.25, z + 0.2),
                (0.26, z + 0.22), (0.26, eave), (0.06, eave)], 'trim', smooth=True)
    _finish(cor, h.name + '_Cornices', M, coll, root)
    bal = MeshBuilder()
    blind_test = _blind_tester(h)
    for f in h.balconies:
        if 1 < f <= h.floors:
            iron_balcony_ring(bal, floor_z(f), skip=blind_test)
    # Konsolen (Modillions) unter dem Hauptgesims
    for p, t in _ring_walk(0.0, 0.3):
        if blind_test(p):
            continue
        n = Vector((t.y, -t.x, 0))
        fr = Frame((p.x, p.y), (t.x, t.y), (n.x, n.y))
        fr.put(bal, g_extrude_dz([(0, z), (0.05, z), (0.08, z + 0.06), (0.15, z + 0.12), (0.15, z + 0.16), (0, z + 0.16)],
                                 -0.022, 0.022), 'trim')
    if h.balustrade:
        stone_balustrade_ring(bal, eave, d=0.12)
    _finish(bal, h.name + '_Balconies', M, coll, root)
    _finish(win, h.name + '_Windows', M, coll, root)
    _finish(orn, h.name + '_Ornament', M, coll, root)

    # ---------- Dach
    roof = MeshBuilder()
    rp = LM.roof_profile()
    dm = MeshBuilder()
    top = MeshBuilder()
    if h.roof_kind == 'attic':
        _attic(h, M, coll, root, roof, eave, rng)
        z_top = eave + 0.1 + h.attic_h + 0.12
    else:
        sweep(roof, rp, h.roof_mat, smooth=h.roof_kind in ('curved', 'bell'))
        sweep(roof, [(0.04, eave), (0.085, eave + 0.02), (0.085, eave + 0.07), (0.05, eave + 0.09)], 'zinc_dark',
              smooth=True)
        if h.roof_kind == 'mansard':  # Stehfalze am Unterhang
            rings = [ring(d) for d, _ in rp]
            for i in range(0, len(rings[0]), 2):
                pts = [(rg[i][0], rg[i][1], zz) for rg, (_, zz) in zip(rings, rp)][1:14]
                v, f = g_tube(pts, 0.007, seg=4)
                roof.add(v, f, 'zinc_seam')
        # Dachrand oben (Zinkwulst) + Deckfläche
        dtop, ztop_ = rp[-1]
        sweep(roof, [(dtop + 0.03, ztop_ - 0.03), (dtop + 0.05, ztop_), (dtop + 0.03, ztop_ + 0.03),
                     (dtop - 0.02, ztop_ + 0.03)], 'zinc_seam', smooth=True)
        top.prism(ring(dtop - 0.01), ztop_ - 0.05, ztop_ + 0.01, 'zinc_light' if h.roof_mat != 'roof_red' else 'roof_red')
        z_top = ztop_
        if h.dormer != 'none':
            for face in h.faces:
                if face in h.blind:
                    continue
                fr, L = F[face], F[face + '_len']
                n = h.dormer_per_face.get(face, max(1, int(round(L / h.bay))))
                if n <= 0:
                    continue
                for k in range(n):
                    s = (k + 0.5) * L / n
                    if h.dormer == 'oeil':
                        LM.dormer(fr, dm, s, t=0.3)
                    else:
                        dormer_window(fr, dm, s, 0.36, h.dormer, 'trim', h.roof_mat)
    _finish(roof, h.name + '_Roof', M, coll, root)
    if dm.verts:
        _finish(dm, h.name + '_Dormers', M, coll, root)
    for (x, y, w, d, hh, pots) in h.chimneys:
        chimney_stack(top, x, y, z_top - 0.02, w, d, hh, pots, 'brick' if rng.random() < 0.5 else 'stone')
    if top.verts:
        _finish(top, h.name + '_RoofTop', M, coll, root)

    root.location = location
    root.rotation_euler = (0, 0, rotation)
    root.scale = (scale, scale, scale)
    root['top_z_design'] = z_top
    return root


def _blind_tester(h):
    """Punkt liegt an einer Brandwand? (nur für gerade Seiten in h.blind)"""
    tests = []
    for face in h.blind:
        if face == 'right':
            tests.append(lambda p: p.y < 0.05 and h.rad['SW'] <= p.x <= h.lx - h.rad['SE'])
        elif face == 'left':
            tests.append(lambda p: p.x < 0.05 and h.rad['SW'] <= p.y <= h.ly - h.rad['NW'])
        elif face == 'east':
            tests.append(lambda p: p.x > h.lx - 0.05 and h.rad['SE'] <= p.y <= h.ly - h.rad['NE'])
        elif face == 'north':
            tests.append(lambda p: p.y > h.ly - 0.05 and h.rad['NW'] <= p.x <= h.lx - h.rad['NE'])
    return lambda p: any(t(p) for t in tests)


def _attic(h, M, coll, root, roof, eave, rng):
    """Zurückgesetztes Attikageschoss mit Fenstern, Terrassengeländer, Flachdach mit Gesims."""
    ai, ah = h.attic_in, h.attic_h
    z0 = eave + 0.08
    # Terrassenboden + Geländer an der Traufkante
    roof.prism(ring(0.02), eave - 0.02, z0, 'deck')
    dr = 0.0
    sweep(roof, [(dr - 0.012, z0 + 0.3), (dr + 0.012, z0 + 0.3), (dr + 0.012, z0 + 0.32), (dr - 0.012, z0 + 0.32)],
          'iron')
    for p, t in _ring_walk(dr, 0.05):
        roof.box((p.x, p.y, z0 + 0.16), (0.01, 0.01, 0.32), 'iron')
    # Attikawand mit Öffnungen
    wall = MeshBuilder()
    sweep(wall, [(-ai, z0), (-ai, z0 + ah), (-ai - T_WALL, z0 + ah), (-ai - T_WALL, z0)], 'stone', closed_profile=True,
          mats=['stone', 'interior', 'interior', 'interior'])
    wob = wall.build(h.name + '_AtticWalls', M, coll)
    cut = Cutters()
    win = MeshBuilder()
    F = LM.edge_frames(-ai)
    for face in h.faces:
        if face in h.blind:
            continue
        fr, L = F[face], F[face + '_len']
        nb = max(1, int(round(L / (h.bay * 0.8))))
        for k in range(nb):
            s = (k + 0.5) * L / nb
            fr2 = Frame((fr.O.x, fr.O.y), (fr.t.x, fr.t.y), (fr.n.x, fr.n.y))
            window(fr2, win, cut, s, z0 + 0.12, z0 + ah - 0.14, 0.34, keystone=False, sill=True)
    _boolean(wob, cut.mb, M, coll)
    wob.parent = root
    _finish(win, h.name + '_AtticWindows', M, coll, root)
    zt = z0 + ah
    sweep(roof, [(-ai - 0.01, zt - 0.02), (-ai + 0.04, zt), (-ai + 0.07, zt + 0.04), (-ai + 0.07, zt + 0.1),
                 (-ai - 0.02, zt + 0.12)], 'trim')
    roof.prism(ring(-ai - 0.01), zt, zt + 0.12, 'deck')
