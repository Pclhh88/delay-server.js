"""Procedural motion helpers that turn time into pose values."""
import math


def walk(phase, stride=1.0):
    """Walk cycle; phase in cycles (1.0 = two steps). Returns pose values."""
    a = 2 * math.pi * phase
    s = math.sin(a)
    return {
        "leg_l": 24 * s * stride, "leg_r": -24 * s * stride,
        "knee_l": max(0.0, -math.cos(a)) * 35 * stride + 5,
        "knee_r": max(0.0, math.cos(a)) * 35 * stride + 5,
        "arm_l": 9 + 12 * s * stride, "arm_r": 9 + 12 * s * stride,
        "elbow_l": 12, "elbow_r": 12,
        "bob": -abs(math.cos(a)) * 14 * stride,
        "head_rot": 2 * s,
    }


def _hash(i, seed):
    x = math.sin(i * 12.9898 + seed * 78.233) * 43758.5453
    return x - math.floor(x)


def blink(t, seed=0, period=(2.2, 4.2), dur=0.16):
    """Automatic blinking: deterministic pseudo-random blink times."""
    tt, i = 0.4 + _hash(0, seed), 0
    while tt <= t + dur:
        if tt <= t < tt + dur:
            p = (t - tt) / dur
            return 1 - abs(2 * p - 1)
        i += 1
        tt += period[0] + (period[1] - period[0]) * _hash(i, seed)
    return 0.0


def talk(t, spans, rate=6.0, seed=0):
    """Mouth flapping inside [start, end] spans (until real lip-sync from audio)."""
    for a, b in spans:
        if a <= t < b:
            ramp = min(1.0, (t - a) / 0.06, (b - t) / 0.06)
            ph = (t - a) * rate
            v = abs(math.sin(math.pi * ph)) * (0.55 + 0.45 * _hash(int(ph), seed))
            return max(0.0, ramp) * v
    return 0.0


def breathe(t):
    return math.sin(t * 2 * math.pi / 3.2) * 3.0
