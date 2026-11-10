"""Teaser Short (9:16, ~70 s) for the long Amelia Earhart video.

    python3 projects/amelia-earhart-short2/build/build_timeline.py

Hook first (13 bones that vanished), story in fast cuts, open question at the end
(what is on the satellite image?) that only the long video answers.
Uses the long version's assets (see make_assets.py).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(PROJ)))

from shortsfactory.collage.choreo import Show, exit_to, fly_camera, pop_in, slide_in  # noqa

W, H = 1080, 1920
CX, CY = W / 2, H / 2
S = Show(os.path.join(HERE, "assets", "meta.json"), os.path.join(PROJ, "analysis", "words.json"))
w, rec, M = S.w, S.rec, S.META
WORDS = S.WORDS
END = WORDS[-1]["end"] + 1.0
mp = M["map_pacific"]
PPD = mp["proj"]["ppd"]
MAP_H = mp["proj"]["h"]
PL = {k: tuple(v) for k, v in M["places"].items()}
HOW, NIK, LAE = tuple(mp["howland"]), tuple(mp["nikumaroro"]), tuple(mp["lae"])
MAP_EXTRA = []
CAM = []


def map_xy(lon, lat):
    lon_min = mp["proj"]["lon_min"]
    while lon < lon_min:
        lon += 360
    return (lon - lon_min) * PPD, (mp["proj"]["lat_max"] - lat) * PPD


def ZP(ppd):
    return ppd / PPD


def cam(t, xy, s, ease="inout"):
    x, y = xy
    half = CY / s
    y = MAP_H / 2 if half >= MAP_H / 2 else min(max(y, half), MAP_H - half)
    CAM.append((round(t, 3), x, y, s, ease))


def L(id_, asset, t_in, t_out, x, y, width, rot=0.0, sound=None, gain=-8.0, exit=None, how="pop", frm=None):
    """label; silent by default (feedback: no click on every label)"""
    if exit is None:
        exit = (x, -300) if y < CY else (x, H + 300)
    S.sticker(id_, asset, t_in, t_out, x, y, width, rot, exit=exit, sound=sound, gain=gain, how=how, frm=frm)


def P(id_, asset, t_in, t_out, x, y, width, rot=0.0, gain=-9.0, exit=None, how="pop", frm=None, sound="paper_drop"):
    if exit is None:
        exit = (-600, y) if x < CX else (W + 600, y)
    S.sticker(id_, asset, t_in, t_out, x, y, width, rot, exit=exit, sound=sound, gain=gain, how=how, frm=frm)


def stamp(id_, asset, t, t_out, x, y, width, rot=-10):
    sm = S.scale_for(asset, width)
    S.image(id_, asset, t, t_out + 0.35, [
        {"t": t, "x": x, "y": y, "scale": sm * 2.2, "rot": rot - 4, "opacity": 0.0}, {"t": t + 0.03, "opacity": 1.0},
        {"t": t + 0.1, "scale": sm, "rot": rot, "ease": "in"}, {"t": t_out, "x": x, "y": y}, exit_to(t_out, x, H + 400)])
    rec("stamp", t + 0.08, -6)


def solid(id_, t0, t1, keys, color=(14, 22, 38)):
    S.layers.append({"id": id_, "type": "solid", "start": t0, "end": t1, "color": list(color), "keys": keys})


def waves(prefix, t0, t1, x, y, rot, size=420, step=0.42):
    a_s = S.scale_for("arc_orange", size)
    t, i = t0, 0
    while t < t1:
        S.image(f"{prefix}{i}", "arc_orange", t, t + 1.2, [
            {"t": t, "x": x, "y": y, "scale": a_s * 0.3, "rot": rot, "opacity": 1.0},
            {"t": t + 0.8, "opacity": 0.9}, {"t": t + 1.2, "scale": a_s * 1.4, "opacity": 0.0, "ease": "out"}], jitter=False)
        t += step
        i += 1


def follow(pts, t0, t1, n_per_s=15):
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    tot = sum(seg)
    keys, prog = [], []
    n = max(2, int((t1 - t0) * n_per_s))
    for k in range(n + 1):
        f = k / n
        d = f * tot
        for (a, b), sl in zip(zip(pts, pts[1:]), seg):
            if d <= sl + 1e-9:
                u = d / sl if sl else 0
                break
            d -= sl
        keys.append({"t": round(t0 + (t1 - t0) * f, 3), "x": a[0] + (b[0] - a[0]) * u, "y": a[1] + (b[1] - a[1]) * u,
                     "rot": math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))})
        prog.append({"t": round(t0 + (t1 - t0) * f, 3), "progress": round(f, 4)})
    return keys, prog


T = {}
for k, a in [("Diese", 0), ("13", 0), ("Rätsel", 0), ("Nur", 4), ("verschwunden", 5), ("1937", 7), ("Amelia", 8),
             ("berühmteste", 10), ("Erde", 13), ("Über", 14), ("Pazifik", 15), ("Funkspruch", 16), ("Wir", 17),
             ("knapp", 21), ("Danach", 22), ("Stille", 23), ("Drei", 24), ("einsamen", 25), ("Nikumaroro", 27),
             ("Skelett", 28), ("Frauenschuhs", 30), ("Kiste", 32), ("Sextanten", 33), ("Arzt", 34), ("Mann", 36),
             ("Fall", 37), ("Bis", 38), ("Forscher", 40), ("Messwerte", 41), ("Ergebnis", 42), ("Knochen", 43),
             ("Amelia", 45), ("99", 46), ("Nur", 49), ("nachprüfen", 50), ("Und", 52), ("Oktober", 52),
             ("Satellitenbildern", 55), ("Lagune", 57), ("Etwas", 59), ("Flugzeugs", 62), ("Was", 63),
             ("welche", 64), ("Theorien", 65), ("siehst", 66), ("Video", 67), ("Kanal", 68)]:
    T[(k, a)] = w(k, a)


def t_(k, a=None):
    if a is None:
        return next(v for (kk, _), v in T.items() if kk == k)
    return T[(k, a)]


Z_ISL = ZP(13000)          # the whole atoll fits the 1080 px width
Z_SAT = ZP(9000)

# ======================================================================= 0  HOOK: 13 bones … vanished
cam(0.0, (NIK[0] - 0.004 * PPD, NIK[1]), Z_ISL * 0.92, None)
cam(t_("Nur", 4) - 0.2, NIK, Z_ISL * 1.08, "linear")
t_v = t_("verschwunden")
bs = S.scale_for("st_bones", 820)
S.image("bones0", "st_bones", 0.0, t_v + 0.5, [
    {"t": 0.0, "x": 540, "y": 1250, "scale": bs * 1.25, "rot": -14, "opacity": 1.0},
    {"t": 0.22, "scale": bs, "rot": -8, "ease": "out3"},
    {"t": t_v - 0.05, "x": 540, "y": 1250, "scale": bs * 1.03, "opacity": 1.0},
    {"t": t_v + 0.05, "opacity": 0.25}, {"t": t_v + 0.12, "opacity": 0.85}, {"t": t_v + 0.2, "opacity": 0.15},
    {"t": t_v + 0.28, "opacity": 0.6}, {"t": t_v + 0.45, "opacity": 0.0, "scale": bs * 0.92}])
rec("bones_rattle", 0.0, -5)
rec("suspense_hit", 0.05, -12)
L("l13", "lbl_13", t_("13") - 0.1, t_v - 0.15, 540, 470, 760, -3, sound="cardboard_hit", gain=-7)
for k_, (y, frm_x, dl) in enumerate([(1650, -350, 0.0), (680, 1430, 0.3)]):
    cs = S.scale_for("st_crab", 330)
    t0 = t_("Rätsel") - 0.6 + dl
    x_to = 300 if k_ == 0 else 800
    S.image(f"crab0_{k_}", "st_crab", t0, t_v + 1.0, [
        {"t": t0, "x": frm_x, "y": y, "scale": cs, "rot": 0 if k_ == 0 else 180},
        {"t": t0 + 1.1, "x": x_to, "y": y, "ease": "out"},
        {"t": t_v - 0.1, "x": x_to + (40 if k_ == 0 else -40), "y": y},
        {"t": t_v + 0.9, "x": -400 if k_ == 0 else 1500, "y": y + 30, "ease": "in"}])
rec("crab_scuttle", t_("Rätsel") - 0.6, -12, trim=[0.0, 3.0], fade=0.8)
P("box0", "st_box_empty", t_v + 0.1, t_("1937") - 0.15, 540, 1020, 520, 4, sound=None)
L("lvers0", "lbl_verschwunden", t_v, t_("1937") - 0.15, 540, 1420, 680, -3, sound=None)
rec("paper_tear", t_v, -8)
S.flash("fl0", t_v, color=(246, 240, 226), peak=0.3)

# ======================================================================= 1  1937 – Amelia, around the world
Z_W = 0.6
cam(t_("1937") - 0.1, map_xy(-160, 8), Z_W, "inout")
rec("map_whoosh", t_("1937") - 0.15, -6, peak=0.38)
L("l1937", "lbl_1937", t_("1937") + 0.05, t_("Erde") - 0.3, 540, 330, 420, -3, sound="cardboard_hit", gain=-9)
P("port1", "st_portrait2", t_("Amelia", 8) - 0.1, t_("Über") - 0.25, 540, 1060, 600, 2, how="slide", frm=(540, 2400),
  sound="paper_slide", exit=(-700, 1060))
L("lam1", "lbl_amelia", t_("Amelia", 8) + 0.1, t_("Über") - 0.25, 300, 1560, 400, -4)
L("lea1", "lbl_earhart", t_("Amelia", 8) + 0.45, t_("Über") - 0.25, 760, 1660, 420, 3)
# around the world: a plane crosses the frame, a dashed line follows it
t_e = t_("Erde") - 0.5
ek, eprog = follow([(-250, 420), (540, 300), (1330, 380)], t_e, t_("Über") + 0.2)
for k in ek:
    k["scale"] = S.scale_for("st_electra", 300)
S.image("pl1", "st_electra", t_e, t_("Über") + 0.25, ek, jitter=False)
S.layers.append({"id": "route1", "type": "dashed_path", "start": t_e, "end": t_("Über") + 0.2,
                 "points": [[-250, 420], [540, 300], [1330, 380]], "props": {"x": 0, "y": 0}, "width": 8, "dash": 24,
                 "gap": 14, "color": [232, 112, 58], "keys": eprog})
rec("plane_flyby", t_e, -12, trim=[0.0, 2.6], fade=0.6)

# ======================================================================= 2  the last radio call
Z_P = 0.95
d = (HOW[0] - LAE[0], HOW[1] - LAE[1])
c2 = (HOW[0] - d[0] * 0.5, HOW[1] - d[1] * 0.5 + 60)
cam(t_("Über") - 0.1, c2, Z_P, "inout")
pk, pprog = follow([LAE, (HOW[0] - d[0] * 0.08, HOW[1] - d[1] * 0.08)], t_("Über"), t_("Danach"))
for k in pk:
    k["scale"] = S.scale_for("st_electra", 260) / Z_P
t_d = t_("Danach")
MAP_EXTRA.append({"id": "pl2", "type": "image", "asset": "st_electra", "start": t_("Über"), "end": t_d + 0.7,
                  "anchor": M["st_electra"]["anchor"],
                  "keys": pk + [{"t": t_d + 0.1, "opacity": 0.2}, {"t": t_d + 0.2, "opacity": 0.9},
                                {"t": t_d + 0.35, "opacity": 0.1}, {"t": t_d + 0.45, "opacity": 0.8},
                                {"t": t_d + 0.65, "opacity": 0.0}]})
MAP_EXTRA.append({"id": "leg2", "type": "dashed_path", "start": t_("Über"), "end": t_d + 0.7,
                  "points": [list(LAE), [HOW[0] - d[0] * 0.08, HOW[1] - d[1] * 0.08]], "props": {"x": 0, "y": 0},
                  "width": 7 / Z_P, "dash": 20 / Z_P, "gap": 12 / Z_P, "color": [232, 112, 58],
                  "keys": pprog + [{"t": t_d + 0.2, "opacity": 1.0}, {"t": t_d + 0.6, "opacity": 0.0}]})
rec("plane_distant", t_("Über"), -16, trim=[0.0, t_d - t_("Über")], fade=1.0)
P("radio2", "st_radio", t_("Funkspruch") - 0.2, t_d - 0.1, 300, 470, 420, -4, sound="paper_drop")
waves("w2_", t_("Funkspruch"), t_d - 0.3, 440, 330, -50, size=380)
S.audio.append({"src": "audio/sfx_prepared/radio_static_long.wav", "start": round(t_("Funkspruch"), 3), "gain_db": -22,
                "trim": [0.0, t_d - t_("Funkspruch") + 0.2], "fade_out": 0.1})
# typed quote strip
qn = M["quote_words"]
i0 = next(i for i, x_ in enumerate(WORDS) if x_["start"] >= t_("Wir") - 0.01)
qw = WORDS[i0:i0 + qn]
qs = S.scale_for("quote_01", 960)
sk = slide_in(t_("Wir") - 0.35, 540, H + 400, 540, 1480, qs, 6, -1.5, 0.3) + [
    {"t": t_d - 0.1, "x": 540, "y": 1480}, exit_to(t_d - 0.1, 540, H + 400, 0.3, rot=8)]
S.image("q0", "quote_00", t_("Wir") - 0.35, qw[0]["start"], sk)
for k, wd in enumerate(qw, 1):
    e0 = qw[k]["start"] if k < qn else t_d + 0.25
    S.image(f"q{k}", f"quote_{k:02d}", wd["start"], e0, sk)
    rec("typewriter_key", wd["start"], -9)
rec("typewriter_bell", t_("knapp") + 0.4, -15)
rec("radio_cutoff", t_d, -9, trim=[0.0, 2.0], fade=0.4)
S.layers.append({"id": "drain2", "type": "grade", "start": t_d, "end": t_("Drei") + 0.6,
                 "keys": [{"t": t_d, "saturation": 1.0}, {"t": t_d + 0.6, "saturation": 0.15},
                          {"t": t_("Drei") - 0.2, "saturation": 0.15}, {"t": t_("Drei") + 0.4, "saturation": 1.0}]})
solid("dark2", t_d, t_("Drei") + 0.4, [{"t": t_d, "opacity": 0.0}, {"t": t_d + 0.6, "opacity": 0.5},
                                        {"t": t_("Drei") - 0.2, "opacity": 0.5}, {"t": t_("Drei") + 0.3, "opacity": 0.0}])
L("lstille", "lbl_stille", t_("Stille"), t_("Drei") - 0.15, 540, 900, 560, -2)
rec("drone_dark", t_d + 0.3, -16, trim=[0.0, 4.0], fade=1.5)

# ======================================================================= 3  three years later: Nikumaroro
L("l3j", "lbl_3jahre", t_("Drei"), t_("Nikumaroro") - 0.2, 540, 330, 640, -3, sound="cardboard_hit", gain=-10)
cam(t_("einsamen") - 0.3, NIK, Z_ISL, "inout")
rec("map_whoosh", t_("einsamen") - 0.4, -6, peak=0.38)
rec("ocean_wind", t_("einsamen"), -20, trim=[0.0, 8.0], fade=2.0)
L("lnik3", "lbl_nikumaroro", t_("Nikumaroro"), t_("Skelett") - 0.15, 540, 330, 620, 2)
P("bones3", "st_bones", t_("Skelett") - 0.05, t_("Arzt") - 0.3, 540, 1180, 760, -6, sound=None)
rec("bones_rattle", t_("Skelett"), -7)
rec("heartbeat_low", t_("Skelett") + 0.3, -12, trim=[0.0, 4.0], fade=0.8)
P("shoe3", "st_shoe", t_("Frauenschuhs") - 0.1, t_("Arzt") - 0.3, 290, 1620, 380, 7)
P("box3", "st_box_empty", t_("Kiste") - 0.1, t_("Arzt") - 0.3, 790, 1620, 400, -5)

# ======================================================================= 4  doctor: a man. case closed.
solid("dim4", t_("Arzt") - 0.4, t_("Und") + 0.4, [
    {"t": t_("Arzt") - 0.4, "opacity": 0.0}, {"t": t_("Arzt"), "opacity": 0.35},
    {"t": t_("Und") - 0.2, "opacity": 0.35}, {"t": t_("Und") + 0.3, "opacity": 0.0}], color=(20, 26, 22))
P("doc4", "st_doctor", t_("Arzt") - 0.2, t_("Bis") - 0.25, 540, 780, 640, -3, how="slide", frm=(-600, 800),
  sound="paper_slide")
FX, FY = 540, 1400
P("fold4", "st_folder", t_("Mann") - 0.5, t_("Bis") - 0.25, FX, FY, 520, 4)
stamp("stamp4", "stamp_mann", t_("Mann"), t_("Bis") - 0.25, FX, FY - 20, 360, rot=-12)
S.flash("fl4", t_("Mann"), peak=0.3)
L("lfall", "lbl_fall", t_("Fall") - 0.05, t_("Bis") - 0.25, 540, 300, 640, -2)

# ======================================================================= 5  2018: the bones fit Amelia – 99 %
L("l2018", "lbl_2018", t_("Bis"), t_("Ergebnis") - 0.2, 540, 300, 420, -3, sound="cardboard_hit", gain=-10)
L("ljantz", "lbl_jantz", t_("Forscher"), t_("Ergebnis") - 0.2, 540, 1500, 600, 2)
P("cal5", "st_caliper", t_("Messwerte") - 0.4, t_("Ergebnis") - 0.2, 540, 900, 820, 8, sound="paper_slide")
P("bones5", "st_bones", t_("Knochen", 43) - 0.1, t_("nachprüfen") - 0.25, 540, 620, 700, -6, sound=None)
rec("bones_rattle", t_("Knochen", 43), -10)
P("port5", "st_portrait", t_("Amelia", 45) - 0.1, t_("nachprüfen") - 0.25, 540, 1230, 460, 3)
L("l99", "lbl_99", t_("99") - 0.05, t_("nachprüfen") - 0.25, 820, 1540, 360, -6, sound="cardboard_hit", gain=-7)
rec("suspense_hit", t_("99"), -14)
P("fopen5", "st_folder_open", t_("nachprüfen") - 0.1, t_("Und") - 0.2, 540, 960, 760, 2)
L("lvers5", "lbl_verschwunden", t_("nachprüfen") + 0.6, t_("Und") - 0.2, 540, 1460, 640, -3)
rec("box_open", t_("nachprüfen"), -9, trim=[0.0, 1.0], fade=0.3)

# ======================================================================= 6  October 2026: something in the lagoon
cam(t_("Und") - 0.2, NIK, Z_SAT, "inout")
cam(t_("Was") - 0.3, (NIK[0] - 0.003 * PPD, NIK[1]), Z_SAT * 1.12, "linear")
rec("map_whoosh", t_("Und") - 0.3, -7, peak=0.38)
L("lokt", "lbl_okt2026", t_("Oktober") - 0.05, t_("Lagune") - 0.2, 540, 330, 620, -3, sound="cardboard_hit", gain=-9)
sat_c = (NIK[0] - 0.006 * PPD, NIK[1] - 0.002 * PPD)
r_c = 0.008 * PPD
MAP_EXTRA.append({"id": "satc", "type": "dashed_path", "start": t_("Satellitenbildern"), "end": END,
                  "points": [[sat_c[0] + r_c * math.cos(a), sat_c[1] + r_c * math.sin(a)]
                             for a in [2 * math.pi * j / 60 for j in range(61)]],
                  "props": {"x": 0, "y": 0}, "width": 8 / Z_SAT, "dash": 22 / Z_SAT, "gap": 14 / Z_SAT,
                  "color": [232, 112, 58],
                  "keys": [{"t": t_("Satellitenbildern"), "progress": 0.0}, {"t": t_("Satellitenbildern") + 0.8, "progress": 1.0, "ease": "inout"}]})
L("lsat", "lbl_satellit", t_("Satellitenbildern"), t_("Etwas") - 0.2, 540, 1560, 560, 3)
t_s = t_("Lagune") - 0.2
sp = S.scale_for("st_satplane", 980)
S.image("sat6", "st_satplane", t_s, END, [
    {"t": t_s, "x": 540, "y": 960, "scale": sp * 0.15, "rot": 2, "opacity": 0.0}, {"t": t_s + 0.05, "opacity": 1.0},
    {"t": t_s + 0.35, "scale": sp, "ease": "out"}, {"t": t_("siehst") - 0.3, "scale": sp * 1.05, "opacity": 1.0},
    {"t": t_("siehst"), "opacity": 0.0}])
rec("paper_drop", t_s + 0.05, -9)
mg_s = S.scale_for("st_magnifier", 520)
S.image("mag6", "st_magnifier", t_s + 0.4, t_("siehst"), slide_in(t_s + 0.4, 1400, 1700, 600, 930, mg_s, -30, -12, 0.45) + [
    {"t": t_("Flugzeugs") - 0.3, "x": 520, "y": 960}, {"t": t_("Was") + 0.4, "x": 560, "y": 940},
    exit_to(t_("siehst") - 0.3, 1500, 1800, 0.3, rot=-40)], anchor=list(M["st_magnifier"]["lens"]))
L("lwas", "lbl_wasdas", t_("Flugzeugs") - 0.6, t_("siehst") - 0.3, 540, 1500, 700, -3,
  sound="cardboard_hit", gain=-6)
rec("suspense_hit", t_("Flugzeugs") - 0.6, -11)
rec("heartbeat_low", t_("Etwas") - 0.2, -12, trim=[0.0, 5.0], fade=1.0)

# ======================================================================= 7  call to action: full video on the channel
solid("dark7", t_("Was") - 0.2, END, [{"t": t_("Was") - 0.2, "opacity": 0.0}, {"t": t_("Was") + 0.4, "opacity": 0.4},
                                      {"t": t_("siehst"), "opacity": 0.55}])
L("l3th", "lbl_3theorien", t_("welche") - 0.05, t_("siehst") - 0.3, 540, 330, 760, 2)
for k_, (aid, x, wd, rot) in enumerate([("st_electra", 210, 300, -6), ("st_photo2017", 540, 280, 4), ("st_house", 870, 290, -4)]):
    P(f"th7_{k_}", aid, t_("Theorien") - 0.4 + 0.15 * k_, t_("siehst") - 0.3, x, 560, wd, rot, gain=-13)
P("port7", "st_portrait", t_("siehst") - 0.1, END + 1, 540, 980, 600, -3, sound="paper_slide")
L("lwo", "lbl_wo", t_("siehst"), END + 1, 540, 420, 760, 2, sound="cardboard_hit", gain=-7)
L("lvid", "lbl_video", t_("Video") - 0.1, END + 1, 540, 1500, 660, -2)
L("lkan", "lbl_kanal", t_("Kanal") - 0.4, END + 1, 540, 1680, 640, 2)
rec("suspense_hit", t_("Video"), -13)

# ======================================================================= camera + map layer
CAM.sort(key=lambda c: c[0])
held = [CAM[0]]
for a, b in zip(CAM, CAM[1:]):
    if b[0] - a[0] > 2.5:
        held.append((round(b[0] - 0.8, 3), a[1], a[2], a[3], "linear"))
    held.append(b)
cam_scale, cam_pan = fly_camera(held, END, center=(CX, CY))
P_OF = [(k["t"], k["scale"] * PPD) for k in cam_scale]


def zoom_fade(p_in0, p_in1):
    def f(P_):
        v = min(1, max(0, (math.log(P_) - math.log(p_in0)) / (math.log(p_in1) - math.log(p_in0))))
        return v * v * (3 - 2 * v)
    keys, last = [], None
    for t, P_ in P_OF:
        v = round(f(P_), 3)
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
ISLANDS = [{"id": n, "type": "image", "asset": n, "anchor": M[n]["anchor"],
            "props": {k: M[n]["place"][k] for k in ("x", "y", "scale", "rot")}, "keys": []}
           for n in ("isl_nikumaroro", "isl_howland") if n in M]
S.layers.insert(0, {"id": "cam", "type": "group", "pivot": [CX, CY], "keys": cam_scale, "children": [
    {"id": "cam_pan", "type": "group", "pivot": [0, 0], "keys": cam_pan, "children": [
        {"id": "map", "type": "image", "asset": "map_pacific", "anchor": [0, 0], "props": {"x": 0, "y": 0}, "keys": []},
        {"id": "map_wl", "type": "image", "asset": "map_wrap_l", "anchor": [0, 0],
         "props": {"x": M["map_wrap_l"]["x"], "y": 0}, "keys": []},
        *tiles, *ISLANDS, *MAP_EXTRA]}]})
S.layers.append({"id": "page", "type": "multiply_image", "asset": "page", "keys": []})

# ======================================================================= music + SFX ceiling
S.audio.append({"src": "audio/music/music_mystery.mp3", "start": 0.0, "gain_db": -20, "trim": [20.0, 20.0 + t_("Drei")],
                "fade_in": 0.5, "fade_out": 1.5})
S.audio.append({"src": "audio/music/music_tension.mp3", "start": round(t_("Drei") - 1.0, 3), "gain_db": -22,
                "trim": [30.0, 30.0 + END - t_("Drei") + 1.0], "fade_in": 1.5, "fade_out": 1.5})
CEIL = {"default": -27.0, "paper_tear": -30.0, "paper_slide": -30.0, "suspense_hit": -24.0, "stamp": -25.0,
        "map_whoosh": -26.0, "drone_dark": -29.0, "ocean_wind": -30.0, "radio_static_long": -29.0, "bones_rattle": -25.0}


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
    over = _mm[k_] + a_["gain_db"] - CEIL.get(os.path.basename(a_["src"])[:-4], CEIL["default"])
    if over > 0:
        a_["gain_db"] = round(a_["gain_db"] - over, 1)

assets = {name: {"path": f"build/assets/{m.get('file', name)}.png", "license": "own"} for name, m in M.items()
          if isinstance(m, dict) and "w" in m}
timeline = {"meta": {"fps": 30, "width": W, "height": H, "design": [W, H], "duration": round(END, 3)},
            "assets": assets, "layers": S.layers,
            "audio": [{"id": "voice", "src": "audio/voice.mp3", "start": 0.0, "gain_db": 0.0}] + S.audio}
json.dump(timeline, open(os.path.join(HERE, "timeline.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("timeline ->", os.path.join(HERE, "timeline.json"), "| end", round(END, 2), "|", len(S.layers), "layers")
