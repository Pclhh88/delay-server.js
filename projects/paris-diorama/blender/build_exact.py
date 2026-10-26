"""Verfeinerte, exakte Rekonstruktion (Schritt 3) auf Basis des vermessenen Blockouts.

  python blender/build_exact.py [--res 2048] [--samples 128] [--out renders/exact.png]

Alle Gebäude stehen exakt auf den Blockout-Massen (Grundriss, Traufhöhe, Dachform aus
measurements.py / blockout.py). Fensterachsen, Geschosse und Gauben sind je Fassade aus der
Vorlage abgezählt. Bäume, Autos, Laternen, Hecke werden über ihre Bildposition platziert.
"""
import argparse, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import blockout as BO  # noqa: E402
from fit_camera import unproject, project  # noqa: E402
from diorama.materials import make_materials  # noqa: E402
from diorama.haussmann import Building, build_building  # noqa: E402
from diorama.eiffel import build_eiffel_measured  # noqa: E402
from diorama.nature import build_tree, build_hedge, build_bush, crown_height, TREE_TYPES  # noqa: E402
from diorama.vehicles import build_car  # noqa: E402
from diorama.street import build_platform, build_lamp, build_bollard, build_patch  # noqa: E402
from diorama import extras  # noqa: E402

PROJECT = os.path.dirname(HERE)
CAM, Z0 = BO.CAM, BO.Z0
FH_DESIGN = 1.25   # Geschosshöhe, für die der Fassadengenerator gestaltet ist -> Maßstabsfaktor k

# Fassaden je Gebäude (aus der Vorlage abgezählt): Obergeschosse, EG-Höhe relativ zu OG,
# Achsbreite (Szeneneinheiten), Balkongeschosse, Gaubenform, Fassaden-/Dachmaterial, Extras
DETAIL = {
    'A_corner_front': dict(floors=3, g=1.35, bay=1.25, balcony_floors=(2,), dormer_style='arch',
                           facade='stone_light', roof_mat='zinc_blue', doors={0: [0]}, door_mat='door_green',
                           n_auto_chimneys=4),
    'B_red_roof': dict(floors=2, g=1.15, bay=1.05, balcony_floors=(), dormer_style='arch', facade='stone_beige',
                       roof_mat='roof_red', roof_top_mat='roof_flat', n_auto_chimneys=2),
    'C_blue_mansard': dict(floors=3, g=1.3, bay=0.85, balcony_floors=(2,), dormer_style='gable',
                           facade='stone_sand', roof_mat='zinc_blue', n_auto_chimneys=6),
    'D_shutters': dict(floors=4, g=1.5, bay=0.92, balcony_floors=(2, 4), dormers=False, facade='stone_warm',
                       roof_mat='zinc_light', shutters='shutter_brown', n_auto_chimneys=1),
    'E_left_large': dict(floors=4, g=1.2, bay=1.12, balcony_floors=(2, 4), dormer_style='gable',
                         facade='stone_cream', roof_mat='zinc_blue', n_auto_chimneys=4),
    'F_right_dome': dict(floors=3, g=1.25, bay=1.2, balcony_floors=(2,), dormer_style='arch',
                         facade='stone_sand', roof_mat='zinc_blue', n_auto_chimneys=0,
                         oriels=[(6, 0.55, 0.9, 1, 3), (9, 0.4, 0.9, 1, 3)]),
    'G_back_left': dict(floors=4, g=1.1, bay=0.78, balcony_floors=(4,), facade='stone_tan',
                        roof_top_mat='roof_flat', n_auto_chimneys=5),
}

