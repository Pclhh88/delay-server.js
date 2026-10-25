"""Hochwertiges Standbild einer Diorama-Kachel (Qualitätsabgleich mit B2).

    python cityshorts/blender/diorama_still.py OUT.png [--city rome --tile colosseum]
        [--percent 100] [--samples 256] [--az .. --el .. --lens .. --dist ..] [--seed ..]
        [--save-blend scene.blend]

Die Kachel-Konfiguration (Wahrzeichen, Plätze, Gasse, Park, Sonderbauten,
Kamera) steht in cities/<stadt>/city.json -> "tiles". Neue Stadt/Kachel =
neuer Eintrag dort, kein Code.
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from cityshorts.blender import landmarks  # noqa: E402
from cityshorts.blender.kit import materials, stage  # noqa: E402
from cityshorts.blender.kit.diorama import Diorama  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load_tile(city, tile_id):
    """Kachel-Konfiguration aus cities/<stadt>/city.json -> "tiles"."""
    import json
    cfg = json.load(open(os.path.join(ROOT, "cities", city, "city.json")))
    for t in cfg.get("tiles", []):
        if t["id"] == tile_id:
            return t
    raise SystemExit(f"Kachel {tile_id} nicht in cities/{city}/city.json")


def build_tile(col, cfg, seed, cam_dir):
    lm = cfg["landmark"]
    lm_col = bpy.data.collections.new("LANDMARK")
    col.children.link(lm_col)
    landmarks.build(lm["builder"], lm_col, {"id": "landmark"})
    root = bpy.data.objects.new("ROOT_landmark", None)
    lm_col.objects.link(root)
    root.scale = (lm["scale"],) * 3
    root.location = (*lm["pos"], 0.1)
    root.rotation_euler = (0, 0, math.radians(lm["rot"]))
    for ob in lm_col.objects:
        if ob is not root and ob.parent is None:
            ob.parent = root
    city = bpy.data.collections.new("CITY")
    col.children.link(city)
    d = Diorama(city, family=cfg["family"], seed=seed, hx=cfg["hx"], hy=cfg["hy"], corner=cfg["corner"],
                hero={"pos": tuple(lm["pos"]), "ellipse": tuple(lm["ellipse"]), "rot": lm["rot"]},
                plazas=[tuple(p) for p in cfg.get("plazas", [])],
                alleys=[([tuple(q) for q in pts], w) for pts, w in cfg.get("alleys", [])],
                park=tuple(cfg["park"]) if cfg.get("park") else None, camera_dir=cam_dir,
                specials_spec=cfg.get("specials", []), composition=cfg.get("composition")).build()
    return d


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--percent", type=int, default=100)
    ap.add_argument("--samples", type=int, default=256)
    ap.add_argument("--az", type=float)
    ap.add_argument("--el", type=float)
    ap.add_argument("--lens", type=float)
    ap.add_argument("--dist", type=float)
    ap.add_argument("--target", type=float, nargs=3)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--city", default="rome")
    ap.add_argument("--tile", default="colosseum")
    ap.add_argument("--save-blend")
    ap.add_argument("--vignette", type=float)
    a = ap.parse_args(argv)
    cfg = load_tile(a.city, a.tile)
    for k, v in cfg.get("camera", {}).items():
        if k != "fstop" and getattr(a, k, None) is None:
            setattr(a, k, v)
    if a.seed is None:
        a.seed = cfg.get("seed", 1)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    materials.set_palette(cfg.get("palette"))
    if cfg.get("mute"):
        materials.mute(amount=cfg["mute"])
    sc = bpy.context.scene
    stage.setup(sc, 30, 1, "final")
    stage.still_look(sc, a.samples, a.percent)
    az, el = math.radians(a.az), math.radians(a.el)
    d = build_tile(sc.collection, cfg, a.seed, (math.cos(az), math.sin(az)))
    n_obj = len([o for o in sc.objects])
    print(f"[diorama] {len(d.houses)} Gebäude, {len(d.trees)} Bäume, {len(d.people)} Personen, "
          f"{len(d.cars)} Autos, {n_obj} Objekte gesamt")

    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = a.lens
    cam_d.sensor_fit = "VERTICAL"
    cam_d.sensor_height = 24
    cam_d.clip_end = 2000
    cam = bpy.data.objects.new("cam", cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    tgt = Vector(a.target)
    cam.location = tgt + Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))) * a.dist
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_d.dof.use_dof = True
    lm = cfg["landmark"]
    focus = Vector((*lm["pos"], 1.5))
    cam_d.dof.focus_distance = (cam.location - focus).length
    cam_d.dof.aperture_fstop = cfg.get("camera", {}).get("fstop", 4.0)

    if a.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.save_blend))
    raw = os.path.abspath(a.out.replace(".png", "_raw.png"))
    sc.render.filepath = raw
    bpy.ops.render.render(write_still=True)
    from PIL import Image
    from cityshorts.grade import grade
    gcfg = dict(cfg.get("grade", {}))
    if a.vignette is not None:
        gcfg["vignette"] = a.vignette
    grade(Image.open(raw), **gcfg).save(os.path.abspath(a.out))
    print("[diorama] gespeichert", a.out)


if __name__ == "__main__":
    main()
