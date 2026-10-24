"""Layers, captions and audio for 20-40 s (frames 598-1200).

Same conventions as build_timeline.py: positions in design units, all
numbers from measurements.json (build_part2.py) unless noted.
"""
import numpy as np

from build_timeline import (D, F, MEAS, M_keys, along, arrow_keys, credit, dedupe, k, label)

# frame-accurate caption words (start frame of each word; end = next start)
WORDS2 = [
    (634, "DIE"), (636, "VON DER"), (644, "BUNDESWEHREIGENEN"), (672, "ZULASSUNGSSTELLE"),
    (695, "AUSGESTELLT"), (710, "WIRD,"), (716, "DIE"), (721, "NUR"), (728, "BUNDESWEHRFAHRZEUGE"),
    (757, "PRÜFT,"), (766, "DENN"), (769, "NATÜRLICH"), (779, "MUSS"), (784, "IN"), (788, "DEUTSCHLAND"),
    (798, "AUCH"), (802, "EIN"), (805, "PANZER", "huge"), (822, "EINE"), (828, "AMTLICHE"),
    (841, "STRAßENZULASSUNG"), (865, "BEKOMMEN."), (880, "IST"), (884, "AUCH"), (887, "GUT"), (891, "SO,"),
    (896, "WAHRSCHEINLICH"), (906, "WÜRDE"), (912, "EIN"), (916, "NORMALER"), (924, "TÜV-PRÜFER"),
    (936, "NEN"), (941, "HERZINFARKT", "big"), (956, "KRIEGEN,"), (965, "WENN"), (968, "ER"), (972, "SIEHT,"),
    (974, "DASS"), (978, "DER"), (982, "LEOPARD 2", "huge"), (1005, "BREITER"), (1018, "IST"), (1022, "ALS"),
    (1028, "DIE"), (1032, "FAHRSPUR"), (1048, "UND"), (1051, "DAS"), (1056, "KANONENROHR"), (1074, "KEIN"),
    (1082, "CE"), (1091, "KENNZEICHEN"), (1106, "HAT."), (1114, None), (1133, "UND"), (1138, "OBWOHL"),
    (1145, "SIE"), (1148, "EIN"), (1153, "SONDERRECHT"), (1168, "HABEN,"), (1176, "MUSS"), (1181, "SICH"),
    (1186, "AUCH"), (1193, "EIN"), (1198, "PANZER", "huge"), (1211, "AN"),
]


def caption_words2():
    out = []
    for cur, nxt in zip(WORDS2, WORDS2[1:]):
        if cur[1] is None:
            continue
        d = {"text": cur[1], "start": F(cur[0]), "end": F(nxt[0]), "frame_start": cur[0], "frame_end": nxt[0]}
        if len(cur) > 2:
            d["size"] = cur[2]
        out.append(d)
    return out


def fix_part1_words(words):
    """Part-1 captions ended at frame 630; the last word runs until 634."""
    for w in words:
        if w["text"] == "SIEGELPLAKETTE":
            w["end"], w["frame_end"] = F(634), 634
    return words


# ------------------------------------------------------------------ 598-643
def scene_seal_plate():
    sp = MEAS["seal_plate"]
    tr = MEAS["seal_plate_track"]
    # 609 is a crossfade TUEV -> seal at unchanged camera (the tracker reads it as a zoom)
    frames = [n for n in range(600, 642) if tr.get(str(n)) and n != 609]
    keys = M_keys(tr, frames, sp["origin"], sp["F"])
    hold = dict([kk for kk in keys if kk["t"] == F(608)][0])
    hold["t"] = F(609)
    keys = sorted(keys + [hold], key=lambda kk: kk["t"])
    last = dict(keys[-1])
    # the plate is pushed up by the house coming in from below (bottom edge 395 -> 60 px)
    out = dict(last, t=F(642), y=last["y"] - 335 * D)
    keys.append(out)
    return [
        {"id": "plate_close_tuev", "type": "image", "asset": "plate_close_tuev", "anchor": [0, 0],
         "start": F(600), "end": F(610), "keys": keys},
        {"id": "plate_close_seal", "type": "image", "asset": "plate_close_seal", "anchor": [0, 0],
         "start": F(609), "end": F(643),
         "keys": [dict(kk, opacity=(0.5 if kk["t"] == F(609) else 1.0)) for kk in keys if kk["t"] >= F(609)]},
        credit("QUELLE: WIKI COMMONS: THORSTENS - CC3, GEMEINFREI", F(602), F(643)),
    ]


