"""Builds timeline.json for the Amelia Earhart short (collage style).

    python3 projects/amelia-earhart/build/build_timeline.py

Uses build/assets/meta.json (from build_assets.py) and analysis/words.json
(word timings of the voice-over, shortsfactory.analysis.align).
Scenes are keyed to the spoken words, so a new voice take only needs a new
words.json.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
META = json.load(open(os.path.join(HERE, "assets", "meta.json")))
WORDS = json.load(open(os.path.join(PROJ, "analysis", "words.json"), encoding="utf-8"))
VOICE = "audio/voice_v5_elevenlabs.mp3"

JIT = {"pos": 1.6, "rot": 0.25, "fps": 12}
layers, audio = [], []


def w(text, after=0.0, which="start"):
    """Time of the first spoken word starting with `text` at/after `after`."""
    for x in WORDS:
        if x["start"] >= after - 1e-6 and x["text"].strip("„“\".,:;?!").lower().startswith(text.lower()):
            return x[which]
    raise KeyError(text)


def rec(name, t, gain=-8.0, trim=None, fade=None, peak=0.0):
    """Recorded effect from audio/sfx_prepared (ElevenLabs). `peak` = time of the
    loudest moment inside the (trimmed) sound, placed exactly on t."""
    a = {"src": f"audio/sfx_prepared/{name}.wav", "start": round(t - peak, 3), "gain_db": gain}
    if trim:
        a["trim"] = trim
    if fade:
        a["fade_out"] = fade
    audio.append(a)


def sfx(name, t, gain=-10.0):
    audio.append({"src": f"@sfx/{name}", "start": round(t, 3), "gain_db": gain})


def size_of(asset):
    return META[asset]["w"], META[asset]["h"]


def scale_for(asset, width):
    return width / META[asset]["w"]


def pop_in(t, x, y, s, rot=0.0, dur=0.28, from_scale=0.15):
    return [
        {"t": t, "x": x, "y": y, "scale": s * from_scale, "rot": rot - 6, "opacity": 0.0},
        {"t": t + 0.04, "opacity": 1.0},
        {"t": t + dur * 0.55, "scale": s * 1.08, "rot": rot + 1.5, "ease": "out"},
        {"t": t + dur, "scale": s, "rot": rot, "ease": "inout"},
    ]


def slide_in(t, x0, y0, x, y, s, rot0, rot, dur=0.35):
    return [
        {"t": t, "x": x0, "y": y0, "scale": s, "rot": rot0, "opacity": 1.0},
        {"t": t + dur, "x": x, "y": y, "rot": rot, "ease": "out3"},
    ]


def move(t, dur, ease="out3", **props):
    k = {"t": t + dur, "ease": ease}
    k.update(props)
    return [{"t": t, **{p: None for p in props}}, k]


def hold(keys, t, **props):
    """Insert a key at t holding the current values of the given props."""
    return keys


def exit_to(t, x, y, dur=0.3, rot=None, scale=None):
    k = {"t": t + dur, "x": x, "y": y, "ease": "in"}
    if rot is not None:
        k["rot"] = rot
    if scale is not None:
        k["scale"] = scale
    return k


def image(id_, asset, start, end, keys, anchor=None, jitter=True, **extra):
    L = {"id": id_, "type": "image", "asset": asset, "start": round(start, 3), "end": round(end, 3),
         "anchor": anchor or META[asset].get("anchor", [0.5, 0.5]), "keys": keys}
    if jitter:
        L["jitter"] = JIT
    L.update(extra)
    return L


def fix_keys(keys):
    """Fill None placeholders with the previous value of that prop."""
    last = {}
    out = []
    for k in sorted(keys, key=lambda k: k["t"]):
        k = dict(k)
        for p, v in list(k.items()):
            if v is None:
                if p in last:
                    k[p] = last[p]
                else:
                    del k[p]
        for p, v in k.items():
            if p not in ("t", "ease"):
                last[p] = v
        out.append(k)
    return out


# ---------------------------------------------------------------- word times
T_AMELIA = w("Amelia")
T_EARHART = w("Earhart")
T_DIE = w("Die")
T_BERUEHMT = w("berühmteste")
T_PILOTIN = w("Pilotin")
T_EINER = w("Einer")
T_FUNK = w("Funksprüche")
T_QUOTE = w("Wir")
T_NICHT = w("nicht", T_QUOTE)
T_KNAPP = w("knapp")
T_1937 = w("1937")
T_FLUG = w("Flug")
T_WELT2 = w("Welt", T_1937, "end")
T_ZIEL = w("Ziel")
T_HOWLAND = w("Howland")
T_ISLAND_END = w("Island", T_HOWLAND, "end")
TEST_END = T_ISLAND_END + 0.45

# ---------------------------------------------------------------- camera / map
mp = META["map_pacific"]
hx, hy = mp["howland"]
f0 = (mp["proj"]["lon_min"], mp["proj"]["lat_max"], mp["proj"]["ppd"])


def map_xy(lon, lat):
    lon_min, lat_max, ppd = f0
    if lon < lon_min:
        lon += 360
    return (lon - lon_min) * ppd, (lat_max - lat) * ppd


fx0, fy0 = map_xy(-175, 8)
T_ZOOM = T_WELT2 + 0.15
cam_scale = [
    {"t": 0.0, "scale": 1.0},
    {"t": T_1937 - 0.2, "scale": 1.12, "ease": "inout"},
    {"t": T_ZOOM, "scale": 1.06, "ease": "inout"},
    {"t": T_HOWLAND + 0.55, "scale": 3.4, "ease": "inout"},
    {"t": TEST_END + 3, "scale": 3.8, "ease": "linear"},
]
fx1, fy1 = map_xy(-168, 5)
cam_pan = [
    {"t": 0.0, "x": 540 - fx0, "y": 960 - fy0},
    {"t": T_1937 - 0.2, "x": 540 - fx1, "y": 960 - fy1, "ease": "inout"},
    {"t": T_ZOOM, "x": 540 - fx1, "y": 960 - fy1},
    {"t": T_HOWLAND + 0.55, "x": 540 - hx, "y": 960 - hy, "ease": "inout"},
]
layers.append({
    "id": "cam", "type": "group", "pivot": [540, 960], "keys": cam_scale,
    "children": [{
        "id": "cam_pan", "type": "group", "pivot": [0, 0], "keys": cam_pan,
        "children": [
            {"id": "map", "type": "image", "asset": "map_pacific", "anchor": [0, 0],
             "props": {"x": 0, "y": 0}, "keys": []},
            {"id": "dot", "type": "image", "asset": "dot", "start": T_ZIEL, "end": 999,
             "keys": [{"t": T_ZIEL, "x": hx, "y": hy, "scale": 0.0},
                      {"t": T_ZIEL + 0.15, "scale": 0.30, "ease": "out"},
                      {"t": T_ZIEL + 0.3, "scale": 0.22, "ease": "inout"}]},
        ]}],
})

# ---------------------------------------------------------------- scene 1: name + portrait
T_S1_OUT = T_EINER - 0.3
clouds = [
    image("cloud1", "st_cloud1", 0, T_1937 - 0.1, [
        {"t": 0, "x": 900, "y": 250, "scale": scale_for("st_cloud1", 360), "rot": 0},
        {"t": T_1937, "x": 760, "y": 240}], jitter=False),
    image("cloud2", "st_cloud2", 0, T_1937 - 0.1, [
        {"t": 0, "x": 120, "y": 760, "scale": scale_for("st_cloud2", 300), "rot": 0},
        {"t": T_1937, "x": 230, "y": 770}], jitter=False),
]
layers += clouds

burst_s = scale_for("burst_orange", 900)
layers.append(image("burst", "burst_orange", T_BERUEHMT, T_S1_OUT + 0.4, fix_keys([
    {"t": T_BERUEHMT, "x": 560, "y": 1000, "scale": 0.0, "rot": 0},
    {"t": T_BERUEHMT + 0.3, "scale": burst_s * 1.05, "ease": "back_out"},
    {"t": T_S1_OUT, "scale": burst_s * 1.12, "rot": 8},
    {"t": T_S1_OUT + 0.3, "scale": 0.0, "ease": "in"}]), jitter=False))
rec("map_whoosh", T_BERUEHMT, -14, peak=0.38)

ns = scale_for("newspaper", 430)
layers.append(image("newspaper", "newspaper", T_DIE, T_S1_OUT + 0.4, fix_keys(
    slide_in(T_DIE, -400, 1500, 230, 1330, ns, -25, 8) +
    [{"t": T_S1_OUT, "x": 230, "y": 1330}, exit_to(T_S1_OUT, -500, 1450, 0.3, rot=-10)])))
rec("paper_slide", T_DIE + 0.2, -6, peak=0.42)

ps = scale_for("st_portrait", 700)
portrait_keys = pop_in(T_AMELIA, 540, 1000, ps, rot=-2, dur=0.32) + [
    {"t": T_S1_OUT, "x": 545, "y": 990, "scale": ps * 1.03},
    {"t": T_S1_OUT + 0.4, "x": 260, "y": 560, "scale": ps * 0.52, "rot": -6, "ease": "out3"},
    {"t": T_1937 - 0.25, "x": 270, "y": 555},
    exit_to(T_1937 - 0.25, -400, 400, 0.3, rot=-20),
]
layers.append(image("portrait", "st_portrait", 0, T_1937 + 0.2, fix_keys(portrait_keys)))
rec("paper_drop", T_AMELIA + 0.1, -3)

for i, (lid, t, x, y, rot) in enumerate([("lbl_amelia", T_AMELIA + 0.05, 330, 330, -3),
                                          ("lbl_earhart", T_EARHART, 740, 360, 2)]):
    s = scale_for(lid, 470 if lid == "lbl_amelia" else 520)
    keys = pop_in(t, x, y, s, rot=rot, dur=0.26) + [
        {"t": T_S1_OUT, "x": x, "y": y}, exit_to(T_S1_OUT, x, -300, 0.3)]
    layers.append(image(lid, lid, t, T_S1_OUT + 0.35, fix_keys(keys)))
    rec("cardboard_hit", t + 0.08, -9 - 2 * i)

# plane crossing on "Pilotin" with an orange dashed trail
es = scale_for("st_electra", 560)
p0, p1 = (-420, 1780), (1520, 1560)
T_PL0, T_PL1 = T_PILOTIN - 0.15, T_PILOTIN + 1.6
ang = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
layers.append({"id": "trail1", "type": "dashed_path", "start": T_PL0, "end": T_EINER,
               "points": [[p0[0] - 900, p0[1] + (p0[1] - p1[1]) * 900 / (p1[0] - p0[0])], list(p0), list(p1)],
               "width": 9, "dash": 34, "gap": 22, "color": [232, 112, 58], "props": {"x": 0, "y": 0},
               "keys": [{"t": T_PL0, "progress": 0.24}, {"t": T_PL1, "progress": 0.93}]})
layers.append(image("electra1", "st_electra", T_PL0, T_PL1, [
    {"t": T_PL0, "x": p0[0], "y": p0[1], "scale": es, "rot": ang},
    {"t": T_PL1, "x": p1[0], "y": p1[1]}]))
rec("plane_flyby", T_PILOTIN + 0.7, -7, trim=[1.6, 5.4], fade=0.6, peak=3.59 - 1.6)

# ---------------------------------------------------------------- scene 2: radio + quote
T_RADIO = T_EINER
T_S2_OUT = T_1937 - 0.25
rs = scale_for("st_radio", 600)
radio_keys = pop_in(T_RADIO, 600, 1060, rs, rot=3, dur=0.3) + [
    {"t": T_KNAPP - 0.02, "x": 600, "rot": 3},
    {"t": T_KNAPP + 0.06, "x": 585, "rot": 0.5},
    {"t": T_KNAPP + 0.14, "x": 612, "rot": 4.5},
    {"t": T_KNAPP + 0.22, "x": 600, "rot": 3},
    {"t": T_S2_OUT, "x": 600, "y": 1060},
    exit_to(T_S2_OUT, 1500, 1200, 0.3, rot=25),
]
layers.append(image("radio", "st_radio", T_RADIO, T_S2_OUT + 0.35, fix_keys(radio_keys)))
rec("paper_drop", T_RADIO + 0.1, -4)
sfx("morse_beeps", T_RADIO + 0.35, -22)

# radio waves: arcs growing from the radio's top-right, stop on "nicht"
arc_s = scale_for("arc_orange", 520)
t = T_FUNK
i = 0
while t < T_NICHT:
    end = min(t + 1.2, T_NICHT + 0.15)
    layers.append(image(f"wave{i}", "arc_orange", t, end, [
        {"t": t, "x": 790, "y": 790, "scale": arc_s * 0.3, "rot": -50, "opacity": 1.0},
        {"t": t + 0.8, "opacity": 0.9},
        {"t": t + 1.2, "scale": arc_s * 1.4, "opacity": 0.0, "ease": "out"}], jitter=False))
    t += 0.4
    i += 1
sfx("radio_static", T_FUNK, -20)

# typewriter strip, one image per typed word
qn = META["quote_words"]
qs = scale_for("quote_01", 980)
qwords = [x for x in WORDS if T_QUOTE - 0.01 <= x["start"] <= T_KNAPP + 0.01]
assert len(qwords) == qn, (len(qwords), qn)
T_STRIP = T_QUOTE - 0.25
strip_keys = fix_keys(slide_in(T_STRIP, 1600, 1620, 540, 1620, qs, 10, -1.5, 0.28) + [
    {"t": T_S2_OUT, "x": 540, "y": 1620}, exit_to(T_S2_OUT, -700, 1700, 0.3, rot=-12)])
layers.append(image("strip_blank", "quote_00", T_STRIP, T_QUOTE, strip_keys))  # empty paper first
for k, wd in enumerate(qwords, 1):
    s0 = wd["start"]
    e0 = qwords[k]["start"] if k < qn else T_S2_OUT + 0.35
    layers.append(image(f"strip_{k:02d}", f"quote_{k:02d}", s0, e0, strip_keys))
    rec("typewriter_key", s0, -5)
rec("paper_slide", T_STRIP + 0.15, -8, peak=0.42)
rec("typewriter_bell", T_KNAPP + 0.3, -13)

# ---------------------------------------------------------------- scene 3: 1937 world flight
rec("paper_tear", T_S2_OUT, -9)
layers.append({"id": "dim", "type": "solid", "start": T_1937 - 0.3, "end": T_ZOOM + 0.4,
               "color": [20, 24, 22], "keys": [{"t": T_1937 - 0.3, "opacity": 0.0},
                                               {"t": T_1937, "opacity": 0.28},
                                               {"t": T_ZOOM, "opacity": 0.28},
                                               {"t": T_ZOOM + 0.35, "opacity": 0.0}]})
ls = scale_for("lbl_1937", 470)
layers.append(image("lbl_1937", "lbl_1937", T_1937, T_ZOOM + 0.35, fix_keys(
    pop_in(T_1937, 540, 560, ls, rot=-4, dur=0.3) + [
        {"t": T_ZOOM, "x": 540, "y": 560}, exit_to(T_ZOOM, 540, -300, 0.3)])))
rec("cardboard_hit", T_1937 + 0.08, -5)
rec("suspense_hit", T_1937 + 0.05, -10)

wc = META["world_card"]
cds = 1060 / wc["w"]
cw, ch = wc["w"] * cds, wc["h"] * cds
route = [[x * cds, y * cds] for x, y in wc["route"]]
T_CARD = T_1937 + 0.1
T_R0, T_R1 = T_1937 + 0.55, T_WELT2 - 0.05


def along(pts, frac):
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    tot = sum(seg)
    d = frac * tot
    for (a, b), s in zip(zip(pts, pts[1:]), seg):
        if d <= s or s == seg[-1]:
            f = d / s if s else 0
            return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f], math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        d -= s
    return pts[-1], 0.0


plane_keys = []
N = 40
prev_ang = None
for k in range(N + 1):
    f = k / N
    ff = 3 * f * f - 2 * f * f * f  # inout
    pos, a = along(route, ff)
    if prev_ang is not None:
        while a - prev_ang > 180:
            a -= 360
        while a - prev_ang < -180:
            a += 360
    a = a if prev_ang is None else prev_ang * 0.6 + a * 0.4
    prev_ang = a
    plane_keys.append({"t": round(T_R0 + (T_R1 - T_R0) * f, 3), "x": pos[0], "y": pos[1], "rot": a})
plane_keys[0]["scale"] = scale_for("st_electra", 110)
layers.append({
    "id": "card", "type": "group", "pivot": [cw / 2, ch / 2], "start": T_CARD, "end": T_ZOOM + 0.4,
    "keys": fix_keys(slide_in(T_CARD, 540, 2300, 540, 1080, 1.0, 8, -2, 0.38) + [
        {"t": T_ZOOM, "x": 540, "y": 1080}, exit_to(T_ZOOM, 540, 2400, 0.35, rot=6)]),
    "jitter": JIT,
    "children": [
        {"id": "card_img", "type": "image", "asset": "world_card", "anchor": [0, 0],
         "props": {"x": 0, "y": 0, "scale": cds}, "keys": []},
        {"id": "route", "type": "dashed_path", "points": route, "props": {"x": 0, "y": 0}, "width": 6, "dash": 14, "gap": 9,
         "color": [232, 112, 58], "keys": [{"t": T_R0, "progress": 0.0},
                                           {"t": T_R1, "progress": 1.0, "ease": "inout"}]},
        {"id": "electra2", "type": "image", "asset": "st_electra", "start": T_R0 - 0.1,
         "anchor": META["st_electra"]["anchor"], "keys": plane_keys},
    ]})
rec("paper_drop", T_CARD + 0.35, -6)
rec("pen_scribble", T_R0, -11, trim=[0.0, T_R1 - T_R0 + 0.2], fade=0.3)
rec("plane_distant", T_R0, -17, trim=[0.0, T_R1 - T_R0 + 0.5], fade=0.5)

# ---------------------------------------------------------------- scene 4: Howland zoom
rec("map_whoosh", T_ZOOM + 0.5, -4, peak=0.38)
rec("ocean_wind", T_ZOOM, -22, trim=[0.0, 12.0], fade=1.0)
rec("cardboard_hit", T_ZIEL + 0.08, -16)
hs = scale_for("lbl_howland", 640)
layers.append(image("lbl_howland", "lbl_howland", T_HOWLAND, TEST_END + 5,
                    pop_in(T_HOWLAND, 540, 600, hs, rot=-2, dur=0.28)))
rec("cardboard_hit", T_HOWLAND + 0.08, -8)
mg = META["st_magnifier"]
f_, ox, oy = mg["src_map"]
lens = mg["lens"]   # glass centre in the sticker (build_assets.glass_window)
mgs = scale_for("st_magnifier", 620)
T_MAG = T_HOWLAND + 0.2
layers.append(image("magnifier", "st_magnifier", T_MAG, TEST_END + 5, fix_keys(
    slide_in(T_MAG, 1300, 1700, 540, 960, mgs, -35, -12, 0.42)), anchor=list(lens)))
rec("paper_slide", T_MAG + 0.2, -8, peak=0.42)

# ---------------------------------------------------------------- page texture on top
layers.append({"id": "page", "type": "multiply_image", "asset": "page", "keys": []})

# ---------------------------------------------------------------- captions
HIDE = [(0.0, T_EARHART + 0.6), (T_QUOTE - 0.05, T_KNAPP + 0.5), (T_1937 - 0.05, T_1937 + 1.2),
        (T_HOWLAND - 0.05, T_ISLAND_END + 0.1)]
BIG = {"berühmteste", "nicht.", "gps.", "nichts.", "skelett.", "mann.", "verschwunden.", "knapp."}
caps = []
for i, x in enumerate(WORDS):
    if any(a <= x["start"] < b for a, b in HIDE):
        continue
    nxt = WORDS[i + 1]["start"] if i + 1 < len(WORDS) else x["end"] + 0.3
    txt = x["text"].replace("„", "").replace("“", "").replace('"', "")
    c = {"text": txt, "start": x["start"], "end": round(min(nxt, x["end"] + 0.25), 3)}
    if txt.lower() in BIG:
        c["size"] = "big"
    caps.append(c)

assets = {}
for name, m in META.items():
    if isinstance(m, dict) and "w" in m:
        a = {"path": f"build/assets/{name}.png", "license": "own"}
        if name.startswith("st_"):
            a["license"] = "user_supplied_cutout (Quelle/Lizenz der Originalfotos vor Veröffentlichung prüfen)"
        assets[name] = a

timeline = {
    "meta": {"fps": 30, "width": 1080, "height": 1920, "duration": 64.76, "test_end": round(TEST_END, 3)},
    "assets": assets,
    "layers": layers,
    "captions": {"style": {"font": "league-spartan-800", "size": 66, "sizes": {"big": 92}, "y": 1450,
                           "stroke_w": 3.0}, "words": caps},
    "audio": [{"id": "voice", "src": VOICE, "start": 0.0, "gain_db": 0.0}] + audio,
}
out = os.path.join(PROJ, "build", "timeline.json")
json.dump(timeline, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("timeline ->", out, "| test end", round(TEST_END, 2), "s |", len(layers), "layers")
