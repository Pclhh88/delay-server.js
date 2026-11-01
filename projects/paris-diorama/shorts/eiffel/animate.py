"""Baut die Animation in paris_city.blend auf und rendert Einzelbilder (9:16).

  python shorts/eiffel/animate.py [--res 540] [--samples 12] [--every 1] [--frames 0-815] [--stills 1.0,5.0]
Ausgabe: shorts/eiffel/frames/f0000.png …, Blend: shorts/eiffel/eiffel_short.blend
"""
import argparse, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import timeline as TL  # noqa: E402


def interp(keys, t):
    if t <= keys[0][0]:
        return keys[0][1:]
    for a, b in zip(keys, keys[1:]):
        if t <= b[0]:
            u = (t - a[0]) / (b[0] - a[0])
            u = u * u * (3 - 2 * u)  # weich ein-/ausblenden
            return tuple(x + (y - x) * u for x, y in zip(a[1:], b[1:]))
    return keys[-1][1:]


def add_reveal(mat):
    """Turm-Material: oberhalb der Schwelle transparent, an der Schwelle leuchtende Baukante."""
    nt = mat.node_tree
    out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    src = out.inputs['Surface'].links[0].from_socket
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sep.inputs['Vector'])
    thr = nt.nodes.new('ShaderNodeValue')
    thr.name = 'RevealThreshold'
    diff = nt.nodes.new('ShaderNodeMath'); diff.operation = 'SUBTRACT'
    nt.links.new(sep.outputs['Z'], diff.inputs[0]); nt.links.new(thr.outputs[0], diff.inputs[1])
    hide = nt.nodes.new('ShaderNodeMath'); hide.operation = 'GREATER_THAN'; hide.inputs[1].default_value = 0.0
    nt.links.new(diff.outputs[0], hide.inputs[0])
    band = nt.nodes.new('ShaderNodeMapRange')  # Glühen 0..1 knapp unterhalb der Schwelle
    band.inputs['From Min'].default_value = -0.35; band.inputs['From Max'].default_value = 0.0
    band.inputs['To Min'].default_value = 0.0; band.inputs['To Max'].default_value = 1.0
    nt.links.new(diff.outputs[0], band.inputs['Value'])
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (1.0, 0.55, 0.15, 1); em.inputs['Strength'].default_value = 25.0
    glow = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(band.outputs['Result'], glow.inputs['Fac'])
    nt.links.new(src, glow.inputs[1]); nt.links.new(em.outputs[0], glow.inputs[2])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(hide.outputs[0], mix.inputs['Fac'])
    nt.links.new(glow.outputs[0], mix.inputs[1]); nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    return thr


def ring_obj(name, z, coll):
    me = bpy.data.meshes.new(name)
    seg, r, w = 64, 1.0, 0.05
    v = [(math.cos(2 * math.pi * i / seg) * rr, math.sin(2 * math.pi * i / seg) * rr, 0) for rr in (r - w, r + w)
         for i in range(seg)]
    f = [(i, (i + 1) % seg, seg + (i + 1) % seg, seg + i) for i in range(seg)]
    me.from_pydata(v, [], f)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (0.55, 0.85, 1.0, 1)
    em.inputs['Strength'].default_value = 12.0
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader'); mix.name = 'Fade'
    nt.links.new(em.outputs[0], mix.inputs[1]); nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob, mix