# ------------------------------------------------------------------ 641-916
def house_cam_keys():
    """Group keys: the group maps the wide shot (frame 760, ref px * D) to the frame."""
    Mc = np.array(MEAS["house_close_M"])
    sc = float(np.hypot(Mc[0, 0], Mc[1, 0]))
    rot = float(np.degrees(np.arctan2(Mc[1, 0], Mc[0, 0])))

    def cam(n, M=None, dx=0.0, dy=0.0, s=None, r=None):
        M = Mc if M is None else np.array(M)
        ss = float(np.hypot(M[0, 0], M[1, 0])) if s is None else s
        return k(n, x=round((M[0, 2] + dx) * D, 2), y=round((M[1, 2] + dy) * D, 2), scale=round(ss, 5),
                 rot=round(rot if r is None else r, 3))
    ht = MEAS["house_track"]
    # vertical push from below: measured +465 px at 642 (logo template match)
    keys = [cam(641, dy=930), cam(642, dy=465), cam(643), cam(719)]
    keys += [cam(n, M=ht[str(n)]["M"]) for n in (720, 721)]
    keys += [k(722, x=0, y=0, scale=1.0, rot=0.0), k(890, x=0, y=0, scale=1.0, rot=0.0)]
    keys += [cam(n, M=ht[str(n)]["M"]) for n in (891, 892)]
    keys += [cam(893), cam(912), cam(913, dx=-248), cam(914, dx=-640)]
    return keys


def vehicle_layer(name, start_extra=1, end_extra=1):
    v = MEAS["street_vehicles"][name]
    fr, xs = v["frames"], v["x"]
    keys = []
    for n, x in zip(fr, xs):
        keys.append(k(n, x=round((v["sprite_x0"] + x) * D, 2), y=round(v["sprite_y0"] * D, 2)))
    # linear continuation one frame before / after (enter / leave the frame)
    d0 = xs[1] - xs[0]
    d1 = xs[-1] - xs[-2]
    keys.insert(0, k(fr[0] - start_extra, x=round((v["sprite_x0"] + xs[0] - d0 * start_extra) * D, 2),
                     y=round(v["sprite_y0"] * D, 2)))
    keys.append(k(fr[-1] + end_extra, x=round((v["sprite_x0"] + xs[-1] + d1 * end_extra) * D, 2),
                  y=round(v["sprite_y0"] * D, 2)))
    return {"id": "veh_" + name, "type": "image", "asset": "street_" + name, "anchor": [0, 0],
            "start": F(fr[0] - start_extra), "end": F(fr[-1] + end_extra + 1), "keys": dedupe(keys)}


def coin_layer(name, pts, end_frame):
    keys = [k(p[0], x=round(p[1] * D, 2), y=round(p[2] * D, 2), scale=round(p[3] / 0.991, 4)) for p in pts]
    return {"id": name, "type": "image", "asset": "seal_coin", "start": F(pts[0][0]), "end": F(end_frame),
            "keys": keys}


