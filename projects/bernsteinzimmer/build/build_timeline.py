"""Timeline v2 of the Bernsteinzimmer video (16:9).

    python3 projects/bernsteinzimmer/build/build_timeline.py [--end SECONDS]

Concept (user feedback on v1: too busy, no red thread, colour photos distract):
  * one hero object – the amber room as a collage panel – lives ON THE MAP and travels / breaks / reassembles
  * the map is the stage; people appear next to their city; at most 2-3 elements at a time
  * every new element acts on something (hands over, draws, carries, marches)
  * flags pale on the map; a country lights up only while it acts
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(PROJ)))
from shortsfactory.collage.choreo import Show, exit_to, fly_camera, pop_in  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--end", type=float, default=None)
ARGS = ap.parse_args()

W, H = 1920, 1080
CX, CY = W / 2, H / 2
S = Show(os.path.join(HERE, "assets", "meta.json"), os.path.join(PROJ, "analysis", "words.json"))
M, WORDS, rec = S.META, S.WORDS, S.rec
FULL_END = WORDS[-1]["end"] + 1.5
END = ARGS.end or FULL_END
MW, MH = M["map_europe"]["w"], M["map_europe"]["h"]
PL = {k: tuple(v) for k, v in M["places"].items()}
CAM, MAPL, HERO = [], [], []          # camera keys, map-space layers (under the dim), hero layers (above it)
FLAG_BASE = 0.42


def w(word, approx):
    return S.w(word, approx - 1.5)


def sc(asset, width):
    return S.scale_for(asset, width)


# ------------------------------------------------------------------ camera
def cam(t, xy, s, ease="inout"):
    x, y = xy
    hw, hh = CX / s, CY / s
    x = MW / 2 if hw >= MW / 2 else min(max(x, hw), MW - hw)
    y = MH / 2 if hh >= MH / 2 else min(max(y, hh), MH - hh)
    CAM.append((round(t, 3), x, y, s, ease))
    return (x, y)


def scr(p, c, z):
    """map point -> screen point for a camera centred on c with zoom z"""
    return ((p[0] - c[0]) * z + CX, (p[1] - c[1]) * z + CY)


# ------------------------------------------------------------------ screen-space helpers
def pop(id_, asset, t0, t1, x, y, width, rot=0.0, sound="paper_drop", gain=-12.0, out="shrink", extra=()):
    s = sc(asset, width)
    k = pop_in(t0, x, y, s, rot) + list(extra)
    k.append({"t": t1, "x": x, "y": y, "scale": s, "opacity": 1.0})
    if out == "shrink":
        k.append({"t": t1 + 0.22, "scale": s * 0.05, "opacity": 0.0, "ease": "in"})
    else:
        tx, ty = {"left": (-700, y), "right": (W + 700, y), "down": (x, H + 700)}[out]
        k.append(exit_to(t1, tx, ty, 0.3))
    k.sort(key=lambda q: q["t"])
    S.image(id_, asset, t0, t1 + 0.35, k)
    if sound:
        rec(sound, t0 + 0.05, gain)


def lbl(id_, asset, t0, t1, x, y, width, rot=-2.0):
    pop(id_, asset, t0, t1, x, y, width, rot, sound=None)


def cap(id_, asset, t0, t1, x, y):
    s = sc(asset, M[asset]["w"])
    S.image(id_, asset, t0, t1 + 0.3, [
        {"t": t0, "x": x, "y": y + 40, "scale": s, "opacity": 0.0},
        {"t": t0 + 0.3, "y": y, "opacity": 1.0, "ease": "out3"},
        {"t": t1, "opacity": 1.0}, {"t": t1 + 0.3, "opacity": 0.0}], jitter=False)


# ------------------------------------------------------------------ map-space helpers
def mimg(lst, id_, asset, t0, t1, keys, anchor=None):
    lst.append({"id": id_, "type": "image", "asset": asset, "start": t0, "end": t1,
                "anchor": anchor or M[asset].get("anchor", [0.5, 0.5]), "keys": keys})


def mcity(key, t0, t1, z):
    a = "city_" + key
    x, y = PL[key]
    s = 1.0 / z
    mimg(MAPL, f"{a}_{int(t0 * 10)}", a, t0, t1 + 0.4,
         [{"t": t0, "x": x, "y": y, "scale": 0.0, "opacity": 1.0}, {"t": t0 + 0.18, "scale": s * 1.15, "ease": "out"},
          {"t": t0 + 0.32, "scale": s}, {"t": t1, "opacity": 1.0}, {"t": t1 + 0.4, "opacity": 0.0}])


FLAG_KEYS = {}


def flags(year, keys, t0, t1, fade=0.8):
    for key in keys:
        a = f"flag_{year}_{key}"
        x0, y0 = M[a]["pos"]
        FLAG_KEYS[(year, key)] = [{"t": t0, "x": x0, "y": y0, "opacity": 0.0}, {"t": t0 + fade, "opacity": FLAG_BASE},
                                  {"t": t1 - fade, "opacity": FLAG_BASE}, {"t": t1, "opacity": 0.0}]


def light(year, key, t0, t1, shake=False):
    """a country lights up (full flag) while it acts"""
    k = FLAG_KEYS[(year, key)]
    k += [{"t": t0, "opacity": FLAG_BASE}, {"t": t0 + 0.35, "opacity": 1.0},
          {"t": t1, "opacity": 1.0}, {"t": t1 + 0.5, "opacity": FLAG_BASE}]
    if shake:
        x0 = M[f"flag_{year}_{key}"]["pos"][0]
        k += [{"t": t0 + 0.3, "x": x0}] + [{"t": t0 + 0.3 + 0.07 * (j + 1), "x": x0 + (12 if j % 2 == 0 else -12)} for j in range(6)] \
            + [{"t": t0 + 0.8, "x": x0}]


def path_keys(pts, t0, t1, s, bob=0.0, mirror=False, smooth=True):
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    tot = sum(seg)
    keys, prog = [], []
    n = max(2, int((t1 - t0) * 12))
    for j in range(n + 1):
        f = j / n
        ff = f * f * (3 - 2 * f) if smooth else f
        d = ff * tot
        for (a, b), sl in zip(zip(pts, pts[1:]), seg):
            if d <= sl + 1e-9:
                u = d / sl if sl else 0
                break
            d -= sl
        x, y = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
        y -= abs(math.sin(j * 1.4)) * bob
        k = {"t": round(t0 + (t1 - t0) * f, 3), "x": x, "y": y, "scale": s, "rot": (3 * math.sin(j * 1.4)) if bob else 0}
        if mirror:
            k["sx"] = -1
        keys.append(k)
        prog.append({"t": k["t"], "progress": round(ff, 4)})
    return keys, prog


def mline(lst, id_, pts, t0, t1, z, t_end, color=(232, 112, 58), prog=None):
    keys = prog or [{"t": t0, "progress": 0.0}, {"t": t1, "progress": 1.0, "ease": "inout"}]
    lst.append({"id": id_, "type": "dashed_path", "start": t0, "end": t_end, "points": [list(p) for p in pts],
                "props": {"x": 0, "y": 0}, "width": 7 / z, "dash": 20 / z, "gap": 13 / z, "color": list(color),
                "keys": keys + [{"t": t_end - 0.4, "opacity": 1.0}, {"t": t_end, "opacity": 0.0}]})


def rings(id_, xy, t0, t1, z, size=560, step=0.7):
    t, i = t0, 0
    s0 = sc("arc_orange", size) / z
    while t < t1:
        for r_ in (0, 120, 240):
            mimg(MAPL, f"{id_}{i}_{r_}", "arc_orange", t, t + 1.4,
                 [{"t": t, "x": xy[0], "y": xy[1], "scale": s0 * 0.2, "rot": r_, "opacity": 1.0},
                  {"t": t + 1.4, "scale": s0 * 1.3, "opacity": 0.0, "ease": "out"}])
        t += step
        i += 1


BER, STP, KOE, DZI, STO = PL["berlin"], PL["st_petersburg"], PL["koenigsberg"], PL["dziemiany"], PL["stockholm"]
NSH = sum(1 for k in M if k.startswith("shard"))
PW = M["amber_panel"]["w"]


def hero_panel(id_, t0, t1, keys):
    mimg(HERO, id_, "amber_panel", t0, t1, keys)


# ======================================================================= 0 – Polen 2025: the hole in the ground
Z0 = 1.6
cam(0.0, (DZI[0] + 300, DZI[1] - 120), 0.75, None)
C0 = cam(w("Genehmigung", 4.7) - 0.6, DZI, Z0, "inout")
flags("2010", ["poland", "germany", "russia_k", "russia", "lithuania", "sweden", "denmark", "belarus", "latvia"], 0.0, w("Geschichte", 41.0))
light("2010", "poland", w("Polen", 3.1) - 0.2, w("SS", 8.0))
lbl("l2025", "lbl_2025", w("2025", 0.6), w("Er", 5.9) - 0.2, 330, 140, 460, -3)
mcity("dziemiany", w("Polen", 3.1), w("Wonach", 16.3), Z0)
t_g = w("Genehmigung", 4.7)
pop("gen", "st_s02_1_schreiben", t_g - 0.2, w("ehemaligen", 7.0) - 0.2, 1380, 470, 380, 4)
S.image("stg", "stamp_genehmigt", t_g + 0.3, w("ehemaligen", 7.0), [
    {"t": t_g + 0.3, "x": 1380, "y": 500, "scale": sc("stamp_genehmigt", 360) * 2.2, "rot": -14, "opacity": 0.0},
    {"t": t_g + 0.33, "opacity": 1.0}, {"t": t_g + 0.42, "scale": sc("stamp_genehmigt", 360), "ease": "in"},
    {"t": w("ehemaligen", 7.0) - 0.2, "scale": sc("stamp_genehmigt", 360), "opacity": 1.0},
    {"t": w("ehemaligen", 7.0), "scale": 0.0, "opacity": 0.0}])
rec("stamp", t_g + 0.38, -9)
# the site: barrier tape, then the radar rolls over it
t_ss = w("ehemaligen", 7.0)
lbl("lss", "lbl_ss", t_ss + 0.4, w("Mit", 9.6) - 0.2, 960, 160, 560, -2)
pop("tape", "st_s01_1_absperrband", t_ss - 0.1, w("entdeckt", 12.1) - 0.3, 960, 640, 520, -2)
t_r = w("Bodenradar", 9.8)
s_r = sc("st_s01_2_radar", 260)
S.image("radar", "st_s01_2_radar", t_r - 0.3, w("Wonach", 16.3) - 0.2, [
    {"t": t_r - 0.3, "x": -300, "y": 470, "scale": s_r, "rot": 0},
    {"t": t_r + 0.6, "x": 760, "y": 470, "ease": "out3"},
    {"t": w("Erde", 15.3), "x": 1080, "y": 470, "ease": "linear"},
    {"t": w("Wonach", 16.3) - 0.2, "x": 1100, "y": 470}, exit_to(w("Wonach", 16.3) - 0.2, 2300, 470, 0.4)])
rec("radar_beep", t_r + 0.4, -12)
rings("rr", DZI, t_r + 0.4, w("Wonach", 16.3), Z0)
# cross-section of the ground slides up; a cavity opens in it
t_e = w("entdeckt", 12.1)
S.image("earth", "earth", t_e - 0.3, w("Einem", 19.0) + 0.6, [
    {"t": t_e - 0.3, "x": 0, "y": H + 20, "scale": 1.0}, {"t": t_e + 0.3, "y": 540, "ease": "out3"},
    {"t": w("Einem", 19.0), "y": 540}, {"t": w("Einem", 19.0) + 0.6, "y": H + 20, "ease": "in"}],
    anchor=[0, 0], jitter=False)
rec("shovel", t_e - 0.2, -14)
t_h = w("Hohlraum", 13.8)
S.image("cav", "cavity", t_h - 0.4, w("Einem", 19.0) + 0.6, [
    {"t": t_h - 0.4, "x": 960, "y": 820, "scale": 0.05}, {"t": t_h + 0.1, "scale": 1.0, "ease": "out"},
    {"t": w("Einem", 19.0), "y": 820}, {"t": w("Einem", 19.0) + 0.6, "y": 820 + (H + 20 - 540), "ease": "in"}], jitter=False)
lbl("lhohl", "lbl_hohlraum", t_h, w("Wonach", 16.3) - 0.2, 1500, 760, 420, -3)
rec("suspense_hit", t_h, -16)

# ======================================================================= the hero appears: a room, out of the hole
t_z = w("Zimmer", 18.2)
P_hole = (C0[0] + (960 - CX) / Z0, C0[1] + (820 - CY) / Z0)
P_up = (C0[0], C0[1] - 60 / Z0)
s_p = sc("amber_panel", 380) / Z0
mimg(HERO, "sil", "amber_panel_dark", t_z - 0.6, t_z + 0.9, [
    {"t": t_z - 0.6, "x": P_hole[0], "y": P_hole[1], "scale": s_p * 0.7, "opacity": 0.0}, {"t": t_z - 0.2, "opacity": 0.9},
    {"t": t_z + 0.5, "opacity": 0.9}, {"t": t_z + 0.9, "opacity": 0.0}])
lbl("lq", "lbl_q", t_z - 0.3, t_z + 0.8, 1180, 700, 120, 8)
t_fill = w("Einem", 19.0)
s_big = sc("amber_panel", 640) / Z0
t_vs = w("spurlos", 29.2)
hero_panel("hero0", t_z + 0.5, t_vs + 0.2, [
    {"t": t_z + 0.5, "x": P_hole[0], "y": P_hole[1], "scale": s_p * 0.7, "opacity": 0.0},
    {"t": t_z + 0.9, "opacity": 1.0},
    {"t": t_fill + 0.2, "x": P_hole[0], "y": P_hole[1], "scale": s_p * 0.7},
    {"t": t_fill + 1.2, "x": P_up[0], "y": P_up[1], "scale": s_big, "ease": "out3"},
    {"t": t_vs, "scale": s_big, "opacity": 1.0}, {"t": t_vs + 0.12, "opacity": 0.0}])
rec("amber_shimmer", t_fill + 0.3, -12)
lbl("l6t", "lbl_6t", w("sechs", 21.7), w("Man", 23.6) + 1.6, 960, 930, 620, -2)
cap("cw", "cap_wunder", w("achte", 24.9) - 0.1, w("Und", 26.6) - 0.2, 960, 110)
lbl("l45", "lbl_1945", w("1945", 27.0), w("Wie", 30.6) - 0.2, 300, 150, 300, -3)
# "spurlos verschwunden": the room shatters, the pieces drift apart (and stay with us)
rec("paper_tear", t_vs, -9)
rec("suspense_hit", t_vs + 0.05, -15)
t_ch1 = w("Geschichte", 41.0) - 0.2
Z1, Z1b = 0.55, 1.3
C1 = cam(t_ch1 + 0.2, (BER[0] + 380, BER[1] - 120), Z1, "inout")
t_ber = w("Berlin", 43.6)
C1b = cam(t_ber - 0.2, BER, Z1b, "inout")
t_pz = w("zusammengesetzt", 63.0)
SH = []
for k in range(NSH):
    a = f"shard{k}"
    dx, dy = M[a]["off"]
    sp = s_big                                      # shard px are panel px
    home = (P_up[0] + dx * sp * M["amber_panel"]["w"] / PW, P_up[1] + dy * sp)
    ang = math.atan2(dy + 1e-3, dx + 1e-3)
    drift = (home[0] + math.cos(ang) * (260 + 40 * k) / Z0, home[1] + math.sin(ang) * (180 + 30 * k) / Z0)
    drift2 = (drift[0] + math.cos(ang + 0.6) * 60 / Z0, drift[1] + math.sin(ang + 0.6) * 40 / Z0)
    # around Berlin, then they snap together into the panel there
    bdx, bdy = math.cos(ang) * (190 + 25 * k) / Z1b, math.sin(ang) * (130 + 18 * k) / Z1b
    sB = sc("amber_panel", 300) / Z1b
    home_b = (BER[0] + dx * sB, BER[1] - 40 / Z1b + dy * sB)
    keys = [{"t": t_vs, "x": home[0], "y": home[1], "scale": sp, "rot": 0, "opacity": 1.0},
            {"t": t_vs + 0.6, "x": drift[0], "y": drift[1], "rot": 40 * (k % 3 - 1), "ease": "out3"},
            {"t": t_ch1, "x": drift2[0], "y": drift2[1], "rot": 60 * (k % 3 - 1), "ease": "linear"},
            {"t": t_ber + 0.3 + 0.08 * k, "x": BER[0] + bdx, "y": BER[1] + bdy, "scale": sB, "rot": 20 * (k % 3 - 1), "ease": "inout"},
            {"t": t_pz - 0.2, "x": BER[0] + bdx * 1.05, "y": BER[1] + bdy * 1.05, "rot": 25 * (k % 3 - 1), "ease": "linear"},
            {"t": t_pz + 0.5 + 0.09 * k, "x": home_b[0], "y": home_b[1], "rot": 0, "ease": "inout"},
            {"t": t_pz + 1.6, "opacity": 1.0}, {"t": t_pz + 1.75, "opacity": 0.0}]
    mimg(HERO, f"sh{k}", a, t_vs, t_pz + 1.8, keys)
rec("map_whoosh", t_ch1 + 0.3, -10, peak=0.38)
# dim the map while the story is "inside" the scene (cavity -> question)
S.layers.append({"id": "dim0", "type": "solid", "start": t_e, "end": t_ch1 + 0.8, "color": [18, 20, 18],
                 "keys": [{"t": t_e, "opacity": 0.0}, {"t": t_e + 0.5, "opacity": 0.45},
                          {"t": w("Wie", 30.6), "opacity": 0.45}, {"t": w("Wie", 30.6) + 0.4, "opacity": 0.7},
                          {"t": w("wo", 33.3), "opacity": 0.7}, {"t": w("wo", 33.3) + 0.4, "opacity": 0.45},
                          {"t": t_ch1, "opacity": 0.45}, {"t": t_ch1 + 0.8, "opacity": 0.0}]})
DIM_INDEX = len(S.layers) - 1
cap("cwie", "cap_wie", w("Wie", 30.6), w("wo", 33.3) - 0.2, 960, 540)
lbl("lq2", "lbl_q", w("wo", 33.3), w("Das", 35.3), 960, 540, 150, 6)
t_th = w("Theorie", 39.3)

# ======================================================================= 1 – Berlin 1701: wish -> design -> craft -> assembly
flags("1715", ["prussia", "brandenburg", "russia", "sweden", "poland"], t_ch1, END + 5)
light("1715", "brandenburg", t_ber - 0.2, w("Doch", 66.5))
light("1715", "prussia", t_ber - 0.2, w("Doch", 66.5))
lbl("l1701", "lbl_1701", w("1701", 42.0), w("Der", 44.4) + 2.5, 300, 140, 340, -3)
mcity("berlin", t_ber, w("1716", 79.7) - 0.2, Z1b)
t_fr = w("Friedrich", 45.6)
pop("fr", "st_a2_friedrich_i", t_fr - 0.2, w("Bildhauer", 53.7) - 0.3, 400, 600, 400, -2, out="left")
lbl("lfr", "lbl_friedrich", t_fr + 0.2, w("Bildhauer", 53.7) - 0.3, 400, 990, 380, 2)
# his wish: an empty frame (dashed outline) appears at Berlin
t_wd = w("Wände", 50.8)
bw, bh = 300 / Z1b / 2, 300 * 440 / 640 / Z1b / 2
by = BER[1] - 40 / Z1b
rect = [(BER[0] - bw, by - bh), (BER[0] + bw, by - bh), (BER[0] + bw, by + bh), (BER[0] - bw, by + bh), (BER[0] - bw, by - bh)]
# Schlüter draws it ("entwirft"), Wolfram builds it
t_sch = w("Bildhauer", 53.7)
t_ent = w("entwirft", 55.6)
mline(HERO, "outline", rect, t_ent - 0.4, t_ent + 1.2, Z1b, t_pz + 0.8, color=(246, 240, 226))
mline(HERO, "wish", rect, t_wd - 0.2, t_wd + 0.3, Z1b, t_ent - 0.3, color=(232, 112, 58))
rec("pen_scribble", t_ent - 0.3, -12, trim=[0.0, 1.6], fade=0.3)
pop("sch", "st_a12_schlueter", t_sch, w("Bernsteindreher", 56.5) - 0.3, 1520, 520, 360, 3, out="right")
pop("fed", "st_s03_3_feder", t_ent - 0.5, w("Bernsteindreher", 56.5) - 0.3, 1290, 720, 150, -20, sound=None,
    extra=[{"t": t_ent, "x": 1250, "y": 700, "rot": -30}, {"t": t_ent + 0.4, "x": 1310, "y": 730, "rot": -10},
           {"t": t_ent + 0.8, "x": 1260, "y": 690, "rot": -30}])
lbl("lsch", "lbl_schlueter", w("Andreas", 54.4), w("Bernsteindreher", 56.5) - 0.3, 1520, 930, 460, 2)
t_dr = w("Bernsteindreher", 56.5)
pop("dre", "st_s03_1_bernsteindreher", t_dr - 0.1, w("Doch", 66.5) - 0.3, 1520, 560, 440, 2, out="right")
lbl("lwol", "lbl_wolfram", w("Gottfried", 57.8), w("Tausende", 60.0) + 1.5, 1520, 960, 480, 2)
rec("drill", w("geschliffen", 61.6) - 0.2, -24, trim=[0.0, 1.5], fade=0.5)
cap("cpz", "cap_puzzle", w("wie", 64.2), w("Doch", 66.5) - 0.2, 760, 980)
rec("amber_shimmer", t_pz + 1.3, -11)
t_sk = w("Doch", 66.5)
t_1716 = w("1716", 79.7)
# the finished room stays in Berlin until it is given away
s_b = sc("amber_panel", 300) / Z1b
Z2 = 0.62
C2 = cam(t_1716 - 0.2, ((BER[0] + STP[0]) / 2, (BER[1] + STP[1]) / 2 + 40), Z2, "inout")
t_gift = w("Bernsteinzimmer", 90.7) - 0.2
t_arr = w("revanchiert", 92.7) + 1.4
route = [(BER[0], by), (KOE[0], KOE[1] - 40 / Z1b), (STP[0], STP[1] - 40 / Z1b)]
s_b2 = sc("amber_panel", 150) / Z2 * 1.0
pk, pprog = path_keys(route, t_gift, t_arr, s_b2, bob=0.0)
hero_keys = [{"t": t_pz + 1.6, "x": BER[0], "y": by, "scale": s_b, "opacity": 0.0}, {"t": t_pz + 1.65, "opacity": 1.0},
             {"t": t_pz + 1.9, "scale": s_b * 1.08, "ease": "out"}, {"t": t_pz + 2.1, "scale": s_b},
             # "keine Kunst": the king turns away, the room sags
             {"t": w("keine", 74.2) + 0.2, "rot": 0, "y": by}, {"t": w("keine", 74.2) + 0.6, "rot": -8, "y": by + 14 / Z1b, "ease": "out"},
             {"t": t_1716 - 0.2, "rot": -8, "scale": s_b}, {"t": t_1716 + 1.0, "rot": 0, "scale": s_b2, "ease": "inout"},
             {"t": t_gift, "x": route[0][0], "y": route[0][1]}] + pk[1:]
hero_panel("hero1", t_pz + 1.6, END + 5, hero_keys)

# ======================================================================= Soldatenkönig: no art, soldiers
t_fw = w("Friedrich", 67.2)
pop("fw", "st_a3_soldatenkoenig", t_fw - 0.2, t_1716 - 0.4, 420, 600, 440, -2, out="left")
lbl("lfw", "lbl_fw", w("Wilhelm", 67.6), w("Soldatenkönig", 72.0) + 0.8, 420, 990, 520, 2)
lbl("lkk", "lbl_keinekunst", w("keine", 74.2), w("Soldaten", 75.7) - 0.1, 960, 860, 420, -3)
t_so = w("Soldaten", 75.7)
s_g = sc("st_s05_1_grenadier", 230)
S.image("gren", "st_s05_1_grenadier", t_so - 0.1, t_1716 - 0.1,
        pop_in(t_so - 0.1, 1460, 640, s_g, 2) + [
            {"t": w("besonders", 77.9), "scale": s_g, "y": 640},
            {"t": w("große", 78.6) + 0.4, "scale": s_g * 1.7, "y": 560, "ease": "out"},
            {"t": t_1716 - 0.35, "scale": s_g * 1.7, "opacity": 1.0}, {"t": t_1716 - 0.1, "scale": 0.0, "opacity": 0.0, "ease": "in"}])
rec("march", t_so, -14)
rec("suspense_hit", w("große", 78.6), -17)

# ======================================================================= 1716: alliance, the gift travels, giants march back
light("1715", "prussia", t_1716, w("In", 103.8) - 0.4)
light("1715", "brandenburg", t_1716, w("In", 103.8) - 0.4)
light("1715", "russia", w("Zar", 82.6) - 0.2, w("In", 103.8) - 0.4)
t_sw = w("Schweden", 86.1)
light("1715", "sweden", t_sw - 0.2, w("Und", 87.0) + 0.8, shake=True)
lbl("l1716", "lbl_1716", t_1716, w("Und", 87.0) - 0.3, 300, 140, 340, -3)
mcity("berlin", t_1716 + 0.2, w("In", 103.8) - 0.4, Z2)
mcity("st_petersburg", w("Zar", 82.6), END + 5, Z2)
sB, sP = scr(BER, C2, Z2), scr(STP, C2, Z2)
pop("fw2", "st_a3_soldatenkoenig", w("besucht", 81.3), w("In", 103.8) - 0.4, sB[0] - 230, sB[1] - 20, 300, -3, out="left")
pop("pe2", "st_a4_peter_der_grosse", w("Zar", 82.6) - 0.2, w("In", 103.8) - 0.4, sP[0] + 180, sP[1] + 250, 320, 3, out="right")
lbl("lpe", "lbl_peter", w("Peter", 82.7) + 0.3, w("Bündnis", 85.3) - 0.3, sP[0] + 180, sP[1] + 520, 400, 2)
# alliance: a line ties the two capitals, a handshake on it
mline(MAPL, "alli", [(BER[0], BER[1]), (STP[0], STP[1])], w("Bündnis", 85.3) - 0.3, w("Bündnis", 85.3) + 0.5, Z2,
      w("Und", 87.0) + 0.8, color=(246, 240, 226))
mid_s = ((sB[0] + sP[0]) / 2, (sB[1] + sP[1]) / 2)
pop("hs", "st_s04_2_handschlag", w("Bündnis", 85.3), w("Und", 87.0) + 0.3, mid_s[0], mid_s[1], 220, 0)
lbl("lbu", "lbl_buendnis", w("Bündnis", 85.3) + 0.2, w("Und", 87.0) + 0.3, mid_s[0], mid_s[1] + 170, 560, -2)
sS = scr(STO, C2, Z2)
pop("swe", "st_s05_4_schwede", t_sw, w("Und", 87.0) + 0.6, sS[0], sS[1] - 60, 140, -5, sound="cannon", gain=-15)
lbl("lgs", "lbl_geschenk", w("Geschenk", 89.5), t_arr - 0.6, sB[0] + 60, sB[1] + 160, 380, -3)
mline(MAPL, "giftline", route, t_gift, t_arr, Z2, w("schickt", 95.9), prog=pprog)
car = [(p[0], p[1] + 70 / Z2) for p in route]
ck, _ = path_keys(car, t_gift, t_arr, sc("st_s04_4_kutsche", 340) / Z2, bob=6 / Z2)
mimg(MAPL, "kut", "st_s04_4_kutsche", t_gift, t_arr + 0.6, ck + [{"t": t_arr + 0.2, "opacity": 1.0}, {"t": t_arr + 0.6, "opacity": 0.0}])
rec("horse_carriage", t_gift, -13)
t_gr = w("schickt", 95.9) - 0.3
for j in range(5):
    t0 = t_gr + 0.35 * j
    gk, gprog = path_keys([(STP[0], STP[1] + 40 / Z2), (KOE[0], KOE[1] + 40 / Z2), (BER[0] + 40 / Z2, BER[1] + 40 / Z2)],
                          t0, t0 + 4.2, sc("st_s05_1_grenadier", 64) / Z2, bob=6 / Z2, mirror=True)
    mimg(MAPL, f"gr{j}", "st_s05_1_grenadier", t0, w("In", 103.8) - 0.4, gk + [{"t": w("In", 103.8) - 0.8, "opacity": 1.0},
                                                                             {"t": w("In", 103.8) - 0.4, "opacity": 0.0}])
rec("march", t_gr, -13)
rec("march", t_gr + 3.6, -15)
lbl("l55", "lbl_55", w("55", 96.1), w("Genau", 100.8) - 0.3, 960, 140, 500, -2)
lbl("lgr", "lbl_gross", w("Alle", 98.8), w("In", 103.8) - 0.4, 960, 980, 500, 2)
# the king is delighted: he jumps
S.layers[[L_["id"] for L_ in S.layers].index("fw2")]["keys"] += [
    {"t": w("Genau", 100.8), "y": sB[1] - 20}, {"t": w("Genau", 100.8) + 0.18, "y": sB[1] - 90, "ease": "out"},
    {"t": w("Genau", 100.8) + 0.36, "y": sB[1] - 20, "ease": "in"}, {"t": w("Genau", 100.8) + 0.54, "y": sB[1] - 70, "ease": "out"},
    {"t": w("Genau", 100.8) + 0.72, "y": sB[1] - 20, "ease": "in"}]
S.layers[[L_["id"] for L_ in S.layers].index("fw2")]["keys"].sort(key=lambda q: q["t"])
rec("crowd_cheer", w("Genau", 100.8), -22, trim=[0.0, 2.0], fade=1.0)
cam(w("In", 103.8), STP, 1.4, "inout")

# ======================================================================= camera + layers
CAM.sort(key=lambda c: c[0])
held = [CAM[0]]
for a, b in zip(CAM, CAM[1:]):
    if b[0] - a[0] > 2.5:
        held.append((round(b[0] - 1.2, 3), a[1], a[2], a[3], "linear"))
    held.append(b)
cam_scale, cam_pan = fly_camera(held, END, center=(CX, CY))
flag_layers = []
for (year, key), k in FLAG_KEYS.items():
    k.sort(key=lambda q: q["t"])
    flag_layers.append({"id": f"flag_{year}_{key}", "type": "image", "asset": f"flag_{year}_{key}", "anchor": [0, 0],
                        "start": k[0]["t"], "end": k[-1]["t"], "keys": k})


def camgroup(id_, children):
    return {"id": id_, "type": "group", "pivot": [CX, CY], "keys": cam_scale, "children": [
        {"id": id_ + "_pan", "type": "group", "pivot": [0, 0], "keys": cam_pan, "children": children}]}


S.layers.insert(0, camgroup("cam", [{"id": "map", "type": "image", "asset": "map_europe", "anchor": [0, 0],
                                     "props": {"x": 0, "y": 0}, "keys": []}, *flag_layers, *MAPL]))
# hero group sits right above the dim layer and the earth section
earth_i = [L_["id"] for L_ in S.layers].index("cav")
S.layers.insert(earth_i + 1, camgroup("camh", HERO))
S.layers.append({"id": "page", "type": "multiply_image", "asset": "page", "keys": [{"t": 0, "opacity": 0.5}]})


def music(track, t0, t1, gain, off=0.0, fi=2.0, fo=3.0):
    S.audio.append({"src": f"audio/music/{track}.mp3", "start": round(t0, 3), "gain_db": gain,
                    "trim": [off, off + (t1 - t0)], "fade_in": fi, "fade_out": fo})


music("music_mystery", 0.0, t_ch1 + 1.5, -20)
music("music_barock", t_ch1 - 0.5, t_ch1 + 119.0, -21, fi=2.5, fo=2.5)

CEIL = {"default": -27.0, "paper_slide": -31.0, "paper_drop": -29.0, "suspense_hit": -24.0, "stamp": -25.0,
        "map_whoosh": -27.0, "amber_shimmer": -28.0, "march": -28.0, "horse_carriage": -27.0, "crowd_cheer": -30.0}


def _mmax(src, trim):
    import re
    import subprocess
    cmd = ["ffmpeg", "-nostats", "-nostdin"] + (["-ss", str(trim[0]), "-t", str(trim[1] - trim[0])] if trim else [])
    cmd += ["-i", os.path.join(PROJ, src), "-af", "apad=pad_dur=1,ebur128", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    vals = [float(v) for v in re.findall(r" M:\s*(-?[\d.]+)", err)]
    return max(vals) if vals else -70.0


_mm = {}
S.audio = [a_ for a_ in S.audio if a_["start"] < END]
for a_ in S.audio:
    if not a_["src"].startswith("audio/sfx_prepared/"):
        continue
    k_ = (a_["src"], str(a_.get("trim")))
    if k_ not in _mm:
        _mm[k_] = _mmax(a_["src"], a_.get("trim"))
    over = _mm[k_] + a_["gain_db"] - CEIL.get(os.path.basename(a_["src"])[:-4], CEIL["default"])
    if over > 0:
        a_["gain_db"] = round(a_["gain_db"] - over, 1)

assets = {n: {"path": f"build/assets/{n}.png", "license": "own"} for n, m in M.items() if isinstance(m, dict) and "w" in m}
timeline = {"meta": {"fps": 30, "width": W, "height": H, "design": [W, H], "duration": round(END, 3)},
            "assets": assets, "layers": S.layers,
            "audio": [{"id": "voice", "src": "audio/voice_komplett.mp3", "start": 0.0, "gain_db": 0.0}] + S.audio}
json.dump(timeline, open(os.path.join(HERE, "timeline.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("timeline ->", os.path.join(HERE, "timeline.json"), "| end", round(END, 2), "|", len(S.layers), "layers")
