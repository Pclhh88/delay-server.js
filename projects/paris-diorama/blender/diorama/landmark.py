"""Qualitäts-Benchmark: das große Kuppel-Mansardhaus rechts neben dem Eiffelturm.

Eigenständiges, frei drehbares Modell (Elternobjekt + benannte Teile). Maße in Szeneneinheiten,
Grundriss/Traufe/Dach aus der Vermessung (analysis/REKONSTRUKTION_EXAKT.md, Gebäude F).

Techniken:
  * Profil-Sweeps entlang des gerundeten Grundrisses (Sockel, Bänder, Hauptgesims, Dach, Falze, Brüstung)
  * Wände als geschlossener Körper, Fensteröffnungen per Boolean (echte Laibungen, Innenraum dahinter)
  * Fenster: Zarge, Flügel, Sprossen, Kämpfer, profilierte Faschen (Gehrung), Schlussstein, Bank auf Konsolen
  * gedrechselte Teile (Erker, Kuppelhaube, Vasen, Schornsteinköpfe), Voluten als Spiralbänder,
    Festons/Draperien als Röhren entlang Kettenlinien
Lokales System: Ursprung = Ecke (min x, min y) des Grundriss-Rechtecks, +x rechte Fassade (Normale -y),
+y linke Fassade (Normale -x), z ab Gehwegoberkante.
"""
import math
import bmesh
import bpy
from mathutils import Vector

from .meshkit import MeshBuilder

# ----------------------------------------------------------------------------- Maße
LX, LY = 4.4, 5.21
RAD = dict(SW=1.3, SE=0.35, NE=0.25, NW=0.35)
T_WALL = 0.16
Z_G, Z_B1 = 1.5, 1.62          # Erdgeschoss, Gurtgesims
Z_F1 = (1.62, 2.62)
Z_F2 = (2.62, 3.55)
Z_BAND = (3.55, 3.72)           # breites Fries-/Kapitellband
Z_F3 = (3.72, 4.78)
Z_CORN = 4.78                   # Unterkante Hauptgesims
Z_EAVE = 5.07                   # Oberkante Hauptgesims = Dachfuß
ROOF_H, ROOF_IN = 1.62, 0.85    # Mansarde: Höhe, Rücksprung
SEG = 12


# ----------------------------------------------------------------------------- Grundriss-Ringe
def _straight_counts(step=0.22):
    r = RAD
    lens = [LX - r['SW'] - r['SE'], LY - r['SE'] - r['NE'], LX - r['NE'] - r['NW'], LY - r['NW'] - r['SW']]
    return [max(1, int(round(L / step))) for L in lens]


_NS = _straight_counts()


def ring(d, rmin=0.04):
    """Gerundetes Rechteck um d nach außen versetzt (d<0 innen); feste Punktzahl für alle d."""
    x0, y0, x1, y1 = -d, -d, LX + d, LY + d
    hw = min(x1 - x0, y1 - y0) / 2 - 1e-3
    r = {k: min(max(v + d, rmin), hw) for k, v in RAD.items()}
    spec = [('SW', (x0 + r['SW'], y0 + r['SW']), 180), ('SE', (x1 - r['SE'], y0 + r['SE']), 270),
            ('NE', (x1 - r['NE'], y1 - r['NE']), 0), ('NW', (x0 + r['NW'], y1 - r['NW']), 90)]
    pts = []
    for ci, (k, (cx, cy), a0) in enumerate(spec):
        for i in range(SEG + 1):
            a = math.radians(a0 + 90 * i / SEG)
            pts.append((cx + r[k] * math.cos(a), cy + r[k] * math.sin(a)))
        # Gerade bis zum nächsten Bogen
        nk, (ncx, ncy), na0 = spec[(ci + 1) % 4]
        a1 = math.radians(na0)
        p_end = pts[-1]
        p_next = (ncx + r[nk] * math.cos(a1), ncy + r[nk] * math.sin(a1))
        n = _NS[ci]
        for j in range(1, n):
            t = j / n
            pts.append((p_end[0] + (p_next[0] - p_end[0]) * t, p_end[1] + (p_next[1] - p_end[1]) * t))
    return pts


def sweep(mb, profile, mat, closed_profile=False, smooth=False, mats=None):
    """Profil [(d, z), ...] entlang des Grundriss-Rings fegen (geschlossene Schleife)."""
    rings = [ring(d) for d, _ in profile]
    n = len(rings[0])
    verts = [(x, y, z) for (d, z), rg in zip(profile, rings) for (x, y) in rg]
    m = len(profile)
    kmax = m if closed_profile else m - 1
    groups = {}
    for k in range(kmax):
        k2 = (k + 1) % m
        mt = mats[k] if mats else mat
        for i in range(n):
            j = (i + 1) % n
            groups.setdefault(mt, []).append((k * n + i, k * n + j, k2 * n + j, k2 * n + i))
    o = None
    for mt, faces in groups.items():
        if o is None:
            o = mb.add(verts, faces, mt, smooth)
        else:  # weitere Materialgruppen auf denselben Punkten
            mi = mb._mi(mt)
            for f in faces:
                mb.faces.append([o + i for i in f])
                mb.face_mats.append(mi)
                mb.smooth.append(smooth)
    return rings


# ----------------------------------------------------------------------------- lokale Fassadensysteme
class Frame:
    """Fassadensystem: s entlang der Wand, d nach außen, z nach oben."""

    def __init__(self, origin, t, n):
        self.O = Vector((origin[0], origin[1], 0))
        self.t = Vector((t[0], t[1], 0)).normalized()
        self.n = Vector((n[0], n[1], 0)).normalized()
        self.flip = self.t.cross(self.n).z < 0  # linkshändig -> Flächen umdrehen

    def P(self, s, d, z):
        return self.O + self.t * s + self.n * d + Vector((0, 0, z))

    def put(self, mb, geo, mat, smooth=False):
        verts, faces = geo
        vv = [self.P(*v) for v in verts]
        if self.flip:
            faces = [tuple(reversed(f)) for f in faces]
        return mb.add(vv, faces, mat, smooth)

    def rotated(self, s, d, ang):
        """Neues System an (s, d), um ang (rad) um z gedreht (für Erkerfenster)."""
        o = self.P(s, d, 0)
        t = self.t * math.cos(ang) + self.n * math.sin(ang)
        n = -self.t * math.sin(ang) + self.n * math.cos(ang)
        return Frame((o.x, o.y), (t.x, t.y), (n.x, n.y))


def edge_frames():
    r = RAD
    return {
        'right': Frame((r['SW'], 0), (1, 0), (0, -1)), 'right_len': LX - r['SW'] - r['SE'],
        'left': Frame((0, LY - r['NW']), (0, -1), (-1, 0)), 'left_len': LY - r['NW'] - r['SW'],
        'east': Frame((LX, r['SE']), (0, 1), (1, 0)), 'east_len': LY - r['SE'] - r['NE'],
        'north': Frame((LX - r['NE'], LY), (-1, 0), (0, 1)), 'north_len': LX - r['NE'] - r['NW'],
    }


# ----------------------------------------------------------------------------- Grundformen (lokal s,d,z)
def g_box(s0, s1, d0, d1, z0, z1):
    v = [(s, d, z) for z in (z0, z1) for d in (d0, d1) for s in (s0, s1)]
    f = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    return v, f


def g_extrude_sz(poly, d0, d1):
    """Konvexes Polygon in (s, z) entlang d extrudieren."""
    n = len(poly)
    v = [(s, d0, z) for s, z in poly] + [(s, d1, z) for s, z in poly]
    f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    f += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return v, f


def g_extrude_dz(poly, s0, s1):
    """Konvexes Polygon in (d, z) entlang s extrudieren (Konsolen, Seitenprofile)."""
    n = len(poly)
    v = [(s0, d, z) for d, z in poly] + [(s1, d, z) for d, z in poly]
    f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    f += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return v, f


