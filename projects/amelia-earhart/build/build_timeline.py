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
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(PROJ)))
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
    if name == "paper_slide":
        gain -= 9.0          # user feedback: slide sound too loud
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
nx, ny = mp["nikumaroro"]
# word times for the rest of the video
T_EINE = w("Eine", T_ISLAND_END)
T_FLACH = w("flach")
T_PFANN = w("Pfannkuchen")
T_MITTEN = w("mitten")
T_PAZ_END = w("Pazifik", T_MITTEN, "end")
T_OHNE = w("Ohne")
T_GPS = w("GPS")
T_NUR = w("Nur")
T_KOMPASS = w("Kompass")
T_UHR = w("Uhr")
T_SEXTANT = w("Sextant")
T_STERNE = w("Sterne")
T_STERNE_END = w("Sterne", T_STERNE, "end")
T_SCHIFF = w("Schiff")
T_FUNKT = w("funkt")
T_DOCH = w("Doch")
T_AMELIA2 = w("Amelia", T_DOCH)
T_NICHT2 = w("nicht", T_DOCH)
T_DANN = w("Dann")
T_BRICHT = w("bricht")
T_AB_END = w("ab", T_BRICHT, "end")
T_NAVY = w("Navy")
T_ZWEI = w("zwei")
T_TRAEGER = w("Flugzeugträger")
T_SCHLACHT = w("Schlachtschiff")
T_KEIN1 = w("Kein", T_SCHLACHT)
T_KEIN2 = w("Kein", T_KEIN1 + 0.1)
T_NICHTS = w("Nichts")
T_DREI = w("Drei")
T_EINSAM = w("einsamen")
T_SKELETT = w("Skelett")
T_DANEBEN = w("Daneben")
T_SCHUH = w("Frauenschuh")
T_LEERE = w("leere")
T_KISTE = w("Sextanten-Kiste")
T_KISTE_END = w("Sextanten-Kiste", T_KISTE, "end")
T_ARZT = w("Arzt")
T_EINDEUTIG = w("eindeutig")
T_MANN = w("Mann")
T_FALL = w("Fall")
T_ERLEDIGT_END = w("erledigt", T_FALL, "end")
T_BIS = w("Bis")
T_2018 = w("2018")
T_FORSCHER = w("Forscher")
T_KNOCHEN1 = w("Knochen")
T_PASSEN = w("passen")
T_AMELIA3 = w("Amelia", T_PASSEN)
T_ALSO = w("Also")
T_UNTERS = w("untersuchen")
T_GEHT = w("Geht")
T_KNOCHEN2 = w("Knochen", T_GEHT)
T_VERSCHW = w("verschwunden")
T_GENAU = w("Genau")
END = 64.76
TEST_END = END


from shortsfactory.render.keyframes import ease as _ease  # noqa: E402

BASE_PPD = mp["proj"]["ppd"]
lx, ly = map_xy(147.0, -6.7)   # Lae


def S(ppd):
    """camera zoom that shows the map at `ppd` design px per degree"""
    return ppd / BASE_PPD


S_HOW = S(7000)
S_NIK = S(10000)
# ---- the 1937 flight on the big map: route Oakland -> ... -> Lae -> (towards) Howland
ROUTE = [tuple(p) for p in mp["route"]]
LAE_I = mp["route_lae_index"]
seg_len = [math.dist(a, b) for a, b in zip(ROUTE, ROUTE[1:])]
L_ALL = sum(seg_len)
L_LAE = sum(seg_len[:LAE_I])
STOP = (L_LAE + 0.97 * seg_len[LAE_I]) / L_ALL       # plane stops just short of Howland
ROUTE_DRAWN = [list(p) for p in ROUTE]
T_R0 = T_1937 + 0.3
T_LEG1 = T_EINE - 0.1


def route_point(frac):
    d = frac * L_ALL
    for (a, b), sl in zip(zip(ROUTE, ROUTE[1:]), seg_len):
        if d <= sl:
            f = d / sl if sl else 0
            return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        d -= sl
    a, b = ROUTE[-2], ROUTE[-1]
    return b, math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def route_frac(t):
    u = min(1.0, max(0.0, (t - T_R0) / (T_LEG1 - T_R0)))
    return STOP * (u * u * (3 - 2 * u))


T_LAE = next(T_R0 + k * 0.01 for k in range(2000) if route_frac(T_R0 + k * 0.01) >= L_LAE / L_ALL)
route_keys, plane_route_keys = [], []
prev = None
n_steps = int((T_LEG1 - T_R0) * 15)
for k in range(n_steps + 1):
    t = T_R0 + (T_LEG1 - T_R0) * k / n_steps
    fr = route_frac(t)
    (px_, py_), ang = route_point(fr)
    if prev is not None:
        while ang - prev > 180:
            ang -= 360
        while ang - prev < -180:
            ang += 360
        ang = prev * 0.7 + ang * 0.3
    prev = ang
    route_keys.append({"t": round(t, 3), "progress": round(fr, 5)})
    plane_route_keys.append({"t": round(t, 3), "x": px_, "y": py_, "rot": ang})
plane_route_keys[0]["scale"] = scale_for("st_electra", 210)

