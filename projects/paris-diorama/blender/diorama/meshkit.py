"""MeshBuilder: sammelt Quader, Balken, Prismen und Lofts in EIN Mesh-Objekt.

Jedes Gebäude, jeder Baum, jedes Auto wird so als einzelnes, eigenständiges
Blender-Objekt erzeugt (Ursprung = Bodenmitte), ist also später einzeln
bearbeit- und animierbar.
"""
import math
import bpy
from mathutils import Vector, Matrix


def _v(p):
    return Vector((p[0], p[1], p[2] if len(p) > 2 else 0.0))


class MeshBuilder:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.face_mats = []
        self.mat_names = []
        self.smooth = []

    # ---- intern -------------------------------------------------------
    def _mi(self, mat):
        if mat not in self.mat_names:
            self.mat_names.append(mat)
        return self.mat_names.index(mat)

    def add(self, verts, faces, mat, smooth=False):
        o = len(self.verts)
        self.verts.extend(Vector(v) for v in verts)
        mi = self._mi(mat)
        for f in faces:
            self.faces.append([o + i for i in f])
            self.face_mats.append(mi)
            self.smooth.append(smooth)
        return o

    # ---- Grundkörper --------------------------------------------------
    def box(self, center, size, mat, rot=0.0, matrix=None):
        """Quader, optional um z gedreht (rot, Radiant) bzw. mit 4x4-Matrix."""
        sx, sy, sz = (s / 2 for s in size)
        loc = [Vector((x, y, z)) for z in (-sz, sz) for y in (-sy, sy) for x in (-sx, sx)]
        R = Matrix.Rotation(rot, 3, 'Z')
        c = _v(center)
        pts = [R @ p + c for p in loc]
        if matrix is not None:
            pts = [matrix @ p for p in pts]
        faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
        return self.add(pts, faces, mat)

    def oriented_box(self, origin, ax, ay, az, mat):
        """Quader aus Ursprung + drei Kantenvektoren (beliebig orientiert)."""
        o = _v(origin)
        ax, ay, az = _v(ax), _v(ay), _v(az)
        pts = [o + ax * i + ay * j + az * k for k in (0, 1) for j in (0, 1) for i in (0, 1)]
        faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
        if ax.cross(ay).dot(az) < 0:  # linkshändiges Achsensystem -> Normalen umdrehen
            faces = [tuple(reversed(f)) for f in faces]
        return self.add(pts, faces, mat)

    def beam(self, p0, p1, w, mat, up=None, h=None):
        """Balken mit Querschnitt w x h zwischen zwei Punkten."""
        p0, p1 = _v(p0), _v(p1)
        d = p1 - p0
        if d.length < 1e-6:
            return
        dn = d.normalized()
        up = _v(up) if up is not None else (Vector((0, 0, 1)) if abs(dn.z) < 0.95 else Vector((1, 0, 0)))
        a = dn.cross(up).normalized()
        b = a.cross(dn).normalized()
        h = w if h is None else h
        o = p0 - a * (w / 2) - b * (h / 2)
        self.oriented_box(o, a * w, b * h, d, mat)

    def prism(self, poly, z0, z1, mat, cap_bottom=False):
        """Konvexes Polygon (xy, gegen den Uhrzeigersinn) extrudieren."""
        n = len(poly)
        pts = [(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in poly]
        faces = [tuple(range(n, 2 * n))]
        if cap_bottom:
            faces.append(tuple(reversed(range(n))))
        for i in range(n):
            j = (i + 1) % n
            faces.append((i, j, n + j, n + i))
        return self.add(pts, faces, mat)

    def loft(self, rings, mat, cap=True, smooth=False):
        """Verbindet Ringe [(poly, z), ...] gleicher Punktzahl (Dächer, Kuppeln)."""
        n = len(rings[0][0])
        pts = []
        for poly, z in rings:
            pts += [(x, y, z) for x, y in poly]
        faces = []
        for r in range(len(rings) - 1):
            for i in range(n):
                j = (i + 1) % n
                faces.append((r * n + i, r * n + j, (r + 1) * n + j, (r + 1) * n + i))
        if cap:
            last = len(rings) - 1
            faces.append(tuple(last * n + i for i in range(n)))
        return self.add(pts, faces, mat, smooth)

    def ring(self, outer, inner, z0, z1, mat, walls=True):
        """Flacher Ring zwischen zwei Polygonen gleicher Punktzahl (Straßen, Gehwege)."""
        n = len(outer)
        pts = [(x, y, z1) for x, y in outer] + [(x, y, z1) for x, y in inner]
        pts += [(x, y, z0) for x, y in outer] + [(x, y, z0) for x, y in inner]
        faces = []
        for i in range(n):
            j = (i + 1) % n
            faces.append((i, j, n + j, n + i))
            if walls:
                faces.append((2 * n + i, 2 * n + j, j, i))          # Außenkante
                faces.append((n + i, n + j, 3 * n + j, 3 * n + i))  # Innenkante
        return self.add(pts, faces, mat)

    def cylinder(self, center, r, h, mat, seg=12, r_top=None, smooth=True, cap=True):
        c = _v(center)
        rt = r if r_top is None else r_top
        pts = []
        for z, rr in ((0, r), (h, rt)):
            for i in range(seg):
                a = 2 * math.pi * i / seg
                pts.append((c.x + rr * math.cos(a), c.y + rr * math.sin(a), c.z + z))
        faces = [(i, (i + 1) % seg, seg + (i + 1) % seg, seg + i) for i in range(seg)]
        if cap:
            faces.append(tuple(range(seg, 2 * seg)))
            faces.append(tuple(reversed(range(seg))))
        return self.add(pts, faces, mat, smooth)

    def cylinder_x(self, center, r, length, mat, seg=12, axis='X'):
        """Liegender Zylinder (Räder, Rohre)."""
        c = _v(center)
        pts = []
        for s in (-length / 2, length / 2):
            for i in range(seg):
                a = 2 * math.pi * i / seg
                u, v = r * math.cos(a), r * math.sin(a)
                pts.append((c.x + s, c.y + u, c.z + v) if axis == 'X' else (c.x + u, c.y + s, c.z + v))
        faces = [(i, (i + 1) % seg, seg + (i + 1) % seg, seg + i) for i in range(seg)]
        faces.append(tuple(range(seg, 2 * seg)))
        faces.append(tuple(reversed(range(seg))))
        return self.add(pts, faces, mat, True)

    def sphere(self, center, radius, mat, seg=10, rings=7, scale=(1, 1, 1), smooth=True, jitter=None):
        c = _v(center)
        pts = []
        for r in range(1, rings):
            th = math.pi * r / rings
            for s in range(seg):
                ph = 2 * math.pi * s / seg
                p = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
                k = radius * (jitter(p) if jitter else 1.0)
                pts.append((c.x + p.x * k * scale[0], c.y + p.y * k * scale[1], c.z + p.z * k * scale[2]))
        top = len(pts)
        kt = radius * (jitter(Vector((0, 0, 1))) if jitter else 1)
        kb = radius * (jitter(Vector((0, 0, -1))) if jitter else 1)
        pts.append((c.x, c.y, c.z + kt * scale[2]))
        pts.append((c.x, c.y, c.z - kb * scale[2]))
        faces = []
        for r in range(rings - 2):
            for s in range(seg):
                t = (s + 1) % seg
                faces.append((r * seg + s, (r + 1) * seg + s, (r + 1) * seg + t, r * seg + t))
        for s in range(seg):
            t = (s + 1) % seg
            faces.append((top, s, t))
            b = (rings - 2) * seg
            faces.append((top + 1, b + t, b + s))
        return self.add(pts, faces, mat, smooth)

    # ---- Ausgabe -------------------------------------------------------
    def build(self, name, materials, collection=None, location=(0, 0, 0), rotation=0.0):
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in self.verts], [], self.faces)
        for mn in self.mat_names:
            me.materials.append(materials[mn])
        me.polygons.foreach_set("material_index", self.face_mats)
        me.polygons.foreach_set("use_smooth", self.smooth)
        me.validate(clean_customdata=False)
        me.update()
        ob = bpy.data.objects.new(name, me)
        ob.location = location
        ob.rotation_euler = (0, 0, rotation)
        (collection or bpy.context.scene.collection).objects.link(ob)
        return ob


