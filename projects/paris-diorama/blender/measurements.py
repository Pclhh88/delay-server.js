"""Bildmessungen der Vorlage (Pixel in reference/reference.png, 2048 x 2048) und daraus
abgeleitete Gebäudemassen. Jede Zahl ist ein abgelesener Bildpunkt (Zoom-Ausschnitte mit
10-px-Raster, blender/measure_crop.py) – die 3D-Maße werden mit der kalibrierten Kamera
(camera.json) daraus zurückgerechnet, nicht geschätzt.

Begriffe pro Gebäude (Blick von vorne, Kamera bei -x/-y):
  top_front  Traufpunkt der vorderen senkrechten Kante (kleinstes x und y)
  top_left   Ende der sichtbaren linken Fassade (Normale -x) auf Traufhöhe
  top_right  Ende der sichtbaren rechten Fassade (Normale -y) auf Traufhöhe
  ground     Fußpunkt senkrecht unter top_front (für die Traufhöhe)
  deck       vorderste Ecke der flachen Dachplattform (für Mansardhöhe + Rücksprung)
"""
import math
import numpy as np
from scipy.optimize import brentq

BLOCK_Z = 0.12

M = {
    # Eckhaus vorne: abgeschrägte Ecke (Facette zur Kamera), Mansarde mit Rundbogengauben
    'A_corner_front': dict(top_front=(1066, 1450), ground=(1066, 1720), top_left=(900, 1397),
                           top_right=(1238, 1390), facet=((1030, 1450), (1102, 1450)), deck=(1072, 1370),
                           deck_left=(930, 1335), deck_right=(1190, 1320)),
    # Haus mit rotem Mansarddach (links neben dem Eckhaus)
    'B_red_roof': dict(top_front=(865, 1465), ground=(865, 1645), top_left=(677, 1380), top_right=None,
                       deck=(870, 1285), deck_left=(755, 1240)),
    # Mansardhaus mit blauem Dach und Terrakotta-Kaminen (hinter dem Eckhaus)
    'C_blue_mansard': dict(top_front=(1280, 1300), ground=(1280, 1600), top_left=(1075, 1205),
                           top_right=(1400, 1230), deck=None,
                           deck_left=(1105, 1135), deck_right=(1310, 1180)),
    # schmales hohes Haus mit braunen Läden, helles flaches Dach
    'D_shutters': dict(top_front=(1400, 1205), ground=(1400, 1515), top_left=None,
                       top_right=(1530, 1135), deck=(1400, 1150),
                       deck_left=(1300, 1097), deck_right=(1505, 1080)),
    # großes Eckhaus links (Balustrade, Mansarde mit Gauben)
    'E_left_large': dict(top_front=(625, 1115), ground=(625, 1390), top_left=(352, 1002),
                         top_right=(760, 1055), deck=(625, 1032), deck_left=(375, 940)),
    # großes Kuppel-Mansardhaus rechts (Fußpunkt rechts außen sichtbar)
    'F_right_dome': dict(top_front=(1560, 955), ground_edge=((1662, 1240), (1662, 905)),
                         top_left=(1292, 850), top_right=(1720, 880), deck=(1552, 805),
                         deck_left=(1380, 735), deck_right=(1705, 720)),
    # hohes Haus hinten links mit Attika und Kuppeltürmchen (Fuß verdeckt -> Traufhöhe aus
    # Geschosszahl: EG + 5 OG wie Nachbarn, z_top_assumed)
    'G_back_left': dict(z_top_assumed=4.9, top_front=(715, 825), top_left=(545, 750), top_right=(950, 765),
                        deck=(715, 780), deck_left=(555, 717), deck_right=(952, 670)),
}

# Eiffelturm: Achse (u) und Höhenmarken (v der linken/rechten Kanten) + Bildbreite
TOWER = dict(axis_u=1030, ground_v=1090,
             levels=[  # (Name, v, Bildbreite px)
                 ('fuss', 1090, 430), ('etage1_oben', 880, 320), ('etage1_unten', 915, 320),
                 ('zwischen_1_2', 800, 210), ('etage2', 735, 170),
                 ('schaft_720', 720, 148), ('schaft_650', 650, 122), ('schaft_550', 550, 98),
                 ('schaft_450', 450, 82), ('schaft_350', 350, 68), ('schaft_280', 280, 62),
                 ('etage3_unten', 273, 85), ('etage3_oben', 253, 85), ('kuppel', 212, 74),
                 ('fahne', 102, 0)])