S_FLY = 0.58
FOLLOW = []
for k in range(int((T_LEG1 - T_R0) * 10) + 1):
    t = T_R0 + k / 10
    (px_, py_), _ = route_point(route_frac(t + 0.25))
    s_ = S_FLY if t < T_LAE else S_FLY + (1.06 - S_FLY) * min(1, (t - T_LAE) / (T_LEG1 - T_LAE))
    half = 960 / s_
    py_ = min(max(py_, half), mp["proj"]["h"] - half)
    px_ = min(max(px_, 540 / s_), mp["proj"]["w"] - 540 / s_)
    FOLLOW.append((t, px_, py_, s_, "inout" if k == 0 else "linear"))

CAM = [  # (t, focus x, focus y in overview-map px, zoom, ease)
    (0.0, fx0, fy0, 1.0, None),
    (T_1937 - 0.25, *map_xy(-168, 5), 1.12, "inout"),
    *FOLLOW,
    (T_FLACH - 0.05, hx, hy, S(24000), "inout"),          # dive onto the real island (from the plane)
    (T_MITTEN, hx, hy, S(26000), "linear"),
    (T_PAZ_END, *map_xy(-172, 2), 0.95, "inout"),        # back out: "mitten im Pazifik"
    (T_SCHIFF - 0.3, *map_xy(-172, 3), 1.02, "linear"),
    (T_SCHIFF + 0.6, hx + 250 / S_HOW, hy + 380 / S_HOW, S_HOW, "inout"),  # island upper left of the ship
    (T_AB_END, hx + 250 / (S_HOW * 1.1), hy + 380 / (S_HOW * 1.1), S_HOW * 1.1, "linear"),
    (T_NAVY + 0.4, hx, hy + 60, 1.35, "inout"),
    (T_NICHTS, hx, hy + 60, 1.45, "linear"),
    (T_DREI + 0.2, hx, hy + 60, 1.45, "linear"),
    (T_EINSAM - 0.1, (hx + nx) / 2, (hy + ny) / 2 + 40, 1.7, "inout"),
    (T_SKELETT - 0.3, nx, ny + 140 / S_NIK, S_NIK, "inout"),  # dive onto Nikumaroro
    (T_BIS, nx, ny + 140 / (S_NIK * 1.06), S_NIK * 1.06, "linear"),
    (T_VERSCHW, nx, ny + 140 / (S_NIK * 1.12), S_NIK * 1.12, "linear"),
    (END, fx0, fy0, 1.0, "inout"),                        # back to the opening view (loop)
]


def cam_at(t):
    """Zoom geometric, pan weighted by 1/zoom (screen-uniform 'fly-to')."""
    if t <= CAM[0][0]:
        return CAM[0][1:4]
    for a, b in zip(CAM, CAM[1:]):
        if a[0] <= t <= b[0]:
            e = _ease(b[4] or "linear", (t - a[0]) / max(1e-6, b[0] - a[0]))
            s0, s1 = a[3], b[3]
            s_ = math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * e)
            wgt = e if abs(s1 - s0) < 1e-9 else (1 / s0 - 1 / s_) / (1 / s0 - 1 / s1)
            return a[1] + (b[1] - a[1]) * wgt, a[2] + (b[2] - a[2]) * wgt, s_
    return CAM[-1][1:4]


FPS = 30
cam_scale, cam_pan, P_OF = [], [], []
for n in range(int(END * FPS) + 2):
    t = n / FPS
    x, y, s_ = cam_at(t)
    cam_scale.append({"t": round(t, 4), "scale": s_})
    cam_pan.append({"t": round(t, 4), "x": 540 - x, "y": 960 - y})
    P_OF.append((t, s_ * BASE_PPD))


def zoom_fade(p_in0, p_in1, p_out0=None, p_out1=None, prop="opacity"):
    """Opacity keys from the camera's map scale P (design px/deg): fade in between
    p_in0..p_in1 and out between p_out0..p_out1 (log-smooth)."""
    def f(P):
        v = 1.0
        if p_in0 is not None:
            v *= min(1, max(0, (math.log(P) - math.log(p_in0)) / (math.log(p_in1) - math.log(p_in0))))
        if p_out0 is not None:
            v *= 1 - min(1, max(0, (math.log(P) - math.log(p_out0)) / (math.log(p_out1) - math.log(p_out0))))
        return v * v * (3 - 2 * v)
    keys, last = [], None
    for t, P in P_OF:
        v = round(f(P), 3)
        if v != last:
            if last is not None and keys and keys[-1]["t"] < t - 1 / FPS - 1e-6:
                keys.append({"t": round(t - 1 / FPS, 4), prop: last})
            keys.append({"t": round(t, 4), prop: v})
            last = v
    return keys


tiles = []
for name in ("tile_mid", "tile_h1", "tile_n1", "tile_h2", "tile_n2", "tile_h25", "tile_h3", "tile_n3"):
    tm = META[name]
    T = tm["ppd"]
    # fade a tile in only once it covers the whole frame (no visible tile edges)
    cover = T * 1920 / (tm["h"] * 0.72)
    tiles.append({"id": name, "type": "image", "asset": name, "anchor": [0, 0],
                  "props": {"x": tm["pos"][0], "y": tm["pos"][1], "scale": tm["design_scale"]},
                  "keys": zoom_fade(cover, cover * 1.3)})
