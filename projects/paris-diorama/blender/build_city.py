"""Ganze Stadt in Benchmark-Qualität (Schritt nach dem Gebäude-F-Benchmark).

  python blender/build_city.py [--res 2048] [--samples 128] [--out renders/city.png]

* Lage/Größe jedes Hauses: vermessene Blockout-Massen (blockout.masses()).
* Gebäude F: unverändert das Benchmark-Modell (diorama/landmark.py).
* Alle anderen Häuser: diorama/city.py (gleiche Techniken: Profil-Sweeps, Boolean-Öffnungen, plastische
  Fenster, Gussbalkone, Gauben mit echten Fenstern, Kaminstöcke), Details je Haus aus der Vorlage.
* Turm, Straße, Autos, Laternen wie in der exakten Rekonstruktion; Bäume neu (Büschel-Kronen).
* Licht/Farbe wie im Benchmark (warme Sonne von rechts vorne, Hintergrund nur für die Kamera hell).
"""
import argparse, math, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import blockout as BO  # noqa: E402
import build_exact as BX  # noqa: E402
from fit_camera import unproject  # noqa: E402
from diorama.materials import make_materials as base_materials  # noqa: E402
from diorama import city as CT, landmark as LM  # noqa: E402
from diorama.eiffel import build_eiffel_measured  # noqa: E402
from diorama.nature import build_tree_hq, build_hedge, crown_height, TREE_TYPES  # noqa: E402
from diorama.vehicles import build_car  # noqa: E402
from diorama.street import build_platform, build_lamp, build_bollard, build_patch  # noqa: E402

PROJECT = os.path.dirname(HERE)
CAM, Z0 = BO.CAM, BO.Z0

# Details je Haus (aus der Vorlage): Geschosse, EG-Verhältnis, Farben, Dach, Gauben, Fassadenmerkmale.
# Maße in Weltmaß (rad, roof_h, roof_in, bay) werden in Designeinheiten umgerechnet.
HOUSES = {
    'A_corner_front': dict(floors=3, g=1.35, stone=('#EAE2D3', '#D5CAB7'), roof_kind='mansard', dormer='arch',
                           rad_sw=0.7, bay=0.95, balconies=(2,), corner_windows=True,
                           doors={'corner': [0]}, door_mat='wood_green', n_chimneys=3),
    'B_red_roof': dict(floors=2, g=1.15, stone=('#DCC6A2', '#C4AC88'), roof_kind='curved', roof_mat='roof_red',
                       dormer='arch', bay=0.95, balconies=(), n_chimneys=2, ground='shop'),
    'C_blue_mansard': dict(floors=3, g=1.3, stone=('#D6BB93', '#BEA078'), roof_kind='mansard', dormer='gable',
                           bay=0.85, balconies=(2,), n_chimneys=5, many_pots=True),
    'D_shutters': dict(floors=4, g=1.5, stone=('#DDB894', '#C69D78'), roof_kind='low', roof_mat='zinc_light',
                       dormer='none', bay=0.8, balconies=(2, 4), shutters='shutter', n_chimneys=1),
    'E_left_large': dict(floors=4, g=1.2, stone=('#E3CFAC', '#CBB48F'), roof_kind='mansard', dormer='gable',
                         rad_sw=0.25, bay=0.95, balconies=(2, 4), balustrade=True, n_chimneys=4),
    'G_back_left': dict(floors=4, g=1.1, stone=('#C9A57B', '#AE8A61'), roof_kind='attic', dormer='none', rad_sw=0.35, bay=0.8,
                        balconies=(), n_chimneys=4, lambrequins=False),
}
SMALL = {  # Kleinbauten: Bildpunkt Dachmitte, Höhe, Größe, Geschosse, EG-Verhältnis
    'H_low_pavilion': dict(uv=(800, 1150), h=2.4, size=(1.8, 2.6), floors=1, g=1.2, stone=('#D8C6A6', '#C0AC8A')),
    'I_annex_left': dict(uv=(345, 1170), h=1.7, size=(0.8, 1.2), floors=1, g=0.9, stone=('#D6C3A2', '#BDA886')),
}


def _chimneys(lx, ly, inset, n, many_pots, rng):
    out = []
    for k in range(n):
        w = rng.uniform(0.45, 0.9) if many_pots else rng.uniform(0.35, 0.65)
        x = rng.uniform(inset + 0.3, max(inset + 0.35, lx - inset - 0.3))
        y = rng.uniform(inset + 0.3, max(inset + 0.35, ly - inset - 0.3))
        out.append((x, y, w, 0.32, rng.uniform(0.45, 0.75), max(1, int(w / 0.15))))
    return out


