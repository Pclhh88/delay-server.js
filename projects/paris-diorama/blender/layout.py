"""Szenen-Layout, vermessen aus references/paris-diorama/reference.png (2048x2048).

Weltkoordinaten: Plattform 24 x 24, Vorderecke (zur Kamera) bei (0,0).
  +x = Kante nach rechts hinten, +y = Kante nach links hinten, z nach oben.
Objekte, deren Fußpunkt im Bild sichtbar ist, werden direkt in Bildkoordinaten
angegeben und über die gemessene Bodenabbildung (img2world) platziert.
"""
import json
import math
import os
import numpy as np
from diorama.meshkit import chamfer_rect

SIZE = 24.0
CORNER_R = round(json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'camera.json')))['corner_radius'], 2)
BLOCK_Z = 0.12            # Oberkante Gehweg/Blockfläche
ROAD = (0.35, 2.55)       # Straße zwischen diesen Randabständen
WALK = 3.45               # Gehweg bis hier

import json, os
from fit_camera import project as _project, unproject as _unproject
_CAM = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'camera.json')))


def img2world(sx, sy, z=BLOCK_Z):
    """Bildpunkt der Referenz -> Weltpunkt auf Höhe z (Sehstrahl der kalibrierten Kamera)."""
    x, y, _ = _unproject(_CAM, (sx, sy), z)
    return float(x), float(y), z


def world2img(p):
    return _project(_CAM, np.array([p], float))[0]


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# ---------------------------------------------------------------- Gebäude
# Kantenindex bei rect(): 0 = Süd (-y, zeigt nach rechts vorne), 1 = Ost, 2 = Nord, 3 = West (-x, links vorne)
# Vermessung: Fußpunkt der vorderen Gebäudekante + Traufpunkt darüber -> Traufhöhe,
# Endpunkte der sichtbaren Fassaden -> Grundriss (siehe analysis/ANALYSE.md, Tabelle 2).
BUILDINGS = [
    dict(name='House_White_Corner', footprint=chamfer_rect(4.3, 4.2, 8.3, 6.8, {'SW': 1.0}, seg=3),
         floors=3, ground_h=1.25, floor_h=1.1, facade='stone_light', roof='mansard', roof_h=1.9, roof_inset=0.7,
         dormer_style='arch', skip_edges=(4, 5), doors={1: [0]}, door_mat='door_green', bay=1.2,
         balcony_floors=(2,), n_auto_chimneys=3, seed=11),
    dict(name='House_Red_Roof', footprint=rect(3.9, 6.8, 7.4, 10.6),
         floors=2, ground_h=1.2, floor_h=1.2, facade='stone_beige', roof='mansard', roof_mat='roof_red',
         roof_top_mat='roof_red', roof_h=2.6, roof_inset=1.0, dormer_style='arch', skip_edges=(0, 1),
         balcony_floors=(), bay=1.25, n_auto_chimneys=2, seed=12),
    dict(name='House_Center_Mansard', footprint=rect(8.3, 4.4, 12.1, 8.6),
         floors=3, ground_h=1.25, floor_h=1.15, facade='stone_sand', roof='mansard', roof_h=1.8, roof_inset=0.75,
         dormer_style='gable', skip_edges=(1, 3), balcony_floors=(2,), bay=1.1, seed=14,
         chimneys=[(-0.7, 0.5, 0.7, 0.3, 0.55, 5), (0.6, -0.5, 0.55, 0.3, 0.45, 4), (0.3, 1.1, 0.45, 0.3, 0.6, 3)]),
    dict(name='House_Center_Tall', footprint=rect(12.1, 4.3, 15.5, 7.6),
         floors=4, ground_h=1.3, floor_h=1.25, facade='stone_warm', roof='mansard', roof_mat='zinc_light',
         roof_h=0.8, roof_inset=0.35, dormers=False, balcony_floors=(2, 4), bay=0.85, shutters='shutter_brown', seed=15,
         chimneys=[(-1.0, 1.0, 0.6, 0.3, 0.5, 4)]),
    dict(name='House_Left_Large', footprint=chamfer_rect(6.2, 15.5, 10.4, 20.6, {'SW': 0.35}, seg=2),
         floors=4, ground_h=1.05, floor_h=0.95, facade='stone_cream', roof='mansard', roof_h=1.7, roof_inset=0.75,
         dormer_style='gable', balcony_floors=(2, 4), bay=1.0, n_auto_chimneys=4, seed=13),
    dict(name='House_Right_Dome', footprint=chamfer_rect(17.4, 7.6, 22.0, 11.6, {'SW': 1.5}, seg=4),
         floors=4, ground_h=1.5, floor_h=1.4, facade='stone_sand', roof='mansard_curved', roof_h=2.1,
         roof_inset=1.0, dormer_style='arch', balcony_floors=(2,), bay=1.1, seed=16,
         oriels=[(4, 0.5, 0.9, 1, 3), (7, 0.5, 0.9, 1, 3)], chimneys=[]),
    dict(name='House_Back_Left', footprint=chamfer_rect(11.2, 18.8, 16.6, 22.4, {'SW': 0.6}, seg=3),
         floors=5, ground_h=1.3, floor_h=1.15, facade='stone_tan', roof='attic', roof_top_mat='roof_flat',
         balcony_floors=(5,), bay=0.9, seed=17,
         chimneys=[(-1.8, 1.0, 0.35, 0.3, 0.6, 2), (1.6, 1.1, 0.35, 0.3, 0.7, 2), (-0.4, -0.9, 0.3, 0.3, 0.5, 1),
                   (1.8, -0.6, 0.4, 0.3, 0.5, 2)]),
]

