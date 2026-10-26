"""Parametrischer Generator für Pariser (Haussmann-)Wohnhäuser.

Ein Gebäude = ein Blender-Objekt mit echter 3D-Geometrie:
  * Kern (dunkles Glas) + Fassadenraster aus Pfeilern/Brüstungen -> echte Fensterlaibungen
  * Fensterrahmen, Sprossen, Gesimse, Fensterverdachungen, Fensterbänke
  * französische Gitter vor den Fenstern, durchgehende Balkone (2. und 5. OG) mit Konsolen
  * Erdgeschoss mit Bossenbändern, Ladenfronten, Türen
  * Mansarddach (gerade oder geschwungen), Gauben (Giebel/Rundbogen), Kamine mit Tonaufsätzen
  * Varianten: Flachdach mit Attikageschoss, Erker (Oriel)
"""
import math
import random
from dataclasses import dataclass, field
from mathutils import Vector

from .meshkit import MeshBuilder, offset_convex


@dataclass
class Building:
    name: str
    footprint: list                      # Welt-Koordinaten, konvex, CCW
    floors: int = 5                      # Obergeschosse ohne EG
    ground_h: float = 1.5
    floor_h: float = 1.25
    facade: str = 'stone_cream'
    trim: str = 'trim_white'
    roof: str = 'mansard'                # mansard | mansard_curved | flat | attic
    roof_mat: str = 'zinc_blue'
    roof_top_mat: str = 'roof_flat'
    roof_h: float = 1.8
    roof_inset: float = 0.9
    bay: float = 1.0
    balcony_floors: tuple = (2, 5)
    railings: bool = True
    dormers: bool = True
    dormer_style: str = 'gable'          # gable | arch | flat
    dormer_every: int = 1
    chimneys: list = None                # [(x, y, w, d, h, pots)] lokal, oder None = automatisch
    chimney_mat: str = 'terracotta'
    n_auto_chimneys: int = 3
    skip_edges: tuple = ()               # Brandwände ohne Fenster
    doors: dict = field(default_factory=dict)  # {edge: [bay, ...]}
    door_mat: str = 'wood_dark'
    oriels: list = field(default_factory=list)  # [(edge, s_frac, width, floor_from, floor_to)]
    rooftop: list = field(default_factory=list)  # zusätzliche Dachaufbauten (siehe extras)
    seed: int = 1
    window_ratio: float = 0.5
    shutters: str = ''                   # Material der Fensterläden ('' = keine)


class EdgeFrame:
    """Lokales Fassadensystem: s entlang der Kante, d nach außen, z nach oben."""

    def __init__(self, p0, p1):
        self.p0 = Vector((p0[0], p0[1], 0))
        p1 = Vector((p1[0], p1[1], 0))
        d = p1 - self.p0
        self.L = d.length
        self.t = d.normalized()
        self.n = Vector((self.t.y, -self.t.x, 0))  # Außennormale bei CCW

    def P(self, s, d, z):
        return self.p0 + self.t * s + self.n * d + Vector((0, 0, z))

    def box(self, mb, s0, s1, z0, z1, d0, d1, mat):
        if s1 - s0 <= 1e-5 or z1 - z0 <= 1e-5 or abs(d1 - d0) <= 1e-5:
            return
        mb.oriented_box(self.P(s0, d0, z0), self.t * (s1 - s0), self.n * (d1 - d0),
                        Vector((0, 0, z1 - z0)), mat)

    def beam(self, mb, a, b, w, mat):
        mb.beam(self.P(*a), self.P(*b), w, mat)

    def profile(self, mb, prof, d0, d1, mat):
        """Konvexes Profil [(s, z), ...] (CCW in s-z) entlang d extrudieren."""
        n = len(prof)
        pts = [self.P(s, d1, z) for s, z in prof] + [self.P(s, d0, z) for s, z in prof]
        faces = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
        for i in range(n):
            j = (i + 1) % n
            faces.append((j, i, n + i, n + j))
        mb.add(pts, faces, mat)


R_WALL = 0.12  # Tiefe der Fensterlaibung


