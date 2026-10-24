"""Layers, captions and audio for 40-50.5 s (frames 1190-1515).

Same conventions as build_timeline.py / timeline_part2.py: positions in design
units, numbers from measurements.json (build_part3.py) unless noted.
"""
import numpy as np

from build_timeline import D, F, MEAS, credit, dedupe, k, label
from timeline_part2 import M_to_keys, merge_keys

END_FRAME = 1515

WORDS3 = [
    (1211, "AN"), (1214, "DIE"), (1217, "STRAßENVERKEHRSORDNUNG"), (1248, "HALTEN."), (1258, "ER"),
    (1262, "MUSS"), (1268, "ALSO"), (1273, "BEI"), (1278, "ROT"), (1286, "STOPPEN."), (1307, "AUßER,"),
    (1313, "ER"), (1318, "HAT"), (1320, "DIE"), (1324, "AMPEL"), (1332, "ÜBERROLLT,", "medium"),
    (1351, "DANN"), (1360, "GILT"), (1368, "GLAUBE"), (1374, "ICH"), (1378, "RECHTS"), (1384, "VOR"),
    (1387, "LINKS."), (1397, "GEBLITZT", "big"), (1409, "WERDEN"), (1418, "KÖNNEN"), (1423, "SIE"),
    (1426, "ÜBRIGENS"), (1438, "AUCH,"), (1448, "OBWOHL"), (1457, "DAS"), (1460, "DANN"),
    (1464, "SCHWIERIGER"), (1478, "ZU"), (1483, "ERKENNEN"), (1494, "IST,"), (1501, "DENN..."),
    (END_FRAME, None),
]


def caption_words3():
    out = []
    for cur, nxt in zip(WORDS3, WORDS3[1:]):
        if cur[1] is None:
            continue
        d = {"text": cur[1], "start": F(cur[0]), "end": F(nxt[0]), "frame_start": cur[0], "frame_end": nxt[0]}
        if len(cur) > 2:
            d["size"] = cur[2]
        out.append(d)
    return out


def fix_part2_words(words):
    """Part-2 captions ended at frame 1211 with 'AN'; part 3 starts there."""
    return [w for w in words if not (w["text"] == "AN" and w["frame_start"] == 1211)]


