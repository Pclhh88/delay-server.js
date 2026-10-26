"""Blockout der Vorlage: nur Hauptmassen, direkt aus den Bildmessungen abgeleitet.

  python blender/blockout.py [--res 1024] [--samples 32]

Erzeugt:
  blockout.blend                       Blockout-Szene (jede Masse ein Objekt)
  renders/blockout.png                 Ton-Render (Clay, je Gebäude eigene Grundfarbe)
  renders/blockout_id.png              Flache ID-Farben (für Umrisse)
  renders/compare_blockout_*.png       Vergleich mit der Vorlage (lokal, nicht im Git)
"""
import argparse, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

from diorama.meshkit import MeshBuilder, rounded_rect, chamfer_rect, offset_convex  # noqa: E402
from fit_camera import unproject  # noqa: E402
import measurements as MS  # noqa: E402

PROJECT = os.path.dirname(HERE)
CAM = json.load(open(os.path.join(HERE, 'camera.json')))
Z0 = MS.BLOCK_Z
SIZE = 24.0
R_CORNER = round(CAM['corner_radius'], 2)

# Straßenquerschnitt (gemessen über Helligkeitsprofile bei x=560 und x=1560):
# Randkante 0..0.55 | Fahrbahn 0.55..2.35 (Randlinie bei 0.75) | Bordstein 2.35..2.5 | Gehweg 2.5..
ROAD = dict(rim=0.55, road=2.35, curb=2.5)

# ---------------------------------------------------------------------------------------
# Gebäudemassen. 'front', 'len_x', 'len_y', 'rot', 'z_top' stammen aus measurements.derive();
# Werte in 'override' sind dort, wo die Vorlage etwas verdeckt (Tiefe, Dachform), begründet gesetzt.
# ---------------------------------------------------------------------------------------
SPEC = {
    'A_corner_front': dict(color='#EFE7D8', roof='mansard', roof_color='#5D6C80', roof_h=1.0, inset=0.35,
                           chamfer=('SW', 0.75)),
    'B_red_roof': dict(color='#E3CFAE', roof='mansard', roof_color='#9C5646', roof_h=1.9, inset=0.78,
                       override=dict(len_x=3.3)),
    'C_blue_mansard': dict(color='#D6BC95', roof='mansard', roof_color='#5D6C80', roof_h=1.1, inset=0.55,
                           chimneys=[(0.6, 0.9, 0.7, 0.3, 0.5), (1.6, 2.0, 0.55, 0.3, 0.45), (1.2, 3.2, 0.5, 0.3, 0.5)]),
    'D_shutters': dict(color='#E3BE98', roof='mansard', roof_color='#B9BCBD', roof_h=0.5, inset=0.25,
                       override=dict(len_y=3.0)),
    'E_left_large': dict(color='#E6D3B2', roof='mansard', roof_color='#5D6C80', roof_h=1.0, inset=0.35,
                         parapet=0.18, chamfer=('SW', 0.25), override=dict(len_y=5.75)),
    # Vorlage: rechte Wand bei x≈1758 px und Dachpavillon mittig auf der Plattform -> Haus reicht bis
    # x≈22.2 (über den Gehweg der hinteren Ringstraße hinaus; dort im Bild verdeckt)
    'F_right_dome': dict(color='#D7B88E', roof='curved', roof_color='#7A8796', roof_h=1.8, inset=0.8,
                         parapet=0.15, rounded=('SW', 1.3), override=dict(rot=0.0, len_x=4.4)),
    'G_back_left': dict(color='#C9A57B', roof='attic', roof_color='#D9D6CF', roof_h=0.65, inset=0.25,
                        chamfer=('SW', 0.35), override=dict(rot=0.0, len_x=4.1, len_y=3.75)),
}
# Kleinbauten (Welt, direkt aus Bildpunkten: siehe ANALYSE.md Tabelle 3)
SMALL = [
    # Name, Bildpunkt Dachmitte, Dachhöhe, Größe (x, y), Höhe, Farbe Dach
    ('H_low_pavilion', (800, 1150), 2.4, (1.8, 2.6), 2.4, '#3E4A5E'),
    ('I_annex_left', (345, 1170), 1.7, (0.8, 1.2), 1.7, '#4A4F55'),
]
# Dachaufbauten (Bildpunkt Fuß, Bezug-Gebäude, Höhe)
ROOFTOP = [
    ('G_cupola', (735, 640), 'G_back_left', 2.3, '#F2EEE6'),
    ('F_kiosk', (1560, 700), 'F_right_dome', 0.8, '#A9C49A'),
]


def hexc(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)


_MATS = {}


