"""Plattform (Diorama-Sockel), Ringstraße, Gehwege, Markierungen, Laternen, Poller."""
import math
from mathutils import Vector
from .meshkit import MeshBuilder, rounded_rect

SEG = 10


def _rr(x0, y0, x1, y1, r, off):
    return rounded_rect(x0 + off, y0 + off, x1 - off, y1 - off, max(0.25, r - off), SEG)


def _resample(poly, step):
    """Geschlossenes Polygon -> Punkte im festen Bogenabstand (Pos, Richtung)."""
    pts = [Vector((p[0], p[1], 0)) for p in poly] + [Vector((poly[0][0], poly[0][1], 0))]
    out, carry = [], 0.0
    for a, b in zip(pts, pts[1:]):
        L = (b - a).length
        if L < 1e-6:
            continue
        d = (b - a) / L
        s = carry
        while s < L:
            out.append((a + d * s, d))
            s += step
        carry = s - L
    return out


def build_platform(size, r, materials, collection, road=(0.35, 2.55), walk=3.45):
    x0, y0, x1, y1 = 0, 0, size, size
    objs = []
    # Sockel
    mb = MeshBuilder()
    outer = _rr(x0, y0, x1, y1, r, 0)
    mb.prism(outer, -0.5, -0.0, 'slab', cap_bottom=True)
    mb.ring(outer, _rr(x0, y0, x1, y1, r, road[0]), 0.0, 0.1, 'curb')
    objs.append(mb.build('Platform_Base', materials, collection))
    # Straße
    mb = MeshBuilder()
    mb.ring(_rr(x0, y0, x1, y1, r, road[0]), _rr(x0, y0, x1, y1, r, road[1]), 0.0, 0.03, 'asphalt', walls=False)
    objs.append(mb.build('Road_Ring', materials, collection))
    # Markierungen
    mb = MeshBuilder()
    mid = (road[0] + road[1]) / 2
    for p, d in _resample(_rr(x0, y0, x1, y1, r, mid), 1.0):
        q = p + d * 0.5
        mb.beam((p.x, p.y, 0.032), (q.x, q.y, 0.032), 0.07, 'marking', h=0.006)
    for off in (road[0] + 0.18, road[1] - 0.18):
        mb.ring(_rr(x0, y0, x1, y1, r, off - 0.03), _rr(x0, y0, x1, y1, r, off + 0.03), 0.03, 0.034, 'marking', walls=False)
    objs.append(mb.build('Road_Markings', materials, collection))
    # Gehweg + Bordstein + Block
    mb = MeshBuilder()
    mb.ring(_rr(x0, y0, x1, y1, r, road[1]), _rr(x0, y0, x1, y1, r, road[1] + 0.1), 0.0, 0.13, 'curb')
    mb.ring(_rr(x0, y0, x1, y1, r, road[1] + 0.1), _rr(x0, y0, x1, y1, r, walk), 0.0, 0.12, 'sidewalk')
    inner = _rr(x0, y0, x1, y1, r, walk)
    mb.prism(inner, 0.0, 0.12, 'plaza')
    objs.append(mb.build('Sidewalk_Block', materials, collection))
    return objs


def build_lamp(name, location, materials, collection, h=1.0):
    mb = MeshBuilder()
    mb.cylinder((0, 0, 0), 0.05, 0.08, 'iron_black', seg=8)
    mb.cylinder((0, 0, 0.08), 0.022, h, 'iron_black', seg=8, r_top=0.016)
    mb.box((0, 0, h + 0.1), (0.1, 0.1, 0.14), 'lamp_glow')
    mb.cylinder((0, 0, h + 0.17), 0.08, 0.05, 'iron_black', seg=8, r_top=0.01)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        mb.box((sx * 0.05, sy * 0.05, h + 0.1), (0.015, 0.015, 0.16), 'iron_black')
    return mb.build(name, materials, collection, location=location)


def build_bollard(name, location, materials, collection):
    mb = MeshBuilder()
    mb.cylinder((0, 0, 0), 0.04, 0.22, 'iron_black', seg=8)
    mb.sphere((0, 0, 0.22), 0.045, 'iron_black', seg=8, rings=5)
    return mb.build(name, materials, collection, location=location)


def build_patch(name, poly, z, mat, materials, collection, h=0.03):
    mb = MeshBuilder()
    mb.prism(poly, z, z + h, mat)
    return mb.build(name, materials, collection)