# ---- 2D-Polygonhelfer ---------------------------------------------------

def offset_convex(poly, d):
    """Konvexes CCW-Polygon um d nach innen versetzen (d<0: nach außen)."""
    n = len(poly)
    lines = []
    for i in range(n):
        p, q = Vector(poly[i]), Vector(poly[(i + 1) % n])
        t = (q - p).normalized()
        nrm = Vector((-t.y, t.x))  # Innennormale bei CCW
        lines.append((p + nrm * d, t))
    out = []
    for i in range(n):
        p1, t1 = lines[i - 1]
        p2, t2 = lines[i]
        den = t1.x * t2.y - t1.y * t2.x
        if abs(den) < 1e-9:
            out.append(tuple(p2))
            continue
        s = ((p2.x - p1.x) * t2.y - (p2.y - p1.y) * t2.x) / den
        out.append(tuple(p1 + t1 * s))
    return out


def rounded_rect(x0, y0, x1, y1, r, seg=8):
    """Abgerundetes Rechteck, CCW, feste Punktzahl 4*(seg+1)."""
    pts = []
    corners = [((x1 - r, y0 + r), -90), ((x1 - r, y1 - r), 0), ((x0 + r, y1 - r), 90), ((x0 + r, y0 + r), 180)]
    for (cx, cy), a0 in corners:
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def chamfer_rect(x0, y0, x1, y1, corners, seg=1):
    """Rechteck mit abgeschrägten/gerundeten Ecken. corners: {'SW': r, ...}."""
    spec = [('SW', (x0, y0), 180), ('SE', (x1, y0), 270), ('NE', (x1, y1), 0), ('NW', (x0, y1), 90)]
    pts = []
    for key, (cx, cy), a0 in spec:
        r = corners.get(key, 0)
        if r <= 0:
            pts.append((cx, cy))
            continue
        sx = 1 if key in ('SW', 'NW') else -1
        sy = 1 if key in ('SW', 'SE') else -1
        ccx, ccy = cx + sx * r, cy + sy * r
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    return pts