def _railing(ef, mb, s0, s1, z, d, h, spacing=0.07, mat='iron_black'):
    ef.box(mb, s0, s1, z + h - 0.025, z + h, d - 0.012, d + 0.012, mat)
    ef.box(mb, s0, s1, z + 0.03, z + 0.05, d - 0.008, d + 0.008, mat)
    n = max(2, int((s1 - s0) / spacing))
    for i in range(n + 1):
        s = s0 + (s1 - s0) * i / n
        ef.box(mb, s - 0.006, s + 0.006, z, z + h, d - 0.006, d + 0.006, mat)
    # Zierband (Volute angedeutet) im mittleren Bereich
    ef.box(mb, s0, s1, z + h * 0.55, z + h * 0.58, d - 0.006, d + 0.006, mat)


def _window(ef, mb, b, c, ww, wb, wt, upper=True, cap=False, railing=False, fh=1.0):
    tr, fr = b.trim, 'frame_white'
    dc = -R_WALL  # Glas-/Kernebene
    f = 0.028
    # Rahmen
    ef.box(mb, c - ww / 2, c - ww / 2 + f, wb, wt, dc, dc + 0.03, fr)
    ef.box(mb, c + ww / 2 - f, c + ww / 2, wb, wt, dc, dc + 0.03, fr)
    ef.box(mb, c - ww / 2, c + ww / 2, wt - f, wt, dc, dc + 0.03, fr)
    ef.box(mb, c - ww / 2, c + ww / 2, wb, wb + f, dc, dc + 0.03, fr)
    # Flügel: Mittelpfosten + Kämpfer + Sprossen
    ef.box(mb, c - 0.012, c + 0.012, wb, wt, dc, dc + 0.025, fr)
    zt = wb + (wt - wb) * 0.74
    ef.box(mb, c - ww / 2, c + ww / 2, zt - 0.012, zt + 0.012, dc, dc + 0.025, fr)
    for k in (1, 2):
        zz = wb + (zt - wb) * k / 3
        ef.box(mb, c - ww / 2, c + ww / 2, zz - 0.006, zz + 0.006, dc, dc + 0.018, fr)
    # Fensterumrahmung (Faschen) + Fensterbank
    ef.box(mb, c - ww / 2 - 0.06, c - ww / 2, wb, wt + 0.06, 0, 0.018, tr)
    ef.box(mb, c + ww / 2, c + ww / 2 + 0.06, wb, wt + 0.06, 0, 0.018, tr)
    ef.box(mb, c - ww / 2 - 0.06, c + ww / 2 + 0.06, wt, wt + 0.06, 0, 0.018, tr)
    ef.box(mb, c - ww / 2 - 0.08, c + ww / 2 + 0.08, wb - 0.045, wb, -R_WALL, 0.05, tr)
    if cap:  # Verdachung
        ef.box(mb, c - ww / 2 - 0.1, c + ww / 2 + 0.1, wt + 0.08, wt + 0.13, 0, 0.07, tr)
        ef.box(mb, c - ww / 2 - 0.07, c + ww / 2 + 0.07, wt + 0.06, wt + 0.08, 0, 0.045, tr)
        for sx in (-1, 1):  # Konsölchen
            ef.box(mb, c + sx * (ww / 2 + 0.05) - 0.025, c + sx * (ww / 2 + 0.05) + 0.025,
                   wt - 0.1, wt + 0.08, 0, 0.05, tr)
    if railing:
        _railing(ef, mb, c - ww / 2 - 0.02, c + ww / 2 + 0.02, wb, 0.04, fh * 0.3)
    if b.shutters:  # geöffnete Holzläden mit Lamellen
        for sx in (-1, 1):
            s0 = c + sx * (ww / 2 + 0.07)
            s1 = s0 + sx * ww * 0.48
            ef.box(mb, min(s0, s1), max(s0, s1), wb, wt, 0.0, 0.03, b.shutters)
            for k in range(1, 6):
                zz = wb + (wt - wb) * k / 6
                ef.box(mb, min(s0, s1) + 0.01, max(s0, s1) - 0.01, zz - 0.008, zz + 0.008, 0.03, 0.04, b.shutters)


