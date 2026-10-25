"""Hochwertigere Detail-Requisiten für Diorama-Ansichten:
buschige Bäume (verschobene Kugeln = Blumenkohl-Krone wie im Referenzbild),
Hecken, abgerundete Autos/Lieferwagen, Pariser/Römische Laternen, Poller."""
import math
import random

import bpy

from .mesh import MeshBuilder

_TEX = {}


def _clouds(scale):
    key = round(scale, 3)
    if key not in _TEX:
        t = bpy.data.textures.new(f"clouds_{key}", "CLOUDS")
        t.noise_scale = scale
        t.noise_depth = 2
        _TEX[key] = t
    return _TEX[key]


def _displace(ob, strength, scale, subdiv=0):
    if subdiv:
        m = ob.modifiers.new("Subdiv", "SUBSURF")
        m.levels = m.render_levels = subdiv
    d = ob.modifiers.new("Displace", "DISPLACE")
    d.texture = _clouds(scale)
    d.texture_coords = "LOCAL"
    d.strength = strength
    d.mid_level = 0.5


def fluffy_tree(name, col, seed, leaf="leaf", size=1.0, shape="round"):
    """Laubbaum mit sichtbarem Stamm/Ästen und unregelmäßiger, buschiger Krone."""
    rng = random.Random(seed)
    trunk = MeshBuilder()
    h = (0.9 + rng.uniform(0, 0.35)) * size * (1.6 if shape == "umbrella" else 1.0)
    trunk.cyl((0, 0, 0), 0.06 * size, h, "trunk", seg=8, r2=0.035 * size)
    for k in range(3):  # Hauptäste
        a = rng.uniform(0, 2 * math.pi)
        trunk.cyl((0, 0, h * 0.75), 0.025 * size, 0.45 * size, "trunk", seg=6, r2=0.012,
                  rx=math.cos(a) * 0.6, ry=math.sin(a) * 0.6)
    tob = trunk.build(name + "_trunk", col)
    crown = MeshBuilder()
    cz = h + 0.35 * size
    n = rng.randint(5, 8)
    for k in range(n):
        if shape == "umbrella":  # römische Schirmpinie
            a = rng.uniform(0, 2 * math.pi)
            rr = rng.uniform(0.1, 0.5) * size
            x, y, z = rr * math.cos(a), rr * math.sin(a), cz + 0.5 * size + rng.uniform(-0.05, 0.08) * size
            r = rng.uniform(0.35, 0.5) * size
            crown.sphere((x, y, z), r, leaf, ico=3, s=(1, 1, 0.45))
            continue
        if shape == "tall":
            x, y, z = rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15), cz + k / n * 0.9 * size
            r = (0.35 - 0.15 * k / n) * size
        else:
            a = rng.uniform(0, 2 * math.pi)
            rr = rng.uniform(0.0, 0.32) * size
            x, y, z = rr * math.cos(a), rr * math.sin(a), cz + rng.uniform(-0.12, 0.3) * size
            r = rng.uniform(0.28, 0.42) * size
        crown.sphere((x, y, z), r, leaf, ico=3, s=(1, 1, 0.9))
    cob = crown.build(name + "_crown", col)
    _displace(cob, 0.16 * size, 0.09 * size)
    d2 = cob.modifiers.new("Displace_fine", "DISPLACE")
    d2.texture = _clouds(0.025 * size)
    d2.texture_coords = "LOCAL"
    d2.strength = 0.05 * size
    cob.parent = tob
    return tob


def hedge(name, col, length, seed=0, h=0.3, w=0.3):
    mb = MeshBuilder()
    n = max(1, int(length / 0.25))
    for i in range(n):
        x = -length / 2 + (i + 0.5) * length / n
        mb.sphere((x, 0, h * 0.55), max(w, h) * 0.6, "hedge", ico=3, s=(1.1, w / max(w, h), h / max(w, h)))
    ob = mb.build(name, col)
    _displace(ob, 0.07, 0.05)
    return ob


