"""Baut die komplette Paris-Diorama-Szene, speichert die .blend und rendert.

Aufruf (Blender als Python-Modul):
    python blender/build_scene.py [--res 1024] [--samples 64] [--out renders/render.png] [--no-render]
Oder in Blender:
    blender -b -P blender/build_scene.py -- --res 2048 --samples 256
"""
import argparse, json, math, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from diorama.materials import make_materials  # noqa: E402
from diorama.haussmann import Building, build_building  # noqa: E402
from diorama.eiffel import build_eiffel  # noqa: E402
from diorama.nature import build_tree, build_hedge, build_bush, crown_height  # noqa: E402
from diorama.vehicles import build_car  # noqa: E402
from diorama.street import build_platform, build_lamp, build_bollard, build_patch  # noqa: E402
from diorama import extras  # noqa: E402
import layout as LY  # noqa: E402

PROJECT = os.path.dirname(HERE)


def args():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    p = argparse.ArgumentParser()
    p.add_argument('--res', type=int, default=1024)
    p.add_argument('--samples', type=int, default=64)
    p.add_argument('--out', default=os.path.join(PROJECT, 'renders', 'render.png'))
    p.add_argument('--blend', default=os.path.join(PROJECT, 'paris_diorama.blend'))
    p.add_argument('--no-render', action='store_true')
    return p.parse_args(argv)


def coll(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def setup_render(sc, a):
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = a.samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.render.resolution_x = sc.render.resolution_y = a.res
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.view_settings.exposure = 0.35
    sc.render.image_settings.file_format = 'PNG'


def setup_world_and_light(sc, M, C):
    w = bpy.data.worlds.new('WarmStudio')
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.95, 0.85, 0.68, 1)
    bg.inputs['Strength'].default_value = 0.75
    sun = bpy.data.objects.new('Sun_Key', bpy.data.lights.new('Sun_Key', 'SUN'))
    sun.data.energy = 4.5
    sun.data.angle = math.radians(12)
    sun.data.color = (1.0, 0.92, 0.80)
    # Licht von rechts (Bild) leicht von vorne/oben -> Schatten fallen nach links
    d = Vector((0.62, -0.42, 0.62)).normalized()
    sun.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    C.objects.link(sun)
    fill = bpy.data.objects.new('Area_Fill', bpy.data.lights.new('Area_Fill', 'AREA'))
    fill.data.energy = 2500
    fill.data.size = 30
    fill.data.color = (1.0, 0.95, 0.88)
    fill.location = (-30, -20, 30)
    fill.rotation_euler = (Vector((12, 12, 4)) - fill.location).to_track_quat('-Z', 'Y').to_euler()
    C.objects.link(fill)
    # Boden (Studio-Hintergrund)
    me = bpy.data.meshes.new('Floor')
    s = 400
    me.from_pydata([(-s, -s, -0.5), (s, -s, -0.5), (s, s, -0.5), (-s, s, -0.5)], [], [(0, 1, 2, 3)])
    me.materials.append(M['floor'])
    fl = bpy.data.objects.new('Studio_Floor', me)
    C.objects.link(fl)


def setup_camera(sc, C):
    cj = json.load(open(os.path.join(HERE, 'camera.json')))
    cam = bpy.data.objects.new('Camera_Reference', bpy.data.cameras.new('Camera_Reference'))
    cam.location = cj['location']
    cam.rotation_euler = (cj['pitch'], cj['roll'], cj['yaw'])
    cam.data.lens = cj['lens']
    cam.data.sensor_width = cj['sensor']
    cam.data.sensor_fit = 'HORIZONTAL'
    cam.data.shift_x = -cj['shift_x']  # Fit: Hauptpunkt in Bildkoordinaten; Blender: Bildausschnitt
    cam.data.shift_y = -cj['shift_y']
    cam.data.clip_end = 1000
    C.objects.link(cam)
    sc.camera = cam