def _shopfront(ef, mb, b, c, ow, z0, z1, door=False):
    dc = -R_WALL
    wood = b.door_mat if door else 'wood_dark'
    ef.box(mb, c - ow / 2, c + ow / 2, z0, z1, dc, dc + 0.025, wood)
    if door:
        ef.box(mb, c - ow / 2 + 0.06, c + ow / 2 - 0.06, z0 + 0.05, z1 - 0.12, dc + 0.025, dc + 0.035,
               'glass' if wood != 'door_green' else 'door_green')
        ef.box(mb, c - 0.01, c + 0.01, z0 + 0.05, z1 - 0.12, dc + 0.03, dc + 0.045, 'wood_dark')
        ef.box(mb, c - ow / 2 + 0.06, c + ow / 2 - 0.06, z1 - 0.1, z1 - 0.04, dc + 0.025, dc + 0.04, 'glass')
    else:
        ef.box(mb, c - ow / 2 + 0.05, c + ow / 2 - 0.05, z0 + 0.25, z1 - 0.08, dc + 0.025, dc + 0.03, 'glass_warm')
        ef.box(mb, c - 0.012, c + 0.012, z0 + 0.25, z1 - 0.08, dc + 0.025, dc + 0.045, wood)
        ef.box(mb, c - ow / 2 + 0.05, c + ow / 2 - 0.05, z1 - 0.32, z1 - 0.29, dc + 0.025, dc + 0.045, wood)


