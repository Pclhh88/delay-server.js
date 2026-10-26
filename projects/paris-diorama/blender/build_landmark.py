"""Qualitäts-Benchmark: Gebäude F (Kuppel-Mansardhaus rechts neben dem Eiffelturm) als Einzelmodell.

  python blender/build_landmark.py [--res 1600] [--samples 160] [--views closeup,orbit]

Erzeugt landmark_f.blend und
  renders/landmark_closeup.png   gleiche Kamera wie die Vorlage, auf das Gebäude zugeschnitten
  renders/landmark_orbit.png     zweite Ansicht (von rechts unten, andere Seite des Modells)
  renders/landmark_mask.png      Silhouette für den Umrissvergleich
Vergleich (lokal, enthält die Vorlage): renders/compare_landmark_*.png
"""
import argparse, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from diorama import landmark as LM  # noqa: E402

PROJECT = os.path.dirname(HERE)
CAM = json.load(open(os.path.join(HERE, 'camera.json')))
LOCATION = (17.75, 6.82, 0.12)   # vordere Grundriss-Ecke von Gebäude F in der Szene (Blockout-Messung)
CROP = (1210, 605, 660)          # Ausschnitt der Vorlage: x0, y0, Kantenlänge (px, 2048er Bild)


def setup_world(sc):
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
    d = Vector((0.05, -0.8, 0.55)).normalized()   # Licht von rechts vorne oben wie in der Vorlage
    sun.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sc.collection.objects.link(sun)
    fill = bpy.data.objects.new('Area_Fill', bpy.data.lights.new('Area_Fill', 'AREA'))
    fill.data.energy = 3500
    fill.data.size = 40
    fill.data.color = (1.0, 0.95, 0.88)
    fill.location = (-25, -10, 30)
    fill.rotation_euler = (Vector((20, 9, 3)) - fill.location).to_track_quat('-Z', 'Y').to_euler()
    sc.collection.objects.link(fill)


def setup_ground(sc, M):
    me = bpy.data.meshes.new('Studio_Floor')
    s = 400
    me.from_pydata([(-s, -s, -0.3), (s, -s, -0.3), (s, s, -0.3), (-s, s, -0.3)], [], [(0, 1, 2, 3)])
    fm = bpy.data.materials.new('floor')
    fm.use_nodes = True
    fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (1.0, 0.88, 0.7, 1)
    fm.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (1.0, 0.88, 0.7, 1)
    # heller Studiohintergrund: leuchtet nur für Kamerastrahlen, beleuchtet das Haus also nicht
    lp = fm.node_tree.nodes.new('ShaderNodeLightPath')
    mul = fm.node_tree.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = 2.4
    fm.node_tree.links.new(lp.outputs['Is Camera Ray'], mul.inputs[0])
    fm.node_tree.links.new(mul.outputs[0], fm.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'])
    fm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.95
    me.materials.append(fm)
    sc.collection.objects.link(bpy.data.objects.new('Studio_Floor', me))
    # Gehwegplatte um das Haus (wie in der Szene)
    me = bpy.data.meshes.new('Sidewalk')
    x0, y0, x1, y1 = LOCATION[0] - 2.5, LOCATION[1] - 2.5, LOCATION[0] + LM.LX + 2.5, LOCATION[1] + LM.LY + 2.5
    z = LOCATION[2]
    v = [(x0, y0, -0.3), (x1, y0, -0.3), (x1, y1, -0.3), (x0, y1, -0.3), (x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
    f = [(4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me.from_pydata(v, [], f)
    me.materials.append(M['ground'])
    sc.collection.objects.link(bpy.data.objects.new('Sidewalk', me))


def cam_reference_crop(sc):
    """Referenzkamera, nur Bildausschnitt verändert (Brennweite + Shift) -> exakt dieselbe Perspektive."""
    x0, y0, S = CROP
    R = CAM['resolution']
    fsx = ((R / 2 + R * CAM['shift_x'] - x0) / S - 0.5)
    fsy = -((R / 2 - R * CAM['shift_y'] - y0) / S - 0.5)
    cam = bpy.data.objects.new('Camera_Closeup', bpy.data.cameras.new('Camera_Closeup'))
    cam.location = CAM['location']
    cam.rotation_euler = (CAM['pitch'], CAM['roll'], CAM['yaw'])
    cam.data.lens = CAM['lens'] * R / S
    cam.data.sensor_width = CAM['sensor']
    cam.data.sensor_fit = 'HORIZONTAL'
    cam.data.shift_x = -fsx
    cam.data.shift_y = -fsy
    cam.data.clip_end = 2000
    sc.collection.objects.link(cam)
    return cam


def cam_orbit(sc):
    """Zweite Ansicht: von rechts vorne, tief – zeigt rechte und hintere Fassade."""
    tgt = Vector(LOCATION) + Vector((LM.LX * 0.55, LM.LY * 0.45, 3.1))
    d = Vector((0.5, -0.82, 0.28)).normalized()
    cam = bpy.data.objects.new('Camera_Orbit', bpy.data.cameras.new('Camera_Orbit'))
    cam.location = tgt + d * 30
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 85
    cam.data.sensor_width = 36
    cam.data.clip_end = 2000
    sc.collection.objects.link(cam)
    return cam


def render(sc, cam, path, res, samples):
    sc.camera = cam
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.view_settings.exposure = -0.6
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def render_mask(sc, cam, path, res, root):
    """Silhouette des Gebäudes (weiß auf transparent)."""
    keep = {root.name} | {c.name for c in root.children}
    hidden = []
    for o in sc.objects:
        if o.type in ('MESH',) and o.name not in keep:
            o.hide_render = True
            hidden.append(o)
    sc.camera = cam
    sc.render.film_transparent = True
    sc.cycles.samples = 4
    sc.cycles.use_denoising = False
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    for o in hidden:
        o.hide_render = False
    sc.render.film_transparent = False


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--res', type=int, default=1600)
    ap.add_argument('--samples', type=int, default=160)
    ap.add_argument('--views', default='closeup,orbit')
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    coll = bpy.data.collections.new('Landmark_F')
    sc.collection.children.link(coll)
    root, M = LM.build_landmark(coll, LOCATION)
    setup_world(sc)
    setup_ground(sc, M)
    c1 = cam_reference_crop(sc)
    c2 = cam_orbit(sc)
    sc.camera = c1
    nv = sum(len(o.data.vertices) for o in coll.objects if o.type == 'MESH')
    print(f'Modell: {len(root.children)} Teile, {nv} Vertices')
    sc.render.resolution_x = sc.render.resolution_y = a.res
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PROJECT, 'landmark_f.blend'), compress=True)
    out = os.path.join(PROJECT, 'renders')
    if 'closeup' in a.views:
        render(sc, c1, os.path.join(out, 'landmark_closeup.png'), a.res, a.samples)
        render_mask(sc, c1, os.path.join(out, 'landmark_mask.png'), a.res, root)
    if 'orbit' in a.views:
        render(sc, c2, os.path.join(out, 'landmark_orbit.png'), a.res, a.samples)


if __name__ == '__main__':
    main()