def _cam():
    import json, os
    return json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'camera.json')))


def derive(cam=None):
    """Leitet für jedes Gebäude Grundriss (Welt), Drehung, Traufhöhe und Mansardmaße ab."""
    from fit_camera import project, unproject
    cam = cam or _cam()

    def P(p):
        return project(cam, np.array([p], float))[0]

    def U(uv, z):
        return unproject(cam, uv, z)[:2]

    def z_above(xy, v):
        return brentq(lambda z: P((xy[0], xy[1], z))[1] - v, -5, 40)

    out = {}
    for name, m in M.items():
        r = {}
        if 'ground' in m:
            g = U(m['ground'], BLOCK_Z)
            zt = z_above(g, m['top_front'][1])
        elif 'ground_edge' in m:
            (gu, gv), (tu, tv) = m['ground_edge']
            g = U((gu, gv), BLOCK_Z)
            zt = z_above(g, tv)
        else:
            zt = m.get('z_top_assumed')
        r['z_top'] = zt
        out[name] = r
        out[name]['m'] = m
    return out


def footprint_from(m, zt, cam=None):
    """Front-, Links- und Rechtspunkt auf Traufhöhe -> (Ecke, Drehung, Länge x, Länge y)."""
    from fit_camera import unproject
    cam = cam or _cam()
    pf = unproject(cam, m['top_front'], zt)[:2]
    res = dict(front=pf)
    angs = []
    if m.get('top_right'):
        pr = unproject(cam, m['top_right'], zt)[:2]
        d = pr - pf
        res['len_x'] = float(np.hypot(*d))
        angs.append(math.atan2(d[1], d[0]))
    if m.get('top_left'):
        pl = unproject(cam, m['top_left'], zt)[:2]
        d = pl - pf
        res['len_y'] = float(np.hypot(*d))
        angs.append(math.atan2(-d[0], d[1]))
    res['rot'] = float(np.mean(angs)) if angs else 0.0
    return res


def mansard_from(m, zt, fp, cam=None):
    """Dachplattform-Ecken -> (Mansardhöhe, Rücksprung): kleinster Bildfehler der vorhergesagten
    Plattform-Ecken (vorne: Ecke+(i,i), links: linkes Ende+(i,-i), rechts: rechtes Ende+(-i,i))."""
    from fit_camera import project, unproject
    cam = cam or _cam()
    c, s = math.cos(fp['rot']), math.sin(fp['rot'])
    ux, uy = np.array([c, s]), np.array([-s, c])
    pts = []
    if m.get('deck'):
        pts.append((m['deck'], fp['front'], ux + uy))
    if m.get('deck_left') and 'len_y' in fp:
        pts.append((m['deck_left'], fp['front'] + uy * fp['len_y'], ux - uy))
    if m.get('deck_right') and 'len_x' in fp:
        pts.append((m['deck_right'], fp['front'] + ux * fp['len_x'], uy - ux))
    if not pts:
        return None
    best = None
    for hm in np.linspace(0.2, 4.0, 77):
        for i in np.linspace(0.0, 1.6, 65):
            e = 0
            for uv, base, d in pts:
                q = base + d * i
                e += np.sum((project(cam, np.array([[q[0], q[1], zt + hm]]))[0] - np.array(uv)) ** 2)
            if best is None or e < best[0]:
                best = (e, float(hm), float(i))
    return dict(roof_h=round(best[1], 2), inset=round(best[2], 2), err_px=round(math.sqrt(best[0] / len(pts)), 1))


if __name__ == '__main__':
    cam = _cam()
    for name, r in derive(cam).items():
        zt = r['z_top']
        if zt is None:
            print(f'{name:16s} Traufhöhe unbekannt (Fuß verdeckt)')
            continue
        fp = footprint_from(r['m'], zt, cam)
        ms = mansard_from(r['m'], zt, fp, cam)
        print(f"{name:16s} z_top={zt:5.2f}  Ecke=({fp['front'][0]:5.2f},{fp['front'][1]:5.2f})  "
              f"Drehung={math.degrees(fp['rot']):5.1f}°  Lx={fp.get('len_x', float('nan')):4.2f}  "
              f"Ly={fp.get('len_y', float('nan')):4.2f}  Mansarde={ms}")