def scene_house():
    hw = MEAS["house_world"]
    Fh = hw["F"]
    Mc = np.array(MEAS["house_close_M"])
    Mi = np.linalg.inv(np.vstack([Mc, [0, 0, 1]]))

    def close_to_world(p):
        q = Mi @ np.array([p[0], p[1], 1.0])
        return q[0] * D, q[1] * D
    vi = close_to_world(MEAS["villager_idle_close_center"])
    vs = close_to_world(MEAS["villager_seal_close_center"])
    rise = MEAS["villager_rise_dy"]
    ws = MEAS["house_world"]["window_wide"]
    # the villager is clipped by the window opening (rises from below the sill)
    win = [ws[0] * D, ws[1] * D, (ws[2] - ws[0]) * D, (ws[3] - ws[1]) * D]
    idle_keys = [k(672, x=vi[0], y=vi[1] + rise["672"] / Fh * D), k(673, y=vi[1] + rise["673"] / Fh * D),
                 k(674, y=vi[1])]
    villager = {"id": "villager_window", "type": "group", "pivot": [0, 0], "isolate": True, "clip": win,
                "keys": [k(672, x=0, y=0)], "children": [
                    {"id": "villager_idle_a", "type": "image", "asset": "villager_idle", "start": F(672),
                     "end": F(698), "keys": idle_keys},
                    {"id": "villager_seal", "type": "image", "asset": "villager_seal", "start": F(698),
                     "end": F(832), "keys": [k(698, x=vs[0], y=vs[1])]},
                    {"id": "villager_idle_b", "type": "image", "asset": "villager_idle", "start": F(832),
                     "keys": [k(832, x=vi[0], y=vi[1])]},
                ]}
    for ch in villager["children"]:
        ch["props"] = {"scale": 1.0}
    fl = MEAS["seal_flights"]
    sx, sy = MEAS["seal_stamp_845"]
    tank = MEAS["street_vehicles"]["tank_street"]
    tx = dict(zip(tank["frames"], tank["x"]))
    x845 = tx[845]
    stamp_keys = [k(n, x=round((sx + tx[n] - x845) * D, 2), y=round(sy * D, 2))
                  for n in (840, 861, 876)]
    stamp_keys.append(k(877, x=round((sx + tx[876] - x845 - 73.8) * D, 2), y=round(sy * D, 2)))
    house = {"id": "house_world", "type": "group", "pivot": [0, 0], "start": F(641), "end": F(915),
             "keys": house_cam_keys(), "children": [
                 {"id": "house_bg", "type": "image", "asset": "house_world", "anchor": [0, 0],
                  "keys": [k(641, x=hw["origin"][0] * D, y=hw["origin"][1] * D)]},
                 villager,
                 coin_layer("seal_flight_1", fl["seal1"], 735),
                 coin_layer("seal_flight_2", fl["seal2"], 759),
                 coin_layer("seal_flight_3", fl["seal3"], 784),
                 vehicle_layer("truck1"), vehicle_layer("crane"), vehicle_layer("truck3"),
                 vehicle_layer("tank_street"),
                 coin_layer("seal_flight_4", fl["seal4"], 840),
                 {"id": "seal_stamp", "type": "image", "asset": "seal_stamp", "start": F(840), "end": F(878),
                  "keys": dedupe(stamp_keys)},
             ]}
    return [
        house,
        credit("QUELLE: WIKI COMMONS: BUNDESWEHR - GEMEINFREI", F(643), F(675)),
        credit("QUELLE: WIKI COMMONS: BUNDESWEHR - GEMEINFREI, TOBIAS WOLTER - CC3", F(675), F(693)),
        credit("QUELLE: WIKI COMMONS: BUNDESWEHR - GEMEINFREI, TOBIAS WOLTER - CC3, THORSTENS - GEMEINFREI",
               F(693), F(729)),
        credit("QUELLE: WIKI COMMONS: GONZOSFT - CC3", F(729), F(752)),
        credit("QUELLE: WIKI COMMONS: POWIDL - GEMEINFREI", F(752), F(774)),
        credit("QUELLE: WIKI COMMONS: UNTERILLERTALER - CC3", F(774), F(794)),
        credit("QUELLE: WIKI COMMONS: BUNDESWEHR - GEMEINFREI, TOBIAS WOLTER - CC3, THORSTENS - GEMEINFREI",
               F(794), F(807)),
        credit("QUELLE: WIKI COMMONS: BUNDESWEHR-FOTOS - CC2", F(807), F(878)),
        credit("QUELLE: WIKI COMMONS: BUNDESWEHR - GEMEINFREI, TOBIAS WOLTER - CC3", F(878), F(916)),
        label("[Q6]", F(649), F(782), appear=(649, 659, 48), exit=(773, 781, 64)),
        label("[Q7]", F(790), F(872), appear=(790, 799, 64), exit=(864, 871, 64)),
    ]


# ------------------------------------------------------------------ 916-974
def scene_sweat():
    import build_part2 as BP
    tint = [k(n, opacity=a) for n, a in BP.RED_TINT_KEYS] + [k(973.99, opacity=0.75)]
    c = BP.RED_TINT_C[::-1].tolist()
    return [
        {"id": "sweat_meme", "type": "sequence", "asset": "sweat_meme", "anchor": [0, 0], "start": F(924),
         "end": F(974), "keys": [k(924, x=0, y=0)]},
        {"id": "red_tint", "type": "solid", "color": c, "start": F(923), "end": F(974), "keys": tint},
    ]