def car(name, col, color, kind="hatch", seed=0):
    mb = MeshBuilder()
    L, W = (1.0, 0.46) if kind != "van" else (1.15, 0.5)
    # Karosserie unten
    mb.box_on(0, 0, 0.09, L, W, 0.24 if kind != "van" else 0.3, color)
    if kind == "van":
        mb.box_on(-0.12, 0, 0.39, L * 0.72, W * 0.98, 0.3, color)
        mb.loft([(0.24 - 0.0, -W * 0.48), (0.42, -W * 0.46), (0.42, W * 0.46), (0.24, W * 0.48)], 0.39,
                [(0.24, -W * 0.48), (0.26, -W * 0.46), (0.26, W * 0.46), (0.24, W * 0.48)], 0.67, color, cap_top=True)
        mb.box_on(0.3, 0, 0.42, 0.06, W * 0.9, 0.2, "window_glass")
    else:
        back = -0.42 if kind == "hatch" else -0.3
        base = [(back, -W * 0.46), (0.25, -W * 0.46), (0.25, W * 0.46), (back, W * 0.46)]
        top = [(back + 0.08, -W * 0.4), (0.05, -W * 0.4), (0.05, W * 0.4), (back + 0.08, W * 0.4)]
        mb.loft(base, 0.33, top, 0.52, color, cap_top=True)
        g0 = [(back + 0.01, -W * 0.465), (0.235, -W * 0.465), (0.235, W * 0.465), (back + 0.01, W * 0.465)]
        g1 = [(back + 0.085, -W * 0.405), (0.06, -W * 0.405), (0.06, W * 0.405), (back + 0.085, W * 0.405)]
        mb.loft(g0, 0.35, g1, 0.5, "window_glass")
    for x in (-L * 0.32, L * 0.32):
        for y in (-W * 0.47, W * 0.47):
            mb.cyl((x, y - 0.04 * (1 if y > 0 else -1) * 0, 0.11), 0.11, 0.08, "rubber", seg=16, rx=math.pi / 2,
                   rz=0 if y < 0 else math.pi)
            mb.cyl((x, y + (0.042 if y < 0 else -0.042), 0.11), 0.06, 0.005, "metal", seg=12, rx=math.pi / 2,
                   rz=0 if y < 0 else math.pi)
    for y in (-W * 0.32, W * 0.32):
        mb.box((L / 2, y, 0.24), (0.02, 0.09, 0.05), "headlight")
        mb.box((-L / 2, y, 0.25), (0.02, 0.08, 0.05), "taillight")
    mb.box((L / 2 + 0.01, 0, 0.13), (0.03, W * 0.95, 0.05), "metal")
    mb.box((-L / 2 - 0.01, 0, 0.13), (0.03, W * 0.95, 0.05), "metal")
    ob = mb.build(name, col)
    m = ob.modifiers.new("Bevel", "BEVEL")
    m.width = 0.05
    m.segments = 3
    m.limit_method = "ANGLE"
    return ob


def lamp(mb, x, y, z=0.0):
    mb.cyl((x, y, z), 0.05, 0.08, "lamp_green", seg=10)
    mb.cyl((x, y, z + 0.08), 0.022, 0.95, "lamp_green", seg=8, r2=0.016)
    mb.cyl((x, y, z + 1.02), 0.05, 0.03, "lamp_green", seg=8)
    mb.cyl((x, y, z + 1.05), 0.045, 0.12, "headlight", seg=6, r2=0.06)
    mb.cyl((x, y, z + 1.17), 0.075, 0.05, "lamp_green", seg=6, r2=0.01)


def bollard(mb, x, y, z=0.0):
    mb.cyl((x, y, z), 0.025, 0.16, "lamp_green", seg=8)
    mb.sphere((x, y, z + 0.16), 0.027, "lamp_green", seg=8, rings=5)


def bench(mb, x, y, z, rz):
    c, s = math.cos(rz), math.sin(rz)
    mb.box((x, y, z + 0.1), (0.4, 0.1, 0.02), "shop_wood", rz=rz)
    mb.box((x - s * 0.05, y + c * 0.05, z + 0.17), (0.4, 0.015, 0.1), "shop_wood", rz=rz)
    for d in (-0.17, 0.17):
        mb.box((x + c * d, y + s * d, z + 0.05), (0.02, 0.1, 0.1), "iron", rz=rz)