def build_houses(coll):
    roots = {}
    for b in BO.masses():
        if b['name'] == 'F_right_dome':
            continue
        d = HOUSES[b['name']]
        H = b['z_top'] - Z0
        fh = H / (d['floors'] + d['g'])
        k = 1.0 / fh
        rad = dict(SW=d.get('rad_sw', 0.05) * k, SE=0.05, NE=0.05, NW=0.05)
        rng = random.Random(sum(map(ord, b['name'])))
        lx, ly = b['len_x'] * k, b['len_y'] * k
        roof_h = b['roof_h'] * k
        roof_in = b['inset'] * k
        h = CT.House(name=b['name'], lx=lx, ly=ly, rad=rad, floors=d['floors'], gh=d['g'], stone=d['stone'],
                     roof_kind=d['roof_kind'], roof_h=roof_h, roof_in=roof_in, roof_mat=d.get('roof_mat', 'zinc'),
                     dormer=d['dormer'], bay=d['bay'] * k, balconies=d['balconies'], shutters=d.get('shutters', ''),
                     ground=d.get('ground', 'shop'), doors=d.get('doors', {}), door_mat=d.get('door_mat', 'wood'),
                     corner_windows=d.get('corner_windows', False), balustrade=d.get('balustrade', False),
                     lambrequins=d.get('lambrequins', False), attic_in=0.45 * k, attic_h=b['roof_h'] * k,
                     chimneys=_chimneys(lx, ly, roof_in, d['n_chimneys'], d.get('many_pots', False), rng),
                     seed=rng.randint(0, 999))
        root = CT.build_house(h, coll, (b['front'][0], b['front'][1], Z0), b['rot'], 1.0 / k)
        roots[b['name']] = (root, k)
        print(f"{b['name']:16s} EG+{d['floors']}  Geschoss {fh:.2f}  k={k:.2f}  {len(root.children)} Teile")
    for name, s in SMALL.items():
        fh = s['h'] / (s['floors'] + s['g'])
        k = 1.0 / fh
        x, y, _ = unproject(CAM, s['uv'], Z0 + s['h'])
        sx, sy = s['size']
        h = CT.House(name=name, lx=sx * k, ly=sy * k, rad=dict(SW=0.05, SE=0.05, NE=0.05, NW=0.05),
                     floors=s['floors'], gh=s['g'], stone=s['stone'], roof_kind='mansard', roof_h=0.45 * k,
                     roof_in=0.3 * k, dormer='none', bay=0.7 * k, balconies=(), ground='arch')
        CT.build_house(h, coll, (x - sx / 2, y - sy / 2, Z0), 0.0, 1.0 / k)
    return roots


def build_rooftops(coll, roots):
    mb = LM.MeshBuilder()
    root, k = roots['G_back_left']
    z = Z0 + root['top_z_design'] / k
    x, y, _ = unproject(CAM, (735, 640), z)
    CT.cupola(mb, x, y, z, s=0.62)
    for i in range(6):  # Antennen, Lüfter
        rng = random.Random(i)
        mb.cylinder((x + rng.uniform(-1.4, 0.6), y + rng.uniform(-1.6, 0.4), z), 0.02, rng.uniform(0.2, 0.45), 'iron', seg=6)
    ob = mb.build('G_Cupola', CT.shared_materials(), coll)
    return ob


def build_trees(M, coll):
    for i, ((u, v), r_px, kind) in enumerate(BX.TREES):
        R = TREE_TYPES[kind][1]
        size = 0.8
        for _ in range(4):
            ch = crown_height(kind, size)
            x, y, _ = unproject(CAM, (u, v), Z0 + ch)
            size = BX.TREE_SCALE * r_px / BX.px_per_unit((x, y), Z0 + ch) / R
        build_tree_hq(f'Tree_{i:02d}_{kind}', kind, (x, y, Z0), M, coll, size=size, seed=i + 1)
    pts = [tuple(unproject(CAM, uv, 0.3)[:2]) + (0.1,) for uv in BX.HEDGE]
    build_hedge('Hedge_Front', pts, M, coll, height=0.45, width=0.5, seed=5)
    for i, pts in enumerate((((1385, 1440), (1430, 1418), (1480, 1395)), ((560, 1500), (600, 1520)))):
        build_hedge(f'Hedge_{i}', [tuple(unproject(CAM, uv, Z0 + 0.2)[:2]) + (Z0,) for uv in pts], M, coll,
                    height=0.35, width=0.4, seed=40 + i)