# Bäume: Kronenmitte (Bild), Kronenradius (px), Typ
TREES = [
    ((400, 1235), 65, 'orange'), ((200, 1000), 62, 'orange'), ((235, 1150), 55, 'round'), ((290, 1080), 45, 'dark'),
    ((350, 875), 50, 'blossom'), ((430, 765), 45, 'round'), ((395, 815), 35, 'small'), ((790, 960), 58, 'dark'),
    ((800, 1075), 45, 'round'), ((950, 1065), 62, 'round'), ((900, 1160), 50, 'round'), ((1195, 730), 78, 'tall'),
    ((1150, 975), 45, 'dark'), ((1640, 790), 45, 'round'), ((1735, 945), 70, 'round'), ((1500, 1250), 45, 'round'),
    ((1610, 1215), 60, 'ochre'), ((1700, 1150), 50, 'round'), ((1790, 1290), 85, 'orange'),
    ((1270, 1430), 55, 'orange'), ((940, 1560), 45, 'small'), ((1085, 1545), 45, 'small'), ((600, 1360), 45, 'dark'),
    ((640, 1430), 40, 'small'), ((1080, 1150), 40, 'small'), ((1180, 1060), 40, 'round'), ((870, 1010), 40, 'dark'),
    # weiteres Grün, das in der Vorlage die Lücken füllt
    ((240, 1230), 60, 'round'), ((190, 1140), 50, 'round'), ((285, 1285), 45, 'dark'), ((760, 1005), 50, 'dark'),
    ((1830, 1180), 45, 'round'), ((1560, 1190), 40, 'dark'), ((700, 1080), 40, 'small'), ((1010, 1120), 40, 'dark'),
]
TREE_SCALE = 1.12   # Kronen im Bild wirken durch Büschel größer als der Kernradius
# Fahrzeuge: Bildmitte, Typ, Material, Straße ('L' entlang y / 'R' entlang x), Richtung
CARS = [((745, 1650), 'van', 'car_white', 'L', 1), ((540, 1445), 'compact', 'car_dark', 'L', -1),
        ((1270, 1700), 'sedan', 'car_gray', 'R', 1), ((1370, 1605), 'boxvan', 'car_teal', 'R', -1),
        ((1585, 1470), 'sedan', 'car_red', 'R', 1)]
LAMPS = [(1015, 1735), (405, 1395), (1530, 1355), (1820, 1085), (1265, 1615)]
BOLLARDS = [(1500, 1590), (85, 1395), (1160, 1710)]
HEDGE = [(915, 1852), (990, 1860), (1065, 1858), (1135, 1846), (1195, 1822)]


def px_per_unit(xy, z):
    a = project(CAM, np.array([[xy[0], xy[1], z]]))[0]
    b = project(CAM, np.array([[xy[0] + 0.7071, xy[1] - 0.7071, z]]))[0]
    return float(np.linalg.norm(b - a))