def _facade_edge(b, mb, ef, i, rng):
    L = ef.L
    gh, fh, F = b.ground_h, b.floor_h, b.floors
    zt = gh + F * fh
    fac = b.facade
    if i in b.skip_edges or L < 0.45:
        ef.box(mb, 0, L, 0, zt, -R_WALL - 0.02, 0, fac)
        if L >= 0.45:  # Gesimse laufen auch über Brandwände weiter
            ef.box(mb, 0, L, gh - 0.1, gh, 0, 0.05, b.trim)
        return
    nb = max(1, int(round(L / b.bay)))
    bw = L / nb
    ww = min(bw * b.window_ratio, 0.7)
    centers = [(k + 0.5) * bw for k in range(nb)]

    def openings_row(z0, z1, wb, wt, ow):
        ef.box(mb, 0, L, z0, wb, -R_WALL, 0, fac)
        ef.box(mb, 0, L, wt, z1, -R_WALL, 0, fac)
        edges = [0.0] + [x for c in centers for x in (c - ow / 2, c + ow / 2)] + [L]
        for k in range(0, len(edges), 2):
            ef.box(mb, edges[k], edges[k + 1], wb, wt, -R_WALL, 0, fac)

    # ---- Erdgeschoss ----
    ow = min(bw * 0.68, 0.9)
    ob, ot = 0.06, gh * 0.82
    openings_row(0, gh, ob, ot, ow)
    doors = b.doors.get(i, [])
    for k, c in enumerate(centers):
        _shopfront(ef, mb, b, c, ow, ob, ot, door=k in doors)
        ef.box(mb, c - ow / 2 - 0.04, c + ow / 2 + 0.04, ot, ot + 0.07, 0, 0.03, b.trim)  # Sturz
    for zz in [gh * f for f in (0.2, 0.38, 0.56, 0.74)]:  # Bossenbänder
        ef.box(mb, 0, L, zz, zz + 0.025, 0, 0.012, b.trim)
    ef.box(mb, -0.02, L + 0.02, 0, 0.08, 0, 0.03, 'curb')  # Sockel
    ef.box(mb, -0.06, L + 0.06, gh - 0.12, gh, 0, 0.07, b.trim)  # EG-Gesims

    # ---- Obergeschosse ----
    for k in range(1, F + 1):
        z0 = gh + (k - 1) * fh
        z1 = z0 + fh
        balcony = k in b.balcony_floors
        top = k == F
        wb = z0 + (0.06 if balcony else 0.14) * fh
        wt = z0 + (0.72 if top else 0.8) * fh
        openings_row(z0, z1, wb, wt, ww)
        for c in centers:
            _window(ef, mb, b, c, ww, wb, wt, cap=(k <= 2), railing=(b.railings and not balcony), fh=fh)
        ef.box(mb, -0.03, L + 0.03, z1 - 0.035, z1, 0, 0.025, b.trim)  # Stockwerksband
        if balcony:
            dd = 0.3
            ef.box(mb, -dd, L + dd, z0 - 0.02, z0 + 0.06, 0, dd, b.trim)  # Balkonplatte
            for c in [0.05] + [cc + bw / 2 for cc in centers[:-1]] + [L - 0.05]:
                ef.box(mb, c - 0.04, c + 0.04, z0 - 0.2, z0 - 0.02, 0, dd * 0.8, b.trim)  # Konsolen
            _railing(ef, mb, -dd + 0.02, L + dd - 0.02, z0 + 0.06, dd - 0.02, fh * 0.32, 0.055)

    # ---- Hauptgesims ----
    for j, (h, dd) in enumerate(((0.07, 0.05), (0.06, 0.12), (0.07, 0.2))):
        z = zt - 0.07 + j * 0.065
        ef.box(mb, -dd, L + dd, z, z + h, 0, dd, b.trim)
    for c in [0.02] + [cc + bw / 2 for cc in centers[:-1]] + [L - 0.02]:  # Zahnschnitt/Konsolen
        ef.box(mb, c - 0.03, c + 0.03, zt - 0.2, zt - 0.06, 0, 0.09, b.trim)

    # ---- Erker ----
    for (e, sf, w, f0, f1) in b.oriels:
        if e != i:
            continue
        c = sf * L
        z0 = gh + (f0 - 1) * fh
        z1 = gh + f1 * fh
        dep = 0.38
        prof = [(c - w / 2, z0), (c + w / 2, z0), (c + w / 2, z1), (c - w / 2, z1)]
        ef.box(mb, c - w / 2, c + w / 2, z0, z1, 0, dep, b.facade)
        ef.box(mb, c - w / 2 - 0.06, c + w / 2 + 0.06, z0 - 0.25, z0, 0, dep * 0.7, b.trim)  # Konsole
        ef.box(mb, c - w / 2 - 0.06, c + w / 2 + 0.06, z1, z1 + 0.1, 0, dep + 0.06, b.trim)
        for fl in range(f0, f1 + 1):
            zb = gh + (fl - 1) * fh + 0.18 * fh
            zw = gh + (fl - 1) * fh + 0.78 * fh
            for sx in (-0.28, 0.28):
                cc = c + sx * w
                ef.box(mb, cc - w * 0.15, cc + w * 0.15, zb, zw, dep, dep + 0.012, 'glass')
                ef.box(mb, cc - 0.01, cc + 0.01, zb, zw, dep, dep + 0.02, 'frame_white')
            ef.box(mb, c - w / 2, c + w / 2, zw + 0.04, zw + 0.09, dep, dep + 0.03, b.trim)
        del prof


