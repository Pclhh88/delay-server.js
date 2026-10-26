"""Kamera-Fit für die Vorlage (2048 x 2048).

Befunde der Vermessung (analysis/ANALYSE.md):
  * Senkrechte bleiben im ganzen Bild exakt senkrecht (z. B. linke Hauskante x=350, y=1000..1200)
    -> Bildebene senkrecht (Architektur-/Shift-Kamera, Blender: Neigung 90° + Lens-Shift).
  * Horizontale Kanten werden nach oben im Bild flacher (Traufen Steigung ~0,41 statt 0,53 an der
    Plattform) -> echte Perspektive, keine Orthografie.
Gefittet werden Azimut, Kameraposition, Brennweite und Shift an
  - die beiden vorderen Plattform-Oberkanten (Linien), die Extrempunkte der Eckrundungen,
  - Fluchtrichtungen langer Trauf-/Dachkanten (parallel zu Welt-x bzw. Welt-y).
Ausgabe: blender/camera.json
"""
import json, math, os
import numpy as np
try:
    from scipy.optimize import least_squares
except ImportError:  # nur für den Fit selbst nötig
    least_squares = None

RES = 2048
SIZE = 24.0
Z_TOP = 0.1          # Oberkante der Plattform-Randkante
L1 = ((480, 1665), (780, 1825))      # vordere linke Plattformkante (Welt x=0)
R1 = ((1250, 1877), (1800, 1545))    # vordere rechte Plattformkante (Welt y=0)
FRONT, LEFT, RIGHT = (1050, 1907), (36, 1360), (2030, 1310)
# Kanten parallel zu Welt-y ("linke" Fassaden) bzw. Welt-x ("rechte" Fassaden), (Bildpunkt, Bildpunkt)
SEG_Y = [((352, 1002), (625, 1115)),   # großes Haus links, Traufe
         ((1380, 735), (1552, 805)),   # großes Haus rechts, Dachplattform
         ((555, 717), (705, 778)),     # Haus hinten links, Dachplattform
         ((677, 1380), (865, 1465)),   # Haus mit rotem Dach, Traufe
         ((900, 1397), (1030, 1450)),  # Eckhaus, Traufe
         ((662, 1705), (787, 1770))]   # Fahrbahnmarkierung vorne links
SEG_X = [((625, 1115), (760, 1055)),
         ((1552, 805), (1705, 720)),
         ((725, 778), (952, 670)),
         ((1400, 1205), (1530, 1135)),
         ((1280, 1300), (1400, 1230))]


def rot(yaw, pitch, roll):
    cx, sx = math.cos(pitch), math.sin(pitch)
    cz, sz = math.cos(yaw), math.sin(yaw)
    cy, sy = math.cos(roll), math.sin(roll)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def _K(cam):
    f = cam['lens'] / cam['sensor'] * RES
    return f, RES / 2 + cam['shift_x'] * RES, RES / 2 - cam['shift_y'] * RES


def project(cam, P):
    R = rot(cam['yaw'], cam['pitch'], cam['roll'])
    pc = (np.asarray(P, float).reshape(-1, 3) - np.array(cam['location'])) @ R
    f, u0, v0 = _K(cam)
    return np.stack([u0 + f * pc[:, 0] / -pc[:, 2], v0 - f * pc[:, 1] / -pc[:, 2]], 1)


def vanish(cam, d):
    R = rot(cam['yaw'], cam['pitch'], cam['roll'])
    dc = np.asarray(d, float) @ R
    f, u0, v0 = _K(cam)
    return np.array([u0 + f * dc[0] / -dc[2], v0 - f * dc[1] / -dc[2]])


def unproject(cam, uv, z):
    """Bildpunkt -> Weltpunkt auf Höhe z (Sehstrahl)."""
    R = rot(cam['yaw'], cam['pitch'], cam['roll'])
    f, u0, v0 = _K(cam)
    d = R @ np.array([(uv[0] - u0) / f, -(uv[1] - v0) / f, -1.0])
    o = np.array(cam['location'], float)
    return o + (z - o[2]) / d[2] * d


def arc(cx, cy, r, a0, a1, n=60):
    a = np.radians(np.linspace(a0, a1, n))
    return np.stack([cx + r * np.cos(a), cy + r * np.sin(a), np.full(n, Z_TOP)], 1)


def _cam(p):
    yaw, x, y, z, lens, sx, sy = p[:7]
    return dict(type='PERSP', yaw=yaw, pitch=math.pi / 2, roll=0.0, location=[x, y, z],
                lens=lens, sensor=36.0, shift_x=sx, shift_y=sy)


def _line_dist(pts, line):
    (x0, y0), (x1, y1) = line
    n = np.array([y1 - y0, -(x1 - x0)], float)
    n /= np.linalg.norm(n)
    return (pts - np.array([x0, y0])) @ n


def _dir_resid(cam, seg, d):
    """Abweichung (px) der Segment-Endpunkte von der Linie Mitte->Fluchtpunkt."""
    p, q = np.array(seg[0], float), np.array(seg[1], float)
    m = (p + q) / 2
    vp = vanish(cam, d)
    t = vp - m
    n = np.array([t[1], -t[0]]) / np.linalg.norm(t)
    return [(p - m) @ n, (q - m) @ n]


def resid(p, w_dir=1.0):
    cam, R = _cam(p), p[7]
    r = []
    ys = np.linspace(R + 0.3, SIZE - R - 0.3, 8)
    r += list(_line_dist(project(cam, [(0, y, Z_TOP) for y in ys]), L1))
    r += list(_line_dist(project(cam, [(x, 0, Z_TOP) for x in ys]), R1))
    f = project(cam, arc(R, R, R, 180, 270)); i = f[:, 1].argmax(); r += list(f[i] - FRONT)
    l = project(cam, arc(R, SIZE - R, R, 90, 180)); i = l[:, 0].argmin(); r += list(l[i] - LEFT)
    g = project(cam, arc(SIZE - R, R, R, 270, 360)); i = g[:, 0].argmax(); r += list(g[i] - RIGHT)
    for s in SEG_Y:
        r += [w_dir * e for e in _dir_resid(cam, s, (0, 1, 0))]
    for s in SEG_X:
        r += [w_dir * e for e in _dir_resid(cam, s, (1, 0, 0))]
    return np.array(r)


if __name__ == '__main__':
    best = None
    for dist in (40, 70, 110):
        for yaw0 in (-0.75, -0.85):
            x0 = [yaw0, 12 - dist * 0.7, 12 - dist * 0.7, dist * 0.6, 60.0, 0.0, -0.6, 4.0]
            sol = least_squares(resid, x0, x_scale=[0.05, 5, 5, 5, 10, 0.05, 0.05, 0.5], max_nfev=4000)
            if best is None or sol.cost < best.cost:
                best = sol
    p = best.x
    cam = _cam(p)
    e = np.abs(resid(p))
    nplat = 16 + 6
    out = dict(**cam, corner_radius=float(p[7]), resolution=RES,
               rms_px=float(np.sqrt((e ** 2).mean())), rms_platform_px=float(np.sqrt((e[:nplat] ** 2).mean())),
               rms_edges_px=float(np.sqrt((e[nplat:] ** 2).mean())), max_px=float(e.max()))
    out['location'] = [float(v) for v in out['location']]
    out = {k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in out.items()}
    print(json.dumps(out, indent=1))
    print('Restfehler je Kante:', np.round(e[nplat:].reshape(-1, 2).max(1), 1))
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'camera.json'), 'w'), indent=1)
