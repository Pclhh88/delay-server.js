"""Timeline of the long Amelia Earhart video (16:9, ~9:51).

    python3 projects/amelia-earhart-long/build/build_timeline.py [--end SECONDS]

Built chapter by chapter; scenes are keyed to the spoken words (analysis/words.json).
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(PROJ)))

from shortsfactory.collage.choreo import Show, exit_to, fix_keys, fly_camera, path_keys, phrase_captions, pop_in, slide_in  # noqa

ap = argparse.ArgumentParser()
ap.add_argument("--end", type=float, default=None)
ARGS = ap.parse_args()

W, H = 1920, 1080
CX, CY = W / 2, H / 2
S = Show(os.path.join(HERE, "assets", "meta.json"), os.path.join(PROJ, "analysis", "words.json"))
w, rec, M = S.w, S.rec, S.META
WORDS = S.WORDS
FULL_END = WORDS[-1]["end"] + 1.0
END = ARGS.end or FULL_END
mp = M["map_pacific"]
PPD = mp["proj"]["ppd"]
MAP_H = mp["proj"]["h"]
PL = {k: tuple(v) for k, v in M["places"].items()}
HOW = tuple(mp["howland"])
NIK = tuple(mp["nikumaroro"])
LAE = tuple(mp["lae"])


def map_xy(lon, lat):
    lon_min = mp["proj"]["lon_min"]
    while lon < lon_min:
        lon += 360
    return (lon - lon_min) * PPD, (mp["proj"]["lat_max"] - lat) * PPD


def ZP(ppd):
    """camera zoom that shows the map at `ppd` design px per degree"""
    return ppd / PPD


def F(xy, s, ease="inout"):
    x, y = xy
    half = CY / s
    y = MAP_H / 2 if half >= MAP_H / 2 else min(max(y, half), MAP_H - half)
    return (x, y, s, ease)


CAM = []


def cam(t, xy, s, ease="inout"):
    CAM.append((round(t, 3),) + F(xy, s, ease))


# ======================================================================= CHAPTER 0
T = {k: w(k) for k in ["Das", "berühmtesten", "Gesendet", "Kurz", "Stille", "Fast", "Oktober", "landet",
                       "Koralleninsel", "tausende", "Satellitenbildern", "Was", "entscheidest"]}
T_QEND = w("knapp", 0, "end")
T_KEIN = [w("Kein"), w("kein", 17), w("keine", 17)]
T_JULI = w("2", 8)
T_IRGEND = w("irgendwo")
T_CH1 = w("Amelia", 44)

cam(0.0, map_xy(-168, 3), 1.0, None)
cam(T["Kurz"], map_xy(-171, 3), 1.15, "linear")
cam(T["Fast"] - 0.2, map_xy(-172, 1), 1.2, "linear")
cam(T["landet"], map_xy(-174.4, -3.5), ZP(80), "inout")
cam(T["Koralleninsel"] + 0.4, NIK, ZP(14000), "inout")
cam(T["Was"], (NIK[0] + 0.05, NIK[1]), ZP(15500), "linear")
cam(T["entscheidest"] - 0.6, NIK, ZP(60), "inout")

S.layers.append({"id": "dim0", "type": "solid", "start": 0, "end": T["Fast"], "color": [20, 22, 20],
                 "keys": [{"t": 0, "opacity": 0.3}, {"t": T["Kurz"], "opacity": 0.3},
                          {"t": T["Stille"], "opacity": 0.5}, {"t": T["Fast"], "opacity": 0.0}]})
# radio + typed quote
T0_OUT = T["Kurz"] - 0.3
S.sticker("radio", "st_radio", 0.0, T0_OUT, 330, 470, 420, 3, exit=(-500, 600), sound="paper_drop", gain=-6)
arc_s = S.scale_for("arc_orange", 420)
t, i = 0.2, 0
while t < T["Kurz"]:
    S.image(f"wave{i}", "arc_orange", t, t + 1.2, [
        {"t": t, "x": 470, "y": 290, "scale": arc_s * 0.3, "rot": -50, "opacity": 1.0},
        {"t": t + 0.8, "opacity": 0.9}, {"t": t + 1.2, "scale": arc_s * 1.4, "opacity": 0.0, "ease": "out"}],
        jitter=False)
    t += 0.42
    i += 1
S.audio.append({"src": "audio/sfx_prepared/radio_static_long.wav", "start": 0.0, "gain_db": -22,
                "trim": [0.0, T["Kurz"] + 0.2], "fade_out": 0.1})
qn = M["quote_words"]
qwords = [x for x in WORDS if x["start"] <= T_QEND + 0.01][:qn]
qs = S.scale_for("quote_01", 820)
strip_keys = slide_in(0.0, 950, 1500, 950, 820, qs, 6, -1.5, 0.3) + [
    {"t": T0_OUT, "x": 950, "y": 820}, exit_to(T0_OUT, 2600, 860, 0.3, rot=10)]
S.image("strip0", "quote_00", 0.0, qwords[0]["start"], strip_keys)
for k, wd in enumerate(qwords, 1):
    e0 = qwords[k]["start"] if k < qn else T0_OUT + 0.35
    S.image(f"strip{k}", f"quote_{k:02d}", wd["start"], e0, strip_keys)
    rec("typewriter_key", wd["start"], -7)
rec("typewriter_bell", T_QEND + 0.2, -14)
# portrait + name
S.sticker("portrait0", "st_portrait", T["Das"], T0_OUT, 1580, 430, 380, -3, exit=(2400, 400), gain=-5)
S.sticker("lbl_am", "lbl_amelia", T["berühmtesten"], T0_OUT, 1580, 110, 330, -3, exit=(1580, -200), sound="cardboard_hit", gain=-10)
S.sticker("lbl_ea", "lbl_earhart", T["berühmtesten"] + 0.35, T0_OUT, 1600, 770, 340, 2, exit=(1600, 1300), sound="cardboard_hit", gain=-11)
S.sticker("lbl_date", "lbl_date", T_JULI, T0_OUT, 960, 130, 520, -2, exit=(960, -200), sound="cardboard_hit", gain=-8)
# the plane over the Pacific (map space), flickers out on "Kurz danach"
s_pl = S.scale_for("st_electra", 170) / 1.15
d = (HOW[0] - LAE[0], HOW[1] - LAE[1])
p0 = (HOW[0] - d[0] * 0.25, HOW[1] - d[1] * 0.25)
p1 = (HOW[0] - d[0] * 0.03, HOW[1] - d[1] * 0.03)
ang = math.degrees(math.atan2(d[1], d[0]))
MAP_EXTRA = [{"id": "plane0", "type": "image", "asset": "st_electra", "start": T_IRGEND - 0.3, "end": T["Kurz"] + 0.7,
              "anchor": M["st_electra"]["anchor"],
              "keys": [{"t": T_IRGEND - 0.3, "x": p0[0], "y": p0[1], "scale": s_pl, "rot": ang, "opacity": 0.0},
                       {"t": T_IRGEND, "opacity": 1.0},
                       {"t": T["Kurz"], "x": p1[0], "y": p1[1], "opacity": 1.0},
                       {"t": T["Kurz"] + 0.1, "opacity": 0.2}, {"t": T["Kurz"] + 0.2, "opacity": 0.9},
                       {"t": T["Kurz"] + 0.35, "opacity": 0.1}, {"t": T["Kurz"] + 0.45, "opacity": 0.8},
                       {"t": T["Kurz"] + 0.65, "opacity": 0.0}]}]
rec("plane_distant", T_IRGEND - 0.3, -18, trim=[0.0, 2.6], fade=0.6)
rec("radio_cutoff", T["Kurz"], -9, trim=[0.0, 2.0], fade=0.4)
S.layers.append({"id": "drain0", "type": "grade", "start": T["Kurz"], "end": T["Fast"] + 0.6,
                 "keys": [{"t": T["Kurz"], "saturation": 1.0}, {"t": T["Kurz"] + 0.6, "saturation": 0.15},
                          {"t": T["Fast"], "saturation": 0.15}, {"t": T["Fast"] + 0.6, "saturation": 1.0}]})
S.sticker("lbl_stille", "lbl_stille", T["Stille"], T_KEIN[0] - 0.15, 960, 460, 460, -2, exit=(960, -250), sound=None)
rec("drone_dark", T["Kurz"] + 0.5, -16, trim=[0.0, 7.0], fade=1.5)
for k, (lid, x) in enumerate([("lbl_kein_flugzeug", 470), ("lbl_kein_wrack", 960), ("lbl_keine_leiche", 1450)]):
    S.sticker(lid, lid, T_KEIN[k], T["Fast"] - 0.35, x, 520 + 40 * (k % 2), 440, (-3, 2, -2)[k],
              exit=(x, 1400), sound="cardboard_hit", gain=-7)
# 2026 expedition on Nikumaroro
S.sticker("lbl_okt", "lbl_okt2026", T["Oktober"], T["Koralleninsel"] + 0.05, 960, 130, 560, -2, exit=(960, -250), sound="cardboard_hit", gain=-6)
rec("map_whoosh", T["landet"] + 0.6, -5, peak=0.38)
rec("map_whoosh", T["landet"] + 1.6, -10, peak=0.38)
rec("ocean_wind", T["landet"], -20, trim=[0.0, 14.0], fade=2.0)
S.sticker("lbl_niku0", "lbl_nikumaroro", T["Koralleninsel"] + 0.4, T["Was"] - 0.3, 960, 140, 460, 2, exit=(960, -250), sound="cardboard_hit", gain=-8)
s_sat = ZP(14500)
circ_c = (NIK[0] - 0.22, NIK[1] - 0.12)
r_c = 0.13
MAP_EXTRA.append({"id": "satcircle", "type": "dashed_path", "start": T["Satellitenbildern"] - 0.2, "end": T["Was"] + 1.0,
                  "points": [[circ_c[0] + r_c * math.cos(a), circ_c[1] + r_c * math.sin(a)]
                             for a in [2 * math.pi * j / 60 for j in range(61)]],
                  "props": {"x": 0, "y": 0}, "width": 7 / s_sat, "dash": 22 / s_sat, "gap": 14 / s_sat,
                  "color": [232, 112, 58],
                  "keys": [{"t": T["Satellitenbildern"] - 0.2, "progress": 0.0, "opacity": 1.0},
                           {"t": T["Satellitenbildern"] + 0.8, "progress": 1.0, "ease": "inout"},
                           {"t": T["Was"] + 0.5, "opacity": 1.0}, {"t": T["Was"] + 1.0, "opacity": 0.0}]})
S.sticker("lbl_sat", "lbl_satellit", T["Satellitenbildern"], T["Was"] + 0.3, 1450, 850, 440, 3, exit=(1450, 1400), sound="cardboard_hit", gain=-9)
mg_s = S.scale_for("st_magnifier", 420)
S.image("mag0", "st_magnifier", T["Satellitenbildern"] + 0.4, T["Was"] + 0.8,
        slide_in(T["Satellitenbildern"] + 0.4, 2300, 1100, 1150, 500, mg_s, -30, -12, 0.45) +
        [{"t": T["Was"], "x": 1120, "y": 520}, exit_to(T["Was"] + 0.2, 2400, 1200, 0.35, rot=-40)],
        anchor=list(M["st_magnifier"]["lens"]))
rec("paper_slide", T["Satellitenbildern"] + 0.5, -8, peak=0.42)
# teaser: four theories around the question
T_TH = w("Und", 41)
for k, (aid, x, y, wd, rot) in enumerate([("st_electra", 420, 330, 380, -6), ("st_crab", 1500, 330, 330, 5),
                                          ("st_photo2017", 430, 760, 380, 4), ("st_house", 1500, 760, 340, -4)]):
    S.sticker(f"teaser{k}", aid, T_TH + 0.25 * k, T_CH1 - 0.4, x, y, wd, rot, exit=(CX, CY), sound="paper_drop", gain=-10)
S.sticker("lbl_theorie", "lbl_theorie", T["entscheidest"], T_CH1 - 0.4, 960, 545, 680, -2, exit=(960, -300), sound="cardboard_hit", gain=-5)
rec("suspense_hit", T["entscheidest"] + 0.1, -11)

# ======================================================================= CHAPTER 1
T1 = {k: w(k, 44) for k in ["1897", "Kansas", "Ihren", "1920", "zehn", "Los", "Danach", "jobbt", "gebrauchtes",
                            "1928", "Allerdings", "Passagierin", "Sack", "1932", "allein", "zweiter", "Lindbergh",
                            "Weltstar", "Bücher", "Mode", "Chancen", "Aber", "Rekord"]}
T1["Das2"] = w("Das", 72)
T1["fliegt32"] = w("fliegt", 77)
T1["fliegt28"] = w("fliegt", 63)
T_CH2 = w("Sie", 95)
ATC, LA = PL["atchison"], PL["los_angeles"]
TRE, BUR = PL["trepassey"], PL["burry_port"]
HGR, CUL = PL["harbour_grace"], PL["culmore"]

cam(T_CH1 + 0.9, ATC, 1.7, "inout")
cam(T1["Ihren"], (ATC[0] - 20, ATC[1] + 5), 1.75, "linear")
cam(T1["Los"] - 0.3, ((ATC[0] + LA[0]) / 2 - 60, (ATC[1] + LA[1]) / 2), 1.6, "inout")
cam(T1["jobbt"], (LA[0] + 90, LA[1]), 1.7, "inout")
cam(T1["1928"] - 0.2, (LA[0] + 140, LA[1]), 1.75, "linear")
cam(T1["fliegt28"] + 0.3, ((TRE[0] + BUR[0]) / 2, (TRE[1] + BUR[1]) / 2 + 40), 0.95, "inout")
cam(T1["Das2"], ((TRE[0] + BUR[0]) / 2 + 30, (TRE[1] + BUR[1]) / 2 + 40), 1.0, "linear")
cam(T1["fliegt32"] - 0.2, (HGR[0] + 40, HGR[1]), 1.3, "inout")
cam(T1["zweiter"], (CUL[0] - 60, CUL[1]), 1.3, "inout")
cam(T1["Weltstar"], (CUL[0] - 80, CUL[1] + 20), 1.35, "linear")
cam(T1["Aber"], (CUL[0] - 120, CUL[1] + 40), 1.3, "linear")
cam(T1["Rekord"] + 0.3, map_xy(40, 5), 0.42, "inout")

# chapter card
S.sticker("kap1", "lbl_kap", T["entscheidest"] + 1.9, T_CH1 + 1.1, 960, 430, 260, -2, exit=(960, -300), sound="paper_slide", gain=-6, how="slide", frm=(960, -200))
S.sticker("kap1t", "lbl_kap_title", T["entscheidest"] + 2.05, T_CH1 + 1.1, 960, 560, 820, 1, exit=(960, 1400), sound=None, how="slide", frm=(960, 1300))
rec("map_whoosh", T_CH1 - 0.1, -6, peak=0.38)

S.sticker("young", "st_young", T1["1897"] + 0.2, T1["Danach"] - 0.2, 1480, 500, 400, 3, exit=(2400, 500), gain=-5)
S.sticker("l1897", "lbl_1897", T1["1897"], T1["Ihren"] - 0.3, 520, 170, 300, -3, exit=(520, -250), sound="cardboard_hit", gain=-7)
S.sticker("lkansas", "lbl_kansas", T1["Kansas"], T1["Ihren"] - 0.3, 760, 640, 320, 2, exit=(760, 1400), sound="cardboard_hit", gain=-9)
MAP_EXTRA.append({"id": "route_la", "type": "dashed_path", "start": T1["Ihren"], "end": T1["fliegt28"] + 1,
                  "points": [list(ATC), [(ATC[0] + LA[0]) / 2, (ATC[1] + LA[1]) / 2 - 25], list(LA)],
                  "props": {"x": 0, "y": 0}, "width": 6 / 1.7, "dash": 18 / 1.7, "gap": 11 / 1.7, "color": [232, 112, 58],
                  "keys": [{"t": T1["Ihren"], "progress": 0.0}, {"t": T1["Los"], "progress": 1.0, "ease": "inout"}]})
rec("pen_scribble", T1["Ihren"], -13, trim=[0.0, 3.4], fade=0.4)
S.sticker("l1920", "lbl_1920", T1["1920"], T1["Danach"] - 0.2, 520, 170, 300, -3, exit=(520, -250), sound="cardboard_hit", gain=-7)
S.sticker("l10min", "lbl_10min", T1["zehn"], T1["Danach"] - 0.2, 1400, 180, 380, 2, exit=(1400, -250), sound="cardboard_hit", gain=-9)
S.sticker("lla", "lbl_la", T1["Los"], T1["Danach"] - 0.2, 760, 700, 360, -2, exit=(760, 1400), sound="cardboard_hit", gain=-10)
vs = S.scale_for("st_vega", 300)
S.image("vega_loop", "st_vega", T1["zehn"] - 0.2, T1["Danach"] + 0.2, [
    {"t": T1["zehn"] - 0.2, "x": -300, "y": 470, "scale": vs, "sx": -1, "rot": 8},
    {"t": T1["Danach"] + 0.2, "x": 2250, "y": 380, "rot": 2}])
rec("plane_flyby", T1["zehn"] + 0.8, -10, trim=[1.6, 5.0], fade=0.6, peak=2.0)
S.sticker("ljobbt", "lbl_jobbt", T1["jobbt"], T1["1928"] - 0.3, 960, 170, 460, -2, exit=(960, -250), sound="cardboard_hit", gain=-8)
S.sticker("vega_buy", "st_vega", T1["gebrauchtes"], T1["1928"] - 0.3, 1050, 560, 620, -4, exit=(2500, 500), gain=-5)
S.sticker("lgebr", "lbl_gebraucht", T1["gebrauchtes"] + 0.4, T1["1928"] - 0.3, 1050, 860, 460, 2, exit=(1050, 1400), sound="cardboard_hit", gain=-9)
# 1928 as passenger
S.sticker("l1928", "lbl_1928", T1["1928"], T1["Das2"] - 0.3, 960, 160, 300, -3, exit=(960, -250), sound="cardboard_hit", gain=-6)
MAP_EXTRA.append({"id": "route28", "type": "dashed_path", "start": T1["fliegt28"], "end": T1["fliegt32"] + 0.5,
                  "points": [list(TRE), [(TRE[0] + BUR[0]) / 2, (TRE[1] + BUR[1]) / 2 - 60], list(BUR)],
                  "props": {"x": 0, "y": 0}, "width": 6, "dash": 18, "gap": 11, "color": [232, 112, 58],
                  "keys": [{"t": T1["fliegt28"], "progress": 0.0, "opacity": 1.0},
                           {"t": T1["fliegt28"] + 2.0, "progress": 1.0, "ease": "inout"},
                           {"t": T1["fliegt32"], "opacity": 1.0}, {"t": T1["fliegt32"] + 0.4, "opacity": 0.0}]})
rec("pen_scribble", T1["fliegt28"], -13, trim=[0.0, 2.2], fade=0.3)
S.sticker("lpass", "lbl_passagierin", T1["Passagierin"], T1["Das2"] - 0.3, 1400, 330, 520, 3, exit=(2400, 330), sound="cardboard_hit", gain=-6)
S.sticker("potatoes", "st_potatoes", T1["Sack"] - 0.15, T1["Das2"] - 0.3, 1420, 700, 340, -5, exit=(2400, 700), sound="paper_drop", gain=-4)
# 1932 solo
S.sticker("l1932", "lbl_1932", T1["1932"], T1["Weltstar"] - 0.3, 960, 160, 300, -3, exit=(960, -250), sound="cardboard_hit", gain=-6)
r32 = [list(HGR), [(HGR[0] + CUL[0]) / 2, (HGR[1] + CUL[1]) / 2 - 70], list(CUL)]
T32A, T32B = T1["fliegt32"], T1["zweiter"] + 0.2
vk, vprog = path_keys([tuple(p) for p in r32], T32A, T32B)
vk[0].update({"scale": S.scale_for("st_vega", 210) / 1.3, "sx": -1, "rot": 6})   # Vega's nose points left: mirror for eastbound
MAP_EXTRA.append({"id": "route32", "type": "dashed_path", "start": T32A, "end": T1["Aber"] + 0.5, "points": r32,
                  "props": {"x": 0, "y": 0}, "width": 6 / 1.3, "dash": 18 / 1.3, "gap": 11 / 1.3,
                  "color": [232, 112, 58], "keys": vprog})
MAP_EXTRA.append({"id": "vega32", "type": "image", "asset": "st_vega", "start": T32A, "end": T1["Weltstar"],
                  "anchor": M["st_vega"]["anchor"], "keys": vk + [
                      {"t": T1["Weltstar"] - 0.4, "opacity": 1.0}, {"t": T1["Weltstar"], "opacity": 0.0}]})
rec("plane_distant", T32A, -14, trim=[0.0, T32B - T32A + 0.8], fade=0.8)
S.sticker("lallein", "lbl_allein", T1["allein"], T1["Weltstar"] - 0.3, 960, 880, 620, 2, exit=(960, 1400), sound="cardboard_hit", gain=-8)
S.sticker("lindbergh", "st_lindbergh", T1["Lindbergh"] - 0.15, T1["Weltstar"] - 0.3, 1530, 470, 330, 4, exit=(2400, 470), gain=-5)
S.sticker("lnr2", "lbl_nr2", T1["Lindbergh"] + 0.2, T1["Weltstar"] - 0.3, 1530, 770, 440, -2, exit=(2400, 770), sound="cardboard_hit", gain=-9)
# world star
S.flash("flash_star", T1["Weltstar"], color=(255, 250, 235), peak=0.7)
rec("camera_flash", T1["Weltstar"] - 0.02, -6)
rec("camera_flash", T1["Weltstar"] + 0.35, -10)
rec("crowd_cheer", T1["Weltstar"] - 0.1, -14, trim=[0.0, 4.5], fade=1.5)
S.sticker("news32", "st_news1932", T1["Weltstar"], T1["Aber"] - 0.3, 470, 600, 600, -5, exit=(-400, 540), sound="newspaper", gain=-9)
S.sticker("portrait1", "st_portrait", T1["Weltstar"] + 0.1, T1["Aber"] - 0.3, 960, 500, 380, 2, exit=(960, 1500), gain=-6)
S.sticker("lstar", "lbl_weltstar", T1["Weltstar"] + 0.05, T1["Bücher"] - 0.2, 960, 150, 420, -3, exit=(960, -250), sound="cardboard_hit", gain=-6)
S.sticker("book", "st_book", T1["Bücher"], T1["Aber"] - 0.3, 1480, 330, 330, 6, exit=(2400, 330), gain=-7)
rec("page_turn", T1["Bücher"] + 0.2, -10)
S.sticker("lmode", "lbl_mode", T1["Mode"], T1["Aber"] - 0.3, 1480, 620, 260, -3, exit=(2400, 620), sound="cardboard_hit", gain=-9)
S.sticker("lchancen", "lbl_chancen", T1["Chancen"], T1["Aber"] - 0.3, 960, 150, 560, 2, exit=(960, -250), sound="cardboard_hit", gain=-7)
S.sticker("lrekord", "lbl_rekord", T1["Rekord"] - 0.1, T_CH2 + 3.0, 960, 540, 700, -2, exit=(960, -300), sound="cardboard_hit", gain=-5)
rec("suspense_hit", T1["Rekord"], -10)

# ======================================================================= helpers for chapters 2-9
def L(id_, asset, t_in, t_out, x, y, width, rot=0.0, sound="cardboard_hit", gain=-8.0, exit=None, how="pop", frm=None):
    """label sticker; leaves upwards (top half) or downwards (bottom half)"""
    if exit is None:
        exit = (x, -300) if y < CY else (x, H + 300)
    S.sticker(id_, asset, t_in, t_out, x, y, width, rot, exit=exit, sound=sound, gain=gain, how=how, frm=frm)


def P(id_, asset, t_in, t_out, x, y, width, rot=0.0, gain=-6.0, exit=None, how="pop", frm=None, sound="paper_drop"):
    """photo / object sticker; leaves sideways"""
    if exit is None:
        exit = (-500, y) if x < CX else (W + 500, y)
    S.sticker(id_, asset, t_in, t_out, x, y, width, rot, exit=exit, sound=sound, gain=gain, how=how, frm=frm)


def card(kap, title, t, dur=2.3, title_w=880):
    L(f"{kap}_c", kap, t, t + dur, 960, 430, 260, -2, sound="paper_slide", gain=-6, how="slide", frm=(960, -200))
    L(f"{title}_c", title, t + 0.15, t + dur, 960, 565, title_w, 1, sound=None, how="slide", frm=(960, 1300))


def mline(id_, pts, t0, t1, z, t_end=None, color=(232, 112, 58), width=6, dash=18, gap=12):
    """dashed line drawn in map space between t0 and t1 (line width constant on screen at zoom z)"""
    keys = [{"t": t0, "progress": 0.0, "opacity": 1.0}, {"t": t1, "progress": 1.0, "ease": "inout"}]
    if t_end:
        keys += [{"t": t_end, "opacity": 1.0}, {"t": t_end + 0.5, "opacity": 0.0}]
    MAP_EXTRA.append({"id": id_, "type": "dashed_path", "start": t0, "end": (t_end + 0.5) if t_end else FULL_END + 1,
                      "points": [list(p) for p in pts], "props": {"x": 0, "y": 0},
                      "width": width / z, "dash": dash / z, "gap": gap / z, "color": list(color), "keys": keys})


def mcity(key, t0, t1, z, size=1.0):
    """city marker + name on the map, pops in when mentioned"""
    a = "city_" + key
    s = size / z
    x, y = PL[key]
    MAP_EXTRA.append({"id": f"{a}_{int(t0 * 10)}", "type": "image", "asset": a, "start": t0, "end": t1 + 0.5,
                      "anchor": M[a]["anchor"],
                      "keys": [{"t": t0, "x": x, "y": y, "scale": 0.0, "opacity": 1.0},
                               {"t": t0 + 0.18, "scale": s * 1.12, "ease": "out"},
                               {"t": t0 + 0.32, "scale": s, "ease": "inout"},
                               {"t": t1, "opacity": 1.0}, {"t": t1 + 0.5, "opacity": 0.0}]})
    rec("cardboard_hit", t0 + 0.05, -17)


def mobj(id_, asset, t0, t1, keys):
    MAP_EXTRA.append({"id": id_, "type": "image", "asset": asset, "start": t0, "end": t1,
                      "anchor": M[asset].get("anchor", [0.5, 0.5]), "keys": keys})


def follow(pts, sched, n_per_s=15, mirror=False):
    """Move along a polyline with waypoint times sched=[(index, t)].
    Returns (object keys with x, y, rot, progress keys as fraction of the length)."""
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    cum = [0.0]
    for sl in seg:
        cum.append(cum[-1] + sl)
    tot = cum[-1]

    def at(d):
        for i, sl in enumerate(seg):
            if d <= cum[i + 1] or i == len(seg) - 1:
                u = (d - cum[i]) / sl if sl else 0
                a, b = pts[i], pts[i + 1]
                return a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    keys, prog, prev = [], [], None
    samples = []
    for (i0, t0), (i1, t1) in zip(sched, sched[1:]):
        n = max(2, int((t1 - t0) * n_per_s))
        for k in range(n):
            f = k / n
            samples.append((t0 + (t1 - t0) * f, cum[i0] + (cum[i1] - cum[i0]) * f))
    samples.append((sched[-1][1], cum[sched[-1][0]]))
    for t, d in samples:
        x, y, h = at(min(d, tot - 1e-6))
        if prev is not None:
            while h - prev > 180:
                h -= 360
            while h - prev < -180:
                h += 360
            h = prev * 0.75 + h * 0.25
        prev = h
        k = {"t": round(t, 3), "x": x, "y": y, "rot": (h - 180) if mirror else h}
        keys.append(k)
        prog.append({"t": round(t, 3), "progress": round(d / tot, 5)})
    if mirror:
        keys[0]["sx"] = -1
    return keys, prog


def cam_follow(keys, z, every=3, first_ease="inout"):
    for j, k in enumerate(keys[::every]):
        cam(k["t"], (k["x"], k["y"]), z, first_ease if j == 0 else "linear")


def lop(c, deg_len, bearing=157):
    """line of position through c (map px) along bearing/bearing+180, ±deg_len degrees"""
    b = math.radians(bearing)
    dx, dy = math.sin(b) * PPD * deg_len, -math.cos(b) * PPD * deg_len
    return [(c[0] - dx, c[1] - dy), c, (c[0] + dx, c[1] + dy)]


def plane_px(px, z):
    return S.scale_for("st_electra", px) / z


def darkness(id_, t0, t1, op=0.55, color=(14, 22, 38), fade=0.6):
    S.layers.append({"id": id_, "type": "solid", "start": t0, "end": t1 + fade, "color": list(color),
                     "keys": [{"t": t0, "opacity": 0.0}, {"t": t0 + fade, "opacity": op},
                              {"t": t1, "opacity": op}, {"t": t1 + fade, "opacity": 0.0}]})


def drain(id_, t0, t1, sat=0.15):
    S.layers.append({"id": id_, "type": "grade", "start": t0, "end": t1 + 0.6,
                     "keys": [{"t": t0, "saturation": 1.0}, {"t": t0 + 0.6, "saturation": sat},
                              {"t": t1, "saturation": sat}, {"t": t1 + 0.6, "saturation": 1.0}]})


def stamp(id_, asset, t, t_out, x, y, width, rot=-10):
    sm = S.scale_for(asset, width)
    S.image(id_, asset, t, t_out + 0.35, [
        {"t": t, "x": x, "y": y, "scale": sm * 2.2, "rot": rot - 4, "opacity": 0.0}, {"t": t + 0.03, "opacity": 1.0},
        {"t": t + 0.1, "scale": sm, "rot": rot, "ease": "in"}, {"t": t_out, "x": x, "y": y}, exit_to(t_out, x, -400)])
    rec("stamp", t + 0.08, -4)


def waves(prefix, t0, t1, x, y, rot, size=420, step=0.42):
    a_s = S.scale_for("arc_orange", size)
    t, i = t0, 0
    while t < t1:
        S.image(f"{prefix}{i}", "arc_orange", t, t + 1.2, [
            {"t": t, "x": x, "y": y, "scale": a_s * 0.3, "rot": rot, "opacity": 1.0},
            {"t": t + 0.8, "opacity": 0.9}, {"t": t + 1.2, "scale": a_s * 1.4, "opacity": 0.0, "ease": "out"}], jitter=False)
        t += step
        i += 1


def typed_quote(prefix, first_word_t, t_out, x, y, width=820):
    qn = M["quote_words"]
    i0 = next(i for i, x_ in enumerate(WORDS) if x_["start"] >= first_word_t - 0.01)
    qw = WORDS[i0:i0 + qn]
    qs = S.scale_for("quote_01", width)
    sk = slide_in(first_word_t - 0.35, x, H + 400, x, y, qs, 6, -1.5, 0.3) + [
        {"t": t_out, "x": x, "y": y}, exit_to(t_out, x, H + 400, 0.3, rot=8)]
    S.image(prefix + "0", "quote_00", first_word_t - 0.35, qw[0]["start"], sk)
    for k, wd in enumerate(qw, 1):
        e0 = qw[k]["start"] if k < qn else t_out + 0.35
        S.image(f"{prefix}{k}", f"quote_{k:02d}", wd["start"], e0, sk)
        rec("typewriter_key", wd["start"], -8)


# ======================================================================= chapter 1: city markers
for key, t0, t1, z in [("atchison", T1["Kansas"], T1["fliegt28"], 1.7), ("los_angeles", T1["Los"], T1["fliegt28"], 1.7),
                       ("trepassey", T1["fliegt28"] + 0.1, T1["fliegt32"], 0.95),
                       ("burry_port", T1["fliegt28"] + 1.8, T1["fliegt32"], 0.95),
                       ("harbour_grace", T1["fliegt32"], T1["Aber"], 1.3), ("culmore", T1["zweiter"] + 0.1, T1["Aber"], 1.3)]:
    mcity(key, t0, t1, z)

# ======================================================================= CHAPTER 2 – Der Weltflug
T2 = {k: w(k, a - 0.6) for k, a in [("Welt", 95), ("Äquator", 95), ("47", 100), ("Strecke", 100), ("Flugzeug", 106),
                              ("Lockheed", 107), ("Zusatztanks", 107), ("Navigator", 112), ("Fred", 113),
                              ("erste", 118), ("März", 118), ("Hawaii", 118), ("Start", 123), ("bricht", 123),
                              ("schlittert", 123), ("Niemand", 127), ("repariert", 127), ("Juni", 132),
                              ("Osten", 132), ("Miami", 137), ("Südamerika", 137), ("Atlantik", 137), ("Afrika", 137),
                              ("Indien", 137), ("Südostasien", 137), ("Australien", 137), ("Lae", 145), ("Drei", 148),
                              ("Pazifik", 150), ("schwierigste", 152)]}
T_CH3 = w("Ihr", 155)
OAKW, OAKE, HON = PL["oakland_w"], PL["oakland_e"], PL["honolulu"]

card("lbl_kap2", "lbl_t2", T_CH2 - 0.1, 2.0, 620)
cam(T2["Welt"] + 0.3, map_xy(70, 0), 0.34, "inout")
mline("equator", [map_xy(-150, 0), map_xy(295, 0)], T2["Welt"], T2["Äquator"] + 0.8, 0.34, t_end=T2["Flugzeug"],
      color=(246, 240, 226), width=8, dash=26, gap=14)
L("l47", "lbl_47000", T2["47"], T2["Flugzeug"] - 0.3, 960, 300, 480, -2)
L("laeq", "lbl_aequator", T2["Äquator"], T2["Flugzeug"] - 0.3, 960, 760, 560, 2)
cam(T2["Flugzeug"], map_xy(80, 0), 0.36, "linear")
P("electra_big", "st_electra", T2["Flugzeug"], T2["Navigator"] - 0.2, 760, 520, 900, -3, how="slide", frm=(-700, 560), sound="paper_slide")
L("lelectra", "lbl_electra", T2["Lockheed"], T2["Navigator"] - 0.2, 760, 200, 560, -2)
L("ltanks", "lbl_tanks", T2["Zusatztanks"], T2["Navigator"] - 0.2, 1350, 820, 380, 3)
rec("plane_flyby", T2["Flugzeug"] + 0.6, -12, trim=[2.0, 5.0], fade=0.6)
P("noonan", "st_noonan", T2["Navigator"], T2["erste"] - 0.3, 760, 540, 400, -3)
L("lnoonan", "lbl_noonan", T2["Fred"], T2["erste"] - 0.3, 760, 870, 440, 2)
L("lnav", "lbl_navigator", T2["Navigator"] + 0.1, T2["erste"] - 0.3, 760, 160, 340, -2)
P("sext2", "st_sextant", T2["Fred"] + 0.8, T2["erste"] - 0.3, 1300, 560, 380, 6)
# first attempt: Oakland -> Hawaii (westward), crash on take-off
cam(T2["erste"], ((OAKE[0] + HON[0]) / 2, (OAKE[1] + HON[1]) / 2), 0.9, "inout")
mcity("oakland_e", T2["erste"], T2["repariert"], 0.9)
mline("try1", [OAKE, ((OAKE[0] + HON[0]) / 2, (OAKE[1] + HON[1]) / 2 - 40), HON], T2["erste"] + 0.3, T2["Hawaii"] + 0.2, 0.9,
      t_end=T2["repariert"])
k1, _ = follow([OAKE, ((OAKE[0] + HON[0]) / 2, (OAKE[1] + HON[1]) / 2 - 40), HON], [(0, T2["erste"] + 0.3), (2, T2["Hawaii"] + 0.2)], mirror=True)
k1[0]["scale"] = plane_px(150, 0.9)
mobj("plane_try1", "st_electra", T2["erste"] + 0.3, T2["Start"], k1 + [{"t": T2["Start"] - 0.3, "opacity": 1.0}, {"t": T2["Start"], "opacity": 0.0}])
mcity("honolulu", T2["Hawaii"], T2["repariert"], 1.0)
L("lv1", "lbl_versuch1", T2["erste"], T2["Start"] - 0.2, 960, 180, 380, -2)
L("lmaerz", "lbl_maerz", T2["März"], T2["Start"] - 0.2, 960, 860, 440, 2)
cam(T2["Start"], HON, 1.7, "inout")
es2 = S.scale_for("st_electra2", 820)
S.image("skid", "st_electra2", T2["Start"] - 0.1, T2["Niemand"] + 1.2, [
    {"t": T2["Start"] - 0.1, "x": -600, "y": 600, "scale": es2, "rot": 0},
    {"t": T2["bricht"], "x": 700, "y": 600, "rot": 0, "ease": "out"},
    {"t": T2["bricht"] + 0.25, "x": 820, "y": 640, "rot": 18, "ease": "inout"},
    {"t": T2["schlittert"], "x": 1040, "y": 690, "rot": -12},
    {"t": T2["schlittert"] + 0.6, "x": 1120, "y": 700, "rot": 24, "ease": "out"},
    {"t": T2["Niemand"] + 0.8, "x": 1120, "y": 700}, exit_to(T2["Niemand"] + 0.8, 2600, 700, 0.35)])
S.image("dust", "smoke", T2["schlittert"] - 0.1, T2["Niemand"] + 1.0, [
    {"t": T2["schlittert"] - 0.1, "x": 1180, "y": 790, "scale": 0.0, "opacity": 0.8},
    {"t": T2["schlittert"] + 0.5, "scale": S.scale_for("smoke", 520), "ease": "out"},
    {"t": T2["Niemand"] + 0.8, "opacity": 0.0}], jitter=False)
rec("plane_skid", T2["bricht"] - 0.1, -6, trim=[0.0, 3.2], fade=0.6)
L("lrep", "lbl_reparatur", T2["repariert"] - 0.4, T2["Juni"] - 0.2, 960, 830, 600, 2)
# second attempt eastbound, camera follows the plane
cam(T2["repariert"] + 0.7, map_xy(60, 10), 0.33, "inout")
cam(T2["Osten"] + 0.3, OAKW, 0.45, "inout")
rec("map_whoosh", T2["repariert"] + 0.6, -6, peak=0.38)
L("ljuni", "lbl_juni", T2["Juni"], T2["Miami"] - 0.3, 960, 190, 440, -2)
L("losten", "lbl_osten", T2["Osten"], T2["Miami"] - 0.3, 960, 880, 420, 2)
ROUTE = [tuple(p) for p in mp["route"]]
LAE_I = mp["route_lae_index"]
sched = [(0, T2["Osten"] + 0.5), (1, T2["Miami"] + 0.3), (3, T2["Südamerika"] + 0.4), (5, T2["Atlantik"] + 0.2),
         (6, T2["Afrika"] + 0.3), (11, T2["Indien"] + 0.3), (15, T2["Südostasien"] + 0.7), (18, T2["Australien"] + 0.5),
         (LAE_I, T2["Lae"] + 0.2)]
wk, wprog = follow(ROUTE[:LAE_I + 1], sched)
wk[0]["scale"] = plane_px(120, 0.45)
mobj("plane_world", "st_electra", sched[0][1], T2["Pazifik"] + 0.6, wk + [{"t": T2["Pazifik"], "opacity": 1.0}, {"t": T2["Pazifik"] + 0.5, "opacity": 0.0}])
MAP_EXTRA.append({"id": "route_world", "type": "dashed_path", "start": sched[0][1], "end": T_CH3 + 3,
                  "points": [list(p) for p in ROUTE[:LAE_I + 1]], "props": {"x": 0, "y": 0},
                  "width": 6 / 0.45, "dash": 18 / 0.45, "gap": 12 / 0.45, "color": [232, 112, 58],
                  "keys": wprog + [{"t": T_CH3 + 2.4, "opacity": 1.0}, {"t": T_CH3 + 2.9, "opacity": 0.0}]})
cam_follow(wk, 0.45, every=4)
rec("pen_scribble", sched[0][1], -14, trim=[0.0, 3.6], fade=0.4)
rec("plane_distant", sched[0][1], -14, trim=[0.0, T2["Lae"] - sched[0][1] + 0.8], fade=1.0)
mcity("oakland_w", sched[0][1], T_CH3, 0.45)
for key, idx in [("miami", 1), ("natal", 5), ("saint_louis", 6), ("karachi", 11), ("calcutta", 12),
                 ("singapore", 15), ("darwin", 18), ("lae", LAE_I)]:
    t_pass = min(wk, key=lambda k: math.dist((k["x"], k["y"]), ROUTE[idx]))["t"] if idx else sched[0][1]
    mcity(key, t_pass, T_CH3 + 2.4, 0.45)
cam(T2["Drei"], LAE, 0.5, "inout")
L("l34", "lbl_dreiviertel", T2["Drei"], T2["Pazifik"] - 0.2, 960, 220, 520, -2)
PLAN = [LAE, HOW, HON, OAKE]
cam(T2["Pazifik"] + 0.4, map_xy(195, 8), 0.5, "inout")
mline("plan_pacific", [LAE, HOW, (HOW[0] + 120, HOW[1] - 200), HON, OAKE], T2["Pazifik"], T2["Pazifik"] + 2.0, 0.5,
      t_end=T_CH3 + 0.5, color=(246, 240, 226), width=6, dash=14, gap=14)
L("lpaz", "lbl_pazifik", T2["Pazifik"] + 0.2, T_CH3 - 0.2, 960, 200, 620, -2)
rec("suspense_hit", T2["schwierigste"], -12)

# ======================================================================= CHAPTER 3 – Der letzte Flug
T3 = {k: w(k, a - 0.6) for k, a in [("Ziel", 155), ("Howland", 155), ("Insel", 157), ("flach", 157), ("sieht", 157),
                              ("Davor", 165), ("Meer", 166), ("Ohne", 170), ("GPS", 170), ("Uhr", 170),
                              ("Kompass", 170), ("Sternen", 170), ("Fehler", 174), ("vorbei", 174), ("Deshalb", 179),
                              ("Itasca", 179), ("Funk", 183), ("Morgen", 187), ("startet", 188), ("Nacht", 192),
                              ("Sonnenaufgang", 193), ("Stimme", 193), ("lauter", 198), ("Nähe", 199),
                              ("Problem", 201), ("hören", 203), ("nicht", 203), ("Signal", 207), ("Richtung", 207),
                              ("Antenne", 213), ("abbauen", 213), ("weder", 218), ("Morsen", 218), ("7", 222),
                              ("Wir", 224), ("knapp", 227), ("8", 228), ("letzte", 228), ("Linie", 234),
                              ("157", 234), ("Nordnordwest", 240), ("Südsüdost", 240), ("Danach", 244), ("nichts", 244)]}
T_CH4 = w("Die", 245.5)
card("lbl_kap3", "lbl_t3", T_CH3 - 0.2, 2.2, 720)
cam(T3["Howland"], HOW, ZP(60), "inout")
L("lhow", "lbl_howland", T3["Howland"], T3["Davor"] - 0.3, 960, 150, 560, -2)
cam(T3["Insel"] + 0.5, HOW, ZP(24000), "inout")
cam(T3["Davor"] - 0.3, HOW, ZP(26000), "linear")
rec("map_whoosh", T3["Insel"] + 0.2, -5, peak=0.38)
isl_h = 0.0212 * 24000
S.layers.append({"id": "scale23", "type": "dashed_path", "start": T3["Insel"] + 0.8, "end": T3["Davor"],
                 "points": [[1180, CY - isl_h / 2], [1180, CY + isl_h / 2]], "props": {"x": 0, "y": 0},
                 "width": 6, "dash": 16, "gap": 10, "color": [246, 240, 226],
                 "keys": [{"t": T3["Insel"] + 0.8, "progress": 0.0, "opacity": 1.0},
                          {"t": T3["Insel"] + 1.2, "progress": 1.0, "ease": "out"},
                          {"t": T3["Davor"] - 0.4, "opacity": 1.0}, {"t": T3["Davor"] - 0.1, "opacity": 0.0}]})
L("l23", "lbl_25km", T3["Insel"] + 1.0, T3["Davor"] - 0.3, 1370, CY, 280, -3, exit=(2300, CY))
L("lflach", "lbl_flach", T3["flach"], T3["Davor"] - 0.3, 960, 930, 440, 2)
MID = ((LAE[0] + HOW[0]) / 2, (LAE[1] + HOW[1]) / 2)
cam(T3["Davor"] + 0.5, MID, 1.15, "inout")
mline("leg", [LAE, HOW], T3["Davor"] + 0.4, T3["Meer"] + 0.3, 1.15, t_end=T3["Fehler"] - 0.2)
mcity("lae", T3["Davor"] + 0.4, T_CH4, 1.15)
L("l4000", "lbl_4000km", T3["Meer"] - 0.6, T3["Ohne"] - 0.2, 960, 880, 400, 2)
P("phone3", "st_phone", T3["Ohne"], T3["Uhr"] - 0.1, 960, 520, 360, 5)
txs = S.scale_for("tape_x", 420)
S.image("tape3", "tape_x", T3["GPS"], T3["Uhr"] + 0.25, [
    {"t": T3["GPS"], "x": 960, "y": 520, "scale": txs * 1.6, "rot": -8, "opacity": 0.0}, {"t": T3["GPS"] + 0.03, "opacity": 1.0},
    {"t": T3["GPS"] + 0.12, "scale": txs, "ease": "out"}, {"t": T3["Uhr"] - 0.1, "x": 960, "y": 520}, exit_to(T3["Uhr"] - 0.1, 960, 1500)])
rec("paper_tear", T3["GPS"] + 0.05, -9)
P("watch3", "st_watch", T3["Uhr"], T3["Fehler"] - 0.3, 560, 520, 330, -6)
P("compass3", "st_compass", T3["Kompass"], T3["Fehler"] - 0.3, 960, 560, 360, 4)
for i, (x, y) in enumerate([(1290, 300), (1480, 420), (1380, 610), (1640, 280), (1700, 560)]):
    t0 = T3["Sternen"] + 0.08 * i
    S.image(f"star3_{i}", "star", t0, T3["Fehler"], [
        {"t": t0, "x": x, "y": y, "scale": 0.0, "rot": i * 20},
        {"t": t0 + 0.15, "scale": S.scale_for("star", 80 if i % 2 else 110), "ease": "back_out"},
        {"t": T3["Fehler"] - 0.3, "rot": i * 20 + 40}, {"t": T3["Fehler"], "scale": 0.0, "ease": "in"}])
# course error: the right line and one a few degrees off
dvx, dvy = HOW[0] - LAE[0], HOW[1] - LAE[1]
ang_off = math.radians(-5)
wrong = (LAE[0] + 1.25 * (dvx * math.cos(ang_off) - dvy * math.sin(ang_off)),
         LAE[1] + 1.25 * (dvx * math.sin(ang_off) + dvy * math.cos(ang_off)))
mline("right_line", [LAE, HOW], T3["Fehler"] - 0.2, T3["Fehler"] + 0.6, 1.15, t_end=T3["Deshalb"], color=(246, 240, 226))
mline("wrong_line", [LAE, wrong], T3["Fehler"] + 0.3, T3["vorbei"] + 0.3, 1.15, t_end=T3["Deshalb"])
L("lfehler", "lbl_fehler", T3["Fehler"], T3["Deshalb"] - 0.2, 960, 170, 480, -2)
L("lvorbei", "lbl_vorbei", T3["vorbei"], T3["Deshalb"] - 0.2, 1480, 330, 320, 3, exit=(1480, -300))
rec("pen_scribble", T3["Fehler"] + 0.3, -13, trim=[0.0, 2.0], fade=0.3)
# Itasca waits at Howland
Z_IT = ZP(5000)
cam(T3["Deshalb"] + 0.8, (HOW[0] + 330 / Z_IT, HOW[1] + 120 / Z_IT), Z_IT, "inout")
P("itasca3", "st_itasca", T3["Deshalb"] + 1.2, T3["Morgen"] - 0.3, 1220, 700, 620, 0, how="slide", frm=(2400, 720), sound="paper_slide", gain=-8)
rec("ship_horn", T3["Itasca"] + 0.2, -15, trim=[0.0, 2.4], fade=0.8)
L("litasca", "lbl_itasca", T3["Itasca"] + 0.2, T3["Morgen"] - 0.3, 1220, 950, 440, 2)
waves("w3a_", T3["Funk"] - 0.4, T3["Morgen"] - 0.4, 1190, 470, -150)
S.audio.append({"src": "@sfx/morse_beeps", "start": round(T3["Funk"], 3), "gain_db": -22})
# 2 July: take-off in Lae, the night, sunrise
cam(T3["Morgen"] + 0.3, LAE, 1.2, "inout")
L("ldate3", "lbl_date", T3["Morgen"], T3["Nacht"] - 0.2, 960, 170, 480, -2)
fk, fprog = follow([LAE, HOW], [(0, T3["startet"]), (1, T3["Nähe"] + 6.0)])
fk = [k for k in fk if k["t"] <= T3["Nähe"] + 1.5]
fk[0]["scale"] = plane_px(130, 1.2)
mobj("plane_last", "st_electra", T3["startet"], T3["Problem"] + 0.6, fk + [{"t": T3["Problem"], "opacity": 1.0}, {"t": T3["Problem"] + 0.5, "opacity": 0.0}])
MAP_EXTRA.append({"id": "leg_last", "type": "dashed_path", "start": T3["startet"], "end": T3["Problem"] + 0.6,
                  "points": [list(LAE), list(HOW)], "props": {"x": 0, "y": 0}, "width": 6 / 1.2, "dash": 18 / 1.2,
                  "gap": 12 / 1.2, "color": [232, 112, 58],
                  "keys": [k for k in fprog if k["t"] <= T3["Nähe"] + 1.5] + [{"t": T3["Problem"], "opacity": 1.0}, {"t": T3["Problem"] + 0.5, "opacity": 0.0}]})
cam_follow(fk, 1.2, every=4)
cam(T3["Nähe"] + 1.0, (HOW[0] - 60, HOW[1] + 15), 1.6, "inout")
mcity("howland", T3["Stimme"], T_CH4, 1.6)
rec("plane_distant", T3["startet"], -15, trim=[0.0, T3["Problem"] - T3["startet"]], fade=1.5)
darkness("night", T3["Nacht"] - 0.2, T3["Sonnenaufgang"] - 0.1, op=0.55)
for i, (x, y) in enumerate([(300, 180), (620, 120), (980, 210), (1340, 140), (1660, 230), (450, 330), (1500, 380)]):
    t0 = T3["Nacht"] + 0.1 * i
    S.image(f"nstar{i}", "star", t0, T3["Sonnenaufgang"] + 0.4, [
        {"t": t0, "x": x, "y": y, "scale": 0.0, "rot": i * 13},
        {"t": t0 + 0.2, "scale": S.scale_for("star", 60 + 15 * (i % 3)), "ease": "back_out"},
        {"t": T3["Sonnenaufgang"], "opacity": 1.0}, {"t": T3["Sonnenaufgang"] + 0.4, "opacity": 0.0}], jitter=False)
S.flash("sunrise", T3["Sonnenaufgang"], color=(250, 214, 150), peak=0.35)
lw_s = S.scale_for("arc_orange", 300)
t, i = T3["Stimme"], 0
while t < T3["Problem"] - 0.3:
    grow = 0.6 + 1.2 * (t - T3["Stimme"]) / (T3["Problem"] - T3["Stimme"])
    S.image(f"vox{i}", "arc_orange", t, t + 1.1, [
        {"t": t, "x": CX + 30, "y": CY - 30, "scale": lw_s * 0.3 * grow, "rot": -20, "opacity": 1.0},
        {"t": t + 1.1, "scale": lw_s * 1.4 * grow, "opacity": 0.0, "ease": "out"}], jitter=False)
    t += 0.45
    i += 1
S.audio.append({"src": "audio/sfx_prepared/radio_static_long.wav", "start": round(T3["Stimme"], 3), "gain_db": -20,
                "trim": [0.0, 7.0], "fade_out": 1.0})
# the radio problem
L("lprob", "lbl_problem", T3["Problem"], T3["hören"] - 0.2, 960, 540, 520, -2, exit=(960, -300))
rec("drone_dark", T3["Problem"], -15, trim=[0.0, 12.0], fade=2.0)
P("itasca3b", "st_itasca", T3["hören"] - 0.2, T3["Signal"] - 0.3, 520, 560, 560, 0, sound="paper_slide", gain=-9)
P("portrait3", "st_portrait", T3["hören"] - 0.1, T3["Signal"] - 0.3, 1400, 520, 330, 3)
L("lhoeren", "lbl_hoeren", T3["hören"], T3["Signal"] - 0.3, 520, 860, 380, 2)
L("lpeilen", "lbl_peilen", T3["nicht"], T3["Signal"] - 0.3, 960, 170, 440, -2)
S.flash("fl_peil", T3["nicht"], peak=0.4)
rec("suspense_hit", T3["nicht"], -14)
P("radio3", "st_radio", T3["Signal"], T3["Antenne"] - 0.3, 600, 560, 420, 3)
cs3 = S.scale_for("st_compass", 340)
S.image("spin", "st_compass", T3["Signal"] + 0.4, T3["Antenne"] + 0.05, [
    {"t": T3["Signal"] + 0.4, "x": 1300, "y": 560, "scale": cs3, "rot": 0, "opacity": 1.0},
    {"t": T3["Richtung"], "rot": 200, "ease": "inout"}, {"t": T3["Richtung"] + 0.8, "rot": 90, "ease": "inout"},
    {"t": T3["Antenne"] - 0.3, "rot": 140, "ease": "inout", "x": 1300}, exit_to(T3["Antenne"] - 0.3, 2400, 560)])
L("lrichtung", "lbl_keine_richtung", T3["Richtung"], T3["Antenne"] - 0.3, 1300, 860, 440, 2)
P("electra_ant", "st_electra", T3["Antenne"] - 0.2, T3["weder"] - 0.3, 960, 560, 1000, 0, how="slide", frm=(-800, 560), sound="paper_slide")
S.layers.append({"id": "antline", "type": "dashed_path", "start": T3["Antenne"] + 0.2, "end": T3["weder"],
                 "points": [[700, 470], [1200, 455]], "props": {"x": 0, "y": 0}, "width": 6, "dash": 3000, "gap": 1,
                 "color": [232, 112, 58], "keys": [{"t": T3["Antenne"] + 0.2, "progress": 0.0}, {"t": T3["Antenne"] + 0.6, "progress": 1.0},
                                                   {"t": T3["abbauen"] + 0.2, "opacity": 1.0}, {"t": T3["abbauen"] + 0.5, "opacity": 0.0}]})
S.image("tape_ant", "tape_x", T3["abbauen"], T3["weder"], [
    {"t": T3["abbauen"], "x": 950, "y": 465, "scale": txs * 1.4, "rot": -6, "opacity": 0.0}, {"t": T3["abbauen"] + 0.03, "opacity": 1.0},
    {"t": T3["abbauen"] + 0.12, "scale": txs * 0.8, "ease": "out"}, {"t": T3["weder"] - 0.3, "x": 950, "y": 465},
    exit_to(T3["weder"] - 0.3, 950, -400)])
rec("paper_tear", T3["abbauen"] + 0.05, -9)
L("lant", "lbl_antenne", T3["Antenne"] + 0.4, T3["weder"] - 0.3, 960, 870, 520, 2)
P("port3b", "st_portrait", T3["weder"], T3["7"] - 0.3, 520, 520, 320, -4)
P("noon3b", "st_noonan", T3["weder"] + 0.4, T3["7"] - 0.3, 1400, 520, 320, 4)
P("morse", "st_morse", T3["Morsen"] - 0.3, T3["7"] - 0.3, 960, 640, 420, 0)
L("lmorsen", "lbl_morsen", T3["Morsen"], T3["7"] - 0.3, 960, 170, 340, -2)
S.audio.append({"src": "@sfx/morse_beeps", "start": round(T3["Morsen"] - 0.2, 3), "gain_db": -16})
# the last messages
L("l742", "lbl_742", T3["7"], T3["8"] - 0.3, 960, 150, 400, -2)
P("radio3b", "st_radio", T3["7"], T3["8"] - 0.3, 420, 520, 400, 3)
typed_quote("q3_", T3["Wir"], T3["8"] - 0.3, 1150, 660)
rec("typewriter_bell", T3["knapp"] + 0.3, -15)
L("l843", "lbl_843", T3["8"], T3["Linie"] - 0.2, 960, 380, 400, -2)
L("lletzter", "lbl_letzter", T3["letzte"], T3["Linie"] - 0.2, 960, 640, 560, 2)
cam(T3["Linie"], HOW, ZP(60), "inout")
LOP = lop(HOW, 6.0)
mline("lop3", [LOP[0], LOP[2]], T3["157"], T3["157"] + 1.2, ZP(60), t_end=T3["Danach"] + 1.0, color=(246, 240, 226), width=7)
L("l157", "lbl_157", T3["157"], T3["Danach"] - 0.2, 1350, 450, 460, 2, exit=(2400, 450))
for nm, end, lbl, lx, ly, t0 in [("nnw", LOP[0], "lbl_nnw", 640, 200, T3["Nordnordwest"]), ("sso", LOP[2], "lbl_sso", 1300, 900, T3["Südsüdost"])]:
    kk, _ = follow([HOW, end], [(0, t0 - 0.1), (1, t0 + 1.4)], mirror=(nm == "nnw"))
    kk[0]["scale"] = plane_px(110, ZP(60))
    kk[0]["opacity"] = 0.85
    mobj("ghost_" + nm, "st_electra", t0 - 0.1, T3["Danach"] + 0.4, kk + [{"t": T3["Danach"], "opacity": 0.85}, {"t": T3["Danach"] + 0.35, "opacity": 0.0}])
    L("l" + nm, lbl, t0, T3["Danach"] - 0.2, lx, ly, 380, -2 if nm == "nnw" else 2)
rec("radio_cutoff", T3["Danach"], -9, trim=[0.0, 2.0], fade=0.4)
drain("drain3", T3["Danach"], T_CH4 - 0.2)
L("lnm", "lbl_nichts_mehr", T3["nichts"], T_CH4 - 0.1, 960, 540, 520, -2, sound=None)

# ======================================================================= CHAPTER 4 – Die Suche
T4 = {k: w(k, a - 0.6) for k, a in [("fährt", 246), ("halbe", 248), ("Colorado", 250), ("Wasserflugzeugen", 250),
                              ("Lexington", 250), ("sechzig", 250), ("Wochen", 257), ("600", 259), ("teuerste", 262),
                              ("Gefunden", 268), ("nichts", 269), ("1939", 270), ("tot", 270), ("Rätsel", 275),
                              ("wo", 279), ("vier", 281)]}
T_CH5 = w("Die", 284)
card("lbl_kap4", "lbl_t4", T_CH4 - 0.1, 2.0, 520)
cam(T4["fährt"], HOW, ZP(50), "inout")
itk, _ = follow([HOW, (HOW[0] - 70, HOW[1] - 60)], [(0, T4["fährt"]), (1, T4["halbe"] + 1.5)], mirror=True)
itk[0]["scale"] = S.scale_for("st_itasca", 150) / ZP(50)
mobj("itasca_map", "st_itasca", T4["fährt"], T4["halbe"] + 1.5, [dict(k, rot=0) for k in itk])
CEN4 = ((HON[0] + HOW[0]) / 2, (HON[1] + HOW[1]) / 2)
cam(T4["halbe"] + 0.4, CEN4, 0.85, "inout")
for nm, asset, t_s, dy in [("col", "st_colorado", T4["halbe"], -55), ("lex", "st_lexington", T4["halbe"] + 2.2, 55)]:
    sk, _ = follow([(HON[0], HON[1] + dy), (HOW[0] + 40, HOW[1] + dy)], [(0, t_s), (1, T4["Wochen"])], mirror=True)
    sk = [dict(k, rot=0) for k in sk]
    sk[0].update(scale=S.scale_for(asset, 15) / 0.85, opacity=0.0)
    sk.insert(1, {"t": round(t_s + 0.3, 3), "scale": S.scale_for(asset, 130) / 0.85, "opacity": 1.0, "ease": "out"})
    mobj("ship_" + nm, asset, t_s, T4["Wochen"] + 0.3, fix_keys(sk))
    rec("ship_horn", t_s + 0.1, -15, trim=[0.0, 2.0], fade=0.6)
mcity("honolulu", T4["halbe"], T4["Wochen"], 0.85)
mcity("howland", T4["halbe"], T4["Wochen"], 0.85)
P("colorado4", "st_colorado", T4["Colorado"], T4["Lexington"] - 0.3, 700, 560, 760, -2, how="slide", frm=(-800, 560), sound="paper_slide")
L("lcol", "lbl_colorado", T4["Colorado"] + 0.2, T4["Lexington"] - 0.3, 700, 220, 440, -2)
P("float4", "st_floatplane", T4["Wasserflugzeugen"], T4["Lexington"] - 0.3, 1450, 400, 420, 6)
rec("plane_flyby", T4["Wasserflugzeugen"] + 0.4, -14, trim=[2.0, 4.6], fade=0.5)
P("lex4", "st_lexington", T4["Lexington"], T4["Wochen"] - 0.3, 1100, 600, 820, 2, how="slide", frm=(2600, 620), sound="paper_slide")
L("llex", "lbl_lexington", T4["Lexington"] + 0.2, T4["Wochen"] - 0.3, 1100, 220, 460, 2)
L("l60", "lbl_60", T4["sechzig"], T4["Wochen"] - 0.3, 520, 860, 460, -2)
cam(T4["Wochen"], HOW, ZP(40), "inout")
for k_, rdeg in enumerate((1.5, 3.0, 4.8)):
    r = rdeg * PPD
    mline(f"search{k_}", [(HOW[0] + r * math.cos(a), HOW[1] + r * math.sin(a)) for a in [2 * math.pi * j / 90 for j in range(91)]],
          T4["Wochen"] + 0.2 + 0.5 * k_, T4["Wochen"] + 1.8 + 0.5 * k_, ZP(40), t_end=T4["1939"], color=(246, 240, 226), width=6)
S.audio.append({"src": "audio/sfx_prepared/sonar_ping.wav", "start": round(T4["Wochen"], 3), "gain_db": -12})
L("l2w", "lbl_2wochen", T4["Wochen"], T4["600"] - 0.2, 960, 170, 420, -2)
bs = (2 * 3.9 * PPD) / M["burst_orange"]["w"]
mobj("search_area", "burst_orange", T4["600"], T4["1939"] + 0.5, [
    {"t": T4["600"], "x": HOW[0], "y": HOW[1], "scale": 0.0, "opacity": 0.5},
    {"t": T4["600"] + 0.6, "scale": bs, "ease": "out"}, {"t": T4["1939"], "opacity": 0.5}, {"t": T4["1939"] + 0.5, "opacity": 0.0}])
L("l600", "lbl_600k", T4["600"], T4["Gefunden"] - 0.2, 960, 170, 520, -2)
L("lteuer", "lbl_teuer", T4["teuerste"], T4["Gefunden"] - 0.2, 960, 900, 500, 2)
P("news37", "st_news1937", T4["600"] + 0.9, T4["Gefunden"] - 0.2, 1440, 560, 600, 5, sound="newspaper", gain=-14)
L("lnichts4", "lbl_nichts", T4["nichts"], T4["1939"] - 0.2, 960, 540, 520, -2, gain=-5)
S.flash("fl4", T4["nichts"], peak=0.45)
rec("suspense_hit", T4["nichts"], -9)
L("l1939", "lbl_1939", T4["1939"], T4["Rätsel"] - 0.2, 600, 200, 300, -3)
P("port4", "st_portrait2", T4["1939"] + 0.2, T4["Rätsel"] - 0.2, 960, 560, 380, 2)
L("ltot", "lbl_tot", T4["tot"], T4["Rätsel"] - 0.2, 960, 900, 480, 2)
drain("drain4", T4["tot"], T4["Rätsel"])
cam(T4["Rätsel"], map_xy(185, 2), 0.6, "inout")
L("l4th", "lbl_4theorien", T4["vier"], T_CH5 + 0.2, 960, 160, 520, -2)
for k_, (aid, x, y, wd, rot) in enumerate([("st_electra", 420, 420, 360, -5), ("st_crab", 1500, 420, 300, 5),
                                           ("st_photo2017", 430, 780, 360, 4), ("st_house", 1500, 780, 320, -4)]):
    P(f"th4_{k_}", aid, T4["vier"] + 0.2 + 0.2 * k_, T_CH5 + 0.2, x, y, wd, rot, gain=-11)
    L(f"th4n_{k_}", f"lbl_n{k_ + 1}", T4["vier"] + 0.3 + 0.2 * k_, T_CH5 + 0.2, x + (170 if x < CX else -170), y - 90, 90, 0, sound=None)

# ======================================================================= CHAPTER 5 – Theorie 1: Absturz ins Meer
T5 = {k: w(k, a - 0.6) for k, a in [("verfehlt", 287), ("Benzin", 289), ("stürzt", 289), ("versinkt", 289), ("Problem", 294),
                              ("tief", 295), ("Flugzeugwrack", 298), ("Stadions", 298), ("Augen", 298),
                              ("Trotzdem", 307), ("Expeditionen", 308), ("Sonar", 308), ("Anfang", 313), ("Sensation", 313), ("Sonarbild", 316),
                              ("160", 316), ("Form", 324), ("Atem", 327), ("Tauchroboter", 329), ("Felsen", 333),
                              ("Electra", 335)]}
T_CH6 = w("Erinnerst", 339)
card("lbl_th1", "lbl_t5", T_CH5 - 0.1, 2.3, 780)
Z5 = ZP(2500)
cam(T5["verfehlt"] - 0.4, (HOW[0] + 0.01 * PPD, HOW[1]), Z5, "inout")
mk, _ = follow([(HOW[0] - 0.12 * PPD, HOW[1] + 0.05 * PPD), (HOW[0] + 0.14 * PPD, HOW[1] - 0.045 * PPD)],
               [(0, T5["verfehlt"] - 0.3), (1, T5["Benzin"] + 0.3)])
mk[0]["scale"] = plane_px(170, Z5)
mobj("miss", "st_electra", T5["verfehlt"] - 0.3, T5["Benzin"] + 0.4, mk)
L("lverf", "lbl_verfehlt", T5["verfehlt"], T5["Benzin"] - 0.1, 960, 880, 480, 2)
S.image("ocean5", "ocean_strip", T5["Benzin"], T5["Trotzdem"] + 0.3,
        slide_in(T5["Benzin"], CX, H + 300, CX, 900, S.scale_for("ocean_strip", 2100), 0, -1) +
        [{"t": T5["Trotzdem"] - 0.1, "x": CX, "y": 900}, exit_to(T5["Trotzdem"] - 0.1, CX, H + 400)], jitter=False)
fs5 = S.scale_for("st_electra", 520)
S.layers.insert(len(S.layers) - 1, {"id": "fall", "type": "image", "asset": "st_electra", "start": T5["Benzin"], "end": T5["Problem"],
                "anchor": M["st_electra"]["anchor"], "jitter": {"pos": 1.6, "rot": 0.25, "fps": 12},
                "keys": [{"t": T5["Benzin"], "x": 400, "y": 200, "scale": fs5, "rot": 4},
                         {"t": T5["stürzt"], "x": 820, "y": 420, "rot": 22, "ease": "in"},
                         {"t": T5["stürzt"] + 0.6, "x": 980, "y": 820, "rot": 48, "ease": "in"},
                         {"t": T5["versinkt"] + 0.6, "x": 1010, "y": 1150, "rot": 58}]})
S.image("splash", "burst_orange", T5["stürzt"] + 0.5, T5["Problem"], [
    {"t": T5["stürzt"] + 0.5, "x": 990, "y": 820, "scale": 0.0, "opacity": 0.9},
    {"t": T5["stürzt"] + 0.9, "scale": S.scale_for("burst_orange", 520), "ease": "out"},
    {"t": T5["Problem"] - 0.3, "opacity": 0.0}], jitter=False)
rec("rock_thud", T5["stürzt"] + 0.55, -5)
darkness("deep5", T5["versinkt"] + 0.4, T5["Trotzdem"] - 0.2, op=0.68, color=(8, 18, 34))
rec("underwater", T5["versinkt"] + 0.3, -13, trim=[0.0, 12.0], fade=1.5)
S.layers.append({"id": "depth", "type": "dashed_path", "start": T5["tief"] - 0.2, "end": T5["Stadions"] - 0.2,
                 "points": [[1500, 120], [1500, 960]], "props": {"x": 0, "y": 0}, "width": 6, "dash": 22, "gap": 14,
                 "color": [246, 240, 226], "keys": [{"t": T5["tief"] - 0.2, "progress": 0.0}, {"t": T5["tief"] + 0.8, "progress": 1.0},
                                                    {"t": T5["Stadions"] - 0.6, "opacity": 1.0}, {"t": T5["Stadions"] - 0.2, "opacity": 0.0}]})
L("l5km", "lbl_5km", T5["tief"], T5["Stadions"] - 0.5, 1200, 540, 420, 2, exit=(2300, 540))
S.image("mag5", "st_magnifier", T5["Stadions"] - 0.3, T5["Trotzdem"], [
    {"t": T5["Stadions"] - 0.3, "x": 400, "y": 420, "scale": S.scale_for("st_magnifier", 380), "rot": -20, "opacity": 0.0},
    {"t": T5["Stadions"], "opacity": 0.8}, {"t": T5["Augen"], "x": 1300, "y": 600, "rot": -10, "ease": "inout"},
    {"t": T5["Trotzdem"] - 0.3, "x": 800, "y": 500, "opacity": 0.0, "ease": "inout"}], anchor=list(M["st_magnifier"]["lens"]))
# the plane sinks next to the depth line
es = S.scale_for("st_electra", 300)
S.image("sink5", "st_electra", T5["tief"] - 0.1, T5["Stadions"] + 0.2, [
    {"t": T5["tief"] - 0.1, "x": 1330, "y": 150, "scale": es, "rot": 38, "opacity": 0.0},
    {"t": T5["tief"] + 0.2, "opacity": 0.95},
    {"t": T5["Stadions"] - 0.4, "x": 1360, "y": 880, "scale": es * 0.55, "rot": 62, "opacity": 0.45, "ease": "inout"},
    {"t": T5["Stadions"] + 0.2, "opacity": 0.0}])
Z5b = ZP(110)
cam(T5["Trotzdem"], (HOW[0] - 0.8 * PPD, HOW[1]), Z5b, "inout")


def search_grid(id_, x0, x1, y0, y1, lanes, t0, t1, color, ship_w, t_end):
    """lawnmower sonar lanes in screen space, drawn while a ship sails them"""
    pts = []
    for k_ in range(lanes):
        yy = y0 + (y1 - y0) * k_ / (lanes - 1)
        pts += [(x0, yy), (x1, yy)] if k_ % 2 == 0 else [(x1, yy), (x0, yy)]
    S.layers.append({"id": id_, "type": "dashed_path", "start": t0, "end": t_end + 0.5,
                     "points": [list(q) for q in pts], "props": {"x": 0, "y": 0}, "width": 5, "dash": 14, "gap": 9,
                     "color": list(color), "keys": [{"t": t0, "progress": 0.0, "opacity": 1.0}, {"t": t1, "progress": 1.0},
                                                    {"t": t_end, "opacity": 1.0}, {"t": t_end + 0.5, "opacity": 0.0}]})
    seg = [math.dist(u, v) for u, v in zip(pts, pts[1:])]
    tot, d, keys = sum(seg), 0.0, []
    ship = "st_research" if "st_research" in M else "st_itasca"
    sc = S.scale_for(ship, ship_w)
    for (u, v), sl in zip(zip(pts, pts[1:]), seg):
        ta, tb = t0 + (t1 - t0) * d / tot, t0 + (t1 - t0) * (d + sl) / tot
        sx = 1 if v[0] > u[0] else -1
        keys.append({"t": round(ta, 3), "x": u[0], "y": u[1] - 26, "sx": sx})
        keys.append({"t": round(min(tb, ta + 0.18), 3), "sx": sx})
        d += sl
    keys.append({"t": round(t1, 3), "x": pts[-1][0], "y": pts[-1][1] - 22})
    keys[0].update(scale=sc * 0.2, opacity=0.0, rot=0)
    keys.insert(1, {"t": round(t0 + 0.12, 3), "scale": sc, "opacity": 1.0})
    keys += [{"t": t_end, "opacity": 1.0}, {"t": t_end + 0.4, "opacity": 0.0}]
    S.image(id_ + "_ship", ship, t0, t_end + 0.5, keys)


search_grid("grid_a", 330, 900, 330, 800, 6, T5["Trotzdem"] + 0.5, T5["Anfang"] - 0.1, (246, 240, 226), 230, T5["Anfang"] - 0.1)
search_grid("grid_b", 1020, 1590, 380, 850, 6, T5["Expeditionen"], T5["Anfang"] - 0.1, (232, 112, 58), 200, T5["Anfang"] - 0.1)
rec("paper_drop", T5["Trotzdem"] + 0.55, -14)
rec("paper_drop", T5["Expeditionen"] + 0.05, -15)
L("lsonar", "lbl_sonar", T5["Sonar"], T5["Anfang"] - 0.2, 960, 120, 320, -2)
S.audio.append({"src": "audio/sfx_prepared/sonar_ping.wav", "start": round(T5["Sonar"], 3), "gain_db": -15})
L("l2024", "lbl_2024", T5["Anfang"], T5["Sonarbild"] - 0.2, 600, 200, 300, -3)
P("news5", "st_news2024", T5["Sensation"] - 0.2, T5["Sonarbild"] + 0.6, 1280, 540, 680, 4, sound="newspaper", gain=-14)
L("lsens", "lbl_sensation", T5["Sensation"], T5["Sonarbild"] - 0.2, 760, 760, 460, -2)
TGT = map_xy(-178.0, 1.35)
cam(T5["Sonarbild"], ((HOW[0] + TGT[0]) / 2, (HOW[1] + TGT[1]) / 2), Z5b, "inout")
mline("to_tgt", [HOW, TGT], T5["160"] - 0.3, T5["160"] + 0.6, Z5b, t_end=T5["Form"] + 0.5)
mobj("tgt", "dot", T5["160"] + 0.4, T5["Form"] + 0.6, [
    {"t": T5["160"] + 0.4, "x": TGT[0], "y": TGT[1], "scale": 0.0},
    {"t": T5["160"] + 0.55, "scale": 0.3 / Z5b, "ease": "out"}, {"t": T5["Form"], "opacity": 1.0}, {"t": T5["Form"] + 0.5, "opacity": 0.0}])
mcity("howland", T5["Sonarbild"], T5["Form"], Z5b)
L("l160", "lbl_160km", T5["160"], T5["Form"] - 0.2, 960, 870, 360, 2)
darkness("deep5b", T5["Form"] - 0.3, T_CH6 - 0.3, op=0.62, color=(8, 18, 34))
rec("underwater", T5["Form"] - 0.2, -16, trim=[0.0, 15.0], fade=2.0)
# the sonar image: looks like a plane – the rock is only revealed at "Felsen"
SON = (620, 560)
ss = S.scale_for("st_sonar", 860)
S.image("sonar5", "st_sonar", T5["Form"], T5["Felsen"] + 0.15, [
    {"t": T5["Form"], "x": 960, "y": 540, "scale": ss * 0.15, "rot": -3, "opacity": 0.0}, {"t": T5["Form"] + 0.05, "opacity": 1.0},
    {"t": T5["Form"] + 0.35, "scale": ss, "ease": "out"}, {"t": T5["Atem"], "scale": ss * 1.05, "ease": "inout"},
    {"t": T5["Tauchroboter"] - 0.1, "x": 960, "y": 540},
    {"t": T5["Tauchroboter"] + 0.5, "x": SON[0], "y": SON[1], "scale": ss * 0.75, "ease": "inout"},
    {"t": T5["Felsen"], "opacity": 1.0}, {"t": T5["Felsen"] + 0.12, "opacity": 0.0}])
rec("sonar_ping", T5["Form"] + 0.1, -16)
rec("heartbeat_low", T5["Atem"] - 0.2, -14, trim=[0.0, 3.5], fade=0.8)
auk = S.scale_for("st_auv", 520)
S.image("auv", "st_auv", T5["Tauchroboter"], T5["Felsen"] + 0.4, [
    {"t": T5["Tauchroboter"], "x": 2300, "y": 160, "scale": auk, "rot": 14, "opacity": 1.0},
    {"t": T5["Tauchroboter"] + 0.9, "x": 1300, "y": 330, "rot": 10, "ease": "out3"},
    {"t": T5["Felsen"] - 0.1, "x": 1060, "y": 430, "rot": 16, "ease": "inout"},
    exit_to(T5["Felsen"] + 0.05, 2400, 200, 0.35)])
rec("paper_slide", T5["Tauchroboter"] + 0.1, -8, peak=0.42)
rec("underwater", T5["Tauchroboter"] + 0.2, -18, trim=[3.0, 6.0], fade=1.0)
rs = S.scale_for("st_rock", 640)
S.image("rock", "st_rock", T5["Felsen"], T_CH6 - 0.2, [
    {"t": T5["Felsen"], "x": SON[0], "y": SON[1], "scale": rs * 1.25, "rot": -4, "opacity": 0.0},
    {"t": T5["Felsen"] + 0.08, "opacity": 1.0}, {"t": T5["Felsen"] + 0.3, "scale": rs, "ease": "out"},
    {"t": T_CH6 - 0.5, "x": SON[0], "y": SON[1]}, exit_to(T_CH6 - 0.5, -700, SON[1])])
S.flash("fl5", T5["Felsen"], color=(246, 240, 226), peak=0.35)
L("lfels", "lbl_felsen", T5["Felsen"], T_CH6 - 0.4, 960, 170, 520, -2, gain=-12)
rec("rock_thud", T5["Felsen"] + 0.05, -10)
P("electra5", "st_electra", T5["Electra"] - 0.2, T_CH6 - 0.5, 1340, 560, 640, -3)

# ======================================================================= CHAPTER 6 – Theorie 2: Nikumaroro
T6 = {k: w(k, a - 0.6) for k, a in [("Linie", 342), ("Folgt", 346), ("650", 346), ("Insel", 346), ("Nikumaroro", 353),
                              ("Gardner", 353), ("einsames", 356), ("Theorie", 358), ("Riff", 360), ("Hinweise", 365),
                              ("Notrufe", 367), ("Land", 375), ("Wasser", 379), ("1940", 383), ("Kolonialbeamter", 383),
                              ("Skelett", 383), ("Frauenschuhs", 390), ("Kiste", 390), ("13", 394), ("Kokoskrabben", 396),
                              ("Meter", 396), ("Finder", 403), ("verschleppt", 403), ("Experiment", 407), ("Fidschi", 411),
                              ("Arzt", 414), ("Mann", 416), ("2018", 417), ("Jantz", 417), ("99", 424),
                              ("nachprüfen", 430), ("verschwunden", 432), ("Dinge", 435), ("Glasscherben", 439),
                              ("Aluminium", 439), ("Beweise", 448), ("Oktober", 451), ("Satellitenbildern", 454),
                              ("Team", 460), ("Baumstämme", 463)]}
T_CH7 = w("Die", 465.5)
card("lbl_th2", "lbl_t6", T_CH6 - 0.1, 2.3, 980)
cam(T6["Linie"] - 0.2, HOW, ZP(60), "inout")
mline("lop6", [LOP[0], LOP[2]], T6["Linie"], T6["Linie"] + 1.0, ZP(60), t_end=T6["Nikumaroro"], color=(246, 240, 226), width=7)
L("l157b", "lbl_157", T6["Linie"], T6["Folgt"] - 0.2, 1350, 450, 460, 2, exit=(2400, 450))
Z6 = ZP(45)
gk, gprog = follow([HOW, NIK], [(0, T6["Folgt"]), (1, T6["Insel"] + 0.3)])
gk[0]["scale"] = plane_px(120, Z6)
mobj("plane_niku", "st_electra", T6["Folgt"], T6["Nikumaroro"] + 0.6, gk + [{"t": T6["Nikumaroro"], "opacity": 1.0}, {"t": T6["Nikumaroro"] + 0.5, "opacity": 0.0}])
MAP_EXTRA.append({"id": "line_niku", "type": "dashed_path", "start": T6["Folgt"], "end": T6["Nikumaroro"] + 0.6,
                  "points": [list(HOW), list(NIK)], "props": {"x": 0, "y": 0}, "width": 6 / Z6, "dash": 18 / Z6,
                  "gap": 12 / Z6, "color": [232, 112, 58],
                  "keys": gprog + [{"t": T6["Nikumaroro"], "opacity": 1.0}, {"t": T6["Nikumaroro"] + 0.5, "opacity": 0.0}]})
cam(T6["Folgt"] + 0.3, ((HOW[0] + NIK[0]) / 2, (HOW[1] + NIK[1]) / 2), Z6, "inout")
mcity("howland", T6["Folgt"], T6["Nikumaroro"], Z6)
L("l650", "lbl_650km", T6["650"], T6["Nikumaroro"] - 0.2, 1350, 540, 340, 2, exit=(2400, 540))
cam(T6["Nikumaroro"] + 0.5, NIK, ZP(10000), "inout")
rec("map_whoosh", T6["Nikumaroro"] + 0.2, -5, peak=0.38)
rec("ocean_wind", T6["Nikumaroro"], -20, trim=[0.0, 14.0], fade=2.0)
L("lniku6", "lbl_nikumaroro", T6["Nikumaroro"] + 0.2, T6["Theorie"] - 0.2, 960, 150, 460, -2)
L("lgard", "lbl_gardner", T6["Gardner"], T6["Theorie"] - 0.2, 960, 920, 420, 2)
P("land6", "st_electra", T6["Riff"] - 0.6, T6["Hinweise"] - 0.2, 1420, 760, 420, -8, how="slide", frm=(2500, 640), sound="paper_slide")
rec("plane_skid", T6["Riff"] - 0.1, -14, trim=[0.0, 2.0], fade=0.6)
L("lriff", "lbl_riff", T6["Riff"], T6["Hinweise"] - 0.2, 960, 170, 520, -2)
cam(T6["Hinweise"], NIK, ZP(4000), "inout")
P("listener", "st_listener", T6["Notrufe"] - 0.3, T6["Land"] - 0.2, 1350, 560, 640, 3)
waves("w6_", T6["Notrufe"] - 0.2, T6["Land"] - 0.4, 760, 480, 180, size=360)
S.audio.append({"src": "audio/sfx_prepared/radio_static_long.wav", "start": round(T6["Notrufe"] - 0.2, 3), "gain_db": -18,
                "trim": [0.0, T6["Land"] - T6["Notrufe"] + 0.3], "fade_out": 0.6})
L("lnot", "lbl_notrufe", T6["Notrufe"], T6["Land"] - 0.2, 600, 170, 380, -2)
P("land6b", "st_electra", T6["Land"] - 0.2, T6["1940"] - 0.3, 760, 600, 520, -6)
L("lanland", "lbl_an_land", T6["Land"], T6["Wasser"] - 0.2, 760, 880, 380, 2)
P("radio6", "st_radio", T6["Wasser"], T6["1940"] - 0.3, 1350, 560, 380, 4)
S.image("tape6", "tape_x", T6["Wasser"] + 0.6, T6["1940"], [
    {"t": T6["Wasser"] + 0.6, "x": 1350, "y": 560, "scale": txs * 1.5, "rot": -8, "opacity": 0.0}, {"t": T6["Wasser"] + 0.63, "opacity": 1.0},
    {"t": T6["Wasser"] + 0.72, "scale": txs * 0.9, "ease": "out"}, {"t": T6["1940"] - 0.3, "x": 1350, "y": 560}, exit_to(T6["1940"] - 0.3, 2400, 560)])
cam(T6["1940"], NIK, ZP(9500), "inout")
L("l1940", "lbl_1940", T6["1940"], T6["13"] - 0.2, 480, 170, 300, -3)
P("gallagher", "st_gallagher", T6["Kolonialbeamter"] - 0.2, T6["13"] - 0.2, 380, 600, 380, -3)
P("bones6", "st_bones", T6["Skelett"], T6["verschleppt"] + 1.6, 1000, 560, 520, -6, gain=-5)
rec("bones_rattle", T6["Skelett"], -7)
rec("heartbeat_low", T6["Skelett"] + 0.3, -11, trim=[0.0, 4.0], fade=0.8)
P("shoe6", "st_shoe", T6["Frauenschuhs"], T6["13"] - 0.2, 1500, 400, 340, 8)
P("box6", "st_box_empty", T6["Kiste"], T6["13"] - 0.2, 1500, 760, 360, -5)
L("l13", "lbl_13", T6["13"], T6["Experiment"] - 0.2, 960, 170, 480, -2, gain=-6)
for k_, (y, dl) in enumerate([(840, 0.0), (330, 0.35), (760, 0.7)]):
    cs = S.scale_for("st_crab", 300 if k_ != 1 else 240)
    t0 = T6["Kokoskrabben"] + dl
    S.image(f"crab{k_}", "st_crab", t0, T6["Experiment"] + 0.5, [
        {"t": t0, "x": -300 if k_ != 1 else 2200, "y": y, "scale": cs, "rot": 0},
        {"t": t0 + 1.2, "x": 520 + 380 * k_, "y": y, "ease": "out"},
        {"t": T6["verschleppt"] - 0.2, "x": 560 + 380 * k_, "y": y},
        {"t": T6["verschleppt"] + 1.2, "x": 2400 if k_ != 1 else -400, "y": y + 20, "ease": "in"}])
rec("crab_scuttle", T6["Kokoskrabben"], -10, trim=[0.0, T6["Experiment"] - T6["Kokoskrabben"] + 0.5], fade=0.6)
L("lkrabbe", "lbl_krabbe", T6["Kokoskrabben"] + 0.2, T6["Finder"] - 0.2, 960, 600, 440, 2)
L("l1m", "lbl_1m", T6["Meter"], T6["Finder"] - 0.2, 1450, 600, 300, -3)
P("scribble6", "scribble", T6["Experiment"], T6["Fidschi"] - 0.2, 960, 560, 460, -4, sound="paper_slide")
L("lexp", "lbl_experiment", T6["Experiment"] + 0.1, T6["Fidschi"] - 0.2, 960, 880, 420, 2)
FIJ = PL["fiji"]
cam(T6["Fidschi"] - 0.2, ((NIK[0] + FIJ[0]) / 2, (NIK[1] + FIJ[1]) / 2), 1.4, "inout")
mline("to_fiji", [NIK, FIJ], T6["Fidschi"], T6["Fidschi"] + 1.2, 1.4, t_end=T6["2018"])
mcity("nikumaroro", T6["Fidschi"] - 0.1, T6["2018"], 1.4)
mcity("fiji", T6["Fidschi"] + 0.9, T6["2018"], 1.4)
P("doctor6", "st_doctor", T6["Arzt"] - 0.1, T6["2018"] - 0.2, 420, 560, 420, -3, how="slide", frm=(-500, 580), sound="paper_slide")
P("caliper6", "st_caliper", T6["Arzt"] + 0.6, T6["2018"] - 0.2, 1100, 420, 520, 8)
FX6, FY6 = 1250, 720
P("folder6", "st_folder", T6["Mann"] - 0.4, T6["nachprüfen"] - 0.2, FX6, FY6, 380, 4)
stamp("stamp6", "stamp_mann", T6["Mann"], T6["99"] + 1.2, FX6, FY6 - 20, 300, rot=-12)
S.flash("fl6", T6["Mann"], peak=0.35)
L("l2018", "lbl_2018", T6["2018"], T6["nachprüfen"] - 0.2, 480, 170, 300, -3)
L("ljantz", "lbl_jantz", T6["Jantz"], T6["nachprüfen"] - 0.2, 480, 880, 440, 2)
P("scr6b", "scribble", T6["Jantz"] + 0.5, T6["99"] - 0.2, 480, 540, 380, -5, sound="paper_slide", gain=-9)
S.layers.append({"id": "strike6", "type": "dashed_path", "start": T6["99"], "end": T6["nachprüfen"],
                 "points": [[FX6 - 180, FY6 + 10], [FX6 + 180, FY6 - 50]], "props": {"x": 0, "y": 0}, "width": 14,
                 "dash": 2000, "gap": 1, "color": [232, 112, 58],
                 "keys": [{"t": T6["99"], "progress": 0.0}, {"t": T6["99"] + 0.3, "progress": 1.0, "ease": "out"},
                          {"t": T6["nachprüfen"] - 0.4, "opacity": 1.0}, {"t": T6["nachprüfen"] - 0.1, "opacity": 0.0}]})
L("l99", "lbl_99", T6["99"], T6["nachprüfen"] - 0.2, 760, 300, 280, -3)
P("port6", "st_portrait", T6["99"] + 0.3, T6["nachprüfen"] - 0.2, 760, 640, 300, 3)
P("fopen6", "st_folder_open", T6["nachprüfen"], T6["Dinge"] - 0.2, 960, 580, 560, 2)
L("lversch", "lbl_verschwunden", T6["verschwunden"], T6["Dinge"] - 0.2, 960, 180, 480, -2)
rec("box_open", T6["nachprüfen"] + 0.2, -9, trim=[0.0, 1.0], fade=0.3)
cam(T6["Dinge"], NIK, ZP(9500), "inout")
P("jar6", "st_jar", T6["Glasscherben"], T6["Beweise"] - 0.2, 560, 560, 360, -4)
L("lcreme", "lbl_creme", T6["Glasscherben"] + 1.4, T6["Beweise"] - 0.2, 560, 870, 520, 2)
P("alu6", "st_alu", T6["Aluminium"] - 0.2, T6["Beweise"] - 0.2, 1350, 520, 520, 5)
L("lalu", "lbl_alu", T6["Aluminium"] + 0.4, T6["Beweise"] - 0.2, 1350, 860, 420, -2)
stamp("stamp6b", "stamp_keinbeweis", T6["Beweise"], T6["Oktober"] - 0.2, 960, 540, 520)
L("lokt6", "lbl_okt2026", T6["Oktober"], T6["Team"] - 0.2, 960, 160, 480, -2)
sat_c = (NIK[0] - 0.006 * PPD, NIK[1] - 0.002 * PPD)
r_c6 = 0.008 * PPD
zsat = ZP(9500)
MAP_EXTRA.append({"id": "satcircle6", "type": "dashed_path", "start": T6["Satellitenbildern"], "end": T6["Baumstämme"] + 1.0,
                  "points": [[sat_c[0] + r_c6 * math.cos(a), sat_c[1] + r_c6 * math.sin(a)] for a in [2 * math.pi * j / 60 for j in range(61)]],
                  "props": {"x": 0, "y": 0}, "width": 7 / zsat, "dash": 22 / zsat, "gap": 14 / zsat, "color": [232, 112, 58],
                  "keys": [{"t": T6["Satellitenbildern"], "progress": 0.0, "opacity": 1.0},
                           {"t": T6["Satellitenbildern"] + 0.8, "progress": 1.0, "ease": "inout"},
                           {"t": T6["Baumstämme"] + 0.5, "opacity": 1.0}, {"t": T6["Baumstämme"] + 1.0, "opacity": 0.0}]})
L("lsat6", "lbl_satellit", T6["Satellitenbildern"], T6["Team"] - 0.2, 1450, 860, 440, 3)

if "st_satplane" in M:
    sp = S.scale_for("st_satplane", 820)
    S.image("satimg6", "st_satplane", T6["Satellitenbildern"] + 0.2, T6["Baumstämme"] - 0.45, [
        {"t": T6["Satellitenbildern"] + 0.2, "x": 900, "y": 520, "scale": sp * 0.15, "rot": 2, "opacity": 0.0},
        {"t": T6["Satellitenbildern"] + 0.25, "opacity": 1.0}, {"t": T6["Satellitenbildern"] + 0.55, "scale": sp, "ease": "out"},
        {"t": T6["Baumstämme"] - 0.6, "scale": sp * 1.04, "opacity": 1.0}, {"t": T6["Baumstämme"] - 0.48, "opacity": 0.0}])
    rec("paper_drop", T6["Satellitenbildern"] + 0.25, -8)
    S.flash("fl6", T6["Baumstämme"] - 0.6, color=(246, 240, 226), peak=0.35)
S.image("mag6", "st_magnifier", T6["Satellitenbildern"] + 0.4, T6["Baumstämme"], slide_in(T6["Satellitenbildern"] + 0.4, 2300, 1100, 990, 500, mg_s, -30, -12, 0.45) +
        [{"t": T6["Team"], "x": 950, "y": 515}, exit_to(T6["Team"] + 0.2, 2400, 1200, 0.35, rot=-40)], anchor=list(M["st_magnifier"]["lens"]))
P("logs6", "st_logs", T6["Ergebnis"] if "Ergebnis" in T6 else T6["Baumstämme"] - 0.6, T_CH7 - 0.2, 960, 560, 640, -3)
L("lbaum", "lbl_baeume", T6["Baumstämme"], T_CH7 - 0.2, 960, 880, 460, 2, gain=-6)
rec("suspense_hit", T6["Baumstämme"], -12)

# ======================================================================= CHAPTER 7 – Theorie 3: Japan
T7 = {k: w(k, a - 0.6) for k, a in [("düsterste", 465), ("Norden", 468), ("Marshallinseln", 468), ("Japan", 474),
                              ("gefangen", 476), ("Saipan", 476), ("sterben", 476), ("Inselbewohner", 482),
                              ("Frau", 482), ("2017", 489), ("Fernsehdoku", 491), ("Beweis", 491), ("Hafen", 495),
                              ("Earhart", 498), ("Noonan", 498), ("Blogger", 504), ("Reisebuch", 504), ("30", 510),
                              ("1935", 513), ("Zwei", 515)]}
T_CH8 = w("Die", 518.7)
MILI, SAI = PL["mili"], PL["saipan"]
card("lbl_th3", "lbl_t7", T_CH7 - 0.1, 2.3, 860)
rec("drone_dark", T_CH7, -14, trim=[0.0, 14.0], fade=2.0)
Z7 = ZP(30)
cam(T7["Norden"] - 0.3, ((HOW[0] + MILI[0]) / 2, (HOW[1] + MILI[1]) / 2), Z7, "inout")
jk, jprog = follow([HOW, MILI], [(0, T7["Norden"]), (1, T7["Marshallinseln"] + 0.5)], mirror=True)
jk[0]["scale"] = plane_px(120, Z7)
mobj("plane_jap", "st_electra", T7["Norden"], T7["gefangen"] + 0.4, jk + [{"t": T7["gefangen"], "opacity": 1.0}, {"t": T7["gefangen"] + 0.3, "opacity": 0.0}])
MAP_EXTRA.append({"id": "line_mili", "type": "dashed_path", "start": T7["Norden"], "end": T_CH8,
                  "points": [list(HOW), list(MILI)], "props": {"x": 0, "y": 0}, "width": 6 / Z7, "dash": 18 / Z7,
                  "gap": 12 / Z7, "color": [232, 112, 58], "keys": jprog})
mcity("howland", T7["Norden"], T7["2017"], Z7)
mcity("mili", T7["Marshallinseln"], T7["2017"], Z7)
L("ljap", "lbl_japan", T7["Japan"], T7["gefangen"] - 0.2, 960, 170, 520, -2)
cam(T7["gefangen"] + 0.3, ((MILI[0] + SAI[0]) / 2, (MILI[1] + SAI[1]) / 2), Z7 * 0.9, "inout")
mline("to_saipan", [MILI, SAI], T7["gefangen"], T7["Saipan"] + 0.6, Z7 * 0.9, t_end=T7["2017"], color=(150, 40, 40))
mcity("saipan", T7["Saipan"], T7["2017"], Z7 * 0.9)
L("lgef", "lbl_gefangen", T7["gefangen"], T7["Inselbewohner"] - 0.2, 960, 880, 420, 2)
drain("drain7", T7["sterben"], T7["Inselbewohner"])
S.image("ghost7", "st_portrait", T7["Frau"] - 0.3, T7["2017"] - 0.1, [
    {"t": T7["Frau"] - 0.3, "x": 1350, "y": 560, "scale": S.scale_for("st_portrait", 360), "rot": 0, "opacity": 0.0},
    {"t": T7["Frau"] + 0.3, "opacity": 0.6, "ease": "out"}, {"t": T7["2017"] - 0.5, "opacity": 0.6}, {"t": T7["2017"] - 0.1, "opacity": 0.0}], jitter=False)
L("lzeugen", "lbl_zeugen", T7["Inselbewohner"], T7["2017"] - 0.2, 600, 540, 440, -2, exit=(-400, 540))
L("l2017", "lbl_2017", T7["2017"], T7["Blogger"] - 0.2, 360, 170, 300, -3)
P("tv7", "st_tv", T7["Fernsehdoku"] - 0.3, T7["Blogger"] - 0.2, 900, 580, 720, -2)
rec("tv_on", T7["Fernsehdoku"] - 0.1, -9)
S.image("photo_tv", "st_photo2017", T7["Fernsehdoku"] + 0.2, T7["Blogger"] + 0.1, [
    {"t": T7["Fernsehdoku"] + 0.2, "x": 840, "y": 540, "scale": S.scale_for("st_photo2017", 470), "rot": -2, "opacity": 0.0},
    {"t": T7["Fernsehdoku"] + 0.35, "opacity": 1.0}, {"t": T7["Blogger"] - 0.2, "x": 840, "y": 540},
    exit_to(T7["Blogger"] - 0.2, -600, 540)])
L("lbew", "lbl_beweis", T7["Beweis"], T7["Blogger"] - 0.2, 1450, 300, 400, 3)
L("lea", "lbl_earhart_q", T7["Earhart"], T7["Blogger"] - 0.2, 1450, 560, 320, -2)
L("lno", "lbl_noonan_q", T7["Noonan"], T7["Blogger"] - 0.2, 1450, 800, 320, 2)
L("lblog", "lbl_blogger", T7["Blogger"], T7["1935"] - 0.2, 960, 170, 380, -2)
P("travel7", "st_travelbook", T7["Reisebuch"] - 0.2, T_CH8 - 0.3, 860, 600, 760, -3)
rec("page_turn", T7["Reisebuch"], -9)
L("l30", "lbl_30min", T7["30"], T7["1935"] - 0.2, 1450, 880, 380, 2)
P("watch7", "st_watch", T7["30"] + 0.2, T7["1935"] - 0.2, 1500, 520, 260, 5)
L("l1935", "lbl_1935", T7["1935"], T_CH8 - 0.3, 1480, 300, 300, 3)
stamp("stamp7", "stamp_widerlegt", T7["Zwei"], T_CH8 - 0.3, 860, 600, 600)
S.flash("fl7", T7["Zwei"], peak=0.35)

# ======================================================================= CHAPTER 8 – Theorie 4: neues Leben
T8 = {k: w(k, a - 0.6) for k, a in [("Film", 518), ("überlebt", 521), ("USA", 521), ("1970", 527), ("Buch", 527),
                              ("Hausfrau", 527), ("Irene", 527), ("Jersey", 527), ("wirklich", 535), ("Unsinn", 539),
                              ("verklagt", 539), ("Markt", 543), ("widerlegt", 545)]}
T_CH9 = w("Fassen", 549)
NJ = PL["new_jersey"]
card("lbl_th4", "lbl_t8", T_CH8 - 0.1, 2.3, 760)
cam(T8["Film"] + 0.6, map_xy(60, 25), 0.33, "inout")
cam(T8["USA"], NJ, 1.3, "inout")
rec("map_whoosh", T8["Film"] + 0.5, -6, peak=0.38)
mcity("new_jersey", T8["Jersey"], T_CH9, 1.3)
P("young8", "st_young", T8["überlebt"], T8["1970"] - 0.2, 1400, 560, 380, 3)
P("book8", "st_book", T8["Buch"] - 0.2, T8["Markt"] + 0.4, 480, 560, 360, -6)
rec("page_turn", T8["Buch"], -10)
L("l1970", "lbl_1970", T8["1970"], T8["wirklich"] - 0.2, 480, 200, 300, -3)
P("house8", "st_house", T8["Hausfrau"], T8["Unsinn"] - 0.2, 1350, 560, 520, 3)
L("lbolam", "lbl_bolam", T8["Irene"], T8["Unsinn"] - 0.2, 1350, 880, 420, 2)
L("lunsinn", "lbl_unsinn", T8["Unsinn"], T8["Markt"] - 0.2, 1350, 300, 380, -3)
P("court8", "st_court", T8["verklagt"] - 0.1, T8["widerlegt"] + 1.5, 1350, 640, 520, 4)
rec("courtroom", T8["verklagt"] - 0.3, -16, trim=[0.0, 3.5], fade=1.0)
L("lklage", "lbl_klage", T8["verklagt"] + 0.2, T8["widerlegt"] - 0.2, 1350, 920, 300, 2)
S.image("tape8", "tape_x", T8["Markt"], T8["Markt"] + 0.8, [
    {"t": T8["Markt"], "x": 480, "y": 560, "scale": txs * 1.4, "rot": -6, "opacity": 0.0}, {"t": T8["Markt"] + 0.03, "opacity": 1.0},
    {"t": T8["Markt"] + 0.12, "scale": txs * 0.8, "ease": "out"}, {"t": T8["Markt"] + 0.4, "x": 480, "y": 560}, exit_to(T8["Markt"] + 0.4, -500, 560)])
rec("paper_tear", T8["Markt"] + 0.05, -9)
stamp("stamp8", "stamp_widerlegt", T8["widerlegt"], T_CH9 - 0.3, 760, 540, 600)

# ======================================================================= CHAPTER 9 – Fazit
T9 = {k: w(k, a - 0.6) for k, a in [("Absturz", 550), ("Wrack", 553), ("Nikumaroro", 555), ("Beweis", 560),
                              ("Japan-Theorie", 563), ("Erzählungen", 563), ("Identität", 567), ("widerlegt", 567),
                              ("Vielleicht", 570), ("tief", 570), ("Sand", 574), ("Oder", 577), ("Kiste", 577),
                              ("Archiv", 577), ("glaubst", 583), ("Kommentare", 584), ("abonnier", 585)]}
card("lbl_fazit", "lbl_t9", T_CH9 - 0.3, 1.8, 900)
cam(T9["Absturz"] - 0.3, map_xy(188, 0), 0.62, "inout")
T9_OUT = T9["Vielleicht"] - 0.3
for k_, (aid, wd, t_in, lab, t_lab, kind) in enumerate([
        ("st_electra", 330, T9["Absturz"], "lbl_kein_wrack", T9["Wrack"], "label"),
        ("st_crab", 270, T9["Nikumaroro"], "stamp_keinbeweis", T9["Beweis"], "stamp"),
        ("st_photo2017", 330, T9["Japan-Theorie"], "lbl_erzaehlungen", T9["Erzählungen"], "label"),
        ("st_house", 300, T9["Identität"], "stamp_widerlegt", T9["widerlegt"], "stamp")]):
    x = 300 + 440 * k_
    P(f"sum{k_}", aid, t_in, T9_OUT, x, 470, wd, (-4, 3, -2, 4)[k_], gain=-9, exit=(x, -400))
    L(f"sumn{k_}", f"lbl_n{k_ + 1}", t_in + 0.1, T9_OUT, x - 150, 300, 80, -3, sound=None)
    if kind == "label":
        L(f"suml{k_}", lab, t_lab, T9_OUT, x, 780, 340, 2)
    else:
        stamp(f"sums{k_}", lab, t_lab, T9_OUT, x, 760, 330, rot=-8)
L("lhinweise", "lbl_hinweise", T9["Nikumaroro"] + 0.5, T9_OUT, 740, 940, 360, -2)
cam(T9["tief"] - 0.4, HOW, ZP(150), "inout")
darkness("deep9", T9["tief"] - 0.2, T9["Sand"] - 0.5, op=0.66, color=(8, 18, 34))
rec("underwater", T9["tief"] - 0.3, -15, trim=[0.0, 4.5], fade=1.0)
L("l5km9", "lbl_5km", T9["tief"], T9["Sand"] - 0.5, 960, 540, 420, -2, exit=(960, 1400))
cam(T9["Sand"] - 0.1, NIK, ZP(10000), "inout")
rec("ocean_wind", T9["Sand"] - 0.2, -18, trim=[0.0, 5.0], fade=1.5)
P("box9", "st_box_empty", T9["Kiste"] - 0.2, T9["glaubst"] - 0.3, 760, 600, 460, -4)
P("bones9", "st_bones", T9["Kiste"] + 0.4, T9["glaubst"] - 0.3, 1120, 520, 420, 6)
P("folder9", "st_folder", T9["Archiv"] - 0.2, T9["glaubst"] - 0.3, 1450, 680, 340, 3)
cam(T9["glaubst"] - 0.2, map_xy(188, 0), 0.5, "inout")
cam(FULL_END, map_xy(192, 0), 0.47, "linear")
L("lglaubst", "lbl_glaubst", T9["glaubst"], FULL_END, 960, 300, 640, -2, gain=-5)
for k_, (aid, x, y, wd, rot) in enumerate([("st_electra", 380, 640, 300, -5), ("st_crab", 800, 700, 240, 5),
                                           ("st_photo2017", 1180, 650, 290, 4), ("st_house", 1580, 680, 260, -4)]):
    P(f"end{k_}", aid, T9["glaubst"] + 0.2 + 0.15 * k_, FULL_END, x, y, wd, rot, gain=-12)
L("lkomm", "lbl_kommentare", T9["Kommentare"], FULL_END, 960, 900, 700, 2)
L("labo", "lbl_abo", T9["abonnier"] + 0.6, FULL_END, 1600, 160, 380, 4, exit=(1600, -300))
rec("suspense_hit", T9["glaubst"], -14)

# ======================================================================= camera + map layer
CAM.sort(key=lambda c: c[0])
# hold the previous view until shortly before each scene change (no slow drift over long gaps)
held = [CAM[0]]
for a, b in zip(CAM, CAM[1:]):
    if b[0] - a[0] > 2.5:
        held.append((round(b[0] - 1.3, 3), a[1], a[2], a[3], "linear"))
    held.append(b)
CAM = held
cam_scale, cam_pan = fly_camera(CAM, FULL_END, center=(CX, CY))
P_OF = [(k["t"], k["scale"] * PPD) for k in cam_scale]


def zoom_fade(p_in0, p_in1):
    def f(P):
        v = min(1, max(0, (math.log(P) - math.log(p_in0)) / (math.log(p_in1) - math.log(p_in0))))
        return v * v * (3 - 2 * v)
    keys, last = [], None
    for t, P in P_OF:
        v = round(f(P), 3)
        if v != last:
            if last is not None and keys[-1]["t"] < t - 0.034:
                keys.append({"t": round(t - 1 / 30, 4), "opacity": last})
            keys.append({"t": t, "opacity": v})
            last = v
    return keys


tiles = []
for name in ("tile_mid", "tile_n1", "tile_n2", "tile_n3", "tile_h1", "tile_h2", "tile_h25", "tile_h3"):
    tm = M[name]
    cover = max(tm["ppd"] * W / (tm["w"] * 0.72), tm["ppd"] * H / (tm["h"] * 0.72))
    tiles.append({"id": name, "type": "image", "asset": name, "anchor": [0, 0],
                  "props": {"x": tm["pos"][0], "y": tm["pos"][1], "scale": tm["design_scale"]},
                  "keys": zoom_fade(cover, cover * 1.3)})
S.layers.insert(0, {"id": "cam", "type": "group", "pivot": [CX, CY], "keys": cam_scale, "children": [
    {"id": "cam_pan", "type": "group", "pivot": [0, 0], "keys": cam_pan, "children": [
        {"id": "map", "type": "image", "asset": "map_pacific", "anchor": [0, 0], "props": {"x": 0, "y": 0}, "keys": []},
        *tiles, *MAP_EXTRA]}]})
S.layers.append({"id": "page", "type": "multiply_image", "asset": "page", "keys": []})

# ======================================================================= music
def music(track, t0, t1, gain, off=0.0, fi=2.5, fo=3.0):
    S.audio.append({"src": f"audio/music/{track}.mp3", "start": round(t0, 3), "gain_db": gain,
                    "trim": [off, off + (t1 - t0)], "fade_in": fi, "fade_out": fo})


music("music_mystery", 0.0, T_CH1 + 2.0, -19)
music("music_calm", T_CH1 - 1.0, T_CH2 + 2.0, -23)
music("music_mystery", T_CH2 - 1.0, T_CH3 + 2.0, -21, off=40.0)
music("music_tension", T_CH3 - 1.0, T_CH5 + 2.0, -23)
music("music_mystery", T_CH5 - 1.0, T_CH6 + 2.0, -21, off=95.0)
music("music_mystery", T_CH6 - 1.0, T_CH7 + 2.0, -21, off=0.0)
music("music_tension", T_CH7 - 1.0, T_CH8 + 2.0, -23, off=60.0)
music("music_calm", T_CH8 - 1.0, FULL_END, -22, off=40.0, fo=2.0)

# ---------------------------------------------------------------- SFX ceiling (user: some sounds stick out)
# K-weighted momentary max of every sound after its gain is capped well below the voice (~ -17 LUFS).
CEIL = {"default": -27.0, "paper_tear": -32.0, "paper_slide": -30.0, "newspaper": -29.0,
        "rock_thud": -24.0, "suspense_hit": -24.0, "plane_skid": -24.0, "stamp": -25.0, "map_whoosh": -26.0,
        "underwater": -29.0, "drone_dark": -29.0, "ocean_wind": -30.0, "radio_static_long": -29.0}


def _mmax(src, trim):
    import re
    import subprocess
    cmd = ["ffmpeg", "-nostats"] + (["-ss", str(trim[0]), "-t", str(trim[1] - trim[0])] if trim else [])
    cmd += ["-i", os.path.join(PROJ, src), "-af", "apad=pad_dur=1,ebur128", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    return max(float(v) for v in re.findall(r" M:\s*(-?[\d.]+)", err))


_mm = {}
for a_ in S.audio:
    if not a_["src"].startswith("audio/sfx_prepared/"):
        continue
    k_ = (a_["src"], str(a_.get("trim")))
    if k_ not in _mm:
        _mm[k_] = _mmax(a_["src"], a_.get("trim"))
    name_ = os.path.basename(a_["src"])[:-4]
    over = _mm[k_] + a_["gain_db"] - CEIL.get(name_, CEIL["default"])
    if over > 0:
        a_["gain_db"] = round(a_["gain_db"] - over, 1)

HIDE = [(0.0, T_QEND + 0.3)]
caps = None                      # no subtitles in the long version (user feedback)
assets = {name: {"path": f"build/assets/{m.get('file', name)}.png", "license": "own"} for name, m in M.items()
          if isinstance(m, dict) and "w" in m}
timeline = {"meta": {"fps": 30, "width": W, "height": H, "design": [W, H], "duration": round(END, 3)},
            "assets": assets, "layers": S.layers,
            "audio": [{"id": "voice", "src": "audio/voice_komplett.mp3", "start": 0.0, "gain_db": 0.0}] + S.audio}
out = os.path.join(HERE, "timeline.json")
json.dump(timeline, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("timeline ->", out, "| end", round(END, 2), "| ch2 starts", round(T_CH2, 2), "|", len(S.layers), "layers")