MAP_ONLY = zoom_fade(None, None, 45, 90)   # map-space graphics vanish when we dive
layers.append({
    "id": "cam", "type": "group", "pivot": [540, 960], "keys": cam_scale,
    "children": [{
        "id": "cam_pan", "type": "group", "pivot": [0, 0], "keys": cam_pan,
        "children": [
            {"id": "map", "type": "image", "asset": "map_pacific", "anchor": [0, 0],
             "props": {"x": 0, "y": 0}, "keys": []},
            *tiles,
            {"id": "dot2", "type": "image", "asset": "dot", "start": T_EINSAM - 0.6, "end": 999,
             "props": {"x": nx, "y": ny, "scale": 0.17}, "keys": MAP_ONLY},
            {"id": "dot", "type": "image", "asset": "dot", "start": T_ZIEL, "end": 999,
             "props": {"x": hx, "y": hy, "scale": 0.22}, "keys": MAP_ONLY},
        ]}],
})
MAP_CHILDREN = layers[-1]["children"][0]["children"]

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
ls = scale_for("lbl_1937", 470)
layers.append(image("lbl_1937", "lbl_1937", T_1937, T_ZOOM + 0.35, fix_keys(
    pop_in(T_1937, 540, 1240, ls, rot=-4, dur=0.3) + [
        {"t": T_ZOOM, "x": 540, "y": 1240}, exit_to(T_ZOOM, 540, 2300, 0.3)])))
rec("cardboard_hit", T_1937 + 0.08, -5)
rec("suspense_hit", T_1937 + 0.05, -10)
# the flight itself is drawn on the big map (route + plane, camera follows): see FLIGHT above
rec("pen_scribble", T_R0, -12, trim=[0.0, 3.8], fade=0.4)
rec("plane_distant", T_R0, -14, trim=[0.0, T_LEG1 - T_R0 + 0.6], fade=0.8)
route_keys += [dict(k) for k in MAP_ONLY if k["t"] > T_LEG1]
plane_route_keys += [dict(k) for k in MAP_ONLY if k["t"] > T_LEG1]
MAP_CHILDREN.append({"id": "route", "type": "dashed_path", "start": T_R0, "end": T_FLACH,
                     "points": ROUTE_DRAWN, "props": {"x": 0, "y": 0}, "width": 6, "dash": 18, "gap": 12,
                     "color": [232, 112, 58], "keys": route_keys})
MAP_CHILDREN.append({"id": "electra_route", "type": "image", "asset": "st_electra", "start": T_R0,
                     "end": T_FLACH, "anchor": META["st_electra"]["anchor"], "keys": plane_route_keys})

# ---------------------------------------------------------------- scene 4: last leg Lae -> Howland, dive onto the island
rec("ocean_wind", T_ZOOM, -22, trim=[0.0, 12.0], fade=1.0)
km4 = scale_for("lbl_4000km", 420)
layers.append(image("lbl_4000", "lbl_4000km", T_LAE + 0.1, T_HOWLAND, fix_keys(
    pop_in(T_LAE + 0.1, 540, 1230, km4, rot=3, dur=0.26) + [
        {"t": T_HOWLAND - 0.35, "x": 540, "y": 1230}, exit_to(T_HOWLAND - 0.35, 540, 2300, 0.3)])))
rec("cardboard_hit", T_LAE + 0.18, -10)
hs = scale_for("lbl_howland", 640)
layers.append(image("lbl_howland", "lbl_howland", T_HOWLAND, T_PAZ_END + 0.4, fix_keys(
    pop_in(T_HOWLAND, 540, 420, hs, rot=-2, dur=0.28) + [
        {"t": T_MITTEN, "x": 540, "y": 420}, exit_to(T_MITTEN, 540, -250, 0.35)])))
rec("cardboard_hit", T_HOWLAND + 0.08, -8)
rec("map_whoosh", T_EINE + 0.6, -3, peak=0.38)
rec("map_whoosh", T_EINE + 1.2, -9, peak=0.38)
mg = META["st_magnifier"]
lens = mg["lens"]   # glass centre in the sticker (build_assets.glass_window)
mgs = scale_for("st_magnifier", 620)
# scale bar next to the real island (2.5 km)
isl_h = 0.0212 * BASE_PPD * S(24000)          # island height on screen at the dive's end
layers.append({"id": "scalebar", "type": "dashed_path", "start": T_FLACH - 0.1, "end": T_MITTEN + 0.3,
               "points": [[700, 960 - isl_h / 2], [700, 960 + isl_h / 2]], "props": {"x": 0, "y": 0},
               "width": 6, "dash": 16, "gap": 10, "color": [246, 240, 226],
               "keys": [{"t": T_FLACH - 0.1, "progress": 0.0, "opacity": 1.0},
                        {"t": T_FLACH + 0.25, "progress": 1.0, "ease": "out"},
                        {"t": T_MITTEN, "opacity": 1.0}, {"t": T_MITTEN + 0.25, "opacity": 0.0}]})
k25 = scale_for("lbl_25km", 300)
layers.append(image("lbl_25km", "lbl_25km", T_FLACH + 0.1, T_MITTEN + 0.35, fix_keys(
    pop_in(T_FLACH + 0.1, 870, 960, k25, rot=-3, dur=0.25) + [
        {"t": T_MITTEN, "x": 870, "y": 960}, exit_to(T_MITTEN, 1500, 960, 0.3)])))
rec("cardboard_hit", T_FLACH + 0.18, -11)


