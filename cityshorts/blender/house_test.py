"""Studio-Test für Detail-Häuser (Abgleich mit dem Referenzbild).

    python cityshorts/blender/house_test.py OUT.png [--percent 50] [--samples 32] [--az -55]
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from cityshorts.blender.kit import stage, vegetation, vehicles  # noqa: E402
from cityshorts.blender.kit.house_detail import build_house  # noqa: E402
from cityshorts.blender.kit.mesh import MeshBuilder, rounded_rect  # noqa: E402
from cityshorts.blender.kit.props import lamp  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--percent", type=int, default=50)
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--az", type=float, default=-58)
    ap.add_argument("--el", type=float, default=30)
    ap.add_argument("--style2", default="haussmann_red")
    a = ap.parse_args(argv)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    stage.setup(sc, 30, 1, "preview")
    sc.render.resolution_percentage = a.percent
    sc.cycles.samples = a.samples
    col = sc.collection

    # Bürgersteig-Kachel + Straße
    mb = MeshBuilder()
    mb.polygon_prism(rounded_rect(9.5, 6.4, 0.6), -0.4, 0.4, "sidewalk")
    mb.polygon_prism(rounded_rect(9.0, 5.9, 0.4), 0.0, 0.06, "sidewalk")
    mb.box((0.0, -2.75, 0.03), (9.4, 0.04, 0.06), "stone_light")
    mb.build("tile", col, bevel=0.02)
    road = MeshBuilder()
    road.box((0, -4.6, -0.02), (12, 2.6, 0.04), "asphalt")
    for i in range(8):
        road.box((-5 + i * 1.4, -4.6, 0.005), (0.6, 0.06, 0.01), "road_line")
    road.build("road", col)

    # Haus 1: Eckhaus mit abgeschrägter Ecke (wie im Referenzbild)
    corner = [(-1.6, -1.3), (1.05, -1.3), (1.6, -0.75), (1.6, 1.3), (-1.6, 1.3)]
    h1, _ = build_house(corner, "haussmann", blind=[4], seed=1, name="house_corner", collection=col)
    h1.location = (0.9, 0.2, 0.06)
    # Haus 2: niedrigeres Nachbarhaus mit rötlichem Mansarddach
    nb = [(-2.2, -1.3), (0.0, -1.3), (0.0, 1.3), (-2.2, 1.3)]
    h2, _ = build_house(nb, a.style2, blind=[1, 3], seed=2, name="house_neighbor", collection=col)
    h2.location = (-0.7, 0.2, 0.06)

    # Requisiten
    trees = bpy.data.collections.new("trees")
    sc.collection.children.link(trees)
    t = vegetation.make_tree("round", 3).build("tree", col)
    t.location = (-3.6, -2.2, 0.06)
    t2 = vegetation.make_tree("autumn", 5).build("tree2", col)
    t2.location = (3.6, -2.3, 0.06)
    lm = MeshBuilder()
    lamp(lm, 1.6, -2.4, 0.06)
    lm.build("lamp", col)
    car = vehicles.make_car("car_cream").build("car", col, bevel=0.02)
    car.location = (-1.0, -4.2, 0.0)
    van = vehicles.make_car("car_blue").build("car2", col, bevel=0.02)
    van.location = (2.6, -5.0, 0.0)
    van.rotation_euler = (0, 0, math.pi)

    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = 70
    cam_d.sensor_fit = "VERTICAL"
    cam_d.sensor_height = 24
    cam_d.dof.use_dof = True
    cam_d.dof.aperture_fstop = 1.2
    cam = bpy.data.objects.new("cam", cam_d)
    col.objects.link(cam)
    sc.camera = cam
    tgt = Vector((0.0, -0.6, 1.9))
    az, el, d = math.radians(a.az), math.radians(a.el), 24
    cam.location = tgt + Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))) * d
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_d.dof.focus_distance = d
    sc.render.filepath = os.path.abspath(a.out)
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