# ------------------------------------------------------------------ 981-1143
def M_to_keys(n, M):
    M = np.array(M)
    s_ = float(np.hypot(M[0, 0], M[1, 0]))
    r_ = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
    return k(n, x=round(M[0, 2] * D, 2), y=round(M[1, 2] * D, 2), scale=round(s_, 5), rot=round(r_, 3))


def scene_leo():
    tr = MEAS["leo_track"]
    cam = [M_to_keys(n, tr[str(n)]["M"]) for n in range(1007, 1142) if tr.get(str(n))]
    cam = dedupe(cam)
    c = MEAS["leo_tank_center"]
    tank_keys = []
    for n in range(981, 1008):
        M = np.array(MEAS["leo_pop_affine"][str(n)]["M"])
        p = M @ np.array([c[0], c[1], 1.0])
        tank_keys.append(k(n, x=round(p[0] * D, 2), y=round(p[1] * D, 2),
                           sx=round(float(np.hypot(M[0, 0], M[1, 0])), 4),
                           sy=round(float(np.hypot(M[0, 1], M[1, 1])), 4)))
    tank_keys = dedupe(tank_keys)
    hr = MEAS["leo_cannon_hr"]
    # CE mark: bbox centre measured in frame 1080 (static close-up camera)
    M80 = np.vstack([np.array(tr["1080"]["M"]), [0, 0, 1]])
    cx, cy = MEAS["ce_mark"]["center_1080"]
    q = np.linalg.inv(M80) @ np.array([cx, cy, 1.0])
    s80 = float(np.hypot(M80[0, 0], M80[1, 0]))
    ce = {"id": "ce_mark", "type": "image", "asset": "ce_mark", "start": F(1070), "end": F(1089),
          "keys": [k(1070, x=round(q[0] * D, 2), y=round(q[1] * D, 2), scale=round(1 / s80, 5), opacity=1.0),
                   k(1084, opacity=1.0), k(1088, opacity=0.0)]}
    group = {"id": "leo_cam", "type": "group", "pivot": [0, 0], "start": F(981), "end": F(1143), "keys": cam,
             "children": [
                 # crossfade from the stripes background over 4 frames (measured 1020-1024)
                 {"id": "leo_world", "type": "image", "asset": "leo_world", "anchor": [0, 0], "start": F(1020),
                  "keys": [k(1020, x=0, y=0, opacity=0.0), k(1024, opacity=1.0)]},
                 {"id": "leo_tank", "type": "image", "asset": "leo_tank", "keys": tank_keys},
                 {"id": "leo_cannon_hr", "type": "image", "asset": "leo_cannon_hr", "anchor": [0, 0],
                  "start": F(1058), "end": F(1105),
                  "keys": [k(1058, x=hr["origin"][0] * D, y=hr["origin"][1] * D)]},
                 ce,
             ]}
    tip, ang = (298.0, 554.0), 228.4
    arrow = {"id": "arrow_fahrspur", "type": "arrow", "start": F(1033), "end": F(1059),
             "keys": arrow_keys([(1033, *along(tip, ang, 234), ang), (1034, *tip, ang), (1057, *tip, ang),
                                 (1058, *along(tip, ang, 234), ang)])}
    sat = [(1109, 1.0), (1110, 0.999), (1111, 0.825), (1112, 0.67), (1113, 0.456), (1114, 0.262),
           (1115, 0.128), (1116, 0.03), (1125, 0.0)]
    val = [(1109, 1.0), (1110, 0.933), (1116, 0.894), (1121, 0.891), (1125, 0.865), (1130, 0.77),
           (1135, 0.615), (1139, 0.46)]
    wc = MEAS["wasted_text_center"]
    return [
        group,
        arrow,
        {"id": "wasted_desaturate", "type": "grade", "start": F(1110), "end": F(1140),
         "keys": [k(n, saturation=v) for n, v in sat]},
        {"id": "wasted_text", "type": "image", "asset": "wasted_text", "start": F(1110), "end": F(1140),
         "keys": [k(1110, x=wc[0] * D, y=wc[1] * D)]},
        {"id": "wasted_darken", "type": "grade", "start": F(1110), "end": F(1140),
         "keys": [k(n, value=v) for n, v in val]},
    ]


