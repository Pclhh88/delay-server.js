"""Builds timeline.json for the Mary Celeste short (collage style, dark version).

    python3 projects/mary-celeste/build/build_timeline.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(PROJ)))

from shortsfactory.collage.choreo import Show, exit_to, fly_camera, path_keys, pop_in, slide_in  # noqa: E402

S = Show(os.path.join(HERE, "assets", "meta.json"), os.path.join(PROJ, "analysis", "words.json"))
w, rec, M = S.w, S.rec, S.META
END = 64.29
mp = M["map"]
P = {k: tuple(v) for k, v in mp["places"].items()}
MAP_H = mp["proj"]["h"]


def focus(xy, s):
    """camera target clamped so the frame never leaves the map vertically"""
    x, y = xy
    half = 960 / s
    return x, min(max(y, half), MAP_H - half), s


# ---------------------------------------------------------------- word times
T_MARY, T_CELESTE = w("Mary"), w("Celeste")
T_EIN, T_MENSCHEN, T_BORD_END = w("Ein"), w("Menschen"), w("Bord", 0, "end")
T_GEFUNDEN, T_DEZ, T_MITTEN = w("Gefunden"), w("Dezember"), w("mitten")
T_SEGEL, T_LADUNG1, T_SECHS = w("Segel"), w("Ladung"), w("sechs")
T_GESTARTET, T_NEW = w("Gestartet"), w("New")
T_KAPITAEN, T_SEINE, T_SIEBEN = w("Kapitän"), w("seine"), w("sieben")
T_LADUNG2, T_UEBER, T_FAESSER, T_ALK_END = w("Ladung", 22), w("über", 22), w("Fässer"), w("Alkohol", 0, "end")
T_VIER, T_ANDERES, T_DEI, T_AZOREN = w("Vier"), w("anderes"), w("Dei"), w("Azoren")
T_PERS, T_NUR, T_FEHLT, T_UND_S, T_SEXTANT = w("Persönliche"), w("Nur"), w("fehlt"), w("Und", 35), w("Sextant")
T_FINDER1, T_GIB, T_BERGE = w("Finder"), w("Gibraltar"), w("Bergelohn")
T_DOCH, T_FLECKEN1, T_SCHWERT, T_KERBEN = w("Doch"), w("Flecken"), w("Schwert"), w("Kerben")
T_VERDACHT, T_MORD, T_GETOETET, T_GELD = w("Verdacht"), w("Mord"), w("getötet"), w("Geld")
T_ARZT, T_UNTERS, T_KEIN, T_ROST1 = w("Arzt"), w("untersucht"), w("kein"), w("Rost")
T_BEKOMMEN, T_GELDES_END = w("bekommen"), w("Geldes", 0, "end")
T_NUR2, T_ZEHN, T_DAS_BOOT, T_GEFUNDEN2 = w("Nur", 56), w("zehn"), w("Das", 60), w("gefunden", 60)
T_WAS, T_NAME = w("Was"), w("Name")

# ---------------------------------------------------------------- map + camera
found, ny, gib, azo = P["found"], P["new_york"], P["gibraltar"], P["azores"]
route1 = [ny, ((ny[0] + found[0]) / 2, ny[1] + 60), found]
route2 = [found, ((found[0] + gib[0]) / 2, found[1] + 20), gib]
T_R1A, T_R1B = T_VIER + 0.1, T_AZOREN - 0.2
T_R2A, T_R2B = T_FINDER1, T_BERGE + 0.2
ship_keys, prog1 = path_keys(route1, T_R1A, T_R1B)
tow_keys, prog2 = path_keys(route2, T_R2A, T_R2B)

CAM = [
    (0.0, *focus(found, 1.0), None),
    (T_GEFUNDEN, *focus(found, 1.0), "linear"),
    (T_MITTEN + 0.2, *focus(found, 1.7), "inout"),
    (T_GESTARTET - 0.1, *focus(found, 1.8), "linear"),
    (T_NEW, *focus(ny, 1.7), "inout"),
    (T_ALK_END, *focus((ny[0] + 40, ny[1] + 10), 1.8), "linear"),
]
for k in ship_keys[::3]:                      # follow the ship across the Atlantic
    CAM.append((k["t"], *focus((k["x"], k["y"]), 1.35), "linear"))
CAM += [
    (T_AZOREN + 0.5, *focus(found, 1.9), "inout"),
    (T_FINDER1 - 0.05, *focus(found, 1.95), "linear"),
]
for k in tow_keys[::3]:
    CAM.append((k["t"], *focus((k["x"], k["y"]), 1.5), "linear"))
CAM += [
    (T_DOCH + 0.3, *focus(gib, 2.0), "inout"),
    (T_NUR2 - 0.1, *focus(gib, 2.15), "linear"),
    (T_ZEHN, *focus(((found[0] + azo[0]) / 2, found[1] + 40), 2.4), "inout"),
    (T_WAS, *focus(((found[0] + azo[0]) / 2, found[1] + 40), 2.6), "linear"),
    (END, *focus(found, 1.0), "inout"),         # back to the opening view (loop)
]
cam_scale, cam_pan = fly_camera(CAM, END)
ds = M["dot"]
MAP_CHILDREN = [
    {"id": "map", "type": "image", "asset": "map", "anchor": [0, 0], "props": {"x": 0, "y": 0}, "keys": []},
    {"id": "dot_found", "type": "image", "asset": "dot", "start": T_MITTEN, "end": END + 1,
     "keys": [{"t": T_MITTEN, "x": found[0], "y": found[1], "scale": 0.0},
              {"t": T_MITTEN + 0.15, "scale": 0.3, "ease": "out"}, {"t": T_MITTEN + 0.3, "scale": 0.22}]},
    {"id": "dot_ny", "type": "image", "asset": "dot", "start": T_NEW, "end": END + 1,
     "keys": [{"t": T_NEW, "x": ny[0], "y": ny[1], "scale": 0.0},
              {"t": T_NEW + 0.15, "scale": 0.3, "ease": "out"}, {"t": T_NEW + 0.3, "scale": 0.22}]},
    {"id": "dot_gib", "type": "image", "asset": "dot", "start": T_GIB, "end": END + 1,
     "keys": [{"t": T_GIB, "x": gib[0], "y": gib[1], "scale": 0.0},
              {"t": T_GIB + 0.15, "scale": 0.3, "ease": "out"}, {"t": T_GIB + 0.3, "scale": 0.22}]},
    {"id": "route1", "type": "dashed_path", "start": T_R1A, "end": END + 1, "points": [list(p) for p in route1],
     "props": {"x": 0, "y": 0}, "width": 5, "dash": 16, "gap": 11, "color": [232, 112, 58], "keys": prog1},
    {"id": "route2", "type": "dashed_path", "start": T_R2A, "end": END + 1, "points": [list(p) for p in route2],
     "props": {"x": 0, "y": 0}, "width": 5, "dash": 16, "gap": 11, "color": [232, 112, 58], "keys": prog2},
]
ship_s = S.scale_for("st_ship", 170)
ship_keys[0].update({"scale": ship_s})
MAP_CHILDREN.append({"id": "ship_map", "type": "image", "asset": "st_ship", "start": T_R1A, "end": T_AZOREN + 1.0,
                     "anchor": M["st_ship"]["anchor"], "keys": ship_keys + [
                         {"t": T_AZOREN + 0.3, "opacity": 1.0}, {"t": T_AZOREN + 0.9, "opacity": 0.0}]})
# Dei Gratia: same sticker mirrored, approaching from the east
dg = [{"t": T_ANDERES, "x": found[0] + 260, "y": found[1] - 60, "scale": ship_s, "sx": -1, "opacity": 0.0},
      {"t": T_ANDERES + 0.1, "opacity": 1.0},
      {"t": T_AZOREN, "x": found[0] + 60, "y": found[1] - 20, "ease": "out"},
      {"t": T_PERS - 0.2, "opacity": 1.0}, {"t": T_PERS + 0.3, "opacity": 0.0}]
MAP_CHILDREN.append({"id": "deigratia_map", "type": "image", "asset": "st_ship", "start": T_ANDERES,
                     "end": T_PERS + 0.4, "anchor": M["st_ship"]["anchor"], "keys": dg})
tow_keys[0].update({"scale": ship_s})
MAP_CHILDREN.append({"id": "tow_map", "type": "image", "asset": "st_ship", "start": T_R2A, "end": T_DOCH + 0.6,
                     "anchor": M["st_ship"]["anchor"], "keys": tow_keys + [
                         {"t": T_DOCH, "opacity": 1.0}, {"t": T_DOCH + 0.5, "opacity": 0.0}]})
S.layers.append({"id": "cam", "type": "group", "pivot": [540, 960], "keys": cam_scale, "children": [
    {"id": "cam_pan", "type": "group", "pivot": [0, 0], "keys": cam_pan, "children": MAP_CHILDREN}]})
rec("waves_hull", 0.0, -22, trim=[0.0, 19.0], fade=2.0)
rec("ship_creak", 0.0, -18, trim=[0.0, 13.5], fade=1.5)
rec("ocean_wind", 26.0, -24, trim=[0.0, 12.0], fade=1.5)

# ---------------------------------------------------------------- 1 hook: the empty ship
SHIP_W = 900


def opening_ship(id_, t0, t1, appear):
    s = S.scale_for("st_ship", SHIP_W)
    if appear:
        k = pop_in(t0, 540, 900, s, -2, dur=0.32)
    else:
        k = [{"t": t0, "x": 540, "y": 900, "scale": s, "rot": -2, "opacity": 1.0}]
    if t1 < END:
        k += [{"t": t1 - 0.4, "x": 540, "y": 900, "scale": s, "opacity": 1.0},
              {"t": t1, "x": 540, "y": 960, "scale": s * 0.25, "opacity": 0.0, "ease": "in"}]
    S.image(id_, "st_ship", t0, t1 + 0.05, k)


opening_ship("ship_open", 0.0, T_GEFUNDEN + 0.5, appear=False)
for i, (lid, t, x, y, rot, wd) in enumerate([("lbl_mary", T_MARY, 330, 330, -3, 380),
                                             ("lbl_celeste", T_CELESTE, 720, 355, 2, 520)]):
    S.sticker(lid, lid, t, T_GEFUNDEN - 0.1, x, y, wd, rot, exit=(x, -300), sound="cardboard_hit", gain=-8 - 2 * i)
S.image("cloud1", "st_cloud1", 0, T_GEFUNDEN, [{"t": 0, "x": 920, "y": 560, "scale": S.scale_for("st_cloud1", 340)},
                                              {"t": T_GEFUNDEN, "x": 820, "y": 560}], jitter=False)
S.image("cloud2", "st_cloud2", 0, T_GEFUNDEN, [{"t": 0, "x": 140, "y": 640, "scale": S.scale_for("st_cloud2", 300)},
                                              {"t": T_GEFUNDEN, "x": 240, "y": 640}], jitter=False)
S.sticker("lbl_niemand", "lbl_niemand", T_MENSCHEN, T_GEFUNDEN - 0.1, 540, 1290, 640, -2, sound="cardboard_hit")
rec("ship_bell", T_EIN, -14, trim=[0.0, 2.5], fade=0.8)
rec("map_whoosh", T_GEFUNDEN + 0.3, -8, peak=0.38)

# ---------------------------------------------------------------- 2 found in December 1872
S.sticker("lbl_1872", "lbl_1872", T_DEZ, T_SEGEL - 0.35, 540, 400, 620, -3, exit=(540, -300), sound="cardboard_hit")
rec("map_whoosh", T_MITTEN, -6, peak=0.38)

# ---------------------------------------------------------------- 3 sails set, cargo complete, food for 6 months
T3_OUT = T_GESTARTET - 0.3
S.image("ocean3", "ocean_strip", T_SEGEL - 0.25, T3_OUT + 0.4,
        slide_in(T_SEGEL - 0.25, 540, 2300, 540, 1250, S.scale_for("ocean_strip", 1250), 0, -1.5) +
        [{"t": T3_OUT, "x": 540, "y": 1250}, exit_to(T3_OUT, 540, 2400)], jitter=False)
S.sticker("ship3", "st_ship", T_SEGEL - 0.2, T3_OUT, 520, 960, 820, -1, how="slide", frm=(-700, 980),
          exit=(1700, 960), sound="paper_slide", gain=-8)
rec("sails_flap", T_SEGEL, -10, trim=[0.0, 2.6], fade=0.8)
S.sticker("barrel3", "st_barrel", T_LADUNG1, T3_OUT, 860, 1330, 260, 6, sound="barrel_knock", gain=-10)
S.sticker("lbl_6m", "lbl_6monate", T_SECHS, T3_OUT, 540, 380, 620, 2, exit=(540, -300), sound="cardboard_hit")

# ---------------------------------------------------------------- 4 New York, the people, the cargo
T4P_OUT = T_LADUNG2 - 0.3
T4_OUT = T_VIER - 0.15
S.sticker("lbl_ny", "lbl_newyork", T_NEW, T4P_OUT, 540, 330, 520, -2, exit=(540, -300), sound="cardboard_hit")
S.sticker("briggs", "st_briggs", T_KAPITAEN, T4P_OUT, 310, 960, 500, -4, sound="paper_drop", gain=-5)
S.sticker("sarah", "st_sarah", T_SEINE, T4P_OUT, 780, 990, 460, 4, sound="paper_drop", gain=-5)
S.sticker("lbl_7", "lbl_7", T_SIEBEN, T4P_OUT, 540, 1290, 520, -2, exit=(540, 2300), sound="cardboard_hit")
for i, (x, y, rot) in enumerate([(230, 980, -6), (540, 940, 3), (850, 990, -2), (380, 1170, 5), (700, 1180, -4)]):
    S.sticker(f"barrel4_{i}", "st_barrel", T_UEBER + 0.18 * i, T4_OUT, x, y, 300, rot,
              exit=(x, 2300), sound="barrel_knock", gain=-9 - i)
S.sticker("lbl_faesser", "lbl_faesser", T_FAESSER, T4_OUT, 540, 680, 820, -2, exit=(540, -300), sound="cardboard_hit")

# ---------------------------------------------------------------- 5 four weeks later: found near the Azores
S.sticker("lbl_4w", "lbl_4wochen", T_VIER, T_DEI - 0.3, 540, 380, 600, -3, exit=(540, -300), sound="cardboard_hit")
rec("pen_scribble", T_R1A, -13, trim=[0.0, 3.6], fade=0.5)
S.sticker("lbl_dg", "lbl_deigratia", T_DEI, T_AZOREN - 0.1, 540, 1290, 560, 2, exit=(540, 2300), sound="cardboard_hit")
rec("ship_horn", T_ANDERES, -16, trim=[0.0, 2.4], fade=0.8)
S.sticker("lbl_azo", "lbl_azoren", T_AZOREN, T_PERS - 0.2, 540, 380, 460, -2, exit=(540, -300), sound="cardboard_hit")
T5_OUT = T_FINDER1 - 0.3
S.sticker("suitcase", "st_suitcase", T_PERS, T5_OUT, 300, 900, 480, -5, sound="paper_drop", gain=-5)
rec("box_open", T_PERS + 0.3, -12, trim=[0.0, 1.0], fade=0.3)
S.sticker("boat", "st_boat", T_NUR, T5_OUT, 720, 1150, 600, 3, sound="paper_drop", gain=-5)
txs = S.scale_for("tape_x", 420)
for i, (t, x, y) in enumerate([(T_FEHLT, 720, 1150), (T_SEXTANT + 0.25, 600, 640)]):
    S.image(f"tape{i}", "tape_x", t, T5_OUT + 0.35, [
        {"t": t, "x": x, "y": y, "scale": txs * 1.6, "rot": -8, "opacity": 0.0}, {"t": t + 0.03, "opacity": 1.0},
        {"t": t + 0.12, "scale": txs, "ease": "out"}, {"t": T5_OUT, "x": x, "y": y}, exit_to(T5_OUT, x, 2300)])
    rec("paper_tear", t + 0.05, -9)
S.sticker("sextant", "st_sextant", T_UND_S, T5_OUT, 600, 640, 420, -3, sound="paper_drop", gain=-6)

# ---------------------------------------------------------------- 6 towed to Gibraltar, salvage money
T6_OUT = T_DOCH - 0.2
rec("rope_creak", T_R2A, -14, trim=[0.0, 2.5], fade=0.6)
S.sticker("gibraltar", "st_gibraltar", T_GIB, T6_OUT, 790, 820, 440, 3, sound="paper_drop", gain=-6)
S.sticker("lbl_gib", "lbl_gibraltar", T_GIB + 0.05, T6_OUT, 540, 360, 540, -2, exit=(540, -300), sound="cardboard_hit")
S.sticker("coins6", "st_coins", T_BERGE, T6_OUT, 300, 1080, 400, -4, sound="coins", gain=-8)
S.sticker("lbl_berge", "lbl_bergelohn", T_BERGE + 0.1, T6_OUT, 540, 1290, 560, 2, exit=(540, 2300), sound=None)

# ---------------------------------------------------------------- 7 the prosecutor: stains, cuts, murder
T7_OUT = T_ARZT - 0.3
S.layers.append({"id": "dim", "type": "solid", "start": T_DOCH, "end": T_NUR2 + 0.6, "color": [20, 16, 14],
                 "keys": [{"t": T_DOCH, "opacity": 0.0}, {"t": T_DOCH + 0.4, "opacity": 0.3},
                          {"t": T_NUR2, "opacity": 0.3}, {"t": T_NUR2 + 0.5, "opacity": 0.0}]})
sw_s = S.scale_for("st_sword", 900)
S.image("sword", "st_sword", T_SCHWERT - 0.35, T7_OUT + 0.35,
        slide_in(T_SCHWERT - 0.35, 1700, 900, 540, 860, sw_s, 10, -8, 0.35) +
        [{"t": T_KERBEN - 0.2, "x": 540, "y": 860}, {"t": T_KERBEN + 0.15, "x": 540, "y": 560, "ease": "out3"},
         {"t": T7_OUT, "x": 540, "y": 560}, exit_to(T7_OUT, 1700, 560)])
rec("sword_draw", T_SCHWERT - 0.3, -6)
mgs = S.scale_for("st_magnifier", 520)
S.image("mag", "st_magnifier", T_FLECKEN1 - 0.1, T_KERBEN, slide_in(T_FLECKEN1 - 0.1, 1300, 1700, 640, 860, mgs, -35, -12, 0.35) +
        [{"t": T_KERBEN - 0.25, "x": 640, "y": 860}, exit_to(T_KERBEN - 0.25, 1500, 1900)],
        anchor=list(M["st_magnifier"]["lens"]))
rec("paper_slide", T_FLECKEN1, -9, peak=0.42)
S.sticker("bow", "st_bow", T_KERBEN, T7_OUT, 560, 1160, 640, -2, sound="paper_drop", gain=-5)
sm = S.scale_for("stamp_mord", 560)
S.image("stamp", "stamp_mord", T_MORD, T7_OUT + 0.35, [
    {"t": T_MORD, "x": 540, "y": 880, "scale": sm * 2.2, "rot": -12, "opacity": 0.0}, {"t": T_MORD + 0.03, "opacity": 1.0},
    {"t": T_MORD + 0.1, "scale": sm, "ease": "in"}, {"t": T7_OUT, "x": 540, "y": 880}, exit_to(T7_OUT, 540, -400)])
S.flash("flash_mord", T_MORD, peak=0.5)
rec("stamp", T_MORD + 0.08, -3)
rec("suspense_hit", T_MORD, -8)
rec("heartbeat_low", T_MORD + 0.3, -10, trim=[0.0, 3.6], fade=0.8)
S.sticker("coins7", "st_coins", T_GELD - 0.3, T7_OUT, 820, 1380, 360, 5, sound="coins", gain=-12)

# ---------------------------------------------------------------- 8 the doctor: no blood, rust
T8_OUT = T_BEKOMMEN - 0.3
S.sticker("doctor", "st_doctor", T_ARZT - 0.1, T8_OUT, 300, 900, 520, -3, how="slide", frm=(-500, 920),
          exit=(-600, 900), sound="paper_slide", gain=-6)
S.sticker("microscope", "st_microscope", T_UNTERS, T8_OUT, 790, 930, 360, 4, sound="paper_drop", gain=-6)
S.sticker("lbl_kb", "lbl_keinblut", T_KEIN, T8_OUT, 540, 380, 560, -3, exit=(540, -300), sound="cardboard_hit")
S.sticker("lbl_rost", "lbl_rost", T_ROST1, T8_OUT, 540, 1290, 440, 3, exit=(540, 2300), sound="cardboard_hit", gain=-5)
S.flash("flash_blut", T_KEIN, color=(60, 110, 120), peak=0.3)
S.sticker("coins8", "st_coins", T_BEKOMMEN, T_NUR2 - 0.25, 540, 960, 460, -3, sound="coins", gain=-9)
rec("gavel", T_BEKOMMEN + 0.5, -6)

# ---------------------------------------------------------------- 9 ten people, the boat never found
S.sticker("lbl_10", "lbl_10", T_ZEHN, T_DAS_BOOT - 0.2, 540, 400, 600, -2, exit=(540, -300), sound="cardboard_hit")
for i, (aid, x, y, wd) in enumerate([("st_briggs", 320, 960, 420), ("st_sarah", 760, 980, 400)]):
    t0 = T_ZEHN + 0.15 + 0.15 * i
    S.image(f"ghost{i}", aid, t0, T_DAS_BOOT + 0.1, [
        {"t": t0, "x": x, "y": y + 30, "scale": S.scale_for(aid, wd), "rot": 0, "opacity": 0.0},
        {"t": t0 + 0.4, "opacity": 0.55, "y": y, "ease": "out"},
        {"t": T_DAS_BOOT - 0.3, "opacity": 0.55}, {"t": T_DAS_BOOT, "opacity": 0.0, "y": y - 40}], jitter=False)
S.image("ocean9", "ocean_strip", T_DAS_BOOT - 0.2, T_WAS + 0.4,
        slide_in(T_DAS_BOOT - 0.2, 540, 2300, 540, 1250, S.scale_for("ocean_strip", 1250), 0, -1.5) +
        [{"t": T_WAS, "x": 540, "y": 1250}, exit_to(T_WAS, 540, 2400)], jitter=False)
bs = S.scale_for("st_boat", 380)
S.image("boat9", "st_boat", T_DAS_BOOT, T_WAS + 0.1, [
    {"t": T_DAS_BOOT, "x": 300, "y": 1150, "scale": bs, "rot": 0, "opacity": 1.0},
    {"t": T_GEFUNDEN2, "x": 560, "y": 1160, "rot": 4},
    {"t": T_WAS - 0.1, "x": 700, "y": 1170, "rot": -3, "opacity": 0.0}])
rec("waves_hull", T_DAS_BOOT - 0.3, -16, trim=[0.0, 3.5], fade=1.0)
rec("ship_bell", T_GEFUNDEN2 + 0.4, -18, trim=[0.0, 2.0], fade=0.8)
# loop: the empty ship returns exactly as in the first frame
opening_ship("ship_end", T_NAME - 0.25, END + 0.1, appear=True)
rec("paper_drop", T_NAME - 0.15, -6)

S.layers.append({"id": "page", "type": "multiply_image", "asset": "page", "keys": []})

HIDE = [(0.0, T_CELESTE + 0.6), (T_DEZ - 0.05, T_MITTEN - 0.05), (T_NEW - 0.05, T_NEW + 0.6),
        (T_VIER - 0.05, T_ANDERES - 0.05), (T_DEI - 0.05, T_DEI + 0.8), (T_AZOREN - 0.05, T_AZOREN + 0.6),
        (T_GIB - 0.05, T_GIB + 0.6)]
caps = S.captions(hide=HIDE, big={"menschen", "mord", "blut", "rost", "nie"})
assets = {}
for name, m in M.items():
    if isinstance(m, dict) and "w" in m:
        assets[name] = {"path": f"build/assets/{name}.png", "license": "own"}
        if name.startswith("st_"):
            assets[name]["license"] = "user_supplied_cutout (Quelle/Lizenz der Originalfotos vor Veröffentlichung prüfen)"
timeline = {"meta": {"fps": 30, "width": 1080, "height": 1920, "duration": END},
            "assets": assets, "layers": S.layers, "captions": caps,
            "audio": [{"id": "voice", "src": "audio/voice_v1_elevenlabs.mp3", "start": 0.0, "gain_db": 0.0}] + S.audio}
out = os.path.join(HERE, "timeline.json")
json.dump(timeline, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("timeline ->", out, "|", len(S.layers), "layers")
