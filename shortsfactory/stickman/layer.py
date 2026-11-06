"""Timeline layer types for stickman scenes (registered in render/shapes.py).

"stickman": {"type": "stickman", "character": "characters/voigt_zivil.json",
             "pose": {...static pose...},
             "auto": {"blink": true, "breathe": true, "talk": [[t0, t1], ...], "seed": 1},
             "keys": [{"t": 0, "x": 540, "y": 1500, "scale": 0.8, "walk": 1, "expression": "happy", ...}]}
  Keyed values: transform (x, y, scale, sx, sy, rot, opacity), "walk" (0..1 blend of the
  walk cycle), "walk_rate" (cycles/s) and any pose key from rig.py.  String values
  (expression, handshape_*) switch at their key ("hold").
"scene_street": Berlin street around 1900, keyed "pan" (design px) for parallax.
"""
import json
import math
import os

import numpy as np
import skia

from . import motion
from .rig import Stickman

_TRANSFORM = {"x", "y", "scale", "sx", "sy", "rot", "opacity", "walk", "walk_rate"}
_cache = {}


def _surface(r):
    arr = np.zeros((r.H, r.W, 4), np.uint8)
    srf = skia.Surface(arr, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
    return arr, srf.getCanvas()


def _skm(M):
    return skia.Matrix.MakeAll(M[0, 0], M[0, 1], M[0, 2], M[1, 0], M[1, 1], M[1, 2], 0, 0, 1)


def _out(arr):
    return arr.astype(np.float32) / 255.0


def _char(r, ref):
    if isinstance(ref, dict):
        return Stickman(ref)
    path = os.path.join(r.base, ref)
    if path not in _cache:
        with open(path, encoding="utf-8") as f:
            _cache[path] = Stickman(json.load(f))
    return _cache[path]


def _string_at(keys, prop, t, default):
    val = default
    for k in keys:
        if prop in k and k["t"] <= t:
            val = k[prop]
    return val


def stickman(r, layer, p, t, M):
    man = _char(r, layer["character"])
    keys = layer.get("keys", [])
    pose = dict(layer.get("pose", {}))
    lt = t - layer.get("start", 0.0)
    for k, v in p.items():
        if k not in _TRANSFORM and v is not None:
            pose[k] = v
    # walk cycle blended over the (static or keyed) pose
    w = p.get("walk", 0.0)
    if w > 0:
        for k, v in motion.walk(lt * p.get("walk_rate", 0.9)).items():
            pose[k] = pose.get(k, 0.0) * (1 - w) + v * w
    for k in ("expression", "handshape_l", "handshape_r", "facing"):
        if any(k in kk for kk in keys):
            pose[k] = _string_at(keys, k, t, pose.get(k))
    auto = layer.get("auto", {})
    seed = auto.get("seed", 0)
    if auto.get("blink", True):
        pose["blink"] = max(pose.get("blink", 0.0), motion.blink(lt, seed))
    if auto.get("breathe", True) and w < 1:
        pose["bob"] = pose.get("bob", 0.0) + motion.breathe(lt) * (1 - w)
    if auto.get("talk"):
        pose["mouth_open"] = max(pose.get("mouth_open", 0.0), motion.talk(t, auto["talk"], seed=seed))
    pose["t"] = lt
    arr, cv = _surface(r)
    cv.setMatrix(_skm(M @ r._local_matrix(layer, p)))
    man.draw(cv, pose)
    return _out(arr)


# ---------------------------------------------------------------- scenery
def _rgb(c, a=255):
    return skia.Color(int(c[0]), int(c[1]), int(c[2]), a)


def _fill(c):
    return skia.Paint(AntiAlias=True, Color=_rgb(c))


def _line(w, c=(20, 16, 14)):
    return skia.Paint(AntiAlias=True, Color=_rgb(c), Style=skia.Paint.kStroke_Style, StrokeWidth=w,
                      StrokeJoin=skia.Paint.kRound_Join, StrokeCap=skia.Paint.kRound_Cap)


FACADES = [(222, 196, 160), (196, 176, 158), (214, 184, 150), (186, 170, 160), (226, 206, 176), (200, 160, 130)]


def _house(cv, x, ground, w, h, col, seed):
    ol = 7
    cv.drawRect(skia.Rect.MakeXYWH(x, ground - h, w, h), _fill(col))
    cv.drawRect(skia.Rect.MakeXYWH(x, ground - h, w, h), _line(ol))
    # cornice + roof
    cv.drawRect(skia.Rect.MakeXYWH(x - 12, ground - h - 26, w + 24, 26), _fill([c * 0.82 for c in col]))
    cv.drawRect(skia.Rect.MakeXYWH(x - 12, ground - h - 26, w + 24, 26), _line(ol))
    roof = skia.Path()
    roof.moveTo(x - 6, ground - h - 26)
    roof.lineTo(x + 40, ground - h - 110)
    roof.lineTo(x + w - 40, ground - h - 110)
    roof.lineTo(x + w + 6, ground - h - 26)
    roof.close()
    cv.drawPath(roof, _fill((120, 92, 82)))
    cv.drawPath(roof, _line(ol))
    cols = max(2, int(w // 120))
    rows = max(2, int((h - 260) // 190))
    ww = 62
    gap = (w - cols * ww) / (cols + 1)
    for j in range(rows):
        for i in range(cols):
            wx = x + gap + i * (ww + gap)
            wy = ground - h + 60 + j * 190
            rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(wx, wy, ww, 110), 30, 30)
            cv.drawRRect(rr, _fill((120, 150, 170)))
            cv.drawRRect(rr, _line(6))
            cv.drawLine(wx + ww / 2, wy + 10, wx + ww / 2, wy + 110, _line(4))
            cv.drawRect(skia.Rect.MakeXYWH(wx - 8, wy + 110, ww + 16, 12), _fill((235, 225, 210)))
            cv.drawRect(skia.Rect.MakeXYWH(wx - 8, wy + 110, ww + 16, 12), _line(5))
    # door
    dx = x + w / 2 - 45
    door = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(dx, ground - 200, 90, 200), 40, 40)
    cv.drawRRect(door, _fill((110, 78, 60)))
    cv.drawRRect(door, _line(6))


def scene_street(r, layer, p, t, M):
    arr, cv = _surface(r)
    cv.setMatrix(_skm(M))
    W, H = 1080, 1920
    ground = layer.get("ground", 1480)
    pan = p.get("pan", 0.0)
    sky = skia.Paint(Shader=skia.GradientShader.MakeLinear(
        [(0, 0), (0, ground)], [_rgb((150, 200, 225)), _rgb((232, 238, 232))]))
    cv.drawRect(skia.Rect.MakeWH(W, H), sky)
    # clouds (slow parallax)
    for i, (cx, cy) in enumerate(((180, 260), (760, 180), (1300, 320))):
        x = (cx - pan * 0.15 + t * 6) % 1500 - 200
        for dx, dy, rr in ((0, 0, 60), (70, -25, 75), (150, 0, 60)):
            cv.drawCircle(x + dx, cy + dy, rr, _fill((250, 250, 248)))
    # houses (parallax 0.6)
    house_w = [300, 260, 340, 280, 320, 300]
    house_h = [880, 960, 820, 940, 900, 860]
    total = sum(house_w) + 20 * len(house_w)
    x = -((pan * 0.6) % total) - 60
    i = 0
    while x < W + 60:
        k = i % len(house_w)
        _house(cv, x, ground - 120, house_w[k], house_h[k], FACADES[k], k)
        x += house_w[k] + 20
        i += 1
    # sidewalk + curb + cobblestone street
    sw = ground - 120
    cv.drawRect(skia.Rect.MakeLTRB(0, sw, W, ground + 40), _fill((206, 200, 190)))
    cv.drawLine(0, sw, W, sw, _line(7))
    off = -(pan % 160)
    for j in range(10):
        lx = off + j * 160
        cv.drawLine(lx, sw + 6, lx - 60, ground + 36, _line(3, (150, 140, 130)))
    cv.drawRect(skia.Rect.MakeLTRB(0, ground + 40, W, ground + 70), _fill((170, 162, 150)))
    cv.drawLine(0, ground + 40, W, ground + 40, _line(7))
    cv.drawLine(0, ground + 70, W, ground + 70, _line(7))
    cv.drawRect(skia.Rect.MakeLTRB(0, ground + 70, W, H), _fill((132, 120, 110)))
    stone = _line(3, (95, 85, 78))
    for row in range(14):
        yy = ground + 100 + row * 26 * (1 + row * 0.12)
        if yy > H:
            break
        shift = (row % 2) * 30 - (pan * (1.0 + row * 0.04)) % 60
        for j in range(-1, 20):
            xx = shift + j * 60
            cv.drawOval(skia.Rect.MakeXYWH(xx, yy, 48, 18 + row * 2), stone)
    # gas lamp
    lx = (1400 - pan) % 1700 - 100
    cv.drawLine(lx, sw + 20, lx, sw - 560, _line(22))
    cv.drawLine(lx, sw + 20, lx, sw - 560, _line(12, (60, 66, 62)))
    lamp = skia.Path()
    lamp.moveTo(lx - 40, sw - 560)
    lamp.lineTo(lx + 40, sw - 560)
    lamp.lineTo(lx + 55, sw - 660)
    lamp.lineTo(lx - 55, sw - 660)
    lamp.close()
    cv.drawPath(lamp, _fill((250, 236, 180)))
    cv.drawPath(lamp, _line(8))
    cv.drawLine(lx - 70, sw - 664, lx + 70, sw - 664, _line(10))
    return _out(arr)