def _dormers(b, mb, fp, zA, zB, inset, rng):
    n = len(fp)
    for i in range(n):
        if i in b.skip_edges:
            continue
        ef = EdgeFrame(fp[i], fp[(i + 1) % n])
        L = ef.L
        if L < 1.0:
            # schmale Eck-Kante: eine runde Gaube, wenn Platz
            if L < 0.7:
                continue
        nb = max(1, int(round(L / b.bay)))
        bw = L / nb
        dw = min(bw * 0.5, 0.55)
        dh = min(0.8, (zB - zA) * 0.55)
        for k in range(nb):
            if k % b.dormer_every:
                continue
            c = (k + 0.5) * bw
            if c - dw / 2 < 0.25 or c + dw / 2 > L - 0.25:
                if nb > 1:
                    continue
            zb = zA + (zB - zA) * 0.18
            df = -0.05 - inset * 0.22  # Gaubenfront
            dback = -inset - 0.15
            ef.box(mb, c - dw / 2, c + dw / 2, zb, zb + dh, dback, df, b.roof_mat)
            # Front: Rahmen + Glas
            g = 0.05
            ef.box(mb, c - dw / 2 + g, c + dw / 2 - g, zb + g, zb + dh - g, df, df + 0.005, 'glass')
            for s0, s1, z0, z1 in ((c - dw / 2, c - dw / 2 + g, zb, zb + dh),
                                   (c + dw / 2 - g, c + dw / 2, zb, zb + dh),
                                   (c - dw / 2, c + dw / 2, zb, zb + g),
                                   (c - dw / 2, c + dw / 2, zb + dh - g, zb + dh),
                                   (c - 0.012, c + 0.012, zb, zb + dh)):
                ef.box(mb, s0, s1, z0, z1, df, df + 0.035, b.trim)
            top = zb + dh
            if b.dormer_style == 'arch':
                prof = [(c + (dw / 2 + 0.05) * math.cos(a), top + (dw / 2 + 0.05) * math.sin(a) * 0.9)
                        for a in [math.pi * j / 8 for j in range(9)]]
                ef.profile(mb, prof, dback, df + 0.04, b.roof_mat)
                inner = [(c + (dw / 2 - 0.02) * math.cos(a), top + (dw / 2 - 0.02) * math.sin(a) * 0.85)
                         for a in [math.pi * j / 8 for j in range(9)]]
                ef.profile(mb, inner, df + 0.04, df + 0.05, b.trim)
            elif b.dormer_style == 'gable':
                prof = [(c - dw / 2 - 0.06, top), (c + dw / 2 + 0.06, top), (c, top + dw * 0.45)]
                ef.profile(mb, prof, dback, df + 0.06, b.trim)
            else:
                ef.box(mb, c - dw / 2 - 0.04, c + dw / 2 + 0.04, top, top + 0.07, dback, df + 0.05, b.trim)


def _chimney(mb, x, y, z, w, d, h, pots, mat, rng):
    mb.box((x, y, z + h / 2), (w, d, h), mat)
    mb.box((x, y, z + h + 0.03), (w + 0.06, d + 0.06, 0.06), 'trim_white')
    for k in range(pots):
        px = x - w / 2 + w * (k + 0.5) / pots
        r = min(0.06, w / pots * 0.35)
        mb.cylinder((px, y, z + h + 0.06), r, 0.12 + rng.random() * 0.06, 'terracotta', seg=8, r_top=r * 0.8)


