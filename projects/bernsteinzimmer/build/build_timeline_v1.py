"""Timeline of the Bernsteinzimmer long video (16:9, ~10 min).

    python3 projects/bernsteinzimmer/build/build_timeline.py [--end SECONDS]

Two looks that hand over to each other:
  * MAP   – vintage Europe map, countries filled with the flag of their epoch, objects travel on it
  * STAGE – dark newspaper collage, a coloured paper shape, cut-outs that pop out of it, big serif sentences
Scenes are keyed to the spoken words (analysis/words.json).
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
CAM, MAP_EXTRA, STAGE = [], [], []


def w(word, approx):
    """start time of `word` at or after approx-1.5 s"""
    return S.w(word, approx - 1.5)


# ------------------------------------------------------------------ helpers
def cam(t, xy, s, ease="inout"):
    x, y = xy
    hw, hh = CX / s, CY / s
    x = MW / 2 if hw >= MW / 2 else min(max(x, hw), MW - hw)
    y = MH / 2 if hh >= MH / 2 else min(max(y, hh), MH - hh)
    CAM.append((round(t, 3), x, y, s, ease))


def stage(t0, t1):
    STAGE.append((t0, t1))
    rec("map_whoosh", t0, -12, peak=0.38)


def sc(asset, width):
    return S.scale_for(asset, width)


def pop(id_, asset, t0, t1, x, y, width, rot=0.0, sound="paper_drop", gain=-11.0, out="shrink", jitter=True):
    """cut-out pops in (back-out), holds, leaves (shrink | left | right | down | up)"""
    s = sc(asset, width)
    k = pop_in(t0, x, y, s, rot)
    k.append({"t": t1, "x": x, "y": y, "scale": s, "opacity": 1.0})
    if out == "shrink":
        k.append({"t": t1 + 0.22, "scale": s * 0.05, "opacity": 0.0, "ease": "in"})
    else:
        tx, ty = {"left": (-700, y), "right": (W + 700, y), "down": (x, H + 700), "up": (x, -700)}[out]
        k.append(exit_to(t1, tx, ty, 0.3))
    S.image(id_, asset, t0, t1 + 0.35, k, jitter=jitter)
    if sound:
        rec(sound, t0 + 0.05, gain)
    return k


def lbl(id_, asset, t0, t1, x, y, width, rot=-2.0, sound=None, gain=-9.0):
    pop(id_, asset, t0, t1, x, y, width, rot, sound=sound, gain=gain)


def cap(id_, asset, t0, t1, x, y, width=None):
    """big serif sentence: rises in, fades out"""
    s = sc(asset, width or M[asset]["w"])
    S.image(id_, asset, t0, t1 + 0.3, [
        {"t": t0, "x": x, "y": y + 40, "scale": s, "opacity": 0.0},
        {"t": t0 + 0.3, "y": y, "opacity": 1.0, "ease": "out3"},
        {"t": t1, "opacity": 1.0}, {"t": t1 + 0.3, "opacity": 0.0}], jitter=False)


def shape(id_, asset, t0, t1, x, y, width, rot=0.0, grow=None):
    """coloured paper shape / photo circle behind the cut-outs; grow=(t, width) enlarges it"""
    s = sc(asset, width)
    k = [{"t": t0, "x": x, "y": y, "scale": s * 0.1, "rot": rot - 10, "opacity": 0.0},
         {"t": t0 + 0.05, "opacity": 1.0},
         {"t": t0 + 0.32, "scale": s * 1.06, "rot": rot + 2, "ease": "out"},
         {"t": t0 + 0.48, "scale": s, "rot": rot, "ease": "inout"}]
    if grow:
        k += [{"t": grow[0], "scale": s}, {"t": grow[0] + 0.8, "scale": sc(asset, grow[1]), "ease": "inout"}]
        s = sc(asset, grow[1])
    k += [{"t": t1, "scale": s, "opacity": 1.0}, {"t": t1 + 0.25, "scale": s * 0.05, "opacity": 0.0, "ease": "in"}]
    S.image(id_, asset, t0, t1 + 0.3, k, jitter=False)
    rec("paper_slide", t0, -16, peak=0.42)


def mcity(key, t0, t1, z):
    a = "city_" + key
    s = 1.0 / z
    x, y = PL[key]
    MAP_EXTRA.append({"id": f"{a}_{int(t0 * 10)}", "type": "image", "asset": a, "start": t0, "end": t1 + 0.4,
                      "anchor": M[a]["anchor"],
                      "keys": [{"t": t0, "x": x, "y": y, "scale": 0.0, "opacity": 1.0},
                               {"t": t0 + 0.18, "scale": s * 1.15, "ease": "out"}, {"t": t0 + 0.32, "scale": s},
                               {"t": t1, "opacity": 1.0}, {"t": t1 + 0.4, "opacity": 0.0}]})


def flags(year, keys, t0, t1, fade=0.6, shake=None):
    """flag-filled countries of an epoch; shake={key: t} wiggles one country (it reacts)"""
    for key in keys:
        a = f"flag_{year}_{key}"
        x0, y0 = M[a]["pos"]
        k = [{"t": t0, "x": x0, "y": y0, "opacity": 0.0}, {"t": t0 + fade, "opacity": 1.0},
             {"t": t1 - fade, "opacity": 1.0}, {"t": t1, "opacity": 0.0}]
        if shake and key in shake:
            ts = shake[key]
            k += [{"t": ts, "x": x0}] + [{"t": ts + 0.07 * (j + 1), "x": x0 + (14 if j % 2 == 0 else -14)} for j in range(6)] \
                 + [{"t": ts + 0.5, "x": x0}]
            k.sort(key=lambda q: q["t"])
        MAP_EXTRA.append({"id": f"{a}_{int(t0)}", "type": "image", "asset": a, "start": t0, "end": t1,
                          "anchor": [0, 0], "keys": k})


def mtravel(id_, asset, pts, t0, t1, width_px, z, t_end=None, mirror=False, line=True, bob=True):
    """object travels along map points (screen width width_px at zoom z), leaves a dashed line"""
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    tot = sum(seg)
    s = sc(asset, width_px) / z
    keys, prog = [], []
    n = max(2, int((t1 - t0) * 12))
    for j in range(n + 1):
        f = j / n
        ff = f * f * (3 - 2 * f)
        d = ff * tot
        for (a, b), sl in zip(zip(pts, pts[1:]), seg):
            if d <= sl + 1e-9:
                u = d / sl if sl else 0
                break
            d -= sl
        x, y = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
        if bob:
            y -= abs(math.sin(j * 1.3)) * 10 / z
        k = {"t": round(t0 + (t1 - t0) * f, 3), "x": x, "y": y, "scale": s, "rot": 3 * math.sin(j * 1.3)}
        if mirror:
            k["sx"] = -1
        keys.append(k)
        prog.append({"t": k["t"], "progress": round(ff, 4)})
    te = t_end or t1 + 0.6
    keys += [{"t": te - 0.3, "opacity": 1.0}, {"t": te, "opacity": 0.0}]
    MAP_EXTRA.append({"id": id_, "type": "image", "asset": asset, "start": t0, "end": te,
                      "anchor": M[asset].get("anchor", [0.5, 0.5]), "keys": keys})
    if line:
        MAP_EXTRA.insert(0, {"id": id_ + "_line", "type": "dashed_path", "start": t0, "end": te,
                             "points": [list(p) for p in pts], "props": {"x": 0, "y": 0}, "width": 7 / z,
                             "dash": 20 / z, "gap": 13 / z, "color": [232, 112, 58],
                             "keys": prog + [{"t": te - 0.3, "opacity": 1.0}, {"t": te, "opacity": 0.0}]})


def radar_rings(prefix, xy, t0, t1, z, size=520, step=0.7):
    t, i = t0, 0
    s0 = sc("arc_orange", size) / z
    while t < t1:
        for r_ in (0, 120, 240):
            MAP_EXTRA.append({"id": f"{prefix}{i}_{r_}", "type": "image", "asset": "arc_orange", "start": t, "end": t + 1.4,
                              "keys": [{"t": t, "x": xy[0], "y": xy[1], "scale": s0 * 0.2, "rot": r_, "opacity": 1.0},
                                       {"t": t + 1.4, "scale": s0 * 1.3, "opacity": 0.0, "ease": "out"}]})
        t += step
        i += 1


def mid(a, b, f=0.5):
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)


BER, STP, KOE, DZI, ZAR = PL["berlin"], PL["st_petersburg"], PL["koenigsberg"], PL["dziemiany"], PL["zarskoje"]

# ======================================================================= KAPITEL 0 – Polen 2025
T_STAGE_A = w("Wonach", 16.3)
cam(0.0, mid(DZI, PL["warschau"], 0.3), 0.85, None)
cam(T_STAGE_A - 0.3, DZI, 1.6, "linear")
flags("2010", ["poland", "germany", "russia_k", "russia", "lithuania", "sweden", "denmark", "belarus", "latvia"], 0.0, T_STAGE_A + 0.2)
lbl("l2025", "lbl_2025", w("2025", 0.6), w("Er", 5.9) - 0.2, 330, 140, 460, -3)
mcity("dziemiany", w("Polen", 3.1), T_STAGE_A, 1.2)
pop("gen0", "st_s02_1_schreiben", w("Genehmigung", 4.7) - 0.2, w("Bodenradar", 9.8) - 0.4, 1450, 560, 440, 4)
lbl("lgen", "lbl_genehmigung", w("Genehmigung", 4.7), w("Bodenradar", 9.8) - 0.4, 1450, 900, 420, 2)
pop("ss0", "st_s01_1_absperrband", w("ehemaligen", 7.0) - 0.2, w("entdeckt", 12.1) - 0.3, 470, 580, 560, -3)
lbl("lss", "lbl_ss", w("SS", 8.0), w("entdeckt", 12.1) - 0.3, 470, 900, 560, -2)
pop("rad0", "st_s01_2_radar", w("Bodenradar", 9.8) - 0.1, T_STAGE_A - 0.2, 1480, 620, 400, -2)
lbl("lrad", "lbl_radar", w("Bodenradar", 9.8) + 0.2, w("großen", 13.3) - 0.2, 1480, 140, 420, 2)
rec("radar_beep", w("Bodenradar", 9.8), -12)
radar_rings("rr0_", DZI, w("Bodenradar", 9.8), T_STAGE_A, 1.4)
pop("lap0", "st_s01_3_laptop", w("entdeckt", 12.1) - 0.1, T_STAGE_A - 0.2, 760, 560, 680, 2)
lbl("lhohl", "lbl_hohlraum", w("Hohlraum", 13.8), T_STAGE_A - 0.2, 760, 920, 460, -3)
rec("suspense_hit", w("Hohlraum", 13.8), -15)
pop("dig0", "st_s01_4_schatzsucher", w("tief", 14.2) - 0.2, T_STAGE_A - 0.2, 1520, 420, 260, 3, sound="shovel", gain=-16)

# ======================================================================= STAGE A – ein ganzes Zimmer
T_CH1 = w("Geschichte", 41.0) - 0.15
stage(T_STAGE_A, T_CH1)
t_zim = w("Zimmer", 18.2)
shape("ca", "circ_amber", t_zim - 0.7, w("spurlos", 29.2) + 0.3, 960, 500, 820)
pop("room0", "st_a1_bernsteinzimmer_original", t_zim - 0.3, w("spurlos", 29.2) + 0.25, 960, 520, 980, -1, sound="amber_shimmer", gain=-14)
cap("cz", "cap_zimmer", w("Nach", 17.6), w("Einem", 19.0) + 0.2, 960, 980)
pop("amb0", "st_f01_2_bernstein_roh", w("sechs", 21.7) - 0.3, w("Und", 26.6) - 0.3, 1560, 800, 380, 6, sound="amber_shimmer", gain=-16)
lbl("l6t", "lbl_6t", w("sechs", 21.7), w("Und", 26.6) - 0.3, 960, 975, 640, -2)
pop("pyr0", "st_s08_1_pyramide", w("achte", 24.9) - 0.3, w("Und", 26.6) - 0.3, 330, 760, 420, -4)
cap("cw0", "cap_wunder", w("achte", 24.9) - 0.1, w("Und", 26.6) - 0.3, 960, 110)
lbl("l1945", "lbl_1945", w("1945", 27.0), w("Wie", 30.6) - 0.3, 1580, 180, 360, 3)
# the room flickers and vanishes on "spurlos verschwunden"
t_sp = w("spurlos", 29.2)
S.layers[[L_["id"] for L_ in S.layers].index("room0")]["keys"].append({"t": t_sp + 0.05, "opacity": 1.0})
for j, op in enumerate([0.2, 0.9, 0.1, 0.7, 0.0]):
    S.layers[[L_["id"] for L_ in S.layers].index("room0")]["keys"].append({"t": t_sp + 0.1 + 0.08 * j, "opacity": op})
S.layers[[L_["id"] for L_ in S.layers].index("room0")]["keys"].sort(key=lambda q: q["t"])
lbl("lspur", "lbl_spurlos", t_sp + 0.1, w("Wie", 30.6) - 0.3, 960, 540, 760, -2)
rec("radio_cutoff", t_sp + 0.1, -14, trim=[0.0, 1.2], fade=0.3)
pop("frm0", "st_f02_2_goldrahmen", w("Wie", 30.6) - 0.2, w("wo", 33.3) - 0.3, 960, 500, 860, 0, sound="paper_slide", gain=-14)
cap("cwie", "cap_wie", w("Wie", 30.6), w("wo", 33.3) - 0.3, 960, 960)
pop("map0", "st_s29_4_schatzkarte", w("wo", 33.3) - 0.1, T_CH1 - 0.3, 960, 540, 980, 2, sound="page_turn", gain=-12)
pop("komp0", "st_s29_3_kompass", w("heute", 34.2), T_CH1 - 0.3, 1600, 300, 300, 8)
S.image("lupe0", "st_s02_2_lupe", w("Das", 35.3), T_CH1, [
    {"t": w("Das", 35.3), "x": 2300, "y": 900, "scale": sc("st_s02_2_lupe", 420), "rot": -20},
    {"t": w("Das", 35.3) + 0.5, "x": 760, "y": 640, "ease": "out3"},
    {"t": w("Ende", 37.5), "x": 1150, "y": 520, "ease": "inout"},
    {"t": w("stimmt", 40.0), "x": 980, "y": 560, "ease": "inout"}, exit_to(T_CH1 - 0.35, 2300, 1100, 0.3)])

# ======================================================================= KAPITEL 1 – Berlin 1701
flags("1715", ["prussia", "brandenburg", "russia", "sweden", "poland"], T_CH1 - 0.5, END + 5, shake={"sweden": w("Schweden", 86.1)})
cam(T_CH1, mid(BER, STP, 0.45), 0.52, None)
cam(w("Berlin", 43.6) - 0.3, BER, 1.25, "inout")
lbl("l1701", "lbl_1701", w("1701", 42.0), w("einen", 49.3) - 0.5, 300, 140, 360, -3)
mcity("berlin", w("Berlin", 43.6), w("1716", 79.7) - 0.2, 1.25)
pop("ss1", "st_a11_stadtschloss_berlin", w("Berlin", 43.6), w("einen", 49.3) - 0.5, 1430, 520, 620, 2)
pop("fr1", "st_a2_friedrich_i", w("Friedrich", 45.6) - 0.2, w("einen", 49.3) - 0.5, 430, 600, 430, -2)
lbl("lfr1", "lbl_friedrich", w("Friedrich", 45.6) + 0.2, w("einen", 49.3) - 0.5, 430, 990, 380, 2)

# ======================================================================= STAGE B – Wände aus Bernstein, Schlüter, Wolfram, Puzzle
T_B = w("einen", 49.3) - 0.2
T_SK = w("Doch", 66.5) - 0.2
T_MAP2 = w("1716", 79.7) - 0.2
stage(T_B, T_MAP2)
shape("cb", "circ_amber2", T_B + 0.3, w("Tausende", 60.0) - 0.4, 960, 520, 720)
pop("plate1", "st_f01_1_bernsteinplatte", w("Wände", 50.8), w("Tausende", 60.0) - 0.4, 960, 520, 600, -2, sound="amber_shimmer", gain=-15)
shape("bp1", "blob_petrol", w("Bildhauer", 53.7) - 0.3, w("Tausende", 60.0) - 0.4, 330, 560, 540, 8)
pop("sch1", "st_a12_schlueter", w("Bildhauer", 53.7), w("Tausende", 60.0) - 0.4, 330, 560, 400, -3)
lbl("lsch", "lbl_schlueter", w("Andreas", 54.4), w("Tausende", 60.0) - 0.4, 330, 960, 480, -2)
shape("bo1", "blob_orange", w("Bernsteindreher", 56.5) - 0.3, w("Tausende", 60.0) - 0.4, 1590, 560, 560, -6)
pop("dre1", "st_s03_1_bernsteindreher", w("Bernsteindreher", 56.5), w("Tausende", 60.0) - 0.4, 1590, 560, 460, 2)
lbl("lwol", "lbl_wolfram", w("Gottfried", 57.8), w("Tausende", 60.0) - 0.4, 1590, 960, 500, 2)
# thousands of pieces -> they assemble into a panel
t_pz = w("Tausende", 60.0)
shape("cb2", "circ_amber", t_pz - 0.2, T_SK, 960, 520, 820)
pop("puz1", "st_f01_4_bernstein_puzzle", t_pz, w("zusammengesetzt", 63.0) + 0.3, 960, 520, 760, 0, sound="amber_shimmer", gain=-16)
pop("grind1", "st_f03_2_schleifen", w("poliert", 62.3) - 0.3, T_SK - 0.2, 1600, 760, 420, 4)
pop("plate2", "st_f01_1_bernsteinplatte", w("zusammengesetzt", 63.0) + 0.4, T_SK - 0.1, 960, 520, 640, 0, sound="amber_shimmer", gain=-13)
cap("cpz", "cap_puzzle", w("wie", 64.2), T_SK - 0.1, 960, 980)

# ======================================================================= STAGE C – der Soldatenkönig
shape("bp2", "blob_petrol", T_SK + 0.1, T_MAP2 - 0.3, 560, 560, 760, -4)
pop("fw1", "st_a3_soldatenkoenig", w("Friedrich", 67.2) - 0.2, T_MAP2 - 0.3, 560, 600, 560, -2)
lbl("lfw", "lbl_fw", w("Wilhelm", 67.6), w("Soldatenkönig", 72.0) - 0.2, 560, 990, 560, 2)
cap("csk", "cap_soldatenkoenig", w("Soldatenkönig", 72.0) - 0.4, w("Soldaten", 75.7) - 0.3, 1380, 140)
t_kk = w("keine", 74.2)
pop("plate3", "st_f01_1_bernsteinplatte", t_kk - 0.3, w("Soldaten", 75.7) - 0.2, 1400, 560, 420, 4)
S.image("tx3", "tape_x", t_kk + 0.35, w("Soldaten", 75.7) + 0.1, [
    {"t": t_kk + 0.35, "x": 1400, "y": 560, "scale": sc("tape_x", 520) * 1.5, "rot": -8, "opacity": 0.0},
    {"t": t_kk + 0.38, "opacity": 1.0}, {"t": t_kk + 0.47, "scale": sc("tape_x", 420), "ease": "out"},
    {"t": w("Soldaten", 75.7) - 0.2, "opacity": 1.0}, {"t": w("Soldaten", 75.7) + 0.05, "opacity": 0.0}])
rec("stamp", t_kk + 0.4, -10)
lbl("lkk", "lbl_keinekunst", t_kk, w("Soldaten", 75.7) - 0.2, 1400, 900, 440, -3)
t_so = w("Soldaten", 75.7)
s_g = sc("st_s05_1_grenadier", 280)
S.image("gren1", "st_s05_1_grenadier", t_so - 0.1, T_MAP2 - 0.1,
        pop_in(t_so - 0.1, 1400, 640, s_g, 2) + [
            {"t": w("besonders", 77.9), "scale": s_g, "y": 640},
            {"t": w("große", 78.6) + 0.4, "scale": s_g * 1.6, "y": 580, "ease": "out"},
            {"t": T_MAP2 - 0.35, "scale": s_g * 1.6, "opacity": 1.0}, {"t": T_MAP2 - 0.1, "scale": 0.0, "opacity": 0.0, "ease": "in"}])
rec("march", t_so, -14)
pop("drum1", "st_s05_3_trommel", t_so + 0.3, T_MAP2 - 0.35, 1760, 880, 220, 6, sound=None)
lbl("lsol", "lbl_soldaten", t_so + 0.1, w("besonders", 77.9) - 0.1, 1400, 150, 380, 3)
rec("suspense_hit", w("große", 78.6), -17)

# ======================================================================= KAPITEL 1b – 1716 Bündnis, Geschenk
cam(T_MAP2, mid(BER, STP, 0.5), 0.62, None)
lbl("l1716", "lbl_1716", w("1716", 79.7), w("Und", 87.0) - 0.3, 300, 140, 360, -3)
mcity("st_petersburg", w("Zar", 82.6), w("In", 103.8) - 0.2, 0.62)
mcity("berlin", w("1716", 79.7) - 0.1, w("In", 103.8) - 0.2, 0.62)
mcity("stockholm", w("Schweden", 86.1), w("Peter", 92.3), 0.62)
pop("fw2", "st_a3_soldatenkoenig", w("besucht", 81.3), w("Peter", 92.3) - 0.3, 330, 640, 360, -3, out="left")
pop("pe2", "st_a4_peter_der_grosse", w("Zar", 82.6) - 0.2, w("Peter", 92.3) - 0.3, 1600, 620, 420, 3, out="right")
lbl("lpe", "lbl_peter", w("Peter", 82.7) + 0.2, w("Bündnis", 85.3) - 0.3, 1600, 990, 460, 2)
pop("hs2", "st_s04_2_handschlag", w("schließen", 84.7) - 0.2, w("Und", 87.0) - 0.3, 960, 580, 420, 0)
lbl("lbu", "lbl_buendnis", w("Bündnis", 85.3), w("Und", 87.0) - 0.3, 960, 930, 620, -2)
pop("swe2", "st_s05_4_schwede", w("Schweden", 86.1) - 0.1, w("Und", 87.0) + 0.6, 960, 260, 220, -5, sound="cannon", gain=-14)
t_gs = w("Geschenk", 89.5)
pop("box2", "st_s04_3_geschenktruhe", t_gs - 0.4, w("Bernsteinzimmer", 90.7) + 0.4, 960, 560, 420, -3, sound="paper_drop")
lbl("lgs", "lbl_geschenk", t_gs, w("Bernsteinzimmer", 90.7) + 0.4, 960, 900, 460, -2)
mtravel("kut2", "st_s04_4_kutsche", [BER, KOE, STP], w("Bernsteinzimmer", 90.7) - 0.2, w("revanchiert", 92.7) + 1.2, 400, 0.62,
        t_end=w("Er", 95.7))
rec("horse_carriage", w("Bernsteinzimmer", 90.7) - 0.2, -14)

# 55 grenadiers march the other way
for j in range(5):
    t0 = w("schickt", 95.9) - 0.3 + 0.35 * j
    mtravel(f"gr3_{j}", "st_s05_1_grenadier", [STP, KOE, BER], t0, t0 + 4.2, 70, 0.62, t_end=w("Genau", 100.8) + 1.4,
            mirror=True, line=(j == 0))
rec("march", w("schickt", 95.9) - 0.3, -13)
rec("march", w("schickt", 95.9) + 3.5, -15)
lbl("l55", "lbl_55", w("55", 96.1), w("Genau", 100.8) - 0.3, 960, 140, 520, -2)
pop("riese3", "st_s05_2_riese_mensch", w("Alle", 98.8) - 0.1, w("In", 103.8) - 0.4, 1460, 620, 440, 2)
lbl("lgr", "lbl_gross", w("Alle", 98.8) + 0.2, w("In", 103.8) - 0.4, 1460, 990, 520, 2)
pop("fw3", "st_a3_soldatenkoenig", w("Genau", 100.8), w("In", 103.8) - 0.4, 440, 620, 380, -3, out="left")

# ======================================================================= KAPITEL 2 – Russland, Zarin Elisabeth, Katharinenpalast
T_RU = w("In", 103.8) - 0.2
cam(T_RU, STP, 1.5, "inout")
mcity("st_petersburg", T_RU + 0.6, END + 5, 1.5)
pop("box4", "st_s04_3_geschenktruhe", w("Bernsteinplatten", 105.0), w("Erst", 107.9) - 0.3, 1450, 640, 360, 12)
lbl("ljz", "lbl_jahrzehnte", w("jahrzehntelang", 106.3), w("Erst", 107.9) - 0.3, 1450, 940, 520, -3)
rec("clock_tick", w("jahrzehntelang", 106.3) - 0.3, -16)
pop("eli4", "st_a5_zarin_elisabeth", w("Zarin", 109.0) - 0.2, w("Ihr", 117.2) - 0.4, 430, 600, 470, -2)
lbl("leli", "lbl_elisabeth", w("Elisabeth", 109.4), w("Sommerpalast", 112.9) - 0.2, 430, 990, 470, 2)
lbl("l1755", "lbl_1755", w("1755", 110.6), w("Ihr", 117.2) - 0.4, 300, 140, 360, -3)
mcity("zarskoje", w("Katharinenpalast", 114.3), END + 5, 1.5)
pop("kp4", "st_a6_katharinenpalast", w("Sommerpalast", 112.9) - 0.1, w("Ihr", 117.2) - 0.4, 1380, 560, 760, 2, sound="palace_hall", gain=-15)
lbl("lkp", "lbl_katharinen", w("Katharinenpalast", 114.3), w("Ihr", 117.2) - 0.4, 1380, 930, 560, -2)

# ======================================================================= STAGE D – Rastrelli, Erweiterung, Weltwunder, Krieg
T_D = w("Ihr", 117.2) - 0.2
stage(T_D, END + 5)
shape("bo5", "blob_orange", T_D + 0.1, w("Also", 123.8) - 0.2, 500, 560, 700, 6)
pop("ras5", "st_a13_rastrelli", w("Architekt", 117.5), w("Also", 123.8) - 0.2, 500, 580, 460, -2)
lbl("lras", "lbl_rastrelli", w("Rastrelli", 118.1), w("Also", 123.8) - 0.2, 500, 980, 380, 2)
shape("ca5", "circ_amber", w("Problem", 119.2), w("Am", 130.5) - 0.3, 1400, 540, 460, grow=(w("größer", 121.4) - 0.3, 760))
cap("cgr", "cap_groesser", w("größer", 121.4), w("Also", 123.8) - 0.2, 1400, 110)
t_er = w("erweitert", 125.2)
S.image("bau5", "st_s08_3_bauarbeiter", t_er - 1.0, t_er + 4.8, [
    {"t": t_er - 1.0, "x": -300, "y": 780, "scale": sc("st_s08_3_bauarbeiter", 360), "rot": 0},
    {"t": t_er + 4.8, "x": 2250, "y": 780, "ease": "linear"}])
for j in range(18):
    S.layers[-1]["keys"].append({"t": t_er - 1.0 + j * 0.32, "rot": 4 if j % 2 else -4, "y": 770 if j % 2 else 790})
S.layers[-1]["keys"].sort(key=lambda q: q["t"])
pop("spi5", "st_s07_1_spiegel", w("Spiegeln", 126.2), w("Am", 130.5) - 0.3, 330, 470, 300, -4)
pop("put5", "st_s07_2_putte", w("vergoldeten", 126.7), w("Am", 130.5) - 0.3, 700, 330, 240, 5)
pop("amb5", "st_f01_2_bernstein_roh", w("Bernstein", 129.5) - 0.2, w("Am", 130.5) - 0.3, 760, 640, 300, -6, sound="amber_shimmer", gain=-16)
lbl("l55q", "lbl_55qm", w("55", 132.1) - 0.2, w("Verbaut", 134.4) - 0.2, 760, 540, 680, -3)
pop("arch5", "st_s08_4_architekt", w("Raum", 131.5) - 0.2, w("Verbaut", 134.4) - 0.2, 1450, 580, 420, 3)
lbl("l6t5", "lbl_6t", w("sechs", 135.5) - 0.3, w("Bei", 137.4) - 0.3, 960, 300, 800, 2)
pop("pile5", "st_f01_2_bernstein_roh", w("Verbaut", 134.4), w("Bei", 137.4) - 0.3, 960, 680, 620, 0, sound="amber_shimmer", gain=-15)
t_kz = w("Kerzenlicht", 137.6)
shape("ca6", "circ_amber2", t_kz - 0.3, w("Fast", 145.8) - 0.3, 960, 520, 900)
pop("saal6", "st_f04_1_saal_ecke", t_kz - 0.1, w("Fast", 145.8) - 0.3, 960, 520, 820, -1)
pop("kz6", "st_f02_1_kerzenleuchter", t_kz, w("Fast", 145.8) - 0.3, 330, 640, 330, -3, sound="candle", gain=-12)
S.flash("glow6", w("geleuchtet", 139.5), color=(250, 196, 90), peak=0.25)
cap("cgo", "cap_gold", w("wie", 140.7), w("Besucher", 142.3) - 0.2, 960, 980)
pop("bes6", "st_s07_3_besucher", w("Besucher", 142.3) - 0.1, w("Fast", 145.8) - 0.3, 1570, 720, 460, 3, sound="crowd_gasp", gain=-14)
cap("cw6", "cap_wunder", w("achte", 144.1) - 0.2, w("Fast", 145.8) - 0.3, 960, 980)
t_200 = w("Fast", 145.8)
pop("room7", "st_a1_bernsteinzimmer_original", t_200, END + 5, 960, 500, 980, 0, sound="clock_tick", gain=-15)
lbl("l200", "lbl_200", w("200", 146.0), w("Dann", 149.4) - 0.2, 960, 960, 560, -2)
t_kr = w("Dann", 149.4)
S.layers.append({"id": "drain7", "type": "grade", "start": t_kr, "end": END + 5,
                 "keys": [{"t": t_kr, "saturation": 1.0}, {"t": t_kr + 0.8, "saturation": 0.08}]})
cap("ckr", "cap_krieg", t_kr, END + 5, 960, 970)
rec("suspense_hit", t_kr + 0.6, -12)
rec("drone_dark", t_kr, -15, trim=[0.0, 6.0], fade=1.5)
rec("tank_rumble", w("Krieg", 150.5) + 0.3, -15)

# ======================================================================= camera, map, stage background
CAM.sort(key=lambda c: c[0])
held = [CAM[0]]
for a, b in zip(CAM, CAM[1:]):
    if b[0] - a[0] > 2.5:
        held.append((round(b[0] - 1.2, 3), a[1], a[2], a[3], "linear"))
    held.append(b)
cam_scale, cam_pan = fly_camera(held, END, center=(CX, CY))
S.layers.insert(0, {"id": "cam", "type": "group", "pivot": [CX, CY], "keys": cam_scale, "children": [
    {"id": "cam_pan", "type": "group", "pivot": [0, 0], "keys": cam_pan, "children": [
        {"id": "map", "type": "image", "asset": "map_europe", "anchor": [0, 0], "props": {"x": 0, "y": 0}, "keys": []},
        *MAP_EXTRA]}]})
# stage background: one layer, faded in/out per stage block (inserted right above the map)
sk = [{"t": 0.0, "opacity": 0.0}]
for t0, t1 in STAGE:
    sk += [{"t": t0 - 0.01, "opacity": 0.0}, {"t": t0 + 0.25, "opacity": 1.0},
           {"t": t1 - 0.25, "opacity": 1.0}, {"t": t1 + 0.01, "opacity": 0.0}]
S.layers.insert(1, {"id": "stage_bg", "type": "image", "asset": "stage_bg", "anchor": [0, 0],
                    "props": {"x": 0, "y": 0, "scale": 1.0}, "keys": sk})
S.layers.append({"id": "page", "type": "multiply_image", "asset": "page", "keys": [{"t": 0, "opacity": 0.55}]})


# ======================================================================= music + SFX ceiling
def music(track, t0, t1, gain, off=0.0, fi=2.0, fo=3.0):
    S.audio.append({"src": f"audio/music/{track}.mp3", "start": round(t0, 3), "gain_db": gain,
                    "trim": [off, off + (t1 - t0)], "fade_in": fi, "fade_out": fo})


music("music_mystery", 0.0, T_CH1 + 1.5, -20)
music("music_barock", T_CH1 - 0.5, min(T_CH1 + 119.0, w("Dann", 149.4) + 0.5), -21, fi=2.5, fo=2.5)
music("music_tension", w("Dann", 149.4), FULL_END, -23, off=0.0, fi=1.0)

CEIL = {"default": -27.0, "paper_slide": -31.0, "paper_drop": -29.0, "suspense_hit": -24.0, "stamp": -25.0,
        "map_whoosh": -27.0, "drone_dark": -29.0, "amber_shimmer": -28.0, "march": -28.0, "horse_carriage": -27.0}


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