def mat(name, color, rough=0.8):
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = hexc(color)
    b.inputs['Roughness'].default_value = rough
    m.diffuse_color = hexc(color)
    _MATS[name] = m
    return m


def masses():
    """Gebäude-Massen aus Messung + Spezifikation."""
    out = []
    der = MS.derive(CAM)
    for name, spec in SPEC.items():
        m = der[name]['m']
        zt = der[name]['z_top']
        fp = MS.footprint_from(m, zt, CAM)
        fp.update(spec.get('override', {}))
        out.append(dict(name=name, z_top=zt, **fp, **spec))
    return out


def footprint_poly(b):
    Lx, Ly = b['len_x'], b['len_y']
    corners = {}
    seg = 1
    if 'chamfer' in b:
        corners[b['chamfer'][0]] = b['chamfer'][1]
    if 'rounded' in b:
        corners[b['rounded'][0]] = b['rounded'][1]
        seg = 6
    loc = chamfer_rect(0, 0, Lx, Ly, corners, seg=seg)
    c, s = math.cos(b['rot']), math.sin(b['rot'])
    fx, fy = b['front']
    return [(fx + x * c - y * s, fy + x * s + y * c) for x, y in loc]


def build_mass(b, coll):
    fp = footprint_poly(b)
    cx = sum(p[0] for p in fp) / len(fp)
    cy = sum(p[1] for p in fp) / len(fp)
    loc = [(x - cx, y - cy) for x, y in fp]
    mb = MeshBuilder()
    zt = b['z_top'] - Z0
    mb.prism(loc, 0, zt, 'wall')
    if b.get('parapet'):
        mb.ring(loc, offset_convex(loc, 0.08), zt, zt + b['parapet'], 'trim')
    top = zt
    if b['roof'] in ('mansard', 'curved'):
        rings = []
        n = 6 if b['roof'] == 'curved' else 1
        for k in range(n + 1):
            t = k / n
            if b['roof'] == 'curved':
                th = t * math.pi / 2
                off, z = b['inset'] * (1 - math.cos(th)), b['roof_h'] * math.sin(th)
            else:
                off, z = b['inset'] * t, b['roof_h'] * t
            rings.append((offset_convex(loc, off + 0.001), zt + z))
        mb.loft(rings, 'roof', cap=False, smooth=b['roof'] == 'curved')
        mb.prism(rings[-1][0], zt + b['roof_h'] - 0.02, zt + b['roof_h'], 'deck')
        top = zt + b['roof_h']
    elif b['roof'] == 'attic':
        att = offset_convex(loc, b['inset'])
        mb.prism(att, zt, zt + b['roof_h'], 'wall')
        mb.prism(offset_convex(att, -0.06), zt + b['roof_h'], zt + b['roof_h'] + 0.06, 'deck')
        mb.ring(loc, offset_convex(loc, 0.06), zt, zt + 0.25, 'trim')
        top = zt + b['roof_h'] + 0.06
    for (x, y, w, d, h) in b.get('chimneys', []):
        q = Vector((x, y))
        c, s = math.cos(b['rot']), math.sin(b['rot'])
        wx = b['front'][0] + q.x * c - q.y * s - cx
        wy = b['front'][1] + q.x * s + q.y * c - cy
        mb.box((wx, wy, top + h / 2), (w, d, h), 'chimney', rot=b['rot'])
    mats = {'wall': mat(b['name'] + '_wall', b['color']), 'roof': mat(b['name'] + '_roof', b['roof_color'], 0.5),
            'deck': mat('deck', '#CFCCC6'), 'trim': mat(b['name'] + '_wall', b['color']),
            'chimney': mat('chimney', '#B0603F')}
    ob = mb.build(b['name'], mats, coll, location=(cx, cy, Z0))
    ob['top_z'] = Z0 + top
    return ob


def build_platform(coll):
    R = R_CORNER

    def rr(off):
        return rounded_rect(off, off, SIZE - off, SIZE - off, max(0.2, R - off), 12)
    mb = MeshBuilder()
    mb.prism(rr(0), -0.45, 0.0, 'slab', cap_bottom=True)
    mb.ring(rr(0), rr(ROAD['rim']), 0.0, 0.1, 'curb')
    mb.ring(rr(ROAD['rim']), rr(ROAD['road']), 0.0, 0.02, 'asphalt', walls=False)
    mb.ring(rr(0.73), rr(0.79), 0.02, 0.025, 'line', walls=False)
    mb.ring(rr(ROAD['road']), rr(ROAD['curb']), 0.0, Z0 + 0.01, 'curb')
    mb.prism(rr(ROAD['curb']), 0.0, Z0, 'walk')
    mb.build('Platform_Blockout', {'slab': mat('slab', '#C9C5BD'), 'curb': mat('curb', '#D2CEC6'),
                                   'asphalt': mat('asphalt', '#45484E'), 'line': mat('line', '#F0EEE8'),
                                   'walk': mat('walk', '#BEB8AC')}, coll)


