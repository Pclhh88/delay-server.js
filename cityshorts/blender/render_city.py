"""Blender-Einstieg: baut die Miniaturstadt aus plan.json und rendert Frames.

    # mit Blender-Programm
    blender -b --python cityshorts/blender/render_city.py -- build/rome/plan.json [Optionen]
    # oder mit dem bpy-Pythonmodul (pip install bpy)
    python cityshorts/blender/render_city.py build/rome/plan.json [Optionen]

Optionen:
    --frames A:B      nur diesen Frame-Bereich rendern
    --step N          nur jeden N-ten Frame (schnelle Vorschau)
    --stills 0,90,..  einzelne Frames
    --save-blend P    Szene als .blend speichern (zum Nachbearbeiten in Blender)
    --no-render       nur Szene bauen
"""
import argparse
import json
import math
import os
import random
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from cityshorts.blender import landmarks  # noqa: E402
from cityshorts.blender.kit import anim, camera, materials, stage, vehicles  # noqa: E402
from cityshorts.blender.kit.mesh import MeshBuilder  # noqa: E402
from cityshorts.blender.kit.world import World  # noqa: E402


def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--frames")
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--stills")
    ap.add_argument("--save-blend")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--quality")
    return ap.parse_args(argv)


def new_collection(name, parent=None, hidden=False):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    if hidden:
        c.hide_render = True
        c.hide_viewport = True
    return c


# ---------------------------------------------------------------------------
# Aktionen pro Sprechabschnitt (beat["actions"])
# ---------------------------------------------------------------------------
def act_bounce(lm, f0, f1, fps):
    anim.squash_bounce(lm["root"], f0 + 2, fps)


def act_coins(lm, f0, f1, fps):
    ex = lm["info"]["extras"]
    rng = random.Random(4)
    root = lm["root"]
    m = root.matrix_world
    src = m @ Vector(ex["throw_from"])
    for k, c in enumerate(ex["coins"]):
        c.parent = None
        bx, by, bz = ex["basin"]
        dst = m @ Vector((bx + rng.uniform(-2.5, 2.5), by + rng.uniform(-0.8, 1.2), bz))
        start = f0 + int(fps * (0.6 + k * 0.45))
        anim.throw(c, src + Vector((rng.uniform(-1.5, 1.5), 0, 0)), dst, start, start + int(fps * 0.8), apex=2.0)


def act_stones(lm, f0, f1, fps):
    rng = random.Random(9)
    for k, st in enumerate(lm["info"]["extras"]["stones"]):
        p0 = st.location.copy()
        start = f0 + int(fps * (1.0 + k * 0.35))
        out = p0 + Vector((rng.uniform(-6, -2), rng.uniform(-8, -4), rng.uniform(-1, 1)))
        anim.throw(st, p0, out, start, start + int(fps * 1.3), apex=3.5, spin=1.5)


def act_rain(lm, f0, f1, fps):
    ex = lm["info"]["extras"]
    cloud = ex["cloud"]
    cloud.parent = lm["root"]
    anim.visible_between(cloud, f0 + int(fps * 0.8), f1 + int(fps * 0.6), grow=10)
    ox, oy, oz = ex["oculus"]
    rng = random.Random(2)
    for k, d in enumerate(ex["drops"]):
        d.parent = lm["root"]
        t = f0 + int(fps * 1.2) + k * 3
        while t < f1:
            x, y = rng.uniform(-0.45, 0.45), rng.uniform(-0.45, 0.45)
            anim.throw(d, (ox + x, oy + y, oz + 3.0), (ox + x, oy + y, oz - 1.0), t, t + 9, apex=0, spin=0)
            t += 9 + rng.randint(4, 14)


ACTIONS = {"bounce": act_bounce, "coins": act_coins, "stones": act_stones, "rain": act_rain}