# ------------------------------------------------------------------ 1196-1351
def scene_street():
    tr = MEAS["tank_side_track"]
    c = MEAS["tank_side_center_1240"]

    def tank_key(n, M):
        M = np.array(M)
        p = M @ np.array([c[0], c[1], 1.0])
        return k(n, x=round(p[0] * D, 2), y=round(p[1] * D, 2), scale=round(float(np.hypot(M[0, 0], M[1, 0])), 4))
    frames = [n for n in range(1200, 1313) if tr.get(str(n)) and not (1287 <= n <= 1295)]
    tank = [tank_key(n, tr[str(n)]["M"]) for n in frames]
    # 1200: drives in from the right (measured tx 207 at 1200, 4 at 1201)
    tank.insert(0, tank_key(1199, np.array(tr["1200"]["M"]) + np.array([[0, 0, 200], [0, 0, 0]])))
    # 1313-1321: drives off diagonally and shrinks (template match), then -24.7 px/frame
    drive = {1313: (241.0, 341.5, 0.98), 1314: (221.5, 327.5, 0.96), 1315: (201.5, 312.5, 0.94),
             1316: (182.0, 298.0, 0.92), 1317: (162.5, 283.0, 0.90), 1318: (143.0, 268.0, 0.88),
             1319: (123.5, 254.0, 0.84), 1320: (104.0, 239.0, 0.82), 1321: (84.5, 225.0, 0.80)}
    for n, (x, y, sc) in drive.items():
        tank.append(k(n, x=x * D, y=y * D, scale=sc))
    tank.append(k(1342, x=(84.5 - 24.7 * 21) * D, y=225.0 * D, scale=0.8))
    tank = dedupe(sorted(tank, key=lambda kk: kk["t"]))
    # the road world slides in from the left at 1214-1217 (right edge 30 -> 275 -> 480 px)
    world_keys = [k(1214, x=-480 * D, y=0), k(1215, x=(30 - 480) * D), k(1216, x=(275 - 480) * D), k(1217, x=0)]
    # clouds: measured drift (sky strip pixel x -> frame x = x + x0 + cx)
    sky = MEAS["street2_sky"]
    cxs = MEAS["street_cloud_x"]
    sky_keys = dedupe([k(int(n), x=round((sky["x0"] + v) * D, 2), y=0) for n, v in sorted(cxs.items(), key=lambda t: int(t[0]))])
    lc = MEAS["traffic_light_center"]
    light_h = 258 - 27
    pivot = (lc[0], 258.0)                       # foot of the pole
    light = {"id": "traffic_light", "type": "group", "pivot": [pivot[0] * D, pivot[1] * D], "start": F(1274),
             "end": F(1329),
             "keys": [k(1274, x=pivot[0] * D, y=(pivot[1] + 160) * D, rot=0), k(1275, y=pivot[1] * D),
                      # pushed along by the tank (lamp head measured x 68 -> 34 -> 19 -> 9, gone at 1329)
                      k(1325, x=pivot[0] * D, rot=0), k(1326, x=(pivot[0] - 31) * D, rot=-4),
                      k(1327, x=(pivot[0] - 49) * D, rot=-8), k(1328, x=(pivot[0] - 59) * D, rot=-14)],
             "children": [{"type": "image", "asset": "traffic_light",
                           "keys": [k(1274, x=lc[0] * D, y=lc[1] * D)]}]}
    flat = MEAS["traffic_light_flat_center"]
    st = MEAS["stop_sign_center"]
    sa = MEAS["stop_sign_alpha"]
    stop = {"id": "stop_sign", "type": "image", "asset": "stop_sign", "start": F(1287), "end": F(1301),
            "keys": [k(int(n), x=st[0] * D, y=st[1] * D, opacity=v) for n, v in sorted(sa.items(), key=lambda t: int(t[0]))]}
    group = {"id": "street2", "type": "group", "pivot": [0, 0], "start": F(1214), "end": F(1352),
             "isolate": True, "clip": [0, 0, 1080, 1920],
             "keys": world_keys, "children": [
                 {"id": "street2_bg", "type": "image", "asset": "street2_bg", "anchor": [0, 0],
                  "keys": [k(1214, x=0, y=0)]},
                 {"id": "street2_sky", "type": "image", "asset": "street2_sky", "anchor": [0, 0],
                  "keys": sky_keys},
                 light,
                 {"id": "traffic_light_flat", "type": "image", "asset": "traffic_light_flat", "start": F(1329),
                  "keys": [k(1329, x=flat[0] * D, y=flat[1] * D)]},
             ]}
    tf = MEAS["tank_far"]
    # rear part: offset to the tank centre measured at scale 0.8, scaled with the tank
    ox, oy = tf["cx_1321"] - 84.5, tf["cy"] - 225.0
    far_keys = [k(n, x=(x + ox * sc / 0.8) * D, y=(y + oy * sc / 0.8) * D, scale=sc / 0.8)
                for n, (x, y, sc) in drive.items()]
    # same offset for the approach (1199-1312): the rear is visible while the tank is small
    for kk in tank:
        if kk["t"] < F(1313) and "x" in kk:
            sc = kk.get("scale", 1.0)
            far_keys.append(k(round(kk["t"] * 30), x=kk["x"] + ox * sc / 0.8 * D, y=kk["y"] + oy * sc / 0.8 * D,
                              scale=sc / 0.8))
    far_keys.sort(key=lambda kk: kk["t"])
    far_keys.append(k(1342, x=(tf["cx_1321"] + tf["speed"] * 21) * D, y=tf["cy"] * D, scale=1.0))
    far = {"id": "tank_side_far", "type": "image", "asset": "tank_side_far", "start": F(1199), "end": F(1342),
           "keys": far_keys}
    return [group,
            far,
            {"id": "tank_side", "type": "image", "asset": "tank_side", "start": F(1199), "end": F(1342),
             "keys": tank},
            stop]


# ------------------------------------------------------------------ 1351-1393
def scene_crossing():
    tc = MEAS["tank_top_rest_center"]
    dy = MEAS["tank_top_dy"]
    tank = dedupe([k(int(n), x=tc[0] * D, y=(tc[1] + v) * D) for n, v in sorted(dy.items(), key=lambda t: int(t[0]))])
    cx = {int(n): v for n, v in MEAS["cyclist_cx"].items() if v is not None}
    speed = (cx[1392] - cx[1370]) / 22.0
    cyc = [k(1368, x=(cx[1370] - 2 * speed) * D, y=MEAS["cyclist_cy"] * D),
           k(1392, x=cx[1392] * D, y=MEAS["cyclist_cy"] * D)]
    return [
        {"id": "crossing_bg", "type": "image", "asset": "crossing_bg", "anchor": [0, 0], "start": F(1352),
         "end": F(1393), "keys": [k(1352, x=0, y=0)]},
        {"id": "tank_top", "type": "image", "asset": "tank_top", "start": F(1352), "end": F(1393), "keys": tank},
        {"id": "cyclist", "type": "image", "asset": "cyclist", "start": F(1368), "end": F(1393), "keys": cyc},
    ]


