"""MeshBuilder: setzt viele einfache Teile (Box, Zylinder, Kugel, Prisma ...) zu
einem einzigen Mesh-Objekt mit mehreren Materialien zusammen.

Ein Objekt pro Haus / Wahrzeichen hält die Szene schlank (wenige Objekte,
schnelles Rendern) und macht jedes Bauteil wiederverwendbar.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from . import materials


def _mat(c, rz=0.0, s=(1, 1, 1), rx=0.0, ry=0.0):
    return (Matrix.Translation(Vector(c)) @ Matrix.Rotation(rz, 4, "Z") @ Matrix.Rotation(ry, 4, "Y")
            @ Matrix.Rotation(rx, 4, "X") @ Matrix.Diagonal((*s, 1.0)))


class MeshBuilder:
    def __init__(self):
        self.bm = bmesh.new()
        self.mats = []

    def _mi(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def _tag(self, verts, mat, smooth):
        mi = self._mi(mat)
        faces = {f for v in verts for f in v.link_faces}
        for f in faces:
            f.material_index = mi
            f.smooth = smooth
        return faces

    # --- Grundkörper -------------------------------------------------------
    def box(self, c, s, mat, rz=0.0, ry=0.0):
        """Quader mit Mittelpunkt c=(x,y,z) und Größe s=(sx,sy,sz)."""
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=_mat(c, rz, s, ry=ry))
        self._tag(r["verts"], mat, False)

    def box_on(self, x, y, z0, sx, sy, sz, mat, rz=0.0):
        """Quader, der bei Höhe z0 steht (praktisch für Gebäude)."""
        self.box((x, y, z0 + sz / 2), (sx, sy, sz), mat, rz)

    def cyl(self, c, r, h, mat, seg=16, r2=None, rz=0.0, rx=0.0, ry=0.0, smooth=True, cap=True):
        """Zylinder/Kegel(stumpf), c = Mittelpunkt der Grundfläche."""
        m = _mat(c, rz, rx=rx, ry=ry) @ Matrix.Translation((0, 0, h / 2))
        res = bmesh.ops.create_cone(self.bm, cap_ends=cap, cap_tris=False, segments=seg,
                                    radius1=r, radius2=r if r2 is None else r2, depth=h, matrix=m)
        faces = self._tag(res["verts"], mat, smooth)
        if smooth:  # Deckel flach lassen
            for f in faces:
                if abs(f.normal.z) > 0.99 and len(f.verts) > 4:
                    f.smooth = False

    def sphere(self, c, r, mat, seg=16, rings=10, s=(1, 1, 1), zmin=None, zmax=None, smooth=True, ico=0):
        """(Teil-)Kugel. zmin/zmax schneiden in lokalen Einheiten (-1..1) ab."""
        m = _mat(c, s=(r * s[0], r * s[1], r * s[2]))
        if ico:
            res = bmesh.ops.create_icosphere(self.bm, subdivisions=ico, radius=1.0, matrix=m)
        else:
            res = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=rings, radius=1.0, matrix=m)
        verts = res["verts"]
        cut = []
        cz, sz = c[2], r * s[2]
        for v in verts:
            lz = (v.co.z - cz) / sz
            if (zmin is not None and lz < zmin - 1e-4) or (zmax is not None and lz > zmax + 1e-4):
                cut.append(v)
        keep = [v for v in verts if v not in set(cut)]
        if cut:
            bmesh.ops.delete(self.bm, geom=cut, context="VERTS")
        self._tag(keep, mat, smooth)

    def prism(self, x, y, z0, w, d, h, mat, rz=0.0, overhang=0.0):
        """Satteldach: Dreiecksprisma, First entlang der lokalen x-Achse."""
        w2, d2 = w / 2 + overhang, d / 2 + overhang
        m = _mat((x, y, z0), rz)
        pts = [(-w2, -d2, 0), (w2, -d2, 0), (w2, 0, h), (-w2, 0, h), (-w2, d2, 0), (w2, d2, 0)]
        vs = [self.bm.verts.new(m @ Vector(p)) for p in pts]
        for idx in [(0, 1, 2, 3), (3, 2, 5, 4), (0, 3, 4), (1, 5, 2), (0, 4, 5, 1)]:
            self.bm.faces.new([vs[i] for i in idx])
        self._tag(vs, mat, False)

    def hip(self, x, y, z0, w, d, h, mat, rz=0.0, overhang=0.0):
        """Walmdach mit kurzem First (ridge = Firstanteil an der Länge)."""
        w2, d2 = w / 2 + overhang, d / 2 + overhang
        m = _mat((x, y, z0), rz)
        if w >= d:
            r = max(w2 - d2, 0.05 * w2)
            top = [(-r, 0, h), (r, 0, h)]
        else:
            r = max(d2 - w2, 0.05 * d2)
            top = [(0, -r, h), (0, r, h)]
        base = [(-w2, -d2, 0), (w2, -d2, 0), (w2, d2, 0), (-w2, d2, 0)]
        vb = [self.bm.verts.new(m @ Vector(p)) for p in base]
        vt = [self.bm.verts.new(m @ Vector(p)) for p in top]
        if w >= d:
            faces = [(vb[0], vb[1], vt[1], vt[0]), (vb[2], vb[3], vt[0], vt[1]), (vb[1], vb[2], vt[1]), (vb[3], vb[0], vt[0])]
        else:
            faces = [(vb[0], vb[1], vt[0]), (vb[2], vb[3], vt[1]), (vb[1], vb[2], vt[1], vt[0]), (vb[3], vb[0], vt[0], vt[1])]
        for f in faces:
            self.bm.faces.new(f)
        self.bm.faces.new(list(reversed(vb)))
        self._tag(vb + vt, mat, False)

    def polygon_prism(self, pts, z0, h, mat, smooth=False):
        """Extrudiertes Polygon (Grundriss pts=[(x,y),...] gegen den Uhrzeigersinn)."""
        bot = [self.bm.verts.new((p[0], p[1], z0)) for p in pts]
        top = [self.bm.verts.new((p[0], p[1], z0 + h)) for p in pts]
        n = len(pts)
        self.bm.faces.new(list(reversed(bot)))
        self.bm.faces.new(top)
        for i in range(n):
            j = (i + 1) % n
            self.bm.faces.new((bot[i], bot[j], top[j], top[i]))
        self._tag(bot + top, mat, smooth)

    def loft(self, a, za, b, zb, mat, cap_top=False, cap_bottom=False):
        """Mantelfläche zwischen zwei gleich langen Polygonen (Mansarddach, Kuppeln ...)."""
        va = [self.bm.verts.new((p[0], p[1], za)) for p in a]
        vb = [self.bm.verts.new((p[0], p[1], zb)) for p in b]
        n = len(a)
        for i in range(n):
            j = (i + 1) % n
            self.bm.faces.new((va[i], va[j], vb[j], vb[i]))
        if cap_top:
            self.bm.faces.new(vb)
        if cap_bottom:
            self.bm.faces.new(list(reversed(va)))
        self._tag(va + vb, mat, False)

    def strip(self, pts, width, z, mat, thickness=0.0, closed=False):
        """Band entlang einer Polylinie (Straße, Fluss, Gehweg)."""
        left, right = [], []
        n = len(pts)
        for i in range(n):
            p = Vector((*pts[i], 0))
            a = Vector((*pts[i - 1], 0)) if (i > 0 or closed) else p
            b = Vector((*pts[(i + 1) % n], 0)) if (i < n - 1 or closed) else p
            t = (b - a)
            t.normalize()
            nrm = Vector((-t.y, t.x, 0)) * (width / 2)
            left.append(p + nrm)
            right.append(p - nrm)
        top_l = [self.bm.verts.new((v.x, v.y, z)) for v in left]
        top_r = [self.bm.verts.new((v.x, v.y, z)) for v in right]
        segs = n if closed else n - 1
        for i in range(segs):
            j = (i + 1) % n
            self.bm.faces.new((top_r[i], top_r[j], top_l[j], top_l[i]))
        allv = top_l + top_r
        if thickness > 0:
            bot_l = [self.bm.verts.new((v.x, v.y, z - thickness)) for v in left]
            bot_r = [self.bm.verts.new((v.x, v.y, z - thickness)) for v in right]
            for i in range(segs):
                j = (i + 1) % n
                self.bm.faces.new((top_l[i], top_l[j], bot_l[j], bot_l[i]))
                self.bm.faces.new((bot_r[i], bot_r[j], top_r[j], top_r[i]))
            allv += bot_l + bot_r
        self._tag(allv, mat, False)

    def ring(self, a_out, b_out, a_in, b_in, z0, h, mat, n=48, th0=0.0, th1=2 * math.pi, smooth=False, c=(0, 0)):
        """Elliptischer Ring (auch Teilbogen th0..th1) als Volumen – Tribünen, Becken, Kolonnaden."""
        full = abs(th1 - th0 - 2 * math.pi) < 1e-6
        cnt = n if full else n + 1
        ang = [th0 + (th1 - th0) * i / n for i in range(cnt)]
        ob = [self.bm.verts.new((c[0] + a_out * math.cos(t), c[1] + b_out * math.sin(t), z0)) for t in ang]
        ot = [self.bm.verts.new((c[0] + a_out * math.cos(t), c[1] + b_out * math.sin(t), z0 + h)) for t in ang]
        ib = [self.bm.verts.new((c[0] + a_in * math.cos(t), c[1] + b_in * math.sin(t), z0)) for t in ang]
        it = [self.bm.verts.new((c[0] + a_in * math.cos(t), c[1] + b_in * math.sin(t), z0 + h)) for t in ang]
        segs = n
        for i in range(segs):
            j = (i + 1) % cnt
            self.bm.faces.new((ob[i], ob[j], ot[j], ot[i]))
            self.bm.faces.new((it[i], it[j], ib[j], ib[i]))
            self.bm.faces.new((ot[i], ot[j], it[j], it[i]))
            self.bm.faces.new((ib[i], ib[j], ob[j], ob[i]))
        if not full:
            self.bm.faces.new((ob[0], ot[0], it[0], ib[0]))
            self.bm.faces.new((ib[-1], it[-1], ot[-1], ob[-1]))
        self._tag(ob + ot + ib + it, mat, smooth)

    def merge(self, other, matrix=None):
        """Fremden MeshBuilder (z. B. Bauteil-Bibliothek) hineinkopieren."""
        tmp = bpy.data.meshes.new("_tmp")
        other.bm.to_mesh(tmp)
        if matrix is not None:
            tmp.transform(matrix)
        remap = [self._mi(m) for m in other.mats]
        start = len(self.bm.faces)
        self.bm.from_mesh(tmp)
        self.bm.faces.ensure_lookup_table()
        for f in list(self.bm.faces)[start:]:
            f.material_index = remap[f.material_index] if f.material_index < len(remap) else 0
        bpy.data.meshes.remove(tmp)

    # --- Ausgabe -----------------------------------------------------------
    def build(self, name, collection, bevel=0.0, location=(0, 0, 0)):
        me = bpy.data.meshes.new(name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(materials.get(m))
        ob = bpy.data.objects.new(name, me)
        ob.location = location
        collection.objects.link(ob)
        if bevel > 0:
            mod = ob.modifiers.new("Bevel", "BEVEL")
            mod.width = bevel
            mod.segments = 2
            mod.limit_method = "ANGLE"
            mod.angle_limit = math.radians(40)
            mod.harden_normals = False
        return ob


def inset_polygon(pts, d):
    """Konvexes CCW-Polygon um d nach innen versetzen (d<0: nach außen)."""
    n = len(pts)
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
        L = math.hypot(x1 - x0, y1 - y0)
        nx, ny = -(y1 - y0) / L, (x1 - x0) / L  # links = innen
        lines.append(((x0 + nx * d, y0 + ny * d), (x1 - x0, y1 - y0)))
    out = []
    for i in range(n):
        (p, r), (q, s) = lines[i - 1], lines[i]
        den = r[0] * s[1] - r[1] * s[0]
        if abs(den) < 1e-9:
            out.append(q)
            continue
        t = ((q[0] - p[0]) * s[1] - (q[1] - p[1]) * s[0]) / den
        out.append((p[0] + r[0] * t, p[1] + r[1] * t))
    return out


def offset_polyline(pts, d):
    """Parallele Linie im Abstand d (links positiv)."""
    out = []
    n = len(pts)
    for i in range(n):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1.0
        out.append((pts[i][0] - ty / L * d, pts[i][1] + tx / L * d))
    return out


def ellipse(a, b, n, z=0.0, phase=0.0):
    return [(a * math.cos(phase + 2 * math.pi * i / n), b * math.sin(phase + 2 * math.pi * i / n), z) for i in range(n)]


def rounded_rect(w, d, r, n_corner=8):
    pts = []
    cx, cy = w / 2 - r, d / 2 - r
    for k, (sx, sy, a0) in enumerate([(1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)]):
        for i in range(n_corner + 1):
            a = math.radians(a0 + 90 * i / n_corner)
            pts.append((sx * cx + r * math.cos(a), sy * cy + r * math.sin(a)))
    return pts
