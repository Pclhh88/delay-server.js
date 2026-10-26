"""Kamera-Fit: Perspektivkamera (Teleobjektiv) an vermessene Ankerpunkte der Referenz.

Ankerpunkte (Weltpunkt <-> Pixel in reference.png, 2048x2048), vermessen mit
Gitter-Ausschnitten (siehe analysis/ANALYSE.md):
  * vorderster / linker / rechter Punkt der abgerundeten Plattform-Oberkante
  * Fuß und Spitze (Fähnchen) des Eiffelturms
Ausgabe: blender/camera.json (wird von build_scene.py und layout.img2world benutzt).
"""
import json, math, os
import numpy as np
try:
    from scipy.optimize import least_squares
except ImportError:  # nur für den Fit selbst nötig
    least_squares = None

RES, SENSOR, LENS = 2048, 36.0, 120.0
R = 3.2           # Eckradius der Plattform
TOWER = (17.5, 16.9)
ANCHORS = [  # (Welt xyz, Bild uv, Gewicht)
    # Extrempunkte der Rundungen: Richtung = Gradient der Bildkoordinate auf dem Boden
    ((R - 0.726 * R, R - 0.687 * R, 0.1), (1000, 1898), 1.0),   # vorderster Punkt
    ((R - 0.665 * R, 24 - R + 0.746 * R, 0.1), (38, 1325), 1.0),  # linker Punkt
    ((24 - R + 0.665 * R, R - 0.746 * R, 0.1), (2042, 1372), 1.0),  # rechter Punkt
    ((TOWER[0], TOWER[1], 0.12), (1035, 1050), 1.0),     # Turmfuß (Mitte zwischen den Bogenfüßen)
    ((TOWER[0], TOWER[1], 0.12 + 331 * 16.0 / 300), (1030, 100), 1.0),  # Turmspitze
    ((TOWER[0], TOWER[1], 0.12 + 300 * 16.0 / 300), (1000, 190), 0.3),  # Laternen-Oberkante
]


def rot(yaw, pitch, roll):
    cx, sx = math.cos(pitch), math.sin(pitch)
    cz, sz = math.cos(yaw), math.sin(yaw)
    cy, sy = math.cos(roll), math.sin(roll)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def project(params, P, lens=LENS):
    cx, cy, cz, yaw, pitch, roll = params
    pc = (np.asarray(P, float) - np.array([cx, cy, cz])) @ rot(yaw, pitch, roll)
    f = lens / SENSOR * RES
    return np.stack([RES / 2 + f * pc[:, 0] / -pc[:, 2], RES / 2 - f * pc[:, 1] / -pc[:, 2]], 1)


def unproject(params, uv, z, lens=LENS):
    """Bildpunkt -> Weltpunkt auf der Ebene Höhe z."""
    cx, cy, cz, yaw, pitch, roll = params
    f = lens / SENSOR * RES
    d_cam = np.array([(uv[0] - RES / 2) / f, -(uv[1] - RES / 2) / f, -1.0])
    d = rot(yaw, pitch, roll) @ d_cam
    o = np.array([cx, cy, cz])
    t = (z - o[2]) / d[2]
    return o + t * d


if __name__ == '__main__':
    W = np.array([a[0] for a in ANCHORS]); UV = np.array([a[1] for a in ANCHORS], float)
    wt = np.array([a[2] for a in ANCHORS])

    tower_rows = [i for i, a in enumerate(ANCHORS) if a[0][:2] == TOWER]

    def world(p):  # Turmposition ist mitgefittet (nur aus dem Bild bekannt)
        Wp = W.copy()
        Wp[tower_rows, 0] = p[6]
        Wp[tower_rows, 1] = p[7]
        return Wp

    def resid(p):
        return ((project(p[:6], world(p)) - UV) * wt[:, None]).ravel()
    r = least_squares(resid, [-50, -50, 70, math.radians(-48), math.radians(54), 0, *TOWER])
    err = np.abs(project(r.x[:6], world(r.x)) - UV)
    print('Turm-Position:', np.round(r.x[6:], 2))
    cx, cy, cz, yaw, pitch, roll = r.x[:6]
    out = dict(params=list(r.x[:6]), tower_xy=list(r.x[6:]), location=[cx, cy, cz], rotation_euler=[pitch, roll, yaw], lens=LENS,
               sensor=SENSOR, resolution=RES, rms_px=float(np.sqrt((err ** 2).mean())), max_px=float(err.max()))
    for a, e in zip(ANCHORS, err):
        print(a[1], np.round(e, 1))
    print(json.dumps(out, indent=1))
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'camera.json'), 'w'), indent=1)