# ---------------------------------------------------------------- scene 5: pancake, pull back
pk = scale_for("st_pancake", 520)
layers.append(image("pancake", "st_pancake", T_PFANN - 0.25, T_PAZ_END + 0.3, fix_keys([
    {"t": T_PFANN - 0.25, "x": 800, "y": 1270, "scale": 0.0, "sx": 1.0, "sy": 1.0, "rot": -4},
    {"t": T_PFANN - 0.07, "scale": pk * 0.75, "ease": "back_out"},
    {"t": T_PFANN - 0.05, "sy": 1.0, "sx": 1.0},
    {"t": T_PFANN + 0.1, "sy": 0.45, "sx": 1.25, "ease": "out"},
    {"t": T_PFANN + 0.35, "sy": 0.62, "sx": 1.15, "ease": "inout"},
    {"t": T_MITTEN, "scale": pk * 0.7},
    {"t": T_MITTEN + 0.45, "scale": 0.0, "ease": "in"}])))
rec("paper_drop", T_PFANN - 0.15, -6)
rec("cardboard_hit", T_PFANN + 0.1, -9)
rec("map_whoosh", T_MITTEN + 0.35, -5, peak=0.38)
sts = scale_for("lbl_stiller", 640)
layers.append(image("lbl_stiller", "lbl_stiller", T_MITTEN + 0.45, T_OHNE + 0.1, fix_keys(
    pop_in(T_MITTEN + 0.45, 540, 700, sts, rot=-3, dur=0.28) + [
        {"t": T_OHNE - 0.2, "x": 540, "y": 700}, exit_to(T_OHNE - 0.2, 540, -300, 0.3)])))
rec("cardboard_hit", T_MITTEN + 0.53, -9)

# ---------------------------------------------------------------- scene 6: no GPS, compass, watch, sextant, stars
phs = scale_for("st_phone", 520)
layers.append(image("phone", "st_phone", T_OHNE, T_NUR + 0.4, fix_keys(
    pop_in(T_OHNE, 540, 980, phs, rot=6, dur=0.28) + [
        {"t": T_NUR - 0.05, "x": 540, "y": 980}, exit_to(T_NUR - 0.05, 560, 2300, 0.3, rot=25)])))
rec("paper_drop", T_OHNE + 0.1, -5)
txs = scale_for("tape_x", 620)
layers.append(image("tape_x1", "tape_x", T_GPS, T_NUR + 0.4, fix_keys([
    {"t": T_GPS, "x": 540, "y": 980, "scale": txs * 1.6, "rot": -8, "opacity": 0.0},
    {"t": T_GPS + 0.03, "opacity": 1.0},
    {"t": T_GPS + 0.12, "scale": txs, "ease": "out"},
    {"t": T_NUR - 0.05, "x": 540, "y": 980}, exit_to(T_NUR - 0.05, 560, 2300, 0.3, rot=10)])))
rec("paper_tear", T_GPS + 0.05, -8)
for i, (aid, t, x, y, wdt, rot) in enumerate([("st_compass", T_KOMPASS, 290, 820, 400, -8),
                                              ("st_watch", T_UHR, 800, 860, 360, 7),
                                              ("st_sextant", T_SEXTANT, 560, 1220, 600, -3)]):
    sc = scale_for(aid, wdt)
    layers.append(image(f"nav{i}", aid, t, T_STERNE_END + 0.6, fix_keys(
        pop_in(t, x, y, sc, rot=rot, dur=0.28) + [
            {"t": T_STERNE_END + 0.1, "x": x, "y": y}, exit_to(T_STERNE_END + 0.1, x, -400 if y < 1000 else 2400, 0.3)])))
    rec("paper_drop", t + 0.1, -6 - i)
st_s = scale_for("star", 90)
for i, (x, y) in enumerate([(200, 420), (420, 330), (650, 400), (880, 330), (980, 520), (120, 600)]):
    t = T_STERNE + i * 0.07
    layers.append(image(f"star{i}", "star", t, T_STERNE_END + 0.5, fix_keys([
        {"t": t, "x": x, "y": y, "scale": 0.0, "rot": i * 17},
        {"t": t + 0.15, "scale": st_s * (1.3 if i % 2 else 1.0), "ease": "back_out"},
        {"t": T_STERNE_END + 0.1, "scale": st_s * (1.3 if i % 2 else 1.0), "rot": i * 17 + 30},
        {"t": T_STERNE_END + 0.4, "scale": 0.0, "ease": "in"}])))
rec("typewriter_bell", T_STERNE + 0.05, -16)

# ---------------------------------------------------------------- scene 7: Itasca radios, Amelia can't hear, radio dies
T_S7 = T_SCHIFF - 0.25
T_S7_OUT = T_NAVY - 0.3
os_ = scale_for("ocean_strip", 1250)
layers.append(image("ocean", "ocean_strip", T_S7, T_S7_OUT + 0.4, fix_keys(
    slide_in(T_S7, 540, 2300, 540, 1290, os_, 0, -1.5, 0.35) + [
        {"t": T_S7_OUT, "x": 540, "y": 1290}, exit_to(T_S7_OUT, 540, 2400, 0.35)]), jitter=False))
its = scale_for("st_itasca", 760)
it = META["st_itasca"]
IX, IY = 560, 1110
SHIP_PTS = {"funnel": (-124, -45), "mast": (-80, -290)}   # measured offsets from the ship centre


def on_ship(name):
    dx, dy = SHIP_PTS[name]
    return IX + dx, IY + dy