def build_building(b, materials, collection):
    rng = random.Random(b.seed)
    cx = sum(p[0] for p in b.footprint) / len(b.footprint)
    cy = sum(p[1] for p in b.footprint) / len(b.footprint)
    fp = [(x - cx, y - cy) for x, y in b.footprint]
    mb = MeshBuilder()
    gh, fh, F = b.ground_h, b.floor_h, b.floors
    zt = gh + F * fh

    # Kern (sichtbar nur durch die Fensteröffnungen)
    core = offset_convex(fp, R_WALL)
    mb.prism(core, 0, zt, 'glass')
    n = len(fp)
    for i in range(n):
        _facade_edge(b, mb, EdgeFrame(fp[i], fp[(i + 1) % n]), i, rng)

    # Dach
    z_roof_base = zt + 0.13
    deck = None
    if b.roof in ('mansard', 'mansard_curved'):
        rings = []
        steps = 7 if b.roof == 'mansard_curved' else 1
        for k in range(steps + 1):
            th = (math.pi / 2) * k / steps
            if b.roof == 'mansard_curved':
                off = 0.05 + b.roof_inset * (1 - math.cos(th))
                z = z_roof_base + b.roof_h * 0.85 * math.sin(th)
            else:
                off = 0.05 + b.roof_inset * (k / steps)
                z = z_roof_base + b.roof_h * 0.85 * (k / steps)
            rings.append((offset_convex(fp, off), z))
        top_in = b.roof_inset + 0.05 + 0.35
        rings.append((offset_convex(fp, top_in), z_roof_base + b.roof_h))
        mb.loft(rings, b.roof_mat, cap=False, smooth=b.roof == 'mansard_curved')
        deck = offset_convex(fp, top_in)
        mb.prism(deck, z_roof_base + b.roof_h - 0.02, z_roof_base + b.roof_h, b.roof_top_mat)
        # Zinkgrate / Brüstung an der Dachkante
        for i in range(n):
            ef = EdgeFrame(rings[-2][0][i], rings[-2][0][(i + 1) % n])
            ef.box(mb, -0.02, ef.L + 0.02, rings[-2][1] - 0.03, rings[-2][1] + 0.03, -0.04, 0.03, 'zinc_light')
        if b.dormers:
            _dormers(b, mb, fp, z_roof_base, z_roof_base + b.roof_h * 0.85, b.roof_inset, rng)
        top_z = z_roof_base + b.roof_h
    elif b.roof == 'attic':
        att = offset_convex(fp, 0.45)
        ah = fh * 0.85
        mb.prism(offset_convex(att, R_WALL), zt, zt + ah, 'glass')
        m = len(att)
        for i in range(m):
            ef = EdgeFrame(att[i], att[(i + 1) % m])
            if i in b.skip_edges:
                ef.box(mb, 0, ef.L, zt, zt + ah, -R_WALL, 0, b.facade)
                continue
            nb = max(1, int(round(ef.L / b.bay)))
            bw = ef.L / nb
            ww = min(bw * 0.5, 0.55)
            cs = [(k + 0.5) * bw for k in range(nb)]
            wb, wt = zt + 0.12, zt + ah - 0.12
            ef.box(mb, 0, ef.L, zt, wb, -R_WALL, 0, b.facade)
            ef.box(mb, 0, ef.L, wt, zt + ah, -R_WALL, 0, b.facade)
            edges = [0.0] + [x for c in cs for x in (c - ww / 2, c + ww / 2)] + [ef.L]
            for k in range(0, len(edges), 2):
                ef.box(mb, edges[k], edges[k + 1], wb, wt, -R_WALL, 0, b.facade)
            for c in cs:
                ef.box(mb, c - 0.012, c + 0.012, wb, wt, -R_WALL, -R_WALL + 0.025, 'frame_white')
        # Terrassengeländer + Dachplatte
        for i in range(n):
            ef = EdgeFrame(fp[i], fp[(i + 1) % n])
            _railing(ef, mb, 0.05, ef.L - 0.05, zt + 0.13, -0.1, 0.32, 0.06)
        mb.prism(offset_convex(fp, 0.02), zt + 0.06, zt + 0.13, b.roof_top_mat)
        deck = offset_convex(att, -0.08)
        mb.prism(deck, zt + ah, zt + ah + 0.1, b.roof_top_mat)
        top_z = zt + ah + 0.1
    else:  # flat
        mb.prism(offset_convex(fp, 0.02), zt + 0.06, zt + 0.16, b.roof_top_mat)
        for i in range(n):
            ef = EdgeFrame(fp[i], fp[(i + 1) % n])
            ef.box(mb, 0, ef.L, zt + 0.16, zt + 0.32, -0.08, 0.0, b.trim)
        deck = offset_convex(fp, 0.1)
        top_z = zt + 0.16

    # Kamine
    xs = [p[0] for p in deck]
    ys = [p[1] for p in deck]
    if b.chimneys is None:
        chims = []
        for k in range(b.n_auto_chimneys):
            w = rng.uniform(0.35, 0.8)
            chims.append((rng.uniform(min(xs) + 0.3, max(xs) - 0.3), rng.uniform(min(ys) + 0.3, max(ys) - 0.3),
                          w, rng.uniform(0.25, 0.35), rng.uniform(0.45, 0.85), max(1, int(w / 0.16))))
    else:
        chims = b.chimneys
    for (x, y, w, d, h, pots) in chims:
        _chimney(mb, x, y, top_z - 0.02, w, d, h, pots, b.chimney_mat, rng)

    ob = mb.build(b.name, materials, collection, location=(cx, cy, 0))
    ob['roof_top_z'] = top_z
    ob['wall_top_z'] = zt
    return ob, (fp, top_z, deck)