def build_buildings(M, coll):
    objs = {}
    for b in BO.masses():
        d = DETAIL[b['name']]
        H = b['z_top'] - Z0
        fh = H / (d['floors'] + d['g'])
        k = FH_DESIGN / fh
        fp = BO.footprint_poly(b)
        cx = sum(p[0] for p in fp) / len(fp)
        cy = sum(p[1] for p in fp) / len(fp)
        fpk = [(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in fp]
        roof = {'mansard': 'mansard', 'curved': 'mansard_curved', 'attic': 'attic'}[b['roof']]
        kw = dict(d)
        kw.pop('g')
        kw['bay'] = d['bay'] * k
        spec = Building(name=b['name'], footprint=fpk, ground_h=fh * d['g'] * k, floor_h=FH_DESIGN, roof=roof,
                        roof_h=b['roof_h'] * k, roof_inset=b['inset'] * k, seed=sum(map(ord, b['name'])), **kw)
        ob, _ = build_building(spec, M, coll)
        ob.scale = (1 / k, 1 / k, 1 / k)
        ob.location = (cx, cy, Z0)
        ob['top_z'] = Z0 + ob['roof_top_z'] / k
        ob['scale_factor'] = k
        objs[b['name']] = ob
        print(f"{b['name']:16s} Geschosse EG+{d['floors']}  Geschosshöhe {fh:.2f}  Maßstab k={k:.2f}")
    return objs


def build_rooftops(M, coll, objs):
    for name, uv, ref, h, col in BO.ROOFTOP:
        z = objs[ref]['top_z']
        x, y, _ = unproject(CAM, uv, z)
        if 'cupola' in name:
            extras.build_cupola('Roof_Cupola', (x, y, z), M, coll, s=0.75)
        else:
            extras.build_kiosk('Roof_Kiosk', (x, y, z), M, coll, s=0.7)
    for name, ref, n, seed in (('Roof_Clutter_G', 'G_back_left', 9, 3), ('Roof_Clutter_F', 'F_right_dome', 5, 4)):
        ob = objs[ref]
        extras.build_roof_clutter(name, (ob.location.x, ob.location.y, ob['top_z']), M, coll,
                                  area=(1.8, 1.6), n=n, seed=seed)


def build_trees(M, coll):
    for i, ((u, v), r_px, kind) in enumerate(TREES):
        R = TREE_TYPES[kind][1]
        # Größe iterativ: Kronenradius im Bild / Pixel pro Einheit an der Kronenposition
        size = 0.8
        for _ in range(4):
            ch = crown_height(kind, size)
            x, y, _ = unproject(CAM, (u, v), Z0 + ch)
            size = TREE_SCALE * r_px / px_per_unit((x, y), Z0 + ch) / R
        build_tree(f'Tree_{i:02d}_{kind}', kind, (x, y, Z0), M, coll, size=size, seed=i + 1)
    pts = [tuple(unproject(CAM, uv, 0.3)[:2]) + (0.1,) for uv in HEDGE]
    build_hedge('Hedge_Front', pts, M, coll, height=0.45, width=0.5, seed=5)


def build_cars(M, coll):
    for i, ((u, v), kind, color, road, direction) in enumerate(CARS):
        x, y, _ = unproject(CAM, (u, v), 0.3)
        head = (math.pi / 2 if direction > 0 else -math.pi / 2) if road == 'L' else (0.0 if direction > 0 else math.pi)
        ob = build_car(f'Car_{i}_{kind}', kind, color, (x, y, 0.02), head, M, coll)
        ob.scale = (1.15, 1.15, 1.15)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--res', type=int, default=1024)
    ap.add_argument('--samples', type=int, default=64)
    ap.add_argument('--out', default=os.path.join(PROJECT, 'renders', 'exact.png'))
    ap.add_argument('--ids', action='store_true', help='zusätzlich ID-Render für den Umriss-Abgleich')
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    M = make_materials()
    names = ('Street', 'Buildings', 'Tower', 'Trees', 'Vehicles', 'Props', 'Light_Camera')
    C = {n: bpy.data.collections.new(n) for n in names}
    for c in C.values():
        sc.collection.children.link(c)

    build_platform(24.0, BO.R_CORNER, M, C['Street'], road=(BO.ROAD['rim'], BO.ROAD['road']), walk=BO.ROAD['curb'])
    t, prof = BO.tower_profile()
    build_patch('Tower_Ground', [(t[0] - 2.6, t[1] - 2.6), (t[0] + 2.6, t[1] - 2.6), (t[0] + 2.6, t[1] + 2.6),
                                 (t[0] - 2.6, t[1] + 2.6)], Z0, 'dirt', M, C['Street'], h=0.01)
    build_eiffel_measured(M, C['Tower'], (t[0], t[1], Z0), prof)
    objs = build_buildings(M, C['Buildings'])
    BO.build_small(C['Props'], objs)
    build_rooftops(M, C['Props'], objs)
    build_trees(M, C['Trees'])
    build_cars(M, C['Vehicles'])
    for i, (pts, h) in enumerate(((((1385, 1440), (1430, 1418), (1480, 1395)), 0.35),
                                  (((560, 1500), (600, 1520)), 0.35))):
        build_hedge(f'Hedge_{i}', [tuple(unproject(CAM, uv, Z0 + 0.2)[:2]) + (Z0,) for uv in pts], M, C['Trees'],
                    height=h, width=0.4, seed=40 + i)
    for i, uv in enumerate(LAMPS):
        build_lamp(f'Lamp_{i}', unproject(CAM, uv, Z0), M, C['Props'], h=0.75)
    for i, uv in enumerate(BOLLARDS):
        build_bollard(f'Bollard_{i}', unproject(CAM, uv, Z0), M, C['Props'])

    BO.setup_camera_and_light(sc, C['Light_Camera'])
    sc.objects['Studio_Floor'].data.materials[0] = M['floor']
    sc.render.resolution_x = sc.render.resolution_y = a.res
    nverts = sum(len(o.data.vertices) for o in sc.objects if o.type == 'MESH')
    print(f'Szene: {len(sc.objects)} Objekte, {nverts} Vertices')
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PROJECT, 'paris_diorama_exact.blend'), compress=True)
    BO.render(sc, a.out, a.res, a.samples)
    if a.ids:
        BO.render_ids(sc, a.out.replace('.png', '_id.png'), 2048)


if __name__ == '__main__':
    main()