layers.append(image("smoke", "smoke", T_SCHIFF + 0.1, T_S7_OUT + 0.4, fix_keys([
    {"t": T_SCHIFF + 0.1, "x": on_ship("funnel")[0], "y": on_ship("funnel")[1], "scale": 0.0, "rot": 0},
    {"t": T_SCHIFF + 0.7, "x": on_ship("funnel")[0] - 60, "y": on_ship("funnel")[1] - 120,
     "scale": scale_for("smoke", 230), "ease": "out"},
    {"t": T_S7_OUT, "x": on_ship("funnel")[0] - 150, "y": on_ship("funnel")[1] - 230, "scale": scale_for("smoke", 330), "rot": 12},
    {"t": T_S7_OUT + 0.3, "scale": 0.0, "ease": "in"}]), jitter=False))
layers.append(image("itasca", "st_itasca", T_SCHIFF - 0.1, T_S7_OUT + 0.4, fix_keys(
    slide_in(T_SCHIFF - 0.1, 1500, IY + 40, IX, IY, its, 6, 0, 0.45) + [
        {"t": T_S7_OUT, "x": IX, "y": IY}, exit_to(T_S7_OUT, -600, IY + 100, 0.35, rot=-8)])))
rec("ship_horn", T_SCHIFF + 0.05, -12, trim=[0.0, 2.8], fade=0.8)
rec("paper_slide", T_SCHIFF, -9, peak=0.42)
# Amelia's plane, small, upper left
PX, PY = 920, 280
layers.append(image("electra3", "st_electra", T_FUNKT, T_AB_END + 0.2, fix_keys([
    {"t": T_FUNKT, "x": 1400, "y": PY - 60, "scale": scale_for("st_electra", 380), "sx": -1, "rot": 6, "opacity": 1.0},
    {"t": T_FUNKT + 0.6, "x": PX, "y": PY, "ease": "out3"},
    {"t": T_BRICHT, "x": PX - 120, "y": PY + 20},
    {"t": T_BRICHT + 0.08, "opacity": 0.2}, {"t": T_BRICHT + 0.16, "opacity": 1.0},
    {"t": T_BRICHT + 0.28, "opacity": 0.1}, {"t": T_BRICHT + 0.36, "opacity": 0.9},
    {"t": T_BRICHT + 0.6, "opacity": 0.0, "x": PX - 160}])))
rec("plane_distant", T_FUNKT, -20, trim=[2.0, 6.5], fade=0.8)
# radio waves from the mast towards the plane; they stop short of it
mx, my = on_ship("mast")
ang_up = math.degrees(math.atan2(PY - my, PX - mx))
t = T_FUNKT
i = 0
while t < T_NICHT2:
    layers.append(image(f"swave{i}", "arc_orange", t, t + 1.3, [
        {"t": t, "x": mx, "y": my, "scale": arc_s * 0.25, "rot": ang_up, "opacity": 1.0},
        {"t": t + 0.9, "opacity": 0.9},
        {"t": t + 1.3, "scale": arc_s * 1.55, "opacity": 0.0, "ease": "out"}], jitter=False))
    t += 0.38
    i += 1
sfx("morse_beeps", T_FUNKT, -20)
# "hört es nicht": red flash
layers.append({"id": "flash1", "type": "solid", "start": T_NICHT2 - 0.02, "end": T_NICHT2 + 0.6,
               "color": [168, 40, 45], "keys": [{"t": T_NICHT2 - 0.02, "opacity": 0.0},
                                               {"t": T_NICHT2 + 0.1, "opacity": 0.45},
                                               {"t": T_NICHT2 + 0.55, "opacity": 0.0}]})
rec("suspense_hit", T_NICHT2, -16)
# "bricht der Funk ab": static, colour drains
rec("radio_cutoff", T_DANN, -10, trim=[0.0, 2.2], fade=0.4)
layers.append({"id": "drain", "type": "grade", "start": T_BRICHT, "end": T_NAVY + 0.3,
               "keys": [{"t": T_BRICHT, "saturation": 1.0}, {"t": T_BRICHT + 0.5, "saturation": 0.15},
                        {"t": T_NAVY - 0.1, "saturation": 0.15}, {"t": T_NAVY + 0.3, "saturation": 1.0}]})

# ---------------------------------------------------------------- scene 8: Navy search
T_S8_OUT = T_NICHTS + 0.45
circles = []
for k, rdeg in enumerate((2.0, 4.0, 6.5)):
    r = rdeg * mp["proj"]["ppd"]
    pts = [[hx + r * math.cos(a), hy + r * math.sin(a)] for a in [2 * math.pi * j / 90 for j in range(91)]]
    t0 = T_NAVY + 0.2 + 0.5 * k
    circles.append({"id": f"search{k}", "type": "dashed_path", "start": t0, "end": T_S8_OUT + 0.3,
                    "points": pts, "props": {"x": 0, "y": 0}, "width": 7, "dash": 26, "gap": 18,
                    "color": [245, 238, 220],
                    "keys": [{"t": t0, "progress": 0.0, "opacity": 0.95},
                             {"t": t0 + 1.6, "progress": 1.0, "ease": "inout"},
                             {"t": T_S8_OUT, "opacity": 0.95}, {"t": T_S8_OUT + 0.3, "opacity": 0.0}]})