TOWER = dict(location=(18.73, 19.25, BLOCK_Z), height_m=300, scale=16.0 / 300, rotation=0.0)

EXTRAS = [  # (Funktion, Name, Position, Parameter)
    ('cupola', 'Roof_Cupola', (13.8, 21.4), dict(s=0.9)),
    ('kiosk', 'Roof_Kiosk', (19.9, 9.9), dict(s=0.9)),
    ('clutter', 'Roof_Clutter_BackLeft', (14.6, 20.4), dict(area=(2.5, 1.6), n=8, seed=3)),
    ('clutter', 'Roof_Clutter_Right', (18.8, 9.4), dict(area=(1.2, 1.0), n=4, seed=4)),
    ('pavilion', 'Courtyard_Pavilion', (6.0, 12.8), dict(size=(2.0, 1.3, 1.1))),
]

# ---------------------------------------------------------------- Bäume (Bild-Fußpunkt, Typ, Größe)
TREES_IMG = [  # Kronenmitte im Bild (gemessen), Typ, Größe
    ((400, 1235), 'orange', 1.05), ((200, 1000), 'orange', 1.1), ((235, 1150), 'round', 1.1),
    ((290, 1080), 'dark', 1.0), ((350, 875), 'blossom', 1.0), ((430, 765), 'round', 1.0),
    ((395, 815), 'small', 1.3), ((790, 960), 'dark', 1.1), ((800, 1075), 'round', 1.0),
    ((950, 1065), 'round', 1.15), ((900, 1160), 'round', 1.0), ((1195, 730), 'tall', 1.1),
    ((1150, 975), 'dark', 0.9), ((1640, 790), 'round', 1.0), ((1735, 945), 'round', 1.2),
    ((1500, 1250), 'round', 0.95), ((1610, 1215), 'ochre', 1.1), ((1700, 1150), 'round', 1.0),
    ((1790, 1290), 'orange', 1.3), ((1270, 1430), 'orange', 1.05), ((940, 1560), 'small', 1.2),
    ((1085, 1545), 'small', 1.2), ((600, 1360), 'dark', 0.9), ((640, 1430), 'small', 1.1),
]

# Zusätzliches Grün in Höfen/Ecken (im Bild nur teilweise sichtbar -> direkt in Weltkoordinaten)
TREES_WORLD = [
    (13.6, 12.4, 'round', 1.0), (15.0, 14.6, 'dark', 1.05), (12.3, 14.3, 'round', 0.9), (16.0, 12.0, 'small', 1.2),
    (11.2, 11.0, 'dark', 0.9), (14.4, 10.2, 'small', 1.1), (22.0, 15.0, 'round', 1.0), (21.6, 13.0, 'dark', 0.9),
    (16.2, 22.0, 'round', 1.0), (8.0, 13.5, 'small', 1.1), (4.6, 13.0, 'dark', 0.9), (4.4, 15.0, 'round', 0.85),
    (19.0, 4.6, 'small', 1.0), (21.5, 6.0, 'round', 0.8),
    # linke Ecke (dichtes Grün wie in der Vorlage)
    (3.9, 17.8, 'dark', 1.0), (4.8, 19.4, 'round', 1.05), (3.9, 21.0, 'small', 1.2), (5.6, 21.6, 'dark', 0.9),
    (7.5, 21.5, 'round', 0.9), (9.3, 21.6, 'small', 1.1),
    # rechte Ecke / Platz
    (21.0, 7.0, 'small', 1.1), (20.2, 4.0, 'dark', 0.8), (22.2, 9.5, 'round', 0.9),
]
BUSHES = [(13.0, 13.2, 0.35), (15.8, 13.4, 0.3), (17.0, 14.6, 0.35), (12.0, 12.5, 0.3), (16.3, 4.8, 0.3),
          (17.8, 5.0, 0.35), (20.5, 5.2, 0.3), (4.5, 11.6, 0.3), (5.2, 14.3, 0.35), (21.0, 16.5, 0.35),
          (10.8, 15.8, 0.3), (14.0, 15.6, 0.3)]
HEDGES = [[(15.7, 4.0), (17.2, 4.0)], [(4.0, 11.0), (4.0, 13.5)], [(19.0, 3.8), (21.0, 3.8)]]

# ---------------------------------------------------------------- Fahrzeuge (Straße, Spur, Position)
# Straße 'L' = linke vordere Kante (entlang y, x = Spur), 'R' = rechte vordere Kante (entlang x, y = Spur)
LANE = {'outer': 0.95, 'inner': 1.95}
CARS = [
    ('Van_White', 'van', 'car_white', 'L', 'inner', 9.3, +1),
    ('Car_Dark', 'compact', 'car_dark', 'L', 'outer', 13.6, -1),
    ('Car_Gray', 'sedan', 'car_gray', 'R', 'outer', 6.4, +1),
    ('Van_Teal', 'boxvan', 'car_teal', 'R', 'inner', 8.7, -1),
    ('Car_Red', 'sedan', 'car_red', 'R', 'outer', 13.0, +1),
]

LAMPS_IMG = [(1015, 1730), (405, 1390), (1530, 1350), (1820, 1080), (1265, 1610)]
BOLLARDS_IMG = [(1500, 1590), (85, 1395), (1160, 1710)]
