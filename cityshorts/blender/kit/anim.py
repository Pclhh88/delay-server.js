"""Wiederverwendbare Animationen (Keyframes): Einfliegen/Aufbauen der Stadt,
Hervorheben ("Bounce") eines Wahrzeichens, Karten-Pin, Wurfbahnen."""
import math


def back_out(u, s=1.70158):
    u = max(0.0, min(1.0, u)) - 1
    return u * u * ((s + 1) * u + s) + 1


def bounce_out(u):
    u = max(0.0, min(1.0, u))
    if u < 1 / 2.75:
        return 7.5625 * u * u
    if u < 2 / 2.75:
        u -= 1.5 / 2.75
        return 7.5625 * u * u + 0.75
    if u < 2.5 / 2.75:
        u -= 2.25 / 2.75
        return 7.5625 * u * u + 0.9375
    u -= 2.625 / 2.75
    return 7.5625 * u * u + 0.984375


def drop_in(ob, f_start, dur_f, height=4.0, step=1):
    """Haus fällt von oben auf die Insel und federt nach (Aufbau-Intro)."""
    base = ob.location.copy()
    sc = ob.scale.copy()
    ob.scale = (0, 0, 0)
    ob.keyframe_insert("scale", frame=max(f_start - 1, 0))
    for f in range(f_start, f_start + dur_f + 1, step):
        u = (f - f_start) / dur_f
        ob.location = (base.x, base.y, base.z + height * (1 - bounce_out(u)))
        k = min(1.0, u * 4)
        ob.scale = sc * k
        ob.keyframe_insert("location", frame=f)
        ob.keyframe_insert("scale", frame=f)
    ob.location, ob.scale = base, sc


def pop_in(ob, f_start, dur_f, step=1):
    sc = ob.scale.copy()
    ob.scale = (0, 0, 0)
    ob.keyframe_insert("scale", frame=max(f_start - 1, 0))
    for f in range(f_start, f_start + dur_f + 1, step):
        ob.scale = sc * back_out((f - f_start) / dur_f)
        ob.keyframe_insert("scale", frame=f)
    ob.scale = sc


def squash_bounce(ob, f_start, fps, amount=0.08):
    """Kurzes Squash&Stretch, wenn der Sprecher das Wahrzeichen nennt."""
    seq = [(0.0, 1, 1), (0.12, 1 + amount * 0.6, 1 - amount), (0.28, 1 - amount * 0.5, 1 + amount * 1.2),
           (0.45, 1 + amount * 0.2, 1 - amount * 0.3), (0.62, 1, 1)]
    s0 = ob.scale.copy()
    for t, sxy, sz in seq:
        ob.scale = (s0.x * sxy, s0.y * sxy, s0.z * sz)
        ob.keyframe_insert("scale", frame=f_start + int(round(t * fps)))
    ob.scale = s0


def throw(ob, p0, p1, f0, f1, apex=1.5, spin=8.0):
    """Parabelwurf (z. B. Münze in den Trevi-Brunnen)."""
    ob.scale = (0, 0, 0)
    ob.keyframe_insert("scale", frame=max(f0 - 1, 0))
    for f in range(f0, f1 + 1):
        u = (f - f0) / max(f1 - f0, 1)
        x = p0[0] + (p1[0] - p0[0]) * u
        y = p0[1] + (p1[1] - p0[1]) * u
        z = p0[2] + (p1[2] - p0[2]) * u + apex * 4 * u * (1 - u)
        ob.location = (x, y, z)
        ob.rotation_euler = (spin * u * 2 * math.pi, 0, 0)
        ob.scale = (1, 1, 1)
        ob.keyframe_insert("location", frame=f)
        ob.keyframe_insert("rotation_euler", frame=f)
        ob.keyframe_insert("scale", frame=f)
    ob.scale = (0, 0, 0)
    ob.keyframe_insert("scale", frame=f1 + 1)


def visible_between(ob, f0, f1, grow=8):
    sc = ob.scale.copy()
    for f, k in [(0, 0), (f0 - 1, 0), (f0 + grow, 1), (f1 - grow, 1), (f1, 0)]:
        ob.scale = sc * k
        ob.keyframe_insert("scale", frame=max(f, 0))
    ob.scale = sc