MAP_CHILDREN.extend(circles)
rec("sonar_ping", T_NAVY, -12)
rec("sonar_ping", T_NAVY + 2.6, -16)
ws = scale_for("lbl_2wochen", 520)
layers.append(image("lbl_2wochen", "lbl_2wochen", T_ZWEI, T_KEIN1, fix_keys(
    pop_in(T_ZWEI, 540, 330, ws, rot=-3, dur=0.28) + [
        {"t": T_KEIN1 - 0.35, "x": 540, "y": 330}, exit_to(T_KEIN1 - 0.35, 540, -250, 0.3)])))
rec("cardboard_hit", T_ZWEI + 0.08, -8)
lxs = scale_for("st_lexington", 700)
T_LEX = T_NAVY + 0.35
layers.append(image("lexington", "st_lexington", T_LEX, T_S8_OUT + 0.4, fix_keys(
    slide_in(T_LEX, -600, 760, 380, 700, lxs, -4, -3, 0.45) + [
        {"t": T_KEIN1 - 0.3, "x": 420, "y": 700},
        {"t": T_S8_OUT - 0.3, "x": 430, "y": 700}, exit_to(T_S8_OUT - 0.3, -700, 650, 0.3)])))
rec("paper_slide", T_LEX + 0.1, -8, peak=0.42)
cos_ = scale_for("st_colorado", 760)
layers.append(image("colorado", "st_colorado", T_SCHLACHT - 0.1, T_S8_OUT + 0.4, fix_keys(
    slide_in(T_SCHLACHT - 0.1, 1700, 1300, 660, 1260, cos_, 4, 2, 0.45) + [
        {"t": T_S8_OUT - 0.3, "x": 640, "y": 1260}, exit_to(T_S8_OUT - 0.3, 1800, 1300, 0.3)])))
rec("paper_slide", T_SCHLACHT, -8, peak=0.42)
rec("ship_horn", T_SCHLACHT + 0.2, -16, trim=[0.0, 2.0], fade=0.6)
for i, (lid, t, y, rot) in enumerate([("lbl_kein_flugzeug", T_KEIN1, 470, -3),
                                      ("lbl_kein_wrack", T_KEIN2, 1060, 2)]):
    sc = scale_for(lid, 640 if i == 0 else 560)
    layers.append(image(lid, lid, t, T_NICHTS + 0.1, fix_keys(
        pop_in(t, 540, y, sc, rot=rot, dur=0.26) + [
            {"t": T_NICHTS - 0.25, "x": 540, "y": y}, exit_to(T_NICHTS - 0.25, -700 if i == 0 else 1800, y, 0.22)])))
    rec("cardboard_hit", t + 0.08, -6)
nsc = scale_for("lbl_nichts", 820)
layers.append(image("lbl_nichts", "lbl_nichts", T_NICHTS, T_DREI + 0.3, fix_keys(
    pop_in(T_NICHTS, 540, 900, nsc, rot=-2, dur=0.3) + [
        {"t": T_DREI - 0.15, "x": 540, "y": 900}, exit_to(T_DREI - 0.15, 540, -300, 0.3)])))
layers.append({"id": "flash2", "type": "solid", "start": T_NICHTS - 0.02, "end": T_NICHTS + 0.6,
               "color": [168, 40, 45], "keys": [{"t": T_NICHTS - 0.02, "opacity": 0.0},
                                               {"t": T_NICHTS + 0.12, "opacity": 0.5},
                                               {"t": T_NICHTS + 0.55, "opacity": 0.0}]})
rec("suspense_hit", T_NICHTS, -7)
rec("paper_tear", T_S8_OUT - 0.25, -10)

# ---------------------------------------------------------------- scene 9: 1940, Nikumaroro, finds
T_S9_OUT = T_ARZT - 0.4
l40 = scale_for("lbl_1940", 440)
layers.append(image("lbl_1940", "lbl_1940", T_DREI, T_SKELETT, fix_keys(
    pop_in(T_DREI, 540, 330, l40, rot=-4, dur=0.3) + [
        {"t": T_SKELETT - 0.4, "x": 540, "y": 330}, exit_to(T_SKELETT - 0.4, 540, -300, 0.3)])))
rec("cardboard_hit", T_DREI + 0.08, -6)
MAP_CHILDREN.append({
    "id": "to_niku", "type": "dashed_path", "start": T_DREI + 0.4, "end": T_SKELETT,
    "points": [[hx, hy], [nx, ny]], "props": {"x": 0, "y": 0}, "width": 6, "dash": 20, "gap": 13,
    "color": [232, 112, 58], "keys": [{"t": T_DREI + 0.4, "progress": 0.0},
                                      {"t": T_EINSAM, "progress": 1.0, "ease": "inout"}]
    + [dict(k) for k in MAP_ONLY if T_EINSAM < k["t"] < T_SKELETT]})
rec("pen_scribble", T_DREI + 0.4, -12, trim=[0.0, T_EINSAM - T_DREI], fade=0.3)
nks = scale_for("lbl_nikumaroro", 560)
layers.append(image("lbl_niku", "lbl_nikumaroro", T_EINSAM + 0.1, T_SKELETT, fix_keys(
    pop_in(T_EINSAM + 0.1, 540, 1260, nks, rot=2, dur=0.28) + [
        {"t": T_SKELETT - 0.4, "x": 540, "y": 1260}, exit_to(T_SKELETT - 0.4, 540, 2300, 0.3)])))
