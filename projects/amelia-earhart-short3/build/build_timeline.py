"""Short 3 (9:16, ~65 s): the 2017 "proof photo" – teaser for the long Amelia Earhart video.

    python3 projects/amelia-earhart-short3/build/build_timeline.py

Hook: the photo that should prove she survived, debunked in 30 minutes.  Japan part with the
user's imperial flag; open question "where is she then?" → 3 other theories in the long video.
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
for k, a in [("Dieses", 0), ("Foto", 0), ("beweisen", 0), ("Amelia", 1), ("Earhart", 2), ("Blogger", 4), ("30", 5),
             ("zerlegt", 6), ("1937", 7), ("verschwindet", 9), ("Pazifik", 12), ("Seitdem", 13), ("düstere", 14),
             ("landet", 16), ("Marshallinseln", 16), ("Japan", 18), ("gefangen", 20), ("2017", 21), ("Fernsehdoku", 24),
             ("Beweis", 25), ("Hafen", 27), ("Die", 29.5), ("sitzende", 30), ("Amelia", 32), ("Mann", 33), ("Noonan", 35),
             ("Schlagzeilen", 36), ("Dann", 38), ("japanischer", 39), ("Online", 40), ("Nach", 42), ("30", 42),
             ("findet", 44), ("Reisebuch", 46), ("Buch", 47), ("1935", 48), ("Zwei", 50), ("Der", 53), ("geplatzt", 54),
             ("Aber", 55), ("wo", 55), ("Es", 56.5), ("drei", 57), ("Knochen", 60), ("Alle", 61), ("Video", 62),
             ("Kanal", 63)]:
    T[(k, a)] = w(k, a)


def t_(k, a=None):
    if a is None:
        return next(v for (kk, _), v in T.items() if kk == k)
    return T[(k, a)]


def circle(id_, cx, cy, r, t0, t1, color=(232, 112, 58), width=9):
    S.layers.append({"id": id_, "type": "dashed_path", "start": t0, "end": t1 + 0.3,
                     "points": [[cx + r * math.cos(a), cy + r * 0.86 * math.sin(a)]
                                for a in [-math.pi / 2 + 2 * math.pi * j / 60 for j in range(61)]],
                     "props": {"x": 0, "y": 0}, "width": width, "dash": 2000, "gap": 1, "color": list(color),
                     "keys": [{"t": t0, "progress": 0.0, "opacity": 1.0}, {"t": t0 + 0.45, "progress": 1.0, "ease": "inout"},
                              {"t": t1, "opacity": 1.0}, {"t": t1 + 0.3, "opacity": 0.0}]})
    rec("pen_scribble", t0, -14, trim=[0.0, 0.6], fade=0.2)


# the harbour photo: person positions as fractions of the picture
PH_W = 980
ph_s = S.scale_for("st_photo2017", PH_W)
ph_h = M["st_photo2017"]["h"] * ph_s
ax_, ay_ = M["st_photo2017"]["anchor"]


def ph_pt(cx, cy, fx, fy, width=PH_W):
    k = width / PH_W
    return cx + (fx - ax_) * PH_W * k, cy + (fy - ay_) * ph_h * k


SIT, MAN = (0.52, 0.74), (0.41, 0.45)

# ======================================================================= 0  HOOK: this photo was the proof … debunked in 30 min
PX, PY = 540, 960
t_z = t_("zerlegt")
S.image("ph0", "st_photo2017", 0.0, t_("1937") - 0.05, [
    {"t": 0.0, "x": PX, "y": PY, "scale": ph_s * 1.2, "rot": -6, "opacity": 1.0},
    {"t": 0.25, "scale": ph_s, "rot": -2, "ease": "out3"},
    {"t": t_("1937") - 0.4, "x": PX, "y": PY, "scale": ph_s * 1.03}, exit_to(t_("1937") - 0.4, -800, PY, 0.3, rot=-20)])
rec("paper_drop", 0.0, -8)
rec("suspense_hit", 0.05, -12)
L("lbew0", "lbl_beweis", t_("beweisen") - 0.1, t_("Blogger") - 0.2, 540, 330, 620, -3, sound="cardboard_hit", gain=-8)
c1 = ph_pt(PX, PY, *SIT)
c2 = ph_pt(PX, PY, *MAN)
circle("c0a", c1[0], c1[1], 120, t_("Amelia", 1), t_("1937") - 0.4)
circle("c0b", c2[0], c2[1], 105, t_("Earhart") + 0.1, t_("1937") - 0.4)
L("lueb", "lbl_ueberlebt", t_("Amelia", 1) + 0.6, t_("Blogger") - 0.2, 540, 1550, 560, 3)
L("lblog0", "lbl_blogger", t_("Blogger") - 0.05, t_("1937") - 0.4, 540, 330, 560, -2)
L("l30_0", "lbl_30min", t_("30") - 0.05, t_("1937") - 0.4, 540, 1550, 600, 3, sound="cardboard_hit", gain=-9)
stamp("st0", "stamp_widerlegt", t_z, t_("1937") - 0.4, PX, PY, 760, rot=-12)
S.flash("fl0", t_z, peak=0.3)
rec("paper_tear", t_z + 0.1, -10)

# ======================================================================= 1  1937: she vanishes over the Pacific
Z_P = 0.95
d = (HOW[0] - LAE[0], HOW[1] - LAE[1])
cam(0.0, (HOW[0] - d[0] * 0.5, HOW[1] - d[1] * 0.5 + 60), Z_P, None)
L("l1937", "lbl_1937", t_("1937") - 0.05, t_("Seitdem") - 0.25, 540, 330, 420, -3)
P("port1", "st_portrait", t_("verschwindet") - 0.2, t_("Seitdem") - 0.25, 540, 1400, 520, 3, how="slide",
  frm=(540, 2400), sound="paper_slide", exit=(-600, 1400))
t_pa = t_("Pazifik")
pk, pprog = follow([LAE, (HOW[0] - d[0] * 0.1, HOW[1] - d[1] * 0.1)], t_("1937"), t_pa + 0.4)
for k in pk:
    k["scale"] = S.scale_for("st_electra", 260) / Z_P
MAP_EXTRA.append({"id": "pl1", "type": "image", "asset": "st_electra", "start": t_("1937"), "end": t_pa + 1.1,
                  "anchor": M["st_electra"]["anchor"],
                  "keys": pk + [{"t": t_pa + 0.5, "opacity": 0.2}, {"t": t_pa + 0.6, "opacity": 0.9},
                                {"t": t_pa + 0.75, "opacity": 0.1}, {"t": t_pa + 0.85, "opacity": 0.7},
                                {"t": t_pa + 1.05, "opacity": 0.0}]})
MAP_EXTRA.append({"id": "leg1", "type": "dashed_path", "start": t_("1937"), "end": t_pa + 1.1,
                  "points": [list(LAE), [HOW[0] - d[0] * 0.1, HOW[1] - d[1] * 0.1]], "props": {"x": 0, "y": 0},
                  "width": 7 / Z_P, "dash": 20 / Z_P, "gap": 12 / Z_P, "color": [232, 112, 58],
                  "keys": pprog + [{"t": t_pa + 0.6, "opacity": 1.0}, {"t": t_pa + 1.0, "opacity": 0.0}]})
rec("plane_distant", t_("1937"), -16, trim=[0.0, t_pa - t_("1937") + 0.5], fade=0.8)
rec("radio_cutoff", t_pa + 0.5, -10, trim=[0.0, 1.6], fade=0.4)

# ======================================================================= 2  theory: Marshall Islands, Japan, captured
MILI = PL["mili"]
Z_J = 1.15
cam(t_("Seitdem") - 0.2, ((HOW[0] + MILI[0]) / 2, (HOW[1] + MILI[1]) / 2 + 40), Z_J, "inout")
rec("drone_dark", t_("Seitdem"), -15, trim=[0.0, 9.0], fade=1.5)
jk, jprog = follow([HOW, MILI], t_("landet") - 0.2, t_("Marshallinseln") + 0.6)
for k in jk:
    k["scale"] = S.scale_for("st_electra", 220) / Z_J
    k["rot"] -= 180
    k["sx"] = -1
MAP_EXTRA.append({"id": "pl2", "type": "image", "asset": "st_electra", "start": t_("landet") - 0.2, "end": t_("gefangen") + 0.4,
                  "anchor": M["st_electra"]["anchor"],
                  "keys": jk + [{"t": t_("gefangen"), "opacity": 1.0}, {"t": t_("gefangen") + 0.3, "opacity": 0.0}]})
MAP_EXTRA.append({"id": "leg2", "type": "dashed_path", "start": t_("landet") - 0.2, "end": t_("2017"),
                  "points": [list(HOW), list(MILI)], "props": {"x": 0, "y": 0}, "width": 7 / Z_J, "dash": 20 / Z_J,
                  "gap": 12 / Z_J, "color": [232, 112, 58], "keys": jprog})
MAP_EXTRA.append({"id": "city_mili2", "type": "image", "asset": "city_mili", "start": t_("Marshallinseln"), "end": t_("2017") + 0.5,
                  "anchor": M["city_mili"]["anchor"],
                  "keys": [{"t": t_("Marshallinseln"), "x": MILI[0], "y": MILI[1], "scale": 0.0},
                           {"t": t_("Marshallinseln") + 0.2, "scale": 1.15 / Z_J, "ease": "out"},
                           {"t": t_("Marshallinseln") + 0.35, "scale": 1.0 / Z_J}]})
# the flag of imperial Japan: drops in on "Japan", flutters, darkens with "gefangen"
t_j = t_("Japan") - 0.15
fs = S.scale_for("st_flag", 860)
fkeys = [{"t": t_j, "x": 540, "y": -500, "scale": fs, "rot": -12, "opacity": 1.0},
         {"t": t_j + 0.4, "x": 540, "y": 560, "rot": -3, "ease": "out3"}]
tt = t_j + 0.4
while tt < t_("2017") - 0.5:
    tt += 0.55
    fkeys.append({"t": round(tt, 3), "rot": -3 + (1.6 if len(fkeys) % 2 else -1.6), "scale": fs * (1.0 + (0.012 if len(fkeys) % 2 else 0.0)), "ease": "inout"})
fkeys += [{"t": t_("2017") - 0.4, "x": 540, "y": 560}, exit_to(t_("2017") - 0.4, 540, -700, 0.35)]
S.image("flag2", "st_flag", t_j, t_("2017"), fkeys, jitter=False)
rec("paper_slide", t_j + 0.1, -6, peak=0.42)
L("ljap", "lbl_japan", t_("Japan") + 0.3, t_("2017") - 0.4, 540, 1020, 640, 2)
L("lgef", "lbl_gefangen", t_("gefangen"), t_("2017") - 0.4, 540, 1500, 560, -3, sound="cardboard_hit", gain=-9)
S.layers.append({"id": "drain2", "type": "grade", "start": t_("gefangen"), "end": t_("2017") + 0.6,
                 "keys": [{"t": t_("gefangen"), "saturation": 1.0}, {"t": t_("gefangen") + 0.5, "saturation": 0.35},
                          {"t": t_("2017") - 0.2, "saturation": 0.35}, {"t": t_("2017") + 0.3, "saturation": 1.0}]})

# ======================================================================= 3  2017: the TV documentary and the photo
solid("dim3", t_("2017") - 0.3, END + 1, [{"t": t_("2017") - 0.3, "opacity": 0.0}, {"t": t_("2017") + 0.2, "opacity": 0.3}],
      color=(20, 26, 22))
L("l2017", "lbl_2017", t_("2017") - 0.05, t_("sitzende") - 0.3, 540, 300, 420, -3, sound="cardboard_hit", gain=-10)
TVX, TVY, TVW = 540, 1000, 960
P("tv3", "st_tv", t_("Fernsehdoku") - 0.4, t_("sitzende") - 0.3, TVX, TVY, TVW, -2)
rec("tv_on", t_("Fernsehdoku") - 0.2, -10)
k_tv = TVW / 720
S.image("ph_tv", "st_photo2017", t_("Fernsehdoku") + 0.1, t_("sitzende") - 0.25, [
    {"t": t_("Fernsehdoku") + 0.1, "x": TVX - 60 * k_tv, "y": TVY - 40 * k_tv, "scale": S.scale_for("st_photo2017", 470 * k_tv), "rot": -2, "opacity": 0.0},
    {"t": t_("Fernsehdoku") + 0.3, "opacity": 1.0}, {"t": t_("sitzende") - 0.6, "x": TVX - 60 * k_tv, "y": TVY - 40 * k_tv},
    exit_to(t_("sitzende") - 0.6, 1700, TVY, 0.3)])
L("lbew3", "lbl_beweis", t_("Beweis", 25) - 0.05, t_("sitzende") - 0.3, 540, 1620, 620, 3, sound="cardboard_hit", gain=-8)
# close-up on the photo: who is who
t_c = t_("sitzende") - 0.3
S.image("ph3", "st_photo2017", t_c, t_("Dann") - 0.1, [
    {"t": t_c, "x": 1700, "y": PY, "scale": ph_s, "rot": 4, "opacity": 1.0},
    {"t": t_c + 0.35, "x": PX, "y": PY, "rot": -1, "ease": "out3"},
    {"t": t_("Dann") - 0.45, "x": PX, "y": PY}, exit_to(t_("Dann") - 0.45, -800, PY, 0.3, rot=-15)])
rec("paper_slide", t_c, -7, peak=0.42)
circle("c3a", c1[0], c1[1], 120, t_("sitzende") + 0.3, t_("Dann") - 0.45)
L("lea3", "lbl_earhart_q", t_("Amelia", 32), t_("Dann") - 0.45, c1[0] + 230, c1[1] + 260, 380, 4)
circle("c3b", c2[0], c2[1], 105, t_("Mann"), t_("Dann") - 0.45)
L("lno3", "lbl_noonan_q", t_("Noonan") - 0.2, t_("Dann") - 0.45, c2[0] - 160, c2[1] - 260, 380, -4)
for k_, (x, y, rot) in enumerate([(830, 380, 9), (230, 1660, -8)]):
    P(f"news3_{k_}", "newspaper_2017", t_("Schlagzeilen") + 0.25 * k_, t_("Dann") - 0.45, x, y, 420, rot,
      sound="newspaper" if k_ == 0 else None, gain=-10)

# ======================================================================= 4  the blogger: 30 minutes, travel book, 1935
BX, BY, BW = 540, 1000, 1000
L("lblog4", "lbl_blogger", t_("Dann"), t_("findet") - 0.2, 540, 330, 560, -2)
mg_s = S.scale_for("st_magnifier", 560)
S.image("mag4", "st_magnifier", t_("japanischer") - 0.2, t_("1935") - 0.3, slide_in(t_("japanischer") - 0.2, 1400, 1500, 420, 900, mg_s, -30, -12, 0.45) + [
    {"t": t_("Nach") - 0.3, "x": 700, "y": 1050, "ease": "inout"}, {"t": t_("findet"), "x": 380, "y": 860, "ease": "inout"},
    {"t": t_("Reisebuch") + 0.6, "x": BX + (0.72 - M["st_travelbook"]["anchor"][0]) * BW, "y": BY + (0.40 - M["st_travelbook"]["anchor"][1]) * M["st_travelbook"]["h"] * S.scale_for("st_travelbook", BW), "ease": "inout"}, exit_to(t_("1935") - 0.6, 1500, 1800, 0.3, rot=-40)],
    anchor=list(M["st_magnifier"]["lens"]))
P("watch4", "st_watch", t_("Nach") - 0.1, t_("findet") - 0.2, 800, 650, 300, 6, sound=None)
rec("heartbeat_low", t_("Nach"), -13, trim=[0.0, 2.5], fade=0.6)
L("l30_4", "lbl_30min", t_("30", 42) - 0.05, t_("findet") - 0.2, 540, 1550, 600, -3)
bs_ = S.scale_for("st_travelbook", BW)
bh = M["st_travelbook"]["h"] * bs_
bax, bay = M["st_travelbook"]["anchor"]
S.image("book4", "st_travelbook", t_("findet") - 0.15, END + 1, [
    {"t": t_("findet") - 0.15, "x": BX, "y": BY, "scale": bs_ * 0.2, "rot": -8, "opacity": 0.0},
    {"t": t_("findet") - 0.1, "opacity": 1.0}, {"t": t_("findet") + 0.25, "scale": bs_, "rot": -3, "ease": "out3"},
    {"t": t_("Der") - 0.3, "x": BX, "y": BY, "opacity": 1.0}, {"t": t_("Der"), "opacity": 0.0}])
rec("page_turn", t_("findet"), -9)
# the same photo glued into the book (right page)
mini = (BX + (0.72 - bax) * BW, BY + (0.40 - bay) * bh)
mw = 0.27 * BW
S.image("ph_book", "st_photo2017", t_("Reisebuch") - 0.2, END + 1, [
    {"t": t_("Reisebuch") - 0.2, "x": mini[0], "y": mini[1], "scale": S.scale_for("st_photo2017", mw) * 2.5, "rot": 6, "opacity": 0.0},
    {"t": t_("Reisebuch") - 0.15, "opacity": 1.0}, {"t": t_("Reisebuch") + 0.15, "scale": S.scale_for("st_photo2017", mw), "rot": 2, "ease": "in"},
    {"t": t_("Der") - 0.3, "opacity": 1.0}, {"t": t_("Der"), "opacity": 0.0}])
rec("paper_drop", t_("Reisebuch") + 0.1, -10)
S.layers.append(S.layers.pop(next(i for i, L_ in enumerate(S.layers) if L_["id"] == "mag4")))  # lens above the book
L("l1935", "lbl_1935", t_("1935") - 0.05, t_("Der") - 0.3, 540, 330, 560, -3, sound="cardboard_hit", gain=-6)
rec("suspense_hit", t_("1935"), -11)
stamp("st4", "stamp_widerlegt", t_("Zwei") + 0.1, t_("Der") - 0.3, 540, 1450, 760, rot=-10)
S.flash("fl4", t_("Zwei") + 0.1, peak=0.3)

# ======================================================================= 5  proof burst – where is she? + call to action
L("lgepl", "lbl_geplatzt", t_("Der") - 0.05, t_("Aber") - 0.2, 540, 960, 660, -4, sound=None)
rec("paper_tear", t_("geplatzt"), -9)
solid("dark5", t_("Aber") - 0.3, END + 1, [{"t": t_("Aber") - 0.3, "opacity": 0.0}, {"t": t_("Aber") + 0.3, "opacity": 0.35}])
P("port5", "st_portrait", t_("Aber") - 0.1, END + 1, 540, 1020, 560, -3, sound="paper_slide")
L("lwo", "lbl_wo", t_("wo") - 0.05, END + 1, 540, 420, 760, 2, sound="cardboard_hit", gain=-7)
for k_, (aid, x, wd, rot) in enumerate([("st_electra", 190, 300, -6), ("st_bones", 540, 300, 4), ("st_house", 890, 280, -4)]):
    P(f"th5_{k_}", aid, t_("drei") - 0.1 + 0.15 * k_, t_("Alle") - 0.2, x, 1500, wd, rot, gain=-13)
bsx = S.scale_for("st_bones", 300)
S.image("bones_pulse", "st_bones", t_("Knochen"), t_("Alle") + 0.1, [
    {"t": t_("Knochen"), "x": 540, "y": 1500, "scale": bsx, "rot": 4, "opacity": 0.0}, {"t": t_("Knochen") + 0.02, "opacity": 1.0},
    {"t": t_("Knochen") + 0.18, "scale": bsx * 1.35, "ease": "out"}, {"t": t_("Knochen") + 0.4, "scale": bsx * 1.15, "ease": "inout"},
    {"t": t_("Alle") - 0.2, "x": 540, "y": 1500, "opacity": 1.0}, exit_to(t_("Alle") - 0.2, 540, 2300)])
rec("bones_rattle", t_("Knochen"), -11)
L("lvid", "lbl_video", t_("Alle") - 0.05, END + 1, 540, 1500, 660, -2)
L("lkan", "lbl_kanal", t_("Video") - 0.1, END + 1, 540, 1680, 640, 2)
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
S.audio.append({"src": "audio/music/music_mystery.mp3", "start": 0.0, "gain_db": -20, "trim": [20.0, 20.0 + t_("2017")],
                "fade_in": 0.5, "fade_out": 1.5})
S.audio.append({"src": "audio/music/music_tension.mp3", "start": round(t_("2017") - 1.0, 3), "gain_db": -22,
                "trim": [30.0, 30.0 + END - t_("2017") + 1.0], "fade_in": 1.5, "fade_out": 1.5})
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