def setup_light_camera(sc, coll):
    cam = bpy.data.objects.new('Camera_Reference', bpy.data.cameras.new('Camera_Reference'))
    cam.location = CAM['location']
    cam.rotation_euler = (CAM['pitch'], CAM['roll'], CAM['yaw'])
    cam.data.lens = CAM['lens']
    cam.data.sensor_width = CAM['sensor']
    cam.data.sensor_fit = 'HORIZONTAL'
    cam.data.shift_x = -CAM['shift_x']
    cam.data.shift_y = -CAM['shift_y']
    cam.data.clip_end = 2000
    coll.objects.link(cam)
    sc.camera = cam
    w = bpy.data.worlds.new('WarmStudio')
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.96, 0.9, 0.82, 1)
    bg.inputs['Strength'].default_value = 0.45
    sun = bpy.data.objects.new('Sun_Key', bpy.data.lights.new('Sun_Key', 'SUN'))
    sun.data.energy = 5.0
    sun.data.angle = math.radians(9)
    sun.data.color = (1.0, 0.93, 0.83)
    d = Vector((0.05, -0.8, 0.55)).normalized()
    sun.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    coll.objects.link(sun)
    fill = bpy.data.objects.new('Area_Fill', bpy.data.lights.new('Area_Fill', 'AREA'))
    fill.data.energy = 3500
    fill.data.size = 40
    fill.data.color = (1.0, 0.95, 0.88)
    fill.location = (-25, -10, 30)
    fill.rotation_euler = (Vector((12, 12, 3)) - fill.location).to_track_quat('-Z', 'Y').to_euler()
    coll.objects.link(fill)
    me = bpy.data.meshes.new('Studio_Floor')
    s = 400
    me.from_pydata([(-s, -s, -0.45), (s, -s, -0.45), (s, s, -0.45), (-s, s, -0.45)], [], [(0, 1, 2, 3)])
    fm = bpy.data.materials.new('floor')
    fm.use_nodes = True
    nt = fm.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (1.0, 0.88, 0.7, 1)
    b.inputs['Roughness'].default_value = 0.95
    b.inputs['Emission Color'].default_value = (1.0, 0.8, 0.52, 1)
    lp = nt.nodes.new('ShaderNodeLightPath')
    mul = nt.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = 2.4
    nt.links.new(lp.outputs['Is Camera Ray'], mul.inputs[0])
    nt.links.new(mul.outputs[0], b.inputs['Emission Strength'])
    me.materials.append(fm)
    coll.objects.link(bpy.data.objects.new('Studio_Floor', me))


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--res', type=int, default=1024)
    ap.add_argument('--samples', type=int, default=64)
    ap.add_argument('--out', default=os.path.join(PROJECT, 'renders', 'city.png'))
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    names = ('Street', 'Buildings', 'Tower', 'Trees', 'Vehicles', 'Props', 'Light_Camera')
    C = {n: bpy.data.collections.new(n) for n in names}
    for c in C.values():
        sc.collection.children.link(c)
    M = dict(base_materials())
    M.update(CT.shared_materials())

    build_platform(24.0, BO.R_CORNER, M, C['Street'], road=(BO.ROAD['rim'], BO.ROAD['road']), walk=BO.ROAD['curb'])
    t, prof = BO.tower_profile()
    build_patch('Tower_Ground', [(t[0] - 2.6, t[1] - 2.6), (t[0] + 2.6, t[1] - 2.6), (t[0] + 2.6, t[1] + 2.6),
                                 (t[0] - 2.6, t[1] + 2.6)], Z0, 'dirt', M, C['Street'], h=0.01)
    build_eiffel_measured(M, C['Tower'], (t[0], t[1], Z0), prof)

    roots = build_houses(C['Buildings'])
    LM.build_landmark(C['Buildings'], (17.75, 6.82, Z0), name='F_right_dome', M=CT.shared_materials())
    build_rooftops(C['Props'], roots)
    build_trees(M, C['Trees'])
    BX.build_cars(M, C['Vehicles'])
    for i, uv in enumerate(BX.LAMPS):
        build_lamp(f'Lamp_{i}', unproject(CAM, uv, Z0), M, C['Props'], h=0.75)
    for i, uv in enumerate(BX.BOLLARDS):
        build_bollard(f'Bollard_{i}', unproject(CAM, uv, Z0), M, C['Props'])

    setup_light_camera(sc, C['Light_Camera'])
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = a.samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8
    sc.render.resolution_x = sc.render.resolution_y = a.res
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.view_settings.exposure = -0.6
    nverts = sum(len(o.data.vertices) for o in sc.objects if o.type == 'MESH')
    print(f'Szene: {len(sc.objects)} Objekte, {nverts} Vertices')
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PROJECT, 'paris_city.blend'), compress=True)
    sc.render.filepath = a.out
    bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    main()