rec("cardboard_hit", T_EINSAM + 0.18, -9)
layers.append({"id": "dim2", "type": "solid", "start": T_SKELETT - 0.3, "end": T_GENAU + 0.6,
               "color": [20, 24, 22], "keys": [{"t": T_SKELETT - 0.3, "opacity": 0.0},
                                               {"t": T_SKELETT, "opacity": 0.12},
                                               {"t": T_VERSCHW, "opacity": 0.12},
                                               {"t": T_GENAU + 0.4, "opacity": 0.0}]})
bns = scale_for("st_bones", 600)
layers.append(image("bones", "st_bones", T_SKELETT, T_S9_OUT + 0.4, fix_keys(
    pop_in(T_SKELETT, 560, 520, bns, rot=-8, dur=0.28) + [
        {"t": T_S9_OUT, "x": 560, "y": 520}, exit_to(T_S9_OUT, 560, -400, 0.3)])))
rec("bones_rattle", T_SKELETT, -6)
rec("heartbeat_low", T_SKELETT + 0.3, -10, trim=[0.0, 4.5], fade=0.8)
shs = scale_for("st_shoe", 420)
layers.append(image("shoe", "st_shoe", T_SCHUH, T_S9_OUT + 0.4, fix_keys(
    pop_in(T_SCHUH, 300, 1200, shs, rot=-10, dur=0.28) + [
        {"t": T_S9_OUT, "x": 300, "y": 1200}, exit_to(T_S9_OUT, -500, 1300, 0.3)])))
rec("paper_drop", T_SCHUH + 0.1, -5)
bxs = scale_for("st_box_empty", 470)
layers.append(image("box", "st_box_empty", T_LEERE, T_S9_OUT + 0.4, fix_keys(
    pop_in(T_LEERE, 770, 1220, bxs, rot=6, dur=0.28) + [
        {"t": T_S9_OUT, "x": 770, "y": 1220}, exit_to(T_S9_OUT, 1600, 1300, 0.3)])))
rec("box_open", T_LEERE + 0.05, -6, trim=[0.0, 1.2], fade=0.3)
# callback: ghost of the sextant from the navigation scene rises from the box
gs = scale_for("st_sextant", 380)
layers.append(image("ghost_sextant", "st_sextant", T_KISTE + 0.2, T_S9_OUT + 0.1, [
    {"t": T_KISTE + 0.2, "x": 770, "y": 1180, "scale": gs * 0.6, "rot": 0, "opacity": 0.0},
    {"t": T_KISTE + 0.5, "opacity": 0.55, "y": 1020, "scale": gs, "ease": "out"},
    {"t": T_KISTE_END + 0.3, "opacity": 0.0, "y": 960}], jitter=False))
rec("map_whoosh", T_KISTE + 0.3, -14, peak=0.38)

# ---------------------------------------------------------------- scene 10: doctor, stamp, case closed
T_S10_OUT = T_BIS - 0.2
ds_ = scale_for("st_doctor", 560)
layers.append(image("doctor", "st_doctor", T_ARZT - 0.1, T_S10_OUT + 0.4, fix_keys(
    slide_in(T_ARZT - 0.1, -500, 900, 300, 880, ds_, -10, -3, 0.4) + [
        {"t": T_S10_OUT, "x": 300, "y": 880}, exit_to(T_S10_OUT, -600, 900, 0.3)])))
rec("paper_slide", T_ARZT, -6, peak=0.42)
fs_ = scale_for("st_folder", 520)
FX, FY = 760, 1180
folder_keys = fix_keys(pop_in(T_EINDEUTIG, FX, FY, fs_, rot=5, dur=0.28) + [
    {"t": T_FALL, "x": FX, "y": FY, "rot": 5},
    {"t": T_FALL + 0.15, "y": FY + 25, "rot": 3, "ease": "out"},
    {"t": T_FALL + 0.3, "y": FY, "rot": 5, "ease": "inout"},
    {"t": T_ALSO - 0.1, "x": FX, "y": FY},
    {"t": T_ALSO + 0.3, "x": 540, "y": 1050, "scale": fs_ * 1.25, "rot": 2, "ease": "inout"}])
layers.append(image("folder", "st_folder", T_EINDEUTIG, T_UNTERS, folder_keys))
rec("paper_drop", T_EINDEUTIG + 0.1, -6)
sm = scale_for("stamp_mann", 380)


def stamp_keys(t0):
    return [{"t": t0, "x": FX, "y": FY - 30, "scale": sm * 2.2, "rot": -14, "opacity": 0.0},
            {"t": t0 + 0.03, "opacity": 1.0},
            {"t": t0 + 0.1, "scale": sm, "ease": "in"}]


stamp_k = fix_keys(stamp_keys(T_MANN) + [
    {"t": T_FALL, "y": FY - 30}, {"t": T_FALL + 0.15, "y": FY - 5, "ease": "out"},
    {"t": T_FALL + 0.3, "y": FY - 30, "ease": "inout"},
    {"t": T_ALSO - 0.1, "x": FX, "y": FY - 30, "scale": sm}, exit_to(T_ALSO - 0.1, FX + 900, FY - 200, 0.3)])
layers.append(image("stamp", "stamp_mann", T_MANN, T_ALSO + 0.3, stamp_k))
rec("stamp", T_MANN + 0.08, -3)
rec("file_close", T_FALL + 0.1, -5)