def g_molding(path, closed_ends, profile):
    """Profil [(e, d)] entlang offenem Pfad [(s, z)] in der Wandebene; e = Abstand vom Pfad nach
    außen (weg von der Öffnung), Gehrung an den Ecken. closed_ends: (normale_start, normale_ende)."""
    n = len(path)
    segn = []
    for i in range(n - 1):
        (s0, z0), (s1, z1) = path[i], path[i + 1]
        L = math.hypot(s1 - s0, z1 - z0)
        segn.append(((z1 - z0) / L, -(s1 - s0) / L))  # rechts vom Laufweg
    miters = []
    for i in range(n):
        if i == 0:
            m = segn[0]
        elif i == n - 1:
            m = segn[-1]
        else:
            a, b = segn[i - 1], segn[i]
            dot = a[0] * b[0] + a[1] * b[1]
            m = ((a[0] + b[0]) / (1 + dot), (a[1] + b[1]) / (1 + dot))
        miters.append(m)
    v = []
    for (s, z), (ms, mz) in zip(path, miters):
        for e, d in profile:
            v.append((s + ms * e, d, z + mz * e))
    m = len(profile)
    f = []
    for i in range(n - 1):
        for j in range(m - 1):
            f.append((i * m + j, i * m + j + 1, (i + 1) * m + j + 1, (i + 1) * m + j))
    f.append(tuple(range(m)))
    f.append(tuple((n - 1) * m + j for j in range(m - 1, -1, -1)))
    return v, f


def g_revolve(profile, seg=24, a0=0.0, a1=2 * math.pi, cs=0.0, cd=0.0, caps=False):
    """Drehkörper um senkrechte Achse bei (cs, cd); profile [(r, z)] von unten nach oben."""
    full = abs(a1 - a0 - 2 * math.pi) < 1e-6
    cnt = seg if full else seg + 1
    v = []
    for r, z in profile:
        for i in range(cnt):
            a = a0 + (a1 - a0) * i / seg
            v.append((cs + r * math.cos(a), cd + r * math.sin(a), z))
    f = []
    m = len(profile)
    for k in range(m - 1):
        for i in range(seg):
            j = (i + 1) % cnt
            f.append((k * cnt + i, k * cnt + j, (k + 1) * cnt + j, (k + 1) * cnt + i))
    if full:
        if profile[0][0] > 1e-6:
            f.append(tuple(range(cnt - 1, -1, -1)))
        if profile[-1][0] > 1e-6:
            f.append(tuple((m - 1) * cnt + i for i in range(cnt)))
    elif caps:
        f.append(tuple(k * cnt for k in range(m)))
        f.append(tuple(k * cnt + cnt - 1 for k in range(m - 1, -1, -1)))
    return v, f