def make_pin(col):
    mb = MeshBuilder()
    mb.sphere((0, 0, 0.9), 0.45, "pin_red", seg=20, rings=12)
    mb.cyl((0, 0, 0), 0.05, 0.6, "pin_red", seg=16, r2=0.32)
    mb.sphere((0, 0, 1.0), 0.15, "white", seg=12, rings=8, s=(1, 0.3, 1))
    ob = mb.build("pin", col)
    ob.scale = (0, 0, 0)
    return ob


def animate_pin(pin, beats, lms, fps, n_frames):
    sched = []
    for b in beats:
        if b.get("pin") and b.get("focus") in lms:
            sched.append((int(b["t0"] * fps), int(b["t1"] * fps), lms[b["focus"]]))
    for f in range(0, n_frames, 2):
        s = 0.0
        pos = (0, 0, -50)
        for f0, f1, lm in sched:
            if f0 <= f <= f1:
                u_in = anim.back_out((f - f0 - 6) / 12) if f > f0 + 6 else 0.0
                u_out = max(0.0, min(1.0, (f1 - f) / 8))
                s = 1.6 * u_in * u_out
                x, y = lm["pos"]
                h = lm["info"]["height"]
                pos = (x, y, h + 0.8 + 0.3 * math.sin(f / fps * 4))
        pin.location = pos
        pin.scale = (s, s, s)
        pin.rotation_euler = (0, 0, f / fps * 1.5)
        pin.keyframe_insert("location", frame=f)
        pin.keyframe_insert("scale", frame=f)
        pin.keyframe_insert("rotation_euler", index=2, frame=f)