# ---------------------------------------------------------------- scene 11: 2018 recalculation
l18 = scale_for("lbl_2018", 440)
layers.append(image("lbl_2018", "lbl_2018", T_2018, T_ALSO, fix_keys(
    pop_in(T_2018, 540, 330, l18, rot=3, dur=0.3) + [
        {"t": T_ALSO - 0.4, "x": 540, "y": 330}, exit_to(T_ALSO - 0.4, 540, -300, 0.3)])))
rec("cardboard_hit", T_2018 + 0.08, -5)
rec("suspense_hit", T_2018 + 0.05, -12)
scs = scale_for("scribble", 460)
layers.append(image("scribble", "scribble", T_FORSCHER, T_ALSO, fix_keys(
    slide_in(T_FORSCHER, -500, 900, 290, 860, scs, -15, -6, 0.35) + [
        {"t": T_ALSO - 0.3, "x": 290, "y": 860}, exit_to(T_ALSO - 0.3, -600, 900, 0.3)])))
rec("paper_slide", T_FORSCHER + 0.1, -8, peak=0.42)
rec("pen_scribble", T_FORSCHER + 0.35, -9, trim=[0.0, 1.6], fade=0.3)
# strike the stamp through with an orange line
layers.append({"id": "strike", "type": "dashed_path", "start": T_KNOCHEN1, "end": T_ALSO,
               "points": [[FX - 230, FY - 10], [FX + 230, FY - 70]], "props": {"x": 0, "y": 0},
               "width": 16, "dash": 2000, "gap": 1, "color": [232, 112, 58],
               "keys": [{"t": T_KNOCHEN1, "progress": 0.0}, {"t": T_KNOCHEN1 + 0.3, "progress": 1.0, "ease": "out"}]})
rec("pen_scribble", T_KNOCHEN1, -12, trim=[2.8, 3.3], fade=0.1)
p2s = scale_for("st_portrait2", 400)
layers.append(image("burst2", "burst_orange", T_AMELIA3 - 0.15, T_UNTERS, fix_keys([
    {"t": T_AMELIA3 - 0.15, "x": 300, "y": 880, "scale": 0.0, "rot": 0},
    {"t": T_AMELIA3 + 0.2, "scale": scale_for("burst_orange", 640), "ease": "back_out"},
    {"t": T_UNTERS - 0.3, "rot": 10},
    {"t": T_UNTERS, "scale": 0.0, "ease": "in"}]), jitter=False))
layers.append(image("portrait2", "st_portrait2", T_AMELIA3 - 0.1, T_VERSCHW + 0.5, fix_keys(
    pop_in(T_AMELIA3 - 0.1, 290, 900, p2s, rot=-4, dur=0.3) + [
        {"t": T_VERSCHW, "x": 290, "y": 900, "opacity": 1.0},
        {"t": T_VERSCHW + 0.08, "opacity": 0.3}, {"t": T_VERSCHW + 0.16, "opacity": 0.9},
        {"t": T_VERSCHW + 0.45, "opacity": 0.0}])))
rec("paper_drop", T_AMELIA3, -5)

# ---------------------------------------------------------------- scene 12: examine again? gone.
layers.append(image("folder_open", "st_folder_open", T_UNTERS, T_GENAU + 0.2, fix_keys([
    {"t": T_UNTERS, "x": 560, "y": 1080, "scale": scale_for("st_folder_open", 600), "rot": 2},
    {"t": T_VERSCHW, "x": 560, "y": 1080},
    exit_to(T_VERSCHW, 560, 2400, 0.4, rot=15)])))
rec("box_open", T_UNTERS, -8, trim=[0.0, 1.0], fade=0.3)
layers.append(image("magnifier2", "st_magnifier", T_ALSO + 0.1, T_VERSCHW + 0.5, fix_keys(
    slide_in(T_ALSO + 0.1, 1400, 1700, 620, 1060, mgs, -40, -15, 0.45) + [
        {"t": T_UNTERS + 0.3, "x": 600, "y": 1100},
        {"t": T_GEHT, "x": 560, "y": 1060, "ease": "inout"},
        exit_to(T_VERSCHW, 1500, 2000, 0.35, rot=-40)]), anchor=list(lens)))
rec("paper_slide", T_ALSO + 0.2, -9, peak=0.42)
layers.append({"id": "flash3", "type": "solid", "start": T_GEHT - 0.02, "end": T_GEHT + 0.6,
               "color": [168, 40, 45], "keys": [{"t": T_GEHT - 0.02, "opacity": 0.0},
                                               {"t": T_GEHT + 0.12, "opacity": 0.45},
                                               {"t": T_GEHT + 0.55, "opacity": 0.0}]})
rec("suspense_hit", T_GEHT, -9)
rec("paper_tear", T_VERSCHW, -6)
rec("ocean_wind", T_VERSCHW, -20, trim=[0.0, END - T_VERSCHW], fade=0.15)

# ---------------------------------------------------------------- page texture on top
layers.append({"id": "page", "type": "multiply_image", "asset": "page", "keys": []})

# ---------------------------------------------------------------- captions
HIDE = [(0.0, T_EARHART + 0.6), (T_QUOTE - 0.05, T_KNAPP + 0.5), (T_1937 - 0.05, T_1937 + 1.2),
        (T_HOWLAND - 0.05, T_ISLAND_END + 0.1), (T_KEIN1 - 0.05, T_DREI - 0.05),
        (T_2018 - 0.05, T_2018 + 1.0)]
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