# Turmprofil aus measurements.TOWER (z über Block, halbe Breite); Plattformen als Kästen
def build_tower_blockout(coll):
    from scipy.optimize import brentq
    from fit_camera import project
    P = lambda p: project(CAM, np.array([p], float))[0]
    t = unproject(CAM, (MS.TOWER['axis_u'], MS.TOWER['ground_v']), Z0)[:2]
    prof = {}
    for name, v, w in MS.TOWER['levels']:
        z = brentq(lambda z: P((t[0], t[1], z))[1] - v, -2, 40)
        a = brentq(lambda a: P((t[0] + a, t[1] - a, z))[0] - P((t[0] - a, t[1] + a, z))[0] - w, 1e-3, 10) if w else 0
        prof[name] = (z - Z0, a)
    mb = MeshBuilder()

    def sq(a):
        return [(-a, -a), (a, -a), (a, a), (-a, a)]
    # Beine (Fuß -> Etage 1), dann Etage 1 -> 2, dann Schaft
    seq = ['fuss', 'etage1_unten']
    mb.loft([(sq(prof[k][1] * (0.97 if k != 'fuss' else 1)), prof[k][0]) for k in seq], 'tower', cap=False)
    mb.prism(sq(prof['etage1_oben'][1] + 0.08), prof['etage1_unten'][0], prof['etage1_oben'][0], 'tower')
    seq = ['etage1_oben', 'zwischen_1_2', 'etage2']
    mb.loft([(sq(prof[k][1] * (0.9 if k == 'etage1_oben' else 1)), prof[k][0]) for k in seq], 'tower', cap=False)
    z2 = prof['etage2'][0]
    mb.prism(sq(prof['etage2'][1]), z2 - 0.18, z2 + 0.05, 'tower')
    seq = ['schaft_720', 'schaft_650', 'schaft_550', 'schaft_450', 'schaft_350', 'schaft_280']
    mb.loft([(sq(prof['schaft_720'][1]), z2)] + [(sq(prof[k][1]), prof[k][0]) for k in seq], 'tower')
    mb.prism(sq(prof['etage3_oben'][1]), prof['etage3_unten'][0], prof['etage3_oben'][0], 'tower')
    zk = prof['kuppel'][0]
    mb.cylinder((0, 0, prof['etage3_oben'][0]), prof['kuppel'][1], zk - prof['etage3_oben'][0] + 0.2, 'tower',
                seg=16, r_top=prof['kuppel'][1] * 0.45)
    mb.cylinder((0, 0, zk + 0.2), 0.05, prof['fahne'][0] - zk - 0.2, 'tower', seg=6, r_top=0.02)
    ob = mb.build('Eiffel_Blockout', {'tower': mat('tower', '#8A5638', 0.6)}, coll, location=(t[0], t[1], Z0))
    ob['profile'] = json.dumps({k: [round(v[0], 3), round(v[1], 3)] for k, v in prof.items()})
    return ob, prof


def build_small(coll, objs):
    for name, uv, h, (sx, sy), hh, rc in SMALL:
        x, y, _ = unproject(CAM, uv, Z0 + h)
        mb = MeshBuilder()
        mb.box((0, 0, hh / 2), (sx, sy, hh), 'wall')
        mb.loft([([(-sx / 2 - 0.05, -sy / 2 - 0.05), (sx / 2 + 0.05, -sy / 2 - 0.05), (sx / 2 + 0.05, sy / 2 + 0.05),
                   (-sx / 2 - 0.05, sy / 2 + 0.05)], hh),
                 ([(-sx / 2 + 0.3, -sy / 2 + 0.1), (sx / 2 - 0.1, -sy / 2 + 0.1), (sx / 2 - 0.1, sy / 2 - 0.1),
                   (-sx / 2 + 0.3, sy / 2 - 0.1)], hh + 0.35)], 'roof')
        mb.build(name, {'wall': mat(name + '_w', '#D8C6A6'), 'roof': mat(name + '_r', rc, 0.5)}, coll,
                 location=(x, y, Z0))
    for name, uv, ref, h, col in ROOFTOP:
        z = objs[ref]['top_z']
        x, y, _ = unproject(CAM, uv, z)
        mb = MeshBuilder()
        if 'cupola' in name:
            mb.cylinder((0, 0, 0), 0.45, h * 0.5, 'm', seg=12)
            mb.sphere((0, 0, h * 0.5), 0.45, 'm', seg=12, rings=8, scale=(1, 1, 1.2))
            mb.cylinder((0, 0, h * 0.75), 0.04, h * 0.25, 'm', seg=6)
        else:
            mb.box((0, 0, h * 0.4), (1.0, 0.8, h * 0.8), 'm')
            mb.box((0, 0, h * 0.85), (1.2, 1.0, h * 0.15), 'm')
        mb.build(name, {'m': mat(name, col)}, coll, location=(x, y, z))