# ------------------------------------------------------------------ 1393-1462
def scene_blitzer():
    Mc = MEAS["blitzer_close_M"]
    # camera: close-up (s = 2.0) until 1417, zoom out 1418-1420, pan out 1451-1453
    cam = [M_to_keys(1393, Mc), M_to_keys(1417, Mc),
           k(1418, x=-37.29 * D, y=-1.02 * D, scale=1.8), k(1419, x=-20.56 * D, y=0.55 * D, scale=1.4),
           k(1420, x=0, y=0, scale=1.0, rot=0), k(1450, x=0, y=0, scale=1.0),
           k(1451, x=-171.8 * D, y=-1.1 * D, scale=1.1)]
    jp = MEAS["jeep_pass_1432"]
    lx = MEAS["jeep_pass_left_x"]
    jeep = [k(int(n), x=(v + jp["w"] / 2) * D, y=(jp["y0"] + jp["h"] / 2) * D) for n, v in sorted(lx.items(), key=lambda t: int(t[0]))]
    fw = MEAS["flash_white"]
    fc = MEAS["flash_centre"]
    world = {"id": "blitzer_world", "type": "group", "pivot": [0, 0], "start": F(1393), "end": F(1452), "keys": cam,
             "children": [
                 {"id": "blitzer_bg", "type": "image", "asset": "blitzer_bg", "anchor": [0, 0], "keys": [k(1393, x=0, y=0)]},
                 {"id": "jeep_pass", "type": "image", "asset": "jeep_pass", "start": F(1431), "end": F(1435), "keys": jeep},
             ]}
    flash = [
        {"id": "flash_white", "type": "solid", "color": [255, 255, 255], "start": F(1431), "end": F(1435),
         "keys": [k(int(n), opacity=v) for n, v in sorted(fw.items(), key=lambda t: int(t[0]))]},
        {"id": "flash_glow", "type": "glow", "start": F(1432), "end": F(1434), "softness": 0.8,
         "keys": [k(1432, x=fc[0] * D, y=fc[1] * D, radius=110 * D, opacity=0.9), k(1433, radius=80 * D, opacity=0.5)]},
    ]
    road = {"id": "road_blur_bg", "type": "image", "asset": "road_blur_bg", "anchor": [0, 0], "start": F(1451),
            "end": F(1485), "keys": [k(1453, x=0, y=0)]}
    return [road, world, *flash]


# ------------------------------------------------------------------ 1462-1515
def scene_final():
    tr = MEAS["final_jeep_track"]
    ck = MEAS["photo_card_keys"]
    ckeys = [k(int(n), x=v[0] * D, y=v[1] * D, scale=v[2]) for n, v in sorted(ck.items(), key=lambda t: int(t[0]))]
    ckeys.append(k(1483, x=240.0 * D, y=335.5 * D, scale=1.75))       # border rows 82..589 measured
    card = {"id": "photo_card", "type": "image", "asset": "photo_card", "start": F(1462), "end": F(1484),
            "keys": ckeys}
    full = {"id": "final_jeep", "type": "image", "asset": "final_jeep", "start": F(1484), "end": F(END_FRAME + 1),
            "anchor": [0, 0], "keys": [M_to_keys(n, tr[str(n)]) for n in (1484, 1485)]}
    return [card, full]


def credits_labels_4():
    return [
        credit("QUELLE: WIKI COMMONS: BUNDESWEHR-FOTOS - CC2", F(1215), F(1352)),
        credit("QUELLE: WIKI COMMONS: RA BOE - CC3, SONAZ - CC2", F(1352), F(1437)),
        credit("QUELLE: WIKI COMMONS: RA BOE - CC3", F(1437), F(1451)),
        credit("QUELLE: WIKI COMMONS: DARKONE - CC2.5", F(1464), F(END_FRAME + 1)),
        label("[Q9]", F(1402), F(1452)),
    ]


def layers_part3():
    return [*scene_street(), *scene_crossing(), *scene_blitzer(), *scene_final(), *credits_labels_4()]


AUDIO3 = [
    {"id": "sfx_tank_in", "src": "@sfx/engine_pass", "start": 40.0, "gain_db": -22.0},
    {"id": "sfx_road_in", "src": "@sfx/swoosh", "start": 40.45, "gain_db": -18.5},
    {"id": "sfx_light_pop", "src": "@sfx/pop", "start": 42.45, "gain_db": -14.5},
    {"id": "sfx_stop", "src": "@sfx/impact_low", "start": 42.9, "gain_db": -4.5},
    {"id": "sfx_tank_drive", "src": "@sfx/engine_pass", "start": 43.75, "gain_db": -8.5},
    {"id": "sfx_light_crash", "src": "@sfx/impact_low", "start": 44.2, "gain_db": -21.0},
    {"id": "sfx_crossing", "src": "@sfx/swoosh", "start": 45.0, "gain_db": -14.0},
    {"id": "sfx_blitzer_zoom", "src": "@sfx/swoosh_down", "start": 47.25, "gain_db": -17.0},
    {"id": "sfx_flash", "src": "@sfx/camera_flash", "start": 47.7, "gain_db": -11.5},
    {"id": "sfx_pan", "src": "@sfx/swoosh", "start": 48.35, "gain_db": -22.0},
    {"id": "sfx_card_pop", "src": "@sfx/pop", "start": 48.73, "gain_db": -21.0},
    {"id": "sfx_card_zoom", "src": "@sfx/swoosh", "start": 49.4, "gain_db": -15.5},
]
