"""Kleine Requisiten: Menschen, Laternen, Obelisk, Brunnen, Café-Schirme."""
import math
import random

from .mesh import MeshBuilder

PEOPLE_COLORS = ["car_red", "car_blue", "white", "car_yellow", "shutter_green", "dark", "wall_rose"]


def person(mb, x, y, z, rng, scale=1.0):
    c = rng.choice(PEOPLE_COLORS)
    s = scale
    mb.cyl((x, y, z), 0.07 * s, 0.22 * s, "dark", seg=6)
    mb.cyl((x, y, z + 0.2 * s), 0.085 * s, 0.2 * s, c, seg=8, r2=0.06 * s)
    mb.sphere((x, y, z + 0.47 * s), 0.065 * s, "wall_salmon", seg=8, rings=6)


def crowd(mb, cx, cy, radius, n, seed, z=0.0, avoid=None):
    rng = random.Random(seed)
    k = 0
    tries = 0
    while k < n and tries < n * 20:
        tries += 1
        a, r = rng.uniform(0, 2 * math.pi), radius * math.sqrt(rng.random())
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        if avoid and avoid(x, y):
            continue
        person(mb, x, y, z, rng)
        k += 1


def obelisk(mb, x, y, z=0.0, h=2.2, mat="stone_grey"):
    mb.box_on(x, y, z, 0.6, 0.6, 0.3, "travertine")
    mb.cyl((x, y, z + 0.3), 0.22, h, mat, seg=4, r2=0.13, rz=math.pi / 4, smooth=False)
    mb.cyl((x, y, z + 0.3 + h), 0.13, 0.22, mat, seg=4, r2=0.0, rz=math.pi / 4, smooth=False)


def fountain(mb, x, y, z=0.0, r=0.9):
    mb.ring(r, r, r - 0.12, r - 0.12, z, 0.25, "travertine", n=24, c=(x, y))
    mb.cyl((x, y, z), r - 0.12, 0.2, "water", seg=24)
    mb.cyl((x, y, z), 0.12, 0.6, "travertine", seg=10)
    mb.cyl((x, y, z + 0.55), 0.35, 0.08, "travertine", seg=16)
    mb.sphere((x, y, z + 0.75), 0.12, "foam", seg=10, rings=6, s=(1, 1, 1.4))


def lamp(mb, x, y, z=0.0):
    mb.cyl((x, y, z), 0.035, 0.9, "dark", seg=6)
    mb.sphere((x, y, z + 0.95), 0.07, "headlight", seg=8, rings=6)


def cafe(mb, x, y, z, n, seed, color="awning_red"):
    rng = random.Random(seed)
    for i in range(n):
        px, py = x + rng.uniform(-0.8, 0.8), y + rng.uniform(-0.5, 0.5)
        mb.cyl((px, py, z), 0.02, 0.45, "dark", seg=5)
        mb.cyl((px, py, z + 0.42), 0.32, 0.12, color, seg=8, r2=0.02)
        mb.cyl((px, py, z), 0.13, 0.2, "white", seg=8)
