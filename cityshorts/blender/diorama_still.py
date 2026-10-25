"""Hochwertiges Standbild einer Diorama-Kachel (Qualitätsabgleich mit B2).

    python cityshorts/blender/diorama_still.py OUT.png [--percent 100] [--samples 256]
        [--az -135 --el 34 --lens 85] [--family rome] [--seed 3] [--save-blend scene.blend]
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from cityshorts.blender import landmarks  # noqa: E402
from cityshorts.blender.kit import stage  # noqa: E402
from cityshorts.blender.kit.diorama import Diorama  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--percent", type=int, default=100)
    ap.add_argument("--samples", type=int, default=256)
    ap.add_argument("--az", type=float, default=-128)
    ap.add_argument("--el", type=float, default=33)
    ap.add_argument("--lens", type=float, default=85)
    ap.add_argument("--dist", type=float, default=215)
    ap.add_argument("--family", default="rome")
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--save-blend")
    ap.add_argument("--lm-rot", type=float, default=20)
    a = ap.parse_args(argv)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    stage.setup(sc, 30, 1, "final")
    stage.still_look(sc, a.samples, a.percent)
    col = sc.collection

    lm_col = bpy.data.collections.new("LANDMARK")
    col.children.link(lm_col)
    info = landmarks.build("rome.colosseum", lm_col, {"id": "colosseum"})
    root = bpy.data.objects.new("ROOT_colosseum", None)
    lm_col.objects.link(root)
    s = 0.78
    root.scale = (s, s, s)
    root.location = (0.3, 0.6, 0.1)
    root.rotation_euler = (0, 0, math.radians(a.lm_rot))
    for ob in lm_col.objects:
        if ob is not root and ob.parent is None:
            ob.parent = root

    d = Diorama(col, family=a.family, seed=a.seed, hero_ellipse=(8.0 * s + 1.0, 6.6 * s + 1.0)).build()
    # Grün: Schirmpinien + Laubbäume auf Plätzen und in Höfen
    d.fill_greenery(n=34, avoid_ellipse=(8.0 * s + 0.9, 6.6 * s + 0.9), pines=8)
    from cityshorts.blender.kit import props
    from cityshorts.blender.kit.mesh import MeshBuilder
    ppl = MeshBuilder()
    ea, eb = 8.0 * s + 0.3, 6.6 * s + 0.3
    props.crowd(ppl, 0, 0, 9.0, 70, 5, z=0.1, avoid=lambda x, y: (x / ea) ** 2 + (y / eb) ** 2 < 1
                or any(math.hypot(x - fx, y - fy) < fr + 0.2 for fx, fy, fr in d.footprints))
    ppl.build("plaza_people", col)
    print(f"[diorama] {d.n_house} Häuser")

    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = a.lens
    cam_d.sensor_fit = "VERTICAL"
    cam_d.sensor_height = 24
    cam_d.clip_end = 2000
    cam = bpy.data.objects.new("cam", cam_d)
    col.objects.link(cam)
    sc.camera = cam
    tgt = Vector((0.0, 0.0, 3.2))
    az, el = math.radians(a.az), math.radians(a.el)
    cam.location = tgt + Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))) * a.dist
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_d.dof.use_dof = True
    cam_d.dof.focus_distance = a.dist
    cam_d.dof.aperture_fstop = 4.0

    if a.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.save_blend))
    raw = os.path.abspath(a.out.replace(".png", "_raw.png"))
    sc.render.filepath = raw
    bpy.ops.render.render(write_still=True)
    from PIL import Image
    from cityshorts.grade import grade
    grade(Image.open(raw)).save(os.path.abspath(a.out))
    print("[diorama] gespeichert", a.out)


if __name__ == "__main__":
    main()
