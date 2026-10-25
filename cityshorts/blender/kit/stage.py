"""Licht, Hintergrund, Render-Einstellungen (Qualitätsstufen)."""
import math

import bpy

from . import materials
from .mesh import MeshBuilder

QUALITY = {
    #           Auflösung %, Samples, Bewegungsunschärfe
    "draft":   {"percent": 25, "samples": 6, "motion_blur": False, "bounces": 3},
    "preview": {"percent": 50, "samples": 12, "motion_blur": False, "bounces": 4},
    "final":   {"percent": 100, "samples": 48, "motion_blur": True, "bounces": 6},
}


def setup(scene, fps, n_frames, quality="preview", engine="CYCLES", backdrop_col=None):
    q = QUALITY[quality]
    r = scene.render
    r.resolution_x, r.resolution_y = 1080, 1920
    r.resolution_percentage = q["percent"]
    r.fps = fps
    scene.frame_start, scene.frame_end = 0, n_frames - 1
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.use_motion_blur = q["motion_blur"]
    if engine == "CYCLES":
        r.engine = "CYCLES"
        c = scene.cycles
        c.device = "GPU" if _has_gpu() else "CPU"
        c.samples = q["samples"]
        c.use_adaptive_sampling = True
        c.use_denoising = True
        c.max_bounces = q["bounces"]
        c.diffuse_bounces = 2
        c.glossy_bounces = 2
        c.transparent_max_bounces = 4
        c.caustics_reflective = c.caustics_refractive = False
        r.use_persistent_data = True
    else:
        r.engine = "BLENDER_EEVEE"
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass

    # Welt: warmer, heller Studio-Hintergrund wie bei Miniatur-Renderings
    world = bpy.data.worlds.new("World")
    scene.world = world
    try:
        world.use_nodes = True
    except Exception:
        pass
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.82, 0.74, 0.62, 1)
    bg.inputs["Strength"].default_value = 0.55

    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 4.2
    sun_data.angle = math.radians(6)
    sun_data.color = (1.0, 0.93, 0.83)
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.rotation_euler = (math.radians(42), math.radians(8), math.radians(-35))
    scene.collection.objects.link(sun)

    mb = MeshBuilder()
    mb.box((0, 0, -2.7), (600, 600, 0.1), "backdrop")
    mb.build("backdrop", scene.collection)


def _has_gpu():
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for t in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
            try:
                prefs.compute_device_type = t
                prefs.get_devices()
                if any(d.type == t for d in prefs.devices):
                    for d in prefs.devices:
                        d.use = True
                    return True
            except TypeError:
                continue
    except Exception:
        pass
    return False


def still_look(scene, samples=256, percent=100):
    """Einstellungen für Diorama-Standbilder: mehr Samples/Bounces, warmes
    Streiflicht von vorne links, weicher Schatten, warme Umgebung."""
    from mathutils import Vector
    c = scene.cycles
    c.samples = samples
    c.max_bounces = 8
    c.diffuse_bounces = 4
    c.glossy_bounces = 3
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.01
    scene.render.resolution_percentage = percent
    scene.render.use_motion_blur = False
    try:
        scene.view_settings.look = "AgX - Base Contrast"
    except TypeError:
        pass
    scene.view_settings.exposure = 0.15
    bg = scene.world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.95, 0.86, 0.74, 1)
    bg.inputs["Strength"].default_value = 0.55
    sun = bpy.data.objects["Sun"]
    sun.data.energy = 5.2
    sun.data.angle = math.radians(3.5)
    sun.data.color = (1.0, 0.88, 0.74)
    az, el = math.radians(-165), math.radians(38)
    d = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    sun.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