def setup_camera_and_light(sc, coll):
    cam = bpy.data.objects.new('Camera_Reference', bpy.data.cameras.new('Camera_Reference'))
    cam.location = CAM['location']
    cam.rotation_euler = (CAM['pitch'], CAM['roll'], CAM['yaw'])
    cam.data.lens = CAM['lens']
    cam.data.sensor_width = CAM['sensor']
    cam.data.sensor_fit = 'HORIZONTAL'
    # Vorzeichen: im Fit liegt der Hauptpunkt bei +shift (Bildkoordinaten), Blender verschiebt den Bildausschnitt
    cam.data.shift_x = -CAM['shift_x']
    cam.data.shift_y = -CAM['shift_y']
    cam.data.clip_end = 2000
    coll.objects.link(cam)
    sc.camera = cam
    w = bpy.data.worlds.new('Studio')
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.95, 0.88, 0.75, 1)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.7
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
    sun.data.energy = 4.0
    sun.data.angle = math.radians(10)
    sun.data.color = (1.0, 0.94, 0.84)
    d = Vector((0.62, -0.42, 0.62)).normalized()
    sun.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    coll.objects.link(sun)
    me = bpy.data.meshes.new('Floor')
    me.from_pydata([(-400, -400, -0.45), (400, -400, -0.45), (400, 400, -0.45), (-400, 400, -0.45)], [], [(0, 1, 2, 3)])
    me.materials.append(mat('floor', '#FFF1D6', 0.95))
    coll.objects.link(bpy.data.objects.new('Studio_Floor', me))


def render(sc, path, res, samples):
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = samples > 4
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.view_settings.exposure = 0.35
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def render_ids(sc, path, res):
    """Flache, eindeutige Farbe je Objekt (Emission) -> scharfe Umrisse für den Abgleich."""
    import colorsys
    obs = [o for o in sc.objects if o.type == 'MESH' and o.name != 'Studio_Floor']
    for i, o in enumerate(obs):
        m = bpy.data.materials.new('ID_' + o.name)
        m.use_nodes = True
        nt = m.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        em = nt.nodes.new('ShaderNodeEmission')
        r, g, b = colorsys.hsv_to_rgb((i * 0.618) % 1, 0.9, 1.0)
        em.inputs['Color'].default_value = (r, g, b, 1)
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(em.outputs[0], out.inputs[0])
        o.data.materials.clear()
        o.data.materials.append(m)
        for p in o.data.polygons:
            p.material_index = 0
    floor = sc.objects['Studio_Floor']
    floor.hide_render = True
    sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0
    for o in sc.objects:
        if o.type == 'LIGHT':
            o.hide_render = True
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0
    sc.cycles.samples = 8
    sc.cycles.use_denoising = False
    sc.cycles.filter_width = 0.01
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--res', type=int, default=1024)
    ap.add_argument('--samples', type=int, default=32)
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    cB, cP, cT, cS, cL = (bpy.data.collections.new(n) for n in
                          ('Blockout_Buildings', 'Blockout_Platform', 'Blockout_Tower', 'Blockout_Small', 'Light_Camera'))
    for c in (cB, cP, cT, cS, cL):
        sc.collection.children.link(c)
    build_platform(cP)
    objs = {}
    for b in masses():
        ob = build_mass(b, cB)
        objs[b['name']] = ob
        print(f"{b['name']:16s} Ecke=({b['front'][0]:5.2f},{b['front'][1]:5.2f}) Lx={b['len_x']:.2f} "
              f"Ly={b['len_y']:.2f} Drehung={math.degrees(b['rot']):4.1f}° Traufe={b['z_top'] - Z0:.2f}")
    _, prof = build_tower_blockout(cT)
    build_small(cS, objs)
    setup_camera_and_light(sc, cL)
    sc.render.resolution_x = sc.render.resolution_y = a.res
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PROJECT, 'blockout.blend'), compress=True)
    render(sc, os.path.join(PROJECT, 'renders', 'blockout.png'), a.res, a.samples)
    render_ids(sc, os.path.join(PROJECT, 'renders', 'blockout_id.png'), 2048)


if __name__ == '__main__':
    main()