def setup(res, samples):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(PROJECT, 'paris_city.blend'))
    sc = bpy.context.scene
    fps = TL.FPS
    sc.render.fps = fps
    sc.frame_start, sc.frame_end = 0, int(TL.DURATION * fps) - 1
    tower = bpy.data.objects['EiffelTower']
    top = tower.matrix_world @ Vector((0, 0, TL.TOWER_TOP))
    thrs = [add_reveal(m) for m in tower.data.materials]
    coll = bpy.data.collections.new('Short_FX')
    sc.collection.children.link(coll)
    rings = [ring_obj(f'Wave_{i}', top.z, coll) for i in range(len(TL.WAVES))]
    # Antennenlicht
    glow = bpy.data.objects.new('Antenna_Glow', bpy.data.lights.new('Antenna_Glow', 'POINT'))
    glow.data.color = (0.55, 0.85, 1.0)
    glow.data.shadow_soft_size = 0.2
    glow.location = top + Vector((0, 0, 0.1))
    coll.objects.link(glow)
    # Kamera 9:16 an einem Drehpunkt
    piv = bpy.data.objects.new('Cam_Pivot', None)
    coll.objects.link(piv)
    cam = bpy.data.objects.new('Camera_Short', bpy.data.cameras.new('Camera_Short'))
    cam.data.lens = 50
    cam.data.sensor_fit = 'VERTICAL'
    cam.data.sensor_height = 36
    cam.data.clip_end = 3000
    coll.objects.link(cam)
    sc.camera = cam
    center = Vector((15.0, 15.0, 0.0))     # zwischen Diorama-Mitte und Turm: Turm steht im Bildzentrum
    for f in range(sc.frame_start, sc.frame_end + 1):
        t = f / fps
        th = interp(TL.REVEAL, t)[0]
        for n in thrs:
            n.outputs[0].default_value = th
            n.outputs[0].keyframe_insert('default_value', frame=f)
        az, dist, tz = interp(TL.CAMERA, t)
        a = math.radians(az - 90)          # Blickrichtung wie die Referenzkamera (Yaw -47° = von vorne)
        el = math.radians(32)
        tgt = center + Vector((0, 0, tz))
        cam.location = tgt + Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el))) * dist
        cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.keyframe_insert('location', frame=f)
        cam.keyframe_insert('rotation_euler', frame=f)
        for (ob, mix), t0 in zip(rings, TL.WAVES):
            u = (t - t0) / 2.2
            vis = 0.0 <= u <= 1.0
            s = 0.3 + 7.0 * max(0.0, min(1.0, u))
            ob.location = top + Vector((0, 0, -0.6 * max(0.0, min(1.0, u))))
            ob.scale = (s, s, s)
            mix.inputs['Fac'].default_value = (u if vis else 1.0)
            ob.hide_render = not vis
            ob.keyframe_insert('location', frame=f)
            ob.keyframe_insert('scale', frame=f)
            ob.keyframe_insert('hide_render', frame=f)
            mix.inputs['Fac'].keyframe_insert('default_value', frame=f)
        a0, a1 = TL.ANTENNA_GLOW
        glow.data.energy = 60.0 * (1.0 if a0 <= t <= a1 else 0.0) * (0.75 + 0.25 * math.sin(t * 9))
        glow.data.keyframe_insert('energy', frame=f)
    # konstante Interpolation (Werte sind schon je Frame gesetzt)
    for ad in [cam.animation_data] + [o.animation_data for o, _ in rings] + [glow.data.animation_data] + \
              [m.node_tree.animation_data for m in tower.data.materials] + \
              [m.node_tree.animation_data for _, mx in rings for m in [mx.id_data] if False]:
        if ad and ad.action:
            for fc in getattr(ad.action, 'fcurves', []):
                for k in fc.keyframe_points:
                    k.interpolation = 'CONSTANT'
    sc.render.resolution_x, sc.render.resolution_y = res, int(res * 16 / 9)
    sc.render.resolution_percentage = 100
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.use_persistent_data = True
    sc.cycles.transparent_max_bounces = 256   # aufgelöster Turm: viele transparente Stäbe hintereinander
    sc.cycles.max_bounces = 260
    sc.render.image_settings.file_format = 'PNG'
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'eiffel_short.blend'), compress=True)
    return sc


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--res', type=int, default=540)
    ap.add_argument('--samples', type=int, default=12)
    ap.add_argument('--every', type=int, default=1)
    ap.add_argument('--frames', default='')
    ap.add_argument('--stills', default='')
    a = ap.parse_args(argv)
    sc = setup(a.res, a.samples)
    outdir = os.path.join(HERE, 'frames')
    os.makedirs(outdir, exist_ok=True)
    if a.stills:
        frames = [int(float(s) * TL.FPS) for s in a.stills.split(',')]
        outdir = os.path.join(HERE, 'stills')
        os.makedirs(outdir, exist_ok=True)
    else:
        f0, f1 = (map(int, a.frames.split('-')) if a.frames else (sc.frame_start, sc.frame_end))
        frames = range(f0, f1 + 1, a.every)
    for f in frames:
        p = os.path.join(outdir, f'f{f:04d}.png')
        if os.path.exists(p) and not a.stills:
            continue  # Wiederaufnahme nach Abbruch
        sc.frame_set(f)
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        print('FRAME', f, flush=True)


if __name__ == '__main__':
    main()