# ---------------------------------------------------------------------------
def build_scene(plan, quality):
    t_start = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    scene = bpy.context.scene
    city = plan["city"]
    fps, n = plan["fps"], plan["n_frames"]
    materials.set_palette(city.get("palette"))
    stage.setup(scene, fps, n, quality, plan.get("engine", "CYCLES"))

    lib = new_collection("LIBRARY", hidden=True)
    col_city = new_collection("CITY")
    col_lm = new_collection("LANDMARKS")

    # Wahrzeichen
    lms = {}
    for spec in city["landmarks"]:
        sub = new_collection("LM_" + spec["id"], col_lm)
        info = landmarks.build(spec["builder"], sub, spec)
        root = bpy.data.objects.new("ROOT_" + spec["id"], None)
        sub.objects.link(root)
        root.location = (*spec["pos"], 0)
        root.rotation_euler = (0, 0, math.radians(spec.get("rot", 0)))
        s = spec.get("scale", 1.0)
        root.scale = (s, s, s)
        for ob in sub.objects:
            if ob is not root and ob.parent is None:
                ob.parent = root
        info["height"] *= s
        info["radius"] *= s
        lms[spec["id"]] = {"root": root, "info": info, "pos": spec["pos"], "spec": spec}
    bpy.context.view_layer.update()

    # Welt (Insel, Straßen, Fluss, Häuser, Bäume)
    w = World(city["world"], col_city, [
        {"pos": s["pos"], "rot": s.get("rot", 0), "footprint": s["footprint"], "fp_center": s.get("fp_center", (0, 0))}
        for s in city["landmarks"]
    ]).build(lib)
    print(f"[scene] {len(w.houses)} Häuser, {len(w.trees)} Bäume, {len(lms)} Wahrzeichen")

    # Intro: Stadt baut sich auf
    intro = city.get("intro_build", {"start": 0.1, "dur": 2.2})
    t0, dur = intro["start"], intro["dur"]
    R = w.half * 1.42
    for ob in w.houses:
        d = ob.location.length / R
        anim.drop_in(ob, int((t0 + d * dur * 0.75) * fps), int(fps * 0.5))
    for ob in w.trees:
        d = ob.location.length / R
        anim.pop_in(ob, int((t0 + 0.3 + d * dur * 0.75) * fps), int(fps * 0.35))
    for k, lm in enumerate(lms.values()):
        anim.pop_in(lm["root"], int((t0 + dur * 0.55 + 0.15 * k) * fps), int(fps * 0.55))

    # Verkehr
    rng = random.Random(city["world"].get("seed", 1))
    car_lib = new_collection("LIB_cars", lib, hidden=False)
    car_lib.hide_render = True
    car_lib.hide_viewport = True
    for k in range(city["world"].get("cars", 16)):
        path = rng.choice(w.paths)
        if k == 0:
            mbo = vehicles.make_bus()
        else:
            mbo = vehicles.make_car(rng.choice(vehicles.CAR_COLORS))
        car = mbo.build(f"car_{k}", col_city, bevel=0.03)
        vehicles.animate_along(car, path, rng.uniform(0, path.length), rng.uniform(2.2, 3.6),
                               -w.road_w * 0.23, 0, n - 1, fps, z=w.road_z)
        anim.pop_in(car, int((t0 + dur) * fps) + k, int(fps * 0.3))

    materials.animate_water(0, n)

    # Aktionen + Pin
    for b in plan["beats"]:
        lm = lms.get(b.get("focus"))
        for a in b.get("actions", []):
            if lm and a in ACTIONS:
                ACTIONS[a](lm, int(b["t0"] * fps), int(b["t1"] * fps), fps)
    animate_pin(make_pin(col_city), plan["beats"], lms, fps, n)

    # Kamera
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.clip_start, cam_data.clip_end = 0.1, 2000
    cam_data.sensor_fit = "VERTICAL"
    cam_data.sensor_height = 24
    cam_data.dof.use_dof = True
    cam = bpy.data.objects.new("Cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    shots = []
    for b in plan["beats"]:
        sh = b["shot"]
        tgt = sh.get("target", b.get("focus", "island"))
        if tgt in lms:
            lm = lms[tgt]
            target = (*lm["pos"], lm["info"]["height"] * sh.get("look_height", 0.35))
            radius = lm["info"]["radius"]
        else:
            target, radius = (0, 0, 0), w.half
        shots.append(camera.Shot(b["t0"], b["t1"], target, radius, sh))
    track = camera.camera_track(shots, fps, n, plan.get("transition", 0.8))
    prev = None
    for f, (pos, look, lens, fstop) in enumerate(track):
        cam.location = pos
        q = (look - pos).to_track_quat("-Z", "Y")
        e = q.to_euler("XYZ", prev) if prev else q.to_euler("XYZ")
        prev = e
        cam.rotation_euler = e
        cam_data.lens = lens
        cam_data.dof.focus_distance = (look - pos).length
        cam_data.dof.aperture_fstop = fstop
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        cam_data.keyframe_insert("lens", frame=f)
        cam_data.dof.keyframe_insert("focus_distance", frame=f)
        cam_data.dof.keyframe_insert("aperture_fstop", frame=f)
    print(f"[scene] gebaut in {time.time() - t_start:.1f}s")
    return scene


def render(scene, out_dir, frames):
    os.makedirs(out_dir, exist_ok=True)
    for i, f in enumerate(frames):
        path = os.path.join(out_dir, f"{f:05d}.png")
        if os.path.exists(path):
            continue
        t = time.time()
        scene.frame_set(f)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print(f"[render] Frame {f} ({i + 1}/{len(frames)}) {time.time() - t:.1f}s", flush=True)


def main():
    a = _args()
    plan = json.load(open(a.plan))
    quality = a.quality or plan.get("quality", "preview")
    scene = build_scene(plan, quality)
    if a.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.save_blend))
    if a.no_render:
        return
    n = plan["n_frames"]
    if a.stills:
        frames = [int(x) for x in a.stills.split(",")]
        out = plan["out_dir"] + "/stills_" + quality
    else:
        f0, f1 = (int(x) for x in a.frames.split(":")) if a.frames else (0, n)
        frames = list(range(f0, min(f1, n), a.step))
        out = plan["out_dir"] + "/frames_" + quality
    render(scene, out, frames)


if __name__ == "__main__":
    main()