def g_tube(pts, r, seg=8, taper=None):
    """Röhre entlang Punktliste (lokal); taper(i)->Radiusfaktor."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    v = []
    prev_u = None
    for i, p in enumerate(pts):
        tng = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        ref = Vector((0, 0, 1)) if abs(tng.z) < 0.9 else Vector((1, 0, 0))
        u = tng.cross(ref).normalized() if prev_u is None else (prev_u - tng * prev_u.dot(tng)).normalized()
        w = tng.cross(u)
        prev_u = u
        rr = r * (taper(i / max(1, n - 1)) if taper else 1.0)
        for k in range(seg):
            a = 2 * math.pi * k / seg
            q = p + (u * math.cos(a) + w * math.sin(a)) * rr
            v.append((q.x, q.y, q.z))
    f = []
    for i in range(n - 1):
        for k in range(seg):
            j = (k + 1) % seg
            f.append((i * seg + k, i * seg + j, (i + 1) * seg + j, (i + 1) * seg + k))
    f.append(tuple(range(seg - 1, -1, -1)))
    f.append(tuple((n - 1) * seg + k for k in range(seg)))
    return v, f


def g_scroll(cs, cz, r0, d0, d1, turns=1.75, hand=1, band=0.022, n=48):
    """Volute: Spiralband in der Wandebene (s, z), Tiefe d0..d1. hand=+1/-1 Drehsinn."""
    k = math.log(5.0) / (turns * 2 * math.pi)   # Radius schrumpft über die Windungen auf 1/5
    v = []
    for i in range(n + 1):
        th = turns * 2 * math.pi * i / n
        r = r0 * math.exp(-k * th)
        a = math.pi / 2 + hand * th
        ro, ri = r, max(r - band * (1.4 - 0.8 * i / n), 0.004)
        for rr in (ro, ri):
            for d in (d0, d1):
                v.append((cs + rr * math.cos(a), d, cz + rr * math.sin(a)))
    f = []
    for i in range(n):
        a, b = 4 * i, 4 * (i + 1)
        # outer(d0,d1)=0,1 inner(d0,d1)=2,3
        f += [(a, b, b + 1, a + 1), (a + 2, a + 3, b + 3, b + 2), (a + 1, b + 1, b + 3, a + 3), (a, a + 2, b + 2, b)]
    f.append((0, 1, 3, 2))
    e = 4 * n
    f.append((e, e + 2, e + 3, e + 1))
    return v, f


def catenary(s0, s1, z, sag, d, n=14, bulge=0.0):
    pts = []
    for i in range(n + 1):
        t = i / n
        s = s0 + (s1 - s0) * t
        zz = z - sag * (1 - (2 * t - 1) ** 2)
        pts.append((s, d + bulge * (1 - (2 * t - 1) ** 2), zz))
    return pts


# ----------------------------------------------------------------------------- Bauteile
WIN_PROF = [(0.0, 0.0), (0.0, 0.016), (0.012, 0.022), (0.03, 0.022), (0.042, 0.032), (0.058, 0.032),
            (0.066, 0.02), (0.072, 0.0)]   # Faschenprofil (e, d)


def window(fr, mb, cutters, s, zb, zt, w, kind='rect', cap=None, sill=True, rail=False, keystone=True,
           ear=False, depth=T_WALL):
    """Komplettes Fenster: Öffnung (Cutter) + Zarge + Flügel + Sprossen + Glas + Faschen + Bank."""
    h = zt - zb
    rise = w / 2 if kind == 'arch' else (w * 0.18 if kind == 'segment' else 0.0)
    zs = zt - rise                     # Kämpferlinie
    # --- Öffnung
    if kind == 'rect':
        cutters.append(fr, g_box(s - w / 2, s + w / 2, -depth - 0.05, 0.06, zb, zt))
    else:
        poly = [(s - w / 2, zb), (s + w / 2, zb)]
        for i in range(13):
            a = math.pi * i / 12
            if kind == 'arch':
                poly.append((s + w / 2 * math.cos(a), zs + w / 2 * math.sin(a)))
            else:
                R = (w * w / 4 + rise * rise) / (2 * rise)
                a0 = math.asin((w / 2) / R)
                aa = a0 - 2 * a0 * i / 12
                poly.append((s + R * math.sin(aa), zt - R + R * math.cos(aa)))
        # gegen den Uhrzeigersinn: unten links, unten rechts, Bogen von rechts nach links
        cutters.append(fr, g_extrude_sz(poly, -depth - 0.05, 0.06))
    dg = -0.085                        # Glasebene
    fw = 0.026
    # --- Zarge
    fr.put(mb, g_box(s - w / 2, s - w / 2 + fw, dg - 0.02, dg + 0.02, zb, zs), 'frame')
    fr.put(mb, g_box(s + w / 2 - fw, s + w / 2, dg - 0.02, dg + 0.02, zb, zs), 'frame')
    fr.put(mb, g_box(s - w / 2, s + w / 2, dg - 0.02, dg + 0.02, zb, zb + fw), 'frame')
    if kind == 'rect':
        fr.put(mb, g_box(s - w / 2, s + w / 2, dg - 0.02, dg + 0.02, zt - fw, zt), 'frame')
    else:
        arc = [(s + (w / 2 - fw / 2) * math.cos(math.pi * i / 10), dg, zs + (w / 2 - fw / 2) * math.sin(math.pi * i / 10))
               for i in range(11)] if kind == 'arch' else None
        if arc:
            fr.put(mb, g_tube(arc, fw * 0.6, seg=6), 'frame')
        else:
            fr.put(mb, g_box(s - w / 2, s + w / 2, dg - 0.02, dg + 0.02, zs - fw, zs + rise * 0.5), 'frame')
    # --- Flügel, Kämpfer, Sprossen
    ztr = zb + (zs - zb) * 0.76
    fr.put(mb, g_box(s - 0.011, s + 0.011, dg - 0.015, dg + 0.025, zb, ztr), 'frame')
    fr.put(mb, g_box(s - w / 2, s + w / 2, dg - 0.015, dg + 0.025, ztr - 0.014, ztr + 0.014), 'frame')
    for leaf in (-1, 1):
        sc = s + leaf * w / 4
        for k in (1, 2):
            z = zb + (ztr - zb) * k / 3
            fr.put(mb, g_box(sc - w / 4, sc + w / 4, dg - 0.008, dg + 0.012, z - 0.006, z + 0.006), 'frame')
    fr.put(mb, g_box(s - w / 2 + fw, s + w / 2 - fw, dg - 0.004, dg + 0.002, zb + fw, zs + rise * 0.98), 'glass')
    # Vorhang/Innenraum-Andeutung hinter dem Glas
    fr.put(mb, g_box(s - w / 2 + fw, s - w / 2 + w * 0.3, dg - 0.06, dg - 0.05, zb + fw, ztr), 'curtain')
    # --- Faschen (profiliert, auf Gehrung)
    if kind == 'rect':
        path = [(s - w / 2, zb), (s - w / 2, zt), (s + w / 2, zt), (s + w / 2, zb)]
    else:
        path = [(s - w / 2, zb), (s - w / 2, zs)]
        if kind == 'arch':
            path += [(s - w / 2 * math.cos(math.pi * i / 12), zs + w / 2 * math.sin(math.pi * i / 12)) for i in range(1, 12)]
        else:
            R = (w * w / 4 + rise * rise) / (2 * rise)
            a0 = math.asin((w / 2) / R)
            path += [(s + R * math.sin(-a0 + 2 * a0 * i / 12), zt - R + R * math.cos(-a0 + 2 * a0 * i / 12)) for i in range(1, 12)]
        path += [(s + w / 2, zs), (s + w / 2, zb)]
    fr.put(mb, g_molding(path, None, [(-e, d) for e, d in WIN_PROF][::-1]), 'trim')
    if ear:  # Ohren der Faschen
        for sx in (-1, 1):
            fr.put(mb, g_box(s + sx * (w / 2 + 0.035) - 0.04, s + sx * (w / 2 + 0.035) + 0.04, 0, 0.03, zt - 0.06, zt + 0.07), 'trim')
    if keystone:
        top = zt + (0.0 if kind == 'rect' else 0.0)
        fr.put(mb, g_extrude_sz([(s - 0.035, top - 0.07), (s + 0.035, top - 0.07), (s + 0.05, top + 0.08),
                                 (s - 0.05, top + 0.08)], 0, 0.05), 'trim')
    # --- Fensterbank mit Konsolen
    if sill:
        fr.put(mb, g_extrude_dz([(-depth + 0.02, zb - 0.045), (0.07, zb - 0.045), (0.085, zb - 0.025),
                                 (0.075, zb), (-depth + 0.02, zb)], s - w / 2 - 0.08, s + w / 2 + 0.08), 'trim')
        for sx in (-1, 1):
            c = s + sx * (w / 2 + 0.03)
            fr.put(mb, g_extrude_dz([(0, zb - 0.16), (0.02, zb - 0.16), (0.06, zb - 0.07), (0.06, zb - 0.045),
                                     (0, zb - 0.045)], c - 0.025, c + 0.025), 'trim')
    # --- Verdachung
    if cap == 'cornice':
        fr.put(mb, g_extrude_dz([(0, zt + 0.06), (0.06, zt + 0.06), (0.09, zt + 0.09), (0.09, zt + 0.125),
                                 (0, zt + 0.125)], s - w / 2 - 0.12, s + w / 2 + 0.12), 'trim')
        fr.put(mb, g_box(s - w / 2 - 0.09, s + w / 2 + 0.09, 0, 0.045, zt + 0.02, zt + 0.06), 'trim')
        for sx in (-1, 1):
            c = s + sx * (w / 2 + 0.08)
            fr.put(mb, g_extrude_dz([(0, zt - 0.12), (0.025, zt - 0.12), (0.07, zt + 0.02), (0.07, zt + 0.06),
                                     (0, zt + 0.06)], c - 0.022, c + 0.022), 'trim')
    elif cap == 'pediment':
        base = zt + 0.07
        fr.put(mb, g_box(s - w / 2 - 0.11, s + w / 2 + 0.11, 0, 0.07, base - 0.03, base + 0.01), 'trim')
        apex = base + w * 0.32
        pts = [(s - w / 2 - 0.12, base), (s, apex), (s + w / 2 + 0.12, base)]
        fr.put(mb, g_molding(pts, None, [(0.0, 0.0), (0.0, 0.05), (0.03, 0.075), (0.045, 0.075), (0.05, 0.0)]), 'trim')
        fr.put(mb, g_extrude_sz([(s - w / 2 - 0.08, base + 0.01), (s + w / 2 + 0.08, base + 0.01), (s, apex - 0.03)],
                                0, 0.025), 'trim')
    elif cap == 'segment':
        base = zt + 0.06
        R = w * 0.9
        a0 = math.asin(min(0.99, (w / 2 + 0.12) / R))
        pts = [(s + R * math.sin(-a0 + 2 * a0 * i / 14), base - R * math.cos(a0) + R * math.cos(-a0 + 2 * a0 * i / 14))
               for i in range(15)]
        fr.put(mb, g_molding(pts, None, [(0.0, 0.0), (0.0, 0.05), (0.03, 0.08), (0.05, 0.08), (0.06, 0.0)]), 'trim')
    if rail:
        rz = zb + 0.02
        fr.put(mb, g_box(s - w / 2, s + w / 2, 0.015, 0.03, rz + 0.25, rz + 0.27), 'iron')
        fr.put(mb, g_box(s - w / 2, s + w / 2, 0.015, 0.03, rz + 0.02, rz + 0.035), 'iron')
        nb = int(w / 0.035)
        for i in range(nb + 1):
            x = s - w / 2 + w * i / nb
            fr.put(mb, g_box(x - 0.004, x + 0.004, 0.018, 0.027, rz, rz + 0.25), 'iron')
        for i in range(3):  # Zierkreise
            x = s - w / 3 + w / 3 * i
            ring_ = [(x + 0.04 * math.cos(2 * math.pi * k / 12), 0.023, rz + 0.14 + 0.04 * math.sin(2 * math.pi * k / 12))
                     for k in range(13)]
            fr.put(mb, g_tube(ring_, 0.004, seg=4), 'iron')


def festoon(fr, mb, s0, s1, z, sag=0.09, d=0.02):
    """Steinerne Draperie: drei gestaffelte Stoffbahnen, seitlich herabfallende Enden mit Quasten."""
    for k, (sg, rr, dz) in enumerate(((sag, 0.042, 0.0), (sag * 0.8, 0.036, -0.05), (sag * 0.6, 0.03, -0.095))):
        pts = catenary(s0 + k * 0.012, s1 - k * 0.012, z + dz, sg, d + rr, n=16, bulge=0.02)
        fr.put(mb, g_tube(pts, rr, seg=10, taper=lambda t: 0.75 + 0.5 * math.sin(math.pi * t)), 'trim', True)
    for s in (s0, s1):
        drop = [(s, d + 0.03, z + 0.01 - 0.04 * i) for i in range(9)]
        fr.put(mb, g_tube(drop, 0.034, seg=10, taper=lambda t: 1.0 - 0.45 * t), 'trim', True)
        fr.put(mb, g_revolve([(0.0, z - 0.27), (0.022, z - 0.25), (0.016, z - 0.22), (0.0, z - 0.2)], seg=10,
                             cs=s, cd=d + 0.02), 'trim', True)
    fr.put(mb, g_revolve([(0.0, z - 0.03), (0.03, z - 0.01), (0.03, z + 0.02), (0.0, z + 0.04)], seg=10,
                         cs=(s0 + s1) / 2, cd=d + 0.02), 'trim', True)  # Rosette Mitte


def lambrequin(fr, mb, s0, s1, ztop, h=0.2):
    """Gefaltetes Steintuch unter einem Fenster: Faltenwürfe als Röhren, gezackter Saum."""
    nfold = 7
    for i in range(nfold):
        s = s0 + (s1 - s0) * (i + 0.5) / nfold
        L = h * (0.75 + 0.25 * math.cos(math.pi * (2 * i / (nfold - 1) - 1)))
        pts = [(s, 0.012, ztop - L * j / 6) for j in range(7)]
        fr.put(mb, g_tube(pts, (s1 - s0) / nfold * 0.62, seg=10, taper=lambda t: 1.15 - 0.45 * t), 'trim', True)
    fr.put(mb, g_box(s0 - 0.02, s1 + 0.02, 0, 0.04, ztop - 0.02, ztop + 0.03), 'trim')


def ionic_capital(fr, mb, s0, s1, z, d=0.0):
    """Zwei Voluten nebeneinander + Echinus + Abakus (wie in der Vorlage am rechten Eckpfeiler)."""
    w = s1 - s0
    r = w * 0.27
    fr.put(mb, g_scroll(s0 + r * 1.05, z + r * 1.05, r, d, d + 0.07, hand=-1), 'trim')
    fr.put(mb, g_scroll(s1 - r * 1.05, z + r * 1.05, r, d, d + 0.07, hand=1), 'trim')
    for cs in (s0 + r * 1.05, s1 - r * 1.05):  # Volutenauge
        fr.put(mb, g_tube([(cs, d - 0.01, z + r * 1.05), (cs, d + 0.085, z + r * 1.05)], r * 0.22, seg=12), 'trim', True)
    fr.put(mb, g_box(s0 + r * 1.05, s1 - r * 1.05, d, d + 0.05, z + r * 0.3, z + r * 2.0), 'trim')  # Polster
    fr.put(mb, g_extrude_dz([(0, z - 0.02), (0.05, z - 0.02), (0.075, z + 0.04), (0.06, z + 0.08), (0, z + 0.08)],
                            s0 + 0.04, s1 - 0.04), 'trim')  # Echinus
    for i in range(5):  # Eierstab
        s = s0 + 0.08 + (w - 0.16) * i / 4
        fr.put(mb, g_revolve([(0.0, z), (0.022, z + 0.015), (0.022, z + 0.045), (0.0, z + 0.06)], seg=10,
                             cs=s, cd=d + 0.07), 'trim', True)
    fr.put(mb, g_box(s0 - 0.03, s1 + 0.03, d, d + 0.1, z + 2.1 * r, z + 2.1 * r + 0.05), 'trim')  # Abakus


def oriel(fr, mb, cutters, s, r, z0, z1, n_win, cap_h=0.38):
    """Halbrunder Erker: Kragsockel, Körper, Fenster je Geschoss, Bänder, Kuppelhaube mit Knauf."""
    body = []
    body.append(g_revolve([(0.0, z0), (r, z0), (r, z1), (0.0, z1)], seg=24, a0=0, a1=math.pi, cs=s, cd=0.0, caps=True))
    # Kragsockel (Konsolkegel mit Profilen)
    prof = [(0.0, z0 - 0.55), (0.05, z0 - 0.5), (0.12, z0 - 0.38), (0.2, z0 - 0.3), (r * 0.8, z0 - 0.16),
            (r + 0.02, z0 - 0.08), (r + 0.06, z0 - 0.06), (r + 0.06, z0), (0.0, z0)]
    fr.put(mb, g_revolve(prof, seg=24, a0=0, a1=math.pi, cs=s, cd=0.0, caps=True), 'stone', True)
    # Gesimsringe je Geschoss + Kranzgesims
    zs = [z0 + (z1 - z0) * k / n_win for k in range(n_win + 1)]
    for zz in zs[1:-1]:
        fr.put(mb, g_revolve([(0.0, zz - 0.03), (r + 0.035, zz - 0.03), (r + 0.045, zz), (r + 0.035, zz + 0.025),
                              (0.0, zz + 0.025)], seg=24, a0=0, a1=math.pi, cs=s, cd=0.0, caps=True), 'trim', True)
    fr.put(mb, g_revolve([(0.0, z1 - 0.02), (r + 0.03, z1 - 0.02), (r + 0.08, z1 + 0.03), (r + 0.09, z1 + 0.07),
                          (0.0, z1 + 0.07)], seg=24, a0=0, a1=math.pi, cs=s, cd=0.0, caps=True), 'trim', True)
    # Kuppelhaube
    dome = [(r + 0.06, z1 + 0.07)] + [((r + 0.06) * math.cos(a), z1 + 0.07 + cap_h * math.sin(a))
                                      for a in [math.pi / 2 * i / 10 for i in range(1, 11)]]
    dome = [(0.0, z1 + 0.07)] + dome
    fr.put(mb, g_revolve(dome, seg=24, a0=0, a1=math.pi, cs=s, cd=0.0, caps=True), 'stone', True)
    for k in range(1, 6):  # Rippen
        a = math.pi * k / 6
        rib = [(s + (r + 0.07) * math.cos(b) * math.cos(a), (r + 0.07) * math.cos(b) * math.sin(a),
                z1 + 0.07 + (cap_h + 0.01) * math.sin(b)) for b in [math.pi / 2 * i / 10 for i in range(10)]]
        fr.put(mb, g_tube(rib, 0.012, seg=6), 'trim', True)
    fr.put(mb, g_revolve([(0.0, z1 + 0.07 + cap_h), (0.035, z1 + 0.08 + cap_h), (0.02, z1 + 0.13 + cap_h),
                          (0.03, z1 + 0.17 + cap_h), (0.0, z1 + 0.21 + cap_h)], seg=12, cs=s, cd=0.0), 'trim', True)
    # Fenster (Mitte, nach außen)
    for k in range(n_win):
        za, zb_ = zs[k], zs[k + 1]
        h = zb_ - za
        # radiales System: Ursprung Erkermitte, t tangential, n nach außen (Mitte = 90°)
        o = fr.P(s, 0, 0)
        rf = Frame((o.x, o.y), (fr.t.x, fr.t.y), (fr.n.x, fr.n.y))
        rf.O = rf.O + rf.n * r
        window(rf, mb, cutters, 0.0, za + h * 0.2, za + h * 0.82, min(0.3, r * 0.75), sill=True, keystone=False,
               depth=0.12)
    return body


def balcony(fr, mb, s0, s1, z, depth=0.38):
    """Steinbalkon: Platte mit Profil, Konsolen, massive Brüstung mit vertieften Spiegeln."""
    fr.put(mb, g_extrude_dz([(0, z - 0.1), (depth - 0.03, z - 0.1), (depth, z - 0.07), (depth + 0.01, z - 0.03),
                             (depth, z), (0, z)], s0, s1), 'trim')
    n = max(2, int((s1 - s0) / 0.35))
    for i in range(n + 1):
        c = s0 + 0.06 + (s1 - s0 - 0.12) * i / n
        fr.put(mb, g_extrude_dz([(0, z - 0.42), (0.04, z - 0.42), (0.1, z - 0.3), (depth * 0.85, z - 0.12),
                                 (depth * 0.85, z - 0.1), (0, z - 0.1)], c - 0.04, c + 0.04), 'trim')
        fr.put(mb, g_tube([(c, 0.06, z - 0.38), (c, 0.06, z - 0.33)], 0.03, seg=8), 'trim', True)
    # Brüstung: drei Seiten
    hb, tb = 0.32, 0.07
    sides = [(s0, s1, depth - tb, depth), (s0, s0 + tb, 0, depth), (s1 - tb, s1, 0, depth)]
    for a, b, d0, d1 in sides:
        fr.put(mb, g_box(a, b, d0, d1, z, z + hb), 'stone')
    fr.put(mb, g_extrude_dz([(depth - tb - 0.02, z + hb), (depth + 0.02, z + hb), (depth + 0.03, z + hb + 0.03),
                             (depth + 0.01, z + hb + 0.06), (depth - tb - 0.02, z + hb + 0.06)], s0 - 0.02, s1 + 0.02), 'trim')
    for sx, (a, b) in ((0, (s0 - 0.02, s0 + tb + 0.02)), (1, (s1 - tb - 0.02, s1 + 0.02))):
        fr.put(mb, g_box(a, b, -0.01, depth + 0.02, z + hb, z + hb + 0.06), 'trim')
    # vertiefte Spiegel mit Rahmenprofil auf der Front
    m = max(1, int((s1 - s0) / 0.45))
    for i in range(m):
        a = s0 + 0.08 + (s1 - s0 - 0.16) * i / m + 0.03
        b = s0 + 0.08 + (s1 - s0 - 0.16) * (i + 1) / m - 0.03
        path = [(a, z + 0.06), (a, z + hb - 0.06), (b, z + hb - 0.06), (b, z + 0.06), (a, z + 0.06)]
        fr.put(mb, g_molding(path, None, [(0.0, depth), (0.0, depth + 0.012), (0.012, depth + 0.012), (0.02, depth)]),
               'trim')


# ----------------------------------------------------------------------------- Dachdetails
def roof_profile(n=16):
    """Glockenförmige Mansarde: unten senkrecht mit leichtem Ausschwung, oben ~40° flacher."""
    pts = [(0.06, Z_EAVE - 0.01), (0.07, Z_EAVE + 0.04)]
    th_max = math.radians(70)
    for i in range(1, n + 1):
        th = th_max * i / n
        bulge = 0.1 * math.sin(math.pi * min(1.0, 1.6 * i / n))          # Ausbauchung im unteren Drittel
        d = 0.07 + bulge - ROOF_IN * (1 - math.cos(th)) / (1 - math.cos(th_max))
        z = Z_EAVE + 0.04 + (ROOF_H - 0.04) * math.sin(th) / math.sin(th_max)
        pts.append((d, z))
    return pts


def roof_point(t):
    """Punkt (d, z) und Hangneigung auf dem Dachprofil, t in [0, 1]."""
    prof = roof_profile(64)
    i = min(int(t * (len(prof) - 1)), len(prof) - 2)
    (d0, z0), (d1, z1) = prof[i], prof[i + 1]
    f = t * (len(prof) - 1) - i
    return d0 + (d1 - d0) * f, z0 + (z1 - z0) * f, math.atan2(z1 - z0, -(d1 - d0) + 1e-9)


def dormer(fr, mb, s, t=0.3, w=0.3, big=False):
    """Ochsenauge-Gaube mit Haube, auf das Dach gesetzt (Rückseite taucht ins Dach)."""
    d, z, slope = roof_point(t)
    if big:
        w *= 1.35
    h = w * 1.05
    zb = z - 0.02
    fr.put(mb, g_box(s - w / 2, s + w / 2, d - 0.45, d + 0.1, zb, zb + h * 0.75), 'zinc_dark')
    # Front: profiliertes Rund-/Ovalfenster
    cz = zb + h * 0.42
    rr = w * 0.3
    ring_ = [(s + rr * math.cos(2 * math.pi * k / 20), d + 0.105, cz + rr * 1.1 * math.sin(2 * math.pi * k / 20))
             for k in range(21)]
    fr.put(mb, g_tube(ring_, 0.02, seg=8), 'zinc_dark', True)
    disc = [(s + rr * 0.92 * math.cos(2 * math.pi * k / 20), d + 0.1, cz + rr * 1.0 * math.sin(2 * math.pi * k / 20))
            for k in range(20)]
    mb.add([fr.P(*p) for p in disc], [tuple(range(20))], 'glass')
    # Haube: halber Zylinder, nach vorn auskragend
    top = zb + h * 0.75
    hood = []
    for k in range(13):
        a = math.pi * k / 12
        hood.append((s + (w / 2 + 0.03) * math.cos(a), top + (w / 2 + 0.03) * 0.75 * math.sin(a)))
    v, f = [], []
    for j, dd in enumerate((d - 0.45, d + 0.14)):
        for (ss, zz) in hood:
            v.append((ss, dd, zz))
    for (ss, zz) in hood:
        v.append((ss, d + 0.14, zz - 0.03))
    n = len(hood)
    for k in range(n - 1):
        f.append((k, n + k, n + k + 1, k + 1))
        f.append((n + k, 2 * n + k, 2 * n + k + 1, n + k + 1))
    fr.put(mb, (v, f), 'zinc_dark', True)
    fr.put(mb, g_extrude_sz([(s - w / 2 - 0.03, top - 0.03), (s + w / 2 + 0.03, top - 0.03),
                             (s + w / 2 + 0.03, top), (s - w / 2 - 0.03, top)], d - 0.45, d + 0.14), 'zinc_dark')
    # seitliche Voluten der Gaube
    for sx in (-1, 1):
        fr.put(mb, g_tube([(s + sx * (w / 2 + 0.01), d + 0.11, zb + h * 0.1 + 0.05 * math.sin(a)) for a in
                           [math.pi * i / 6 for i in range(7)]], 0.015, seg=6), 'zinc_dark', True)


def terrace(mb, z_deck):
    """Dachterrasse: Deckplatte, zweilagige Brüstung mit Abdeckung (Sweep auf dem Dachrand-Ring)."""
    dtop = roof_profile()[-1][0]
    rg = ring(dtop - 0.02)
    mb.prism(rg, z_deck - 0.06, z_deck, 'deck')
    p = [(dtop + 0.02, z_deck - 0.08), (dtop + 0.05, z_deck - 0.06), (dtop + 0.05, z_deck + 0.06),
         (dtop + 0.07, z_deck + 0.07), (dtop + 0.07, z_deck + 0.14), (dtop + 0.04, z_deck + 0.15),
         (dtop + 0.04, z_deck + 0.24), (dtop + 0.065, z_deck + 0.25), (dtop + 0.065, z_deck + 0.29),
         (dtop - 0.1, z_deck + 0.29), (dtop - 0.1, z_deck)]
    sweep(mb, p, 'trim')
    return dtop


def kiosk(mb, cx, cy, z):
    """Dachpavillon: profilierte Rundtrommel, Stützen, gewölbtes Lamellendach in Kupfergrün."""
    prof = [(0.0, z), (0.5, z), (0.5, z + 0.06), (0.45, z + 0.09), (0.43, z + 0.34), (0.47, z + 0.36),
            (0.47, z + 0.4), (0.38, z + 0.42), (0.0, z + 0.42)]
    v, f = g_revolve(prof, seg=32)
    mb.add([(x + cx, y + cy, zz) for x, y, zz in v], f, 'stone', True)
    for k in range(12):  # Fensterchen in der Trommel
        a = 2 * math.pi * k / 12
        mb.box((cx + 0.435 * math.cos(a), cy + 0.435 * math.sin(a), z + 0.21), (0.03, 0.1, 0.16), 'glass', rot=a)
    zt = z + 0.42
    for sx in (-1, 1):  # vier Stützen
        for sy in (-1, 1):
            mb.cylinder((cx + sx * 0.3, cy + sy * 0.25, zt), 0.025, 0.22, 'iron', seg=8)
    # gewölbte Lamellenhaube 1.25 x 1.05
    W, D, zc = 0.78, 0.64, zt + 0.24
    nx, ny = 16, 14
    v = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, w = -1 + 2 * i / nx, -1 + 2 * j / ny
            zz = zc + 0.1 * (1 - u * u) * (1 - 0.6 * w * w) - 0.03 * abs(u) ** 3
            v.append((cx + W * u * (1 - 0.06 * w * w), cy + D * w * (1 - 0.06 * u * u), zz))
    f = [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i)
         for j in range(ny) for i in range(nx)]
    vb = [(x, y, zz - 0.03) for x, y, zz in v]
    mb.add(v + vb, f + [tuple(reversed([c + len(v) for c in q])) for q in f], 'copper', True)
    mb.loft([([(cx - W, cy - D), (cx + W, cy - D), (cx + W, cy + D), (cx - W, cy + D)], zc - 0.04),
             ([(cx - W, cy - D), (cx + W, cy - D), (cx + W, cy + D), (cx - W, cy + D)], zc)], 'copper', cap=False)
    # Lamellen
    for j in range(1, 2 * ny):
        w = -1 + j / ny
        y = cy + D * w
        pts = []
        for i in range(nx + 1):
            u = -1 + 2 * i / nx
            pts.append((cx + W * u * 0.98, y, zc + 0.1 * (1 - u * u) * (1 - 0.6 * w * w) - 0.03 * abs(u) ** 3 + 0.008))
        v, f = g_tube(pts, 0.007, seg=4)
        mb.add(v, f, 'copper_light', False)


def chimney_pot(mb, x, y, z, h=0.42, r=0.04, mat='stone'):
    v, f = g_revolve([(0.0, z), (r * 1.4, z), (r * 1.4, z + 0.04), (r, z + 0.06), (r, z + h - 0.05),
                      (r * 1.3, z + h - 0.03), (r * 1.3, z + h), (r * 0.7, z + h), (r * 0.7, z + h - 0.01),
                      (0.0, z + h - 0.01)], seg=12)
    mb.add([(px + x, py + y, pz) for px, py, pz in v], f, mat, True)


def statue(mb, x, y, z, s=1.0):
    """Kleine Figur/Vase auf Sockel (Ecken der Terrasse, vgl. weiße Figur links in der Vorlage)."""
    v, f = g_revolve([(0.0, z), (0.07 * s, z), (0.07 * s, z + 0.08 * s), (0.05 * s, z + 0.1 * s),
                      (0.045 * s, z + 0.2 * s), (0.06 * s, z + 0.24 * s), (0.04 * s, z + 0.3 * s),
                      (0.05 * s, z + 0.36 * s), (0.03 * s, z + 0.42 * s), (0.04 * s, z + 0.46 * s),
                      (0.0, z + 0.5 * s)], seg=16)
    mb.add([(px + x, py + y, pz) for px, py, pz in v], f, 'stone_light', True)


# ----------------------------------------------------------------------------- Materialien
def _hex(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)


def _stone(name, c1, c2, grime='#7A6248', ao_dist=0.25, streak=0.35, bump=0.25, rough=0.78):
    """Kalkstein: Farbrauschen, Verschmutzung in Kanten (AO), senkrechte Regenspuren, feine Körnung."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    b = N['Principled BSDF']
    b.inputs['Roughness'].default_value = rough
    tc = N.new('ShaderNodeTexCoord')
    n1 = N.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 6; n1.inputs['Detail'].default_value = 8
    L.new(tc.outputs['Object'], n1.inputs['Vector'])
    r1 = N.new('ShaderNodeValToRGB')
    r1.color_ramp.elements[0].color = _hex(c2); r1.color_ramp.elements[0].position = 0.35
    r1.color_ramp.elements[1].color = _hex(c1); r1.color_ramp.elements[1].position = 0.65
    L.new(n1.outputs['Fac'], r1.inputs['Fac'])
    # Regenspuren: in z gestrecktes Rauschen
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (30, 30, 2.5)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    n2 = N.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 3; n2.inputs['Detail'].default_value = 4
    L.new(mp.outputs['Vector'], n2.inputs['Vector'])
    r2 = N.new('ShaderNodeMapRange'); r2.inputs['From Min'].default_value = 0.45; r2.inputs['From Max'].default_value = 0.75
    L.new(n2.outputs['Fac'], r2.inputs['Value'])
    ao = N.new('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = ao_dist; ao.samples = 8
    inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(ao.outputs['AO'], inv.inputs[1])
    mx = N.new('ShaderNodeMath'); mx.operation = 'MULTIPLY_ADD'
    L.new(r2.outputs['Result'], mx.inputs[0]); mx.inputs[1].default_value = streak
    L.new(inv.outputs[0], mx.inputs[2])
    cl = N.new('ShaderNodeMath'); cl.operation = 'MINIMUM'; cl.inputs[1].default_value = 0.85
    L.new(mx.outputs[0], cl.inputs[0])
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    sock = {s.identifier: s for s in mix.inputs}
    L.new(cl.outputs[0], sock['Factor_Float'])
    L.new(r1.outputs['Color'], sock['A_Color'])
    sock['B_Color'].default_value = _hex(grime)
    L.new([s for s in mix.outputs if s.identifier == 'Result_Color'][0], b.inputs['Base Color'])
    # Körnung
    n3 = N.new('ShaderNodeTexNoise'); n3.inputs['Scale'].default_value = 140; n3.inputs['Detail'].default_value = 3
    L.new(tc.outputs['Object'], n3.inputs['Vector'])
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump; bp.inputs['Distance'].default_value = 0.004
    L.new(n3.outputs['Fac'], bp.inputs['Height'])
    L.new(bp.outputs['Normal'], b.inputs['Normal'])
    m.diffuse_color = _hex(c1)
    return m


def _plain(name, col, rough=0.5, metal=0.0, coat=0.0, var=0.0, scale=20.0, emission=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if coat:
        b.inputs['Coat Weight'].default_value = coat
    if emission:
        b.inputs['Emission Color'].default_value = _hex(emission[0])
        b.inputs['Emission Strength'].default_value = emission[1]
    if var:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = 6
        nt.links.new(tc.outputs['Object'], n.inputs['Vector'])
        r = nt.nodes.new('ShaderNodeValToRGB')
        base = _hex(col)
        r.color_ramp.elements[0].color = tuple(c * (1 - var) for c in base[:3]) + (1,)
        r.color_ramp.elements[1].color = tuple(min(1, c * (1 + var * 0.6)) for c in base[:3]) + (1,)
        nt.links.new(n.outputs['Fac'], r.inputs['Fac'])
        nt.links.new(r.outputs['Color'], b.inputs['Base Color'])
        rr = nt.nodes.new('ShaderNodeMapRange')
        rr.inputs['To Min'].default_value = rough * 0.75
        rr.inputs['To Max'].default_value = min(1, rough * 1.3)
        nt.links.new(n.outputs['Fac'], rr.inputs['Value'])
        nt.links.new(rr.outputs['Result'], b.inputs['Roughness'])
    else:
        b.inputs['Base Color'].default_value = _hex(col)
    m.diffuse_color = _hex(col)
    return m


def make_materials():
    return {
        'stone': _stone('LM_stone', '#C9B193', '#AC957A', grime='#6B5B4B', streak=0.22),
        'trim': _stone('LM_trim', '#D5C3A8', '#BDA88C', grime='#776654', ao_dist=0.15, streak=0.3, bump=0.15),
        'stone_light': _stone('LM_stone_light', '#EFE6D6', '#DCD0BC', streak=0.15),
        'interior': _plain('LM_interior', '#3A2E26', 0.9),
        'curtain': _plain('LM_curtain', '#CFC3AE', 0.9),
        'frame': _plain('LM_frame', '#BFB4A2', 0.5, var=0.08),
        'glass': _plain('LM_glass', '#161B21', 0.05, coat=0.5),
        'iron': _plain('LM_iron', '#24262A', 0.45, metal=0.7),
        'zinc': _plain('LM_zinc', '#7B8DA3', 0.3, metal=0.55, var=0.1, scale=4),
        'zinc_dark': _plain('LM_zinc_dark', '#55606C', 0.45, metal=0.5, var=0.1),
        'zinc_seam': _plain('LM_zinc_seam', '#8696AA', 0.38, metal=0.55),
        'deck': _plain('LM_deck', '#BDB4A7', 0.85, var=0.12, scale=12),
        'copper': _plain('LM_copper', '#A9C59A', 0.55, metal=0.15, var=0.12, scale=15),
        'copper_light': _plain('LM_copper_light', '#C9DDB9', 0.5, metal=0.1),
        'pot': _plain('LM_pot', '#B26A4A', 0.8, var=0.1),
        'ground': _plain('LM_ground', '#B9B2A6', 0.85, var=0.08, scale=40),
    }


# ----------------------------------------------------------------------------- Zusammenbau
class Cutters:
    def __init__(self):
        self.mb = MeshBuilder()

    def append(self, fr, geo):
        fr.put(self.mb, geo, 'cut')


def _finish(mb, name, M, coll, parent, smooth_angle=None):
    ob = mb.build(name, M, coll)
    _recalc(ob)
    ob.parent = parent
    return ob


def _recalc(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()


def _boolean(target, cutter_mb, M, coll):
    cut = cutter_mb.build(target.name + '_cutter', {'cut': M['interior']}, coll)
    _recalc(cut)
    _recalc(target)
    mod = target.modifiers.new('Openings', 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cut
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(target.evaluated_get(dg))
    target.modifiers.clear()
    old = target.data
    target.data = me
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(cut)


def build_landmark(coll, location=(0, 0, 0), name='Landmark_F'):
    M = make_materials()
    root = bpy.data.objects.new(name, None)
    root.empty_display_type = 'CUBE'
    root.empty_display_size = 0.5
    coll.objects.link(root)
    F = edge_frames()
    cut = Cutters()

    # ---------------- Wandkörper (geschlossen, mit Rustika-Fugen im EG) ----------------
    wall = MeshBuilder()
    prof = [(0.0, 0.0)]
    for zz in [0.18 + 0.22 * k for k in range(6)]:
        prof += [(0.0, zz - 0.016), (-0.014, zz - 0.009), (-0.014, zz + 0.009), (0.0, zz + 0.016)]
    prof += [(0.0, Z_CORN + 0.05), (-T_WALL, Z_CORN + 0.05), (-T_WALL, 0.0)]
    mats = ['stone'] * (len(prof) - 2) + ['interior', 'interior']   # Außen | Innenwand, Unterseite
    sweep(wall, prof, 'stone', closed_profile=True, mats=mats)
    walls_ob = wall.build('LM_Walls', M, coll)

    # ---------------- Fassaden: Öffnungen + Fenster ----------------
    win = MeshBuilder()
    orn = MeshBuilder()
    oriels_cut = Cutters()
    oriel_parts = []

    # linke Fassade (zum Eiffelturm hin): 5 Achsen
    fr, L = F['left'], F['left_len']
    bays = [(k + 0.5) * L / 5 for k in range(5)]
    for s in bays:
        window(fr, win, cut, s, 0.2, 1.22, 0.42, kind='arch', sill=False)
        window(fr, win, cut, s, Z_F1[0] + 0.14, Z_F1[1] - 0.2, 0.34, cap='segment', rail=True)
        window(fr, win, cut, s, Z_F2[0] + 0.08, Z_BAND[0] - 0.12, 0.34, keystone=False, sill=False)
        window(fr, win, cut, s, Z_F3[0] + 0.5, Z_F3[1] - 0.1, 0.28, keystone=False, ear=True)
        lambrequin(fr, orn, s - 0.24, s + 0.24, Z_F3[0] + 0.42, h=0.3)      # Steindraperie unter dem Attikafenster
        festoon(fr, orn, s - 0.26, s + 0.26, Z_BAND[0] - 0.08, sag=0.16)    # Draperie über dem hohen Fenster
    for s in [0.0] + [(a + b) / 2 for a, b in zip(bays, bays[1:])] + [L]:  # Lisenen
        fr.put(orn, g_box(s - 0.05, s + 0.05, 0, 0.025, Z_B1, Z_BAND[0]), 'trim')

    # rechte Fassade (zur Kamera rechts): Eckpfeiler mit ionischem Kapitell, großer Erker, Balkon, kleiner Erker
    fr, L = F['right'], F['right_len']
    fr.put(orn, g_box(0.02, 0.5, 0, 0.08, Z_B1, Z_BAND[1] + 0.2), 'stone')        # Pilaster
    for k in range(5):  # Kanneluren
        s = 0.08 + k * 0.09
        fr.put(orn, g_box(s - 0.014, s + 0.014, 0.08, 0.094, Z_B1 + 0.15, Z_BAND[0] - 0.1), 'trim')
    fr.put(orn, g_extrude_dz([(0, Z_B1), (0.12, Z_B1), (0.12, Z_B1 + 0.06), (0.09, Z_B1 + 0.1),
                              (0, Z_B1 + 0.1)], -0.01, 0.53), 'trim')               # Basis
    ionic_capital(fr, orn, -0.16, 0.74, Z_BAND[1] + 0.1, d=0.08)   # Voluten wie in der Vorlage: groß, direkt unter dem Gesims
    oriel_parts += oriel(fr, orn, oriels_cut, 1.13, 0.5, Z_F1[0] + 0.3, Z_F3[1] - 0.3, 3, cap_h=0.42)
    balcony(fr, orn, 1.72, 2.7, Z_F1[0] + 0.02, depth=0.4)
    window(fr, win, cut, 1.95, Z_F1[0] + 0.05, Z_F1[1] - 0.12, 0.3, cap='cornice', sill=False)
    window(fr, win, cut, 2.42, Z_F1[0] + 0.05, Z_F1[1] - 0.12, 0.3, cap='cornice', sill=False)
    oriel_parts += oriel(fr, orn, oriels_cut, 2.2, 0.3, Z_F2[0] + 0.05, Z_F3[1] - 0.36, 2, cap_h=0.3)
    window(fr, win, cut, 2.55, Z_F2[0] + 0.12, Z_F2[1] - 0.2, 0.22, keystone=False)
    window(fr, win, cut, 2.55, Z_F3[0] + 0.35, Z_F3[1] - 0.18, 0.2, keystone=False)
    window(fr, win, cut, 1.8, Z_F3[0] + 0.45, Z_F3[1] - 0.12, 0.2, keystone=False)
    for s in (0.75, 1.55, 2.3):
        window(fr, win, cut, s, 0.2, 1.22, 0.4, kind='arch', sill=False)

    # Rückseiten (für andere Blickwinkel): ruhigeres Raster
    for key in ('east', 'north'):
        fr, L = F[key], F[key + '_len']
        nb = int(L / 0.78)
        for k in range(nb):
            s = (k + 0.5) * L / nb
            window(fr, win, cut, s, 0.2, 1.22, 0.4, kind='arch', sill=False)
            window(fr, win, cut, s, Z_F1[0] + 0.14, Z_F1[1] - 0.2, 0.34, cap='segment', rail=True)
            window(fr, win, cut, s, Z_F2[0] + 0.12, Z_F2[1] - 0.2, 0.32, cap='cornice')
            window(fr, win, cut, s, Z_F3[0] + 0.3, Z_F3[1] - 0.2, 0.3, keystone=False)

    # gerundete Ecke: Lisenen mit Spiegeln, Rundfenster im Fries
    R = RAD['SW']
    for ang in (196, 225, 254):
        a = math.radians(ang)
        o = (R + R * math.cos(a), R + R * math.sin(a))
        fr = Frame(o, (-math.sin(a), math.cos(a)), (math.cos(a), math.sin(a)))
        fr.put(orn, g_box(-0.06, 0.06, -0.01, 0.03, Z_B1, Z_BAND[0]), 'trim')
        path = [(-0.035, Z_B1 + 0.2), (-0.035, Z_BAND[0] - 0.2), (0.035, Z_BAND[0] - 0.2), (0.035, Z_B1 + 0.2),
                (-0.035, Z_B1 + 0.2)]
        fr.put(orn, g_molding(path, None, [(0.0, 0.03), (0.0, 0.042), (0.008, 0.042), (0.012, 0.03)]), 'trim')

    _boolean(walls_ob, cut.mb, M, coll)
    walls_ob.parent = root

    # Erkerkörper (eigenes Objekt, mit Fensteröffnungen)
    ob_mb = MeshBuilder()
    fr = F['right']
    for geo in oriel_parts:
        fr.put(ob_mb, geo, 'stone', True)
    oriel_ob = ob_mb.build('LM_Oriels', M, coll)
    _boolean(oriel_ob, oriels_cut.mb, M, coll)
    oriel_ob.parent = root

    # Innenraum: Geschossdecken (verhindern Durchblick, fangen Licht)
    inner = MeshBuilder()
    for z in (0.0, Z_G, Z_F1[1], Z_F2[1], Z_F3[0], Z_CORN):
        inner.prism(ring(-T_WALL - 0.005), z - 0.04, z, 'interior', cap_bottom=True)
    _finish(inner, 'LM_Interior', M, coll, root)

    # ---------------- Gesimse (Sweeps) ----------------
    cor = MeshBuilder()
    sweep(cor, [(-0.02, -0.02), (0.05, -0.02), (0.05, 0.1), (0.035, 0.12), (0.035, 0.14), (-0.02, 0.14)], 'trim')  # Sockel
    sweep(cor, [(-0.01, Z_G - 0.02), (0.04, Z_G - 0.02), (0.07, Z_G + 0.02), (0.07, Z_G + 0.07), (0.09, Z_G + 0.09),
                (0.09, Z_B1), (-0.01, Z_B1)], 'trim')                                  # Gurtgesims EG
    sweep(cor, [(-0.01, Z_BAND[0] - 0.04), (0.03, Z_BAND[0] - 0.04), (0.05, Z_BAND[0] - 0.01), (0.09, Z_BAND[0] + 0.03),
                (0.1, Z_BAND[0] + 0.07), (0.1, Z_BAND[1] - 0.04), (0.13, Z_BAND[1] - 0.01), (0.14, Z_BAND[1] + 0.03),
                (0.12, Z_BAND[1] + 0.05), (-0.01, Z_BAND[1] + 0.05)], 'trim', smooth=True)                                                                            # Fries-/Kapitellband
    sweep(cor, [(-0.01, Z_F2[0] - 0.02), (0.025, Z_F2[0] - 0.02), (0.03, Z_F2[0]), (0.025, Z_F2[0] + 0.02),
                (-0.01, Z_F2[0] + 0.02)], 'trim')                                            # Stockwerksband
    z = Z_CORN
    sweep(cor, [(-0.01, z - 0.02), (0.03, z - 0.02), (0.03, z + 0.03), (0.05, z + 0.04), (0.05, z + 0.07),
                (0.09, z + 0.09), (0.12, z + 0.12), (0.12, z + 0.15), (0.2, z + 0.18), (0.27, z + 0.2),
                (0.29, z + 0.22), (0.29, z + 0.26), (0.27, z + 0.27), (0.27, Z_EAVE + 0.0), (0.06, Z_EAVE + 0.0)],
          'trim', smooth=True)                                                               # Hauptgesims
    _finish(cor, 'LM_Cornices', M, coll, root)
    # Konsolen unter dem Hauptgesims (rund um, in gleichen Abständen entlang des Rings)
    rg0 = ring(0.0)
    cons = MeshBuilder()
    acc, nxt = 0.0, 0.1
    for i in range(len(rg0)):
        p, q = Vector(rg0[i]), Vector(rg0[(i + 1) % len(rg0)])
        L = (q - p).length
        while nxt <= acc + L:
            t = (nxt - acc) / L
            o = p + (q - p) * t
            tg = (q - p).normalized()
            nrm = (tg.y, -tg.x)
            fr = Frame((o.x, o.y), (tg.x, tg.y), nrm)
            fr.put(cons, g_extrude_dz([(0, z + 0.0), (0.05, z + 0.0), (0.09, z + 0.06), (0.17, z + 0.12),
                                       (0.17, z + 0.17), (0, z + 0.17)], -0.025, 0.025), 'trim')
            nxt += 0.26
        acc += L
    _finish(cons, 'LM_Modillions', M, coll, root)

    _finish(win, 'LM_Windows', M, coll, root)
    _finish(orn, 'LM_Ornament', M, coll, root)

    # ---------------- Dach ----------------
    roof = MeshBuilder()
    rp = roof_profile()
    sweep(roof, rp, 'zinc', smooth=True)
    for t in (0.22, 0.45, 0.66, 0.85):   # waagerechte Falze (in der Vorlage als feine Linien sichtbar)
        d, zz, _ = roof_point(t)
        sweep(roof, [(d - 0.01, zz - 0.008), (d + 0.005, zz - 0.004), (d + 0.005, zz + 0.004), (d - 0.01, zz + 0.008)],
              'zinc_seam', smooth=True)
    sweep(roof, [(0.04, Z_EAVE + 0.0), (0.085, Z_EAVE + 0.02), (0.085, Z_EAVE + 0.07), (0.05, Z_EAVE + 0.09)],
          'zinc_dark', smooth=True)        # Traufblech
    _finish(roof, 'LM_Roof', M, coll, root)

    dm = MeshBuilder()
    fr, L = F['right'], F['right_len']
    for s in (0.75, 1.55, 2.35):          # Vorlage: drei Gauben rechts, drei links, eine auf der Ecke
        dormer(fr, dm, s, t=0.3)
    fr, L = F['left'], F['left_len']
    for s in (0.7, 1.75, 2.8):
        dormer(fr, dm, s, t=0.3)
    for key in ('east', 'north'):
        fr, L = F[key], F[key + '_len']
        n = int(L / 1.2)
        for k in range(n):
            dormer(fr, dm, (k + 0.5) * L / n, t=0.3)
    a = math.radians(225)  # große Gaube auf der gerundeten Ecke
    rr = RAD['SW']
    o = (rr + rr * math.cos(a), rr + rr * math.sin(a))
    dormer(Frame(o, (-math.sin(a), math.cos(a)), (math.cos(a), math.sin(a))), dm, 0.0, t=0.22, big=True)
    _finish(dm, 'LM_Dormers', M, coll, root)

    # ---------------- Dachterrasse & Aufbauten ----------------
    z_deck = rp[-1][1] + 0.02
    top = MeshBuilder()
    dtop = terrace(top, z_deck)
    _finish(top, 'LM_Terrace', M, coll, root)
    kb = MeshBuilder()
    kiosk(kb, LX / 2 + 0.1, LY / 2 + 0.15, z_deck)
    _finish(kb, 'LM_Kiosk', M, coll, root)
    ch = MeshBuilder()
    i0 = -dtop + 0.25
    chimney_pot(ch, i0 + 0.05, LY - i0 - 0.1, z_deck, h=0.5, r=0.05)            # NW: zwei Steinköpfe
    chimney_pot(ch, i0 + 0.22, LY - i0 - 0.1, z_deck, h=0.42, r=0.05)
    chimney_pot(ch, LX - i0 - 0.1, LY - i0 - 0.05, z_deck, h=0.55, r=0.028, mat='iron')  # NE: zwei Rohre
    chimney_pot(ch, LX - i0 - 0.22, LY - i0 - 0.05, z_deck, h=0.5, r=0.028, mat='iron')
    chimney_pot(ch, LX - i0 - 0.05, i0 + 0.3, z_deck, h=0.4, r=0.03, mat='iron')        # SE
    chimney_pot(ch, i0 + 0.05, i0 + 0.75, z_deck, h=0.3, r=0.035)                       # vorne links
    chimney_pot(ch, i0 + 0.2, i0 + 0.75, z_deck, h=0.34, r=0.035)
    statue(ch, i0 + 0.15, LY / 2 + 0.7, z_deck, s=1.1)
    ch.box((i0 + 0.3, LY / 2 + 0.2, z_deck + 0.05), (0.12, 0.6, 0.1), 'stone')       # Bank/Lüfter links
    ch.box((LX - i0 - 0.35, LY / 2 - 0.2, z_deck + 0.04), (0.3, 0.2, 0.08), 'zinc_dark')
    for k in range(4):
        ch.cylinder((LX / 2 - 0.5 + k * 0.3, i0 + 0.3, z_deck), 0.02, 0.12, 'iron', seg=6)
    _finish(ch, 'LM_RoofProps', M, coll, root)

    root.location = location
    return root, M
