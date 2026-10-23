"""Keyframe interpolation.

A layer carries a list of keys: {"t": seconds, "<prop>": value, ..., "ease": "linear"}.
Each property is interpolated independently between the keys that define it.
The "ease" of a key describes how the value travels *towards* that key.
"""
import math

DEFAULTS = {
    "x": None, "y": None, "scale": 1.0, "sx": 1.0, "sy": 1.0, "rot": 0.0,
    "opacity": 1.0,
}


def ease(name, p):
    p = min(1.0, max(0.0, p))
    if name in (None, "linear"):
        return p
    if name == "hold":
        return 0.0 if p < 1.0 else 1.0
    if name == "in":
        return p * p
    if name == "out":
        return 1 - (1 - p) * (1 - p)
    if name == "inout":
        return 3 * p * p - 2 * p * p * p
    if name == "in3":
        return p ** 3
    if name == "out3":
        return 1 - (1 - p) ** 3
    if name == "out5":
        return 1 - (1 - p) ** 5
    if name == "back_out":
        c1, c3 = 1.70158, 2.70158
        return 1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2
    if name == "elastic_out":
        if p in (0.0, 1.0):
            return p
        return 2 ** (-10 * p) * math.sin((p * 10 - 0.75) * (2 * math.pi) / 3) + 1
    raise ValueError(f"unknown ease {name}")


def _lerp(a, b, p):
    if isinstance(a, (list, tuple)):
        return [x + (y - x) * p for x, y in zip(a, b)]
    return a + (b - a) * p


def value_at(keys, prop, t, default=None):
    """Interpolated value of `prop` at time t (seconds)."""
    pts = [k for k in keys if prop in k]
    if not pts:
        return default
    if t <= pts[0]["t"]:
        return pts[0][prop]
    if t >= pts[-1]["t"]:
        return pts[-1][prop]
    for a, b in zip(pts, pts[1:]):
        if a["t"] <= t <= b["t"]:
            span = b["t"] - a["t"]
            p = 0.0 if span <= 0 else (t - a["t"]) / span
            return _lerp(a[prop], b[prop], ease(b.get("ease", "linear"), p))
    return pts[-1][prop]


def props_at(keys, t, base=None):
    out = dict(DEFAULTS)
    if base:
        out.update(base)
    names = set()
    for k in keys:
        names.update(k.keys())
    names.discard("t")
    names.discard("ease")
    for n in names:
        out[n] = value_at(keys, n, t, out.get(n))
    return out
