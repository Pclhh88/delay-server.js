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

from shortsfactory.collage.choreo import Show, exit_to, fly_camera, path_keys, phrase_captions, pop_in, slide_in  # noqa

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
    return (x, min(max(y, half), MAP_H - half), s, ease)


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
cam(FULL_END, map_xy(45, 5), 0.45, "linear")

# chapter card
S.sticker("kap1", "lbl_kap", T["entscheidest"] + 1.9, T_CH1 + 1.1, 960, 430, 260, -2, exit=(960, -300), sound="paper_slide", gain=-6, how="slide", frm=(960, -200))
S.sticker("kap1t", "lbl_kap_title", T["entscheidest"] + 2.05, T_CH1 + 1.1, 960, 560, 820, 1, exit=(960, 1400), sound=None, how="slide", frm=(960, 1300))
rec("map_whoosh", T_CH1 - 0.1, -6, peak=0.38)

MAP_EXTRA.append({"id": "dot_atc", "type": "image", "asset": "dot", "start": T1["Kansas"], "end": T1["fliegt28"] + 1,
                  "keys": [{"t": T1["Kansas"], "x": ATC[0], "y": ATC[1], "scale": 0.0},
                           {"t": T1["Kansas"] + 0.15, "scale": 0.28 / 1.7, "ease": "out"}]})
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
    {"t": T1["zehn"] - 0.2, "x": -300, "y": 470, "scale": vs, "rot": -8},
    {"t": T1["Danach"] + 0.2, "x": 2250, "y": 380, "rot": -14}])
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
S.sticker("news28", "newspaper_1928", T1["fliegt28"] + 0.4, T1["Das2"] - 0.3, 420, 560, 360, -6, exit=(-400, 600), sound="newspaper", gain=-8)
S.sticker("lpass", "lbl_passagierin", T1["Passagierin"], T1["Das2"] - 0.3, 1400, 330, 520, 3, exit=(2400, 330), sound="cardboard_hit", gain=-6)
S.sticker("potatoes", "st_potatoes", T1["Sack"] - 0.15, T1["Das2"] - 0.3, 1420, 700, 340, -5, exit=(2400, 700), sound="paper_drop", gain=-4)
# 1932 solo
S.sticker("l1932", "lbl_1932", T1["1932"], T1["Weltstar"] - 0.3, 960, 160, 300, -3, exit=(960, -250), sound="cardboard_hit", gain=-6)
r32 = [list(HGR), [(HGR[0] + CUL[0]) / 2, (HGR[1] + CUL[1]) / 2 - 70], list(CUL)]
T32A, T32B = T1["fliegt32"], T1["zweiter"] + 0.2
vk, vprog = path_keys([tuple(p) for p in r32], T32A, T32B)
vk[0].update({"scale": S.scale_for("st_vega", 210) / 1.3, "rot": -6})
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
S.sticker("news32", "newspaper", T1["Weltstar"], T1["Aber"] - 0.3, 420, 540, 360, -5, exit=(-400, 540), sound="newspaper", gain=-9)
S.sticker("portrait1", "st_portrait", T1["Weltstar"] + 0.1, T1["Aber"] - 0.3, 960, 500, 380, 2, exit=(960, 1500), gain=-6)
S.sticker("lstar", "lbl_weltstar", T1["Weltstar"] + 0.05, T1["Bücher"] - 0.2, 960, 150, 420, -3, exit=(960, -250), sound="cardboard_hit", gain=-6)
S.sticker("book", "st_book", T1["Bücher"], T1["Aber"] - 0.3, 1480, 330, 330, 6, exit=(2400, 330), gain=-7)
rec("page_turn", T1["Bücher"] + 0.2, -10)
S.sticker("lmode", "lbl_mode", T1["Mode"], T1["Aber"] - 0.3, 1480, 620, 260, -3, exit=(2400, 620), sound="cardboard_hit", gain=-9)
S.sticker("lchancen", "lbl_chancen", T1["Chancen"], T1["Aber"] - 0.3, 960, 150, 560, 2, exit=(960, -250), sound="cardboard_hit", gain=-7)
S.sticker("lrekord", "lbl_rekord", T1["Rekord"] - 0.1, T_CH2 + 3.0, 960, 540, 700, -2, exit=(960, -300), sound="cardboard_hit", gain=-5)
rec("suspense_hit", T1["Rekord"], -10)

# ======================================================================= camera + map layer
CAM.sort(key=lambda c: c[0])
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
S.audio += [
    {"src": "audio/music/music_mystery.mp3", "start": 0.0, "gain_db": -19, "trim": [0.0, T_CH1 + 2.0],
     "fade_in": 2.0, "fade_out": 3.0},
    {"src": "audio/music/music_calm.mp3", "start": T_CH1 - 1.0, "gain_db": -23, "trim": [0.0, 150.0], "fade_in": 3.0,
     "fade_out": 3.0},
]

HIDE = [(0.0, T_QEND + 0.3)]
caps = phrase_captions(WORDS, hide=HIDE)
assets = {name: {"path": f"build/assets/{name}.png", "license": "own"} for name, m in M.items()
          if isinstance(m, dict) and "w" in m}
timeline = {"meta": {"fps": 30, "width": W, "height": H, "design": [W, H], "duration": round(END, 3)},
            "assets": assets, "layers": S.layers, "captions": caps,
            "audio": [{"id": "voice", "src": "audio/voice_komplett.mp3", "start": 0.0, "gain_db": 0.0}] + S.audio}
out = os.path.join(HERE, "timeline.json")
json.dump(timeline, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("timeline ->", out, "| end", round(END, 2), "| ch2 starts", round(T_CH2, 2), "|", len(S.layers), "layers")