def main():
    a = args()
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    M = make_materials()
    C_st, C_bu, C_tw, C_tr, C_ve, C_pr, C_lc = (coll(n) for n in
        ('Street', 'Buildings', 'Tower', 'Trees', 'Vehicles', 'Props', 'Light_Camera'))

    build_platform(LY.SIZE, LY.CORNER_R, M, C_st, road=LY.ROAD, walk=LY.WALK)
    # Grünflächen / Kies um den Turm
    tx, ty, _ = LY.TOWER['location']
    build_patch('Tower_Gravel', [(tx - 3.6, ty - 3.6), (tx + 3.6, ty - 3.6), (tx + 3.6, ty + 3.6), (tx - 3.6, ty + 3.6)],
                LY.BLOCK_Z, 'dirt', M, C_st, h=0.01)
    for i, (cx, cy, w, d) in enumerate([(13.8, 12.5, 2.4, 2.4), (15.0, 6.0, 2.6, 1.6), (4.6, 21.0, 2.6, 2.0),
                                        (19.8, 4.6, 3.0, 1.6), (21.0, 14.0, 1.6, 3.0)]):
        build_patch(f'Lawn_{i}', [(cx - w / 2, cy - d / 2), (cx + w / 2, cy - d / 2), (cx + w / 2, cy + d / 2),
                                  (cx - w / 2, cy + d / 2)], LY.BLOCK_Z, 'grass', M, C_st, h=0.02)

    for spec in LY.BUILDINGS:
        ob, _ = build_building(Building(**spec), M, C_bu)
        ob.location.z = LY.BLOCK_Z

    build_eiffel(M, C_tw, LY.TOWER['location'], LY.TOWER['scale'], LY.TOWER['rotation'])

    for kind, name, (x, y), kw in LY.EXTRAS:
        # Dachaufbauten sitzen auf der Dachfläche des darunterliegenden Hauses
        z = LY.BLOCK_Z
        for ob in C_bu.objects:
            lx, ly = x - ob.location.x, y - ob.location.y
            bb = [v for v in ob.bound_box]
            if min(v[0] for v in bb) < lx < max(v[0] for v in bb) and min(v[1] for v in bb) < ly < max(v[1] for v in bb):
                z = LY.BLOCK_Z + ob.get('roof_top_z', 0)
        if kind == 'cupola':
            extras.build_cupola(name, (x, y, z), M, C_pr, **kw)
        elif kind == 'kiosk':
            extras.build_kiosk(name, (x, y, z), M, C_pr, **kw)
        elif kind == 'clutter':
            extras.build_roof_clutter(name, (x, y, z), M, C_pr, **kw)
        elif kind == 'pavilion':
            extras.build_pavilion(name, (x, y, LY.BLOCK_Z), kw['size'], M, C_pr)

    for i, ((sx, sy), kind, size) in enumerate(LY.TREES_IMG):
        x, y, _ = LY.img2world(sx, sy, LY.BLOCK_Z + crown_height(kind, size))
        z = LY.BLOCK_Z
        build_tree(f'Tree_{i:02d}_{kind}', kind, (x, y, z), M, C_tr, size=size, seed=i + 1)
    for i, (x, y, kind, size) in enumerate(LY.TREES_WORLD):
        build_tree(f'Tree_W{i:02d}_{kind}', kind, (x, y, LY.BLOCK_Z), M, C_tr, size=size, seed=100 + i)
    for i, (x, y, r) in enumerate(LY.BUSHES):
        build_bush(f'Bush_{i:02d}', (x, y, LY.BLOCK_Z), M, C_tr, r=r, seed=200 + i)
    for i, pts in enumerate(LY.HEDGES):
        build_hedge(f'Hedge_{i}', [(x, y, LY.BLOCK_Z) for x, y in pts], M, C_tr, height=0.35, width=0.4, seed=300 + i)
    # Hecke an der Vorderecke (außen an der Straße)
    r = LY.CORNER_R
    hp = [(r + (r - 0.3) * math.cos(math.radians(a)), r + (r - 0.3) * math.sin(math.radians(a)), 0.1)
          for a in range(195, 262, 6)]
    build_hedge('Hedge_Front', hp, M, C_tr, height=0.5, width=0.6, seed=5)

    for name, kind, color, road, lane, pos, direction in LY.CARS:
        off = LY.LANE[lane]
        if road == 'L':
            loc, head = (off, pos, 0.03), math.pi / 2 if direction > 0 else -math.pi / 2
        else:
            loc, head = (pos, off, 0.03), 0.0 if direction > 0 else math.pi
        build_car(name, kind, color, loc, head, M, C_ve)

    for i, (sx, sy) in enumerate(LY.LAMPS_IMG):
        build_lamp(f'Lamp_{i}', LY.img2world(sx, sy), M, C_pr)
    for i, (sx, sy) in enumerate(LY.BOLLARDS_IMG):
        build_bollard(f'Bollard_{i}', LY.img2world(sx, sy), M, C_pr)

    setup_world_and_light(sc, M, C_lc)
    setup_camera(sc, C_lc)
    setup_render(sc, a)
    nverts = sum(len(o.data.vertices) for o in sc.objects if o.type == 'MESH')
    print(f'Szene gebaut: {len(sc.objects)} Objekte, {nverts} Vertices, {time.time() - t0:.1f}s')
    os.makedirs(os.path.dirname(a.blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=a.blend, compress=True)
    if not a.no_render:
        sc.render.filepath = a.out
        bpy.ops.render.render(write_still=True)
        print(f'Render: {a.out} ({time.time() - t0:.1f}s)')


if __name__ == '__main__':
    main()