# ------------------------------------------------------------------ 1141-1200
def scene_stvo():
    pos = [(1140, 854), (1141, 574), (1142, 191), (1143, 0), (1189, 0), (1190, 383), (1191, 735)]
    keys = [k(n, x=0, y=dy * D) for n, dy in pos]
    rev = [(1152, 0.0), (1153, 0.16), (1154, 0.54), (1155, 0.94), (1156, 1.0)]
    marked_keys = merge_keys(keys, [k(n, reveal=v) for n, v in rev])
    return [
        {"id": "stvo_page", "type": "image", "asset": "stvo_page", "anchor": [0, 0], "start": F(1141),
         "end": F(1192), "keys": keys},
        {"id": "stvo_page_marked", "type": "image", "asset": "stvo_page_marked", "anchor": [0, 0],
         "start": F(1152), "end": F(1192), "reveal_map": "wipe_lr_112_363", "reveal_soft": 0.02,
         "keys": marked_keys},
    ]


def merge_keys(a, b):
    by_t = {}
    for key in a + b:
        by_t.setdefault(key["t"], {}).update(key)
    return [by_t[t] for t in sorted(by_t)]


def credits_labels_3():
    return [
        credit("QUELLE: WIKI COMMONS: SONAZ - CC3", F(981), F(1070)),
        credit("QUELLE: WIKI COMMONS: SONAZ - CC3, MATTHIASDD - GEMEINFREI", F(1070), F(1094)),
        credit("QUELLE: WIKI COMMONS: SONAZ - CC3", F(1094), F(1142)),
        credit("QUELLE: STVO (GESETZE-IM-INTERNET.DE)", F(1142), F(1191)),
        label("[Q8]", F(1190), F(1352)),
    ]


def layers_part2():
    return [*scene_seal_plate(), *scene_house(), *scene_sweat(), *scene_leo(), *scene_stvo(),
            *credits_labels_3()]


# onsets measured on the separated effect stem (spectral flux + spectrogram)
AUDIO2 = [
    {"id": "sfx_seal_pop", "src": "@sfx/pop", "start": 20.30, "gain_db": -6.5},
    {"id": "sfx_house_swoosh", "src": "@sfx/swoosh", "start": 21.33, "gain_db": -14.0},
    {"id": "sfx_truck1", "src": "@sfx/engine_pass", "start": 24.25, "gain_db": -12.0},
    {"id": "sfx_crane", "src": "@sfx/engine_pass", "start": 24.98, "gain_db": -12.0},
    {"id": "sfx_truck3", "src": "@sfx/engine_pass", "start": 25.8, "gain_db": -12.0},
    {"id": "sfx_tank", "src": "@sfx/engine_pass", "start": 26.9, "gain_db": -16.0},
    {"id": "sfx_seal_fly", "src": "@sfx/chirp_up", "start": 27.55, "gain_db": -26.0},
    {"id": "sfx_tank_out", "src": "@sfx/engine_pass", "start": 28.6, "gain_db": -18.0},
    {"id": "sfx_zoom_window", "src": "@sfx/swoosh", "start": 29.70, "gain_db": -14.0},
    {"id": "sfx_meme_in", "src": "@sfx/swoosh", "start": 30.50, "gain_db": -14.0},
    {"id": "sfx_panic_drone", "src": "@sfx/drone_low", "start": 30.95, "gain_db": -20.0},
    {"id": "sfx_leo_pop", "src": "@sfx/impact_low", "start": 32.70, "gain_db": -11.5},
    {"id": "sfx_breiter", "src": "@sfx/boing", "start": 33.62, "gain_db": -20.0},
    {"id": "sfx_arrow", "src": "@sfx/pop", "start": 34.44, "gain_db": -14.0},
    {"id": "sfx_cannon_zoom", "src": "@sfx/swoosh", "start": 35.25, "gain_db": -13.0},
    {"id": "sfx_zoom_out", "src": "@sfx/swoosh_down", "start": 36.80, "gain_db": -13.0},
    {"id": "sfx_wasted", "src": "@sfx/wasted", "start": 37.03, "gain_db": -2.0},
    {"id": "sfx_stvo_in", "src": "@sfx/swoosh", "start": 38.0, "gain_db": -14.0},
    {"id": "sfx_stvo_out", "src": "@sfx/swoosh_down", "start": 39.65, "gain_db": -14.0},
]
