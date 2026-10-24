"""Timeline for "Elektroautos dürfen nicht leise sein" (timeline.json).

Built in the style of the reference (docs/STYLE_GUIDE.md): stripes background,
one-word captions in the middle, one visual event per key word (pop-ins with
overshoot, punch zooms, red block arrow, red flash + buzzer on negations,
[Qn] source labels, vertical credit line). Every event is anchored to the
start of a spoken word from words.json (build_voice.py), so a new voice take
only needs build_voice.py + this script.

    python3 projects/elektroauto-sound/build/build_timeline.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PROJ))
STYLE = json.load(open(os.path.join(ROOT, "projects", "bundeswehr-kennzeichen", "analysis",
                                    "style_measurements.json"), encoding="utf-8"))
VOICE = json.load(open(os.path.join(HERE, "words.json"), encoding="utf-8"))
WORDS = VOICE["words"]
FPS = 30
DUR = round(round(VOICE["duration"] * FPS) / FPS, 4)
FR = 1 / FPS

POP = [0.15, 0.45, 1.24, 1.37, 1.28, 1.15, 1.0]       # measured pop-in scale per frame
FLASH = [0.0, .25, .45, .62, .76, .82, .82, .77, .72, .66, .62, .47, .31, .22, .14, .06, 0.0]
EMPHASIS = {"nicht", "lautlos", "reifen", "bobbycar", "lärm", "keinen", "doppelt", "hans", "zimmer",
            "56", "75", "20", "50.000", "2021", "eu", "musik", "kommt"}


def snap(t):
    return round(round(t * FPS) / FPS, 4)


def W(text, occ=1):
    """start time of the occ-th spoken word `text` (case-sensitive, punctuation ignored)."""
    n = 0
    for w in WORDS:
        if w["text"].strip("„“\",.…") == text:
            n += 1
            if n == occ:
                return snap(w["start"])
    raise KeyError(f"{text} #{occ}")


# ------------------------------------------------------------------ element helpers
_ids = {}


def uid(base):
    _ids[base] = _ids.get(base, 0) + 1
    return f"{base}_{_ids[base]}"


def pop_keys(t, x, y, s=1.0, extra=None):
    keys = [{"t": snap(t - FR), "x": x, "y": y, "scale": 0.0}]
    keys += [{"t": snap(t + i * FR), "x": x, "y": y, "scale": round(s * f, 4)} for i, f in enumerate(POP)]
    return keys + (extra or [])


def out_keys(t, x, y, s=1.0):
    """quick shrink-out over 3 frames ending at t."""
    return [{"t": snap(t - 3 * FR), "x": x, "y": y, "scale": s},
            {"t": snap(t - 2 * FR), "x": x, "y": y, "scale": s * 1.12},
            {"t": snap(t), "x": x, "y": y, "scale": 0.0}]


def img(asset, start, end, keys, anchor=None, **kw):
    lay = {"id": uid(asset), "type": "image", "asset": asset, "start": snap(start), "end": snap(end),
           "keys": sorted(keys, key=lambda k: k["t"])}
    if anchor:
        lay["anchor"] = anchor
    lay.update(kw)
    return lay


def pop(asset, t, end, x, y, s=1.0, out=True, extra=None, **kw):
    """pops in at t, shrinks out at end (or is cut at end with out=False)."""
    keys = pop_keys(t, x, y, s)
    if extra:
        keys += extra
    if out:
        last = max(keys, key=lambda k: k["t"])
        keys += out_keys(end, last.get("x", x), last.get("y", y), last.get("scale", s))
    return img(asset, t - FR, end + FR, keys, **kw)


def shake(t0, t1, x, y, amp=10, s=None, every=2):
    keys, i, t = [], 0, t0
    while t < t1:
        k = {"t": snap(t), "x": x + (amp if i % 2 else -amp), "y": y + (amp / 2 if i % 3 == 0 else -amp / 2)}
        if s is not None:
            k["scale"] = s
        keys.append(k)
        t += every * FR
        i += 1
    keys.append({"t": snap(t1), "x": x, "y": y, **({"scale": s} if s is not None else {})})
    return keys


def text(txt, t, end, x, y, size=120, fill=(227, 32, 43), s=1.0):
    return {"id": uid("text"), "type": "text", "text": txt, "start": snap(t - FR), "end": snap(end),
            "size": size, "style": {"font": "league-spartan-800", "fill": list(fill), "stroke": [255, 255, 255],
                                    "stroke_w": 10, "shadow": {"dx": 4, "dy": 6, "blur": 3, "color": [0, 0, 0],
                                                               "alpha": 0.35}},
            "keys": pop_keys(t, x, y, s) + out_keys(end, x, y, s)}


def camera(start, end, children, keys=None, pivot=(540, 960)):
    return {"id": uid("cam"), "type": "group", "start": snap(start), "end": snap(end),
            "pivot": list(pivot), "keys": keys or [{"t": snap(start), "x": pivot[0], "y": pivot[1]}],
            "children": children}


def punch(t, pivot, s0=1.0, s1=1.35, hold_to=None):
    """punch zoom: 3 linear frames, then hold (camera keys)."""
    k = [{"t": snap(t - FR), "x": pivot[0], "y": pivot[1], "scale": s0},
         {"t": snap(t + 2 * FR), "x": pivot[0], "y": pivot[1], "scale": s1}]
    if hold_to:
        k.append({"t": snap(hold_to), "scale": s1})
    return k


def push_in(t, frames=3, dx=1080):
    """scene slides in from the right (camera x keys)."""
    return [{"t": snap(t), "x": 540 + dx, "y": 960}, {"t": snap(t + frames * FR), "x": 540, "y": 960, "ease": "out3"}]


def arrow(tip, ang, t_in, t_out, length=436.0):
    import math
    a = math.radians(ang)

    def back(d):
        return [round(tip[0] - math.cos(a) * d, 1), round(tip[1] - math.sin(a) * d, 1)]
    keys = [{"t": snap(t_in), "x": back(2 * length)[0], "y": back(2 * length)[1], "rot": ang},
            {"t": snap(t_in + FR), "x": back(length)[0], "y": back(length)[1], "rot": ang},
            {"t": snap(t_in + 2 * FR), "x": tip[0], "y": tip[1], "rot": ang},
            {"t": snap(t_out), "x": tip[0], "y": tip[1], "rot": ang},
            {"t": snap(t_out + 2 * FR), "x": back(-1400)[0], "y": back(-1400)[1], "rot": ang, "ease": "in"}]
    return {"id": uid("arrow"), "type": "arrow", "start": snap(t_in), "end": snap(t_out + 3 * FR), "keys": keys}


def red_flash(t):
    keys = [{"t": snap(t + i * FR), "opacity": a} for i, a in enumerate(FLASH)]
    return {"id": uid("flash"), "type": "solid", "color": STYLE["red_flash"]["color"], "start": snap(t),
            "end": snap(t + len(FLASH) * FR), "keys": keys}


def label(txt, start, end):
    st = STYLE["label"]
    return {"id": uid("label"), "type": "text", "text": txt, "start": snap(start), "end": snap(end),
            "size": st["size"], "style": {"font": st["font"], "fill": st["fill"]},
            "keys": [{"t": snap(start), "x": st["x"], "y": st["y"] - st["slide"], "opacity": st["opacity"]},
                     {"t": snap(start + st["slide_dur"]), "x": st["x"], "y": st["y"], "ease": "out3"}]}


def credit(txt, start, end):
    st = STYLE["credit"]
    return {"id": uid("credit"), "type": "text", "text": txt, "start": snap(start), "end": snap(end),
            "size": st["size"], "style": {"font": st["font"], "fill": st["fill"]},
            "keys": [{"t": snap(start), "x": st["x"], "y": st["y_center"], "rot": 90, "opacity": st["opacity"]}]}


def glow(t, end, x, y, r, color=(255, 250, 220), soft=0.8, blend="add", keys=None):
    return {"id": uid("glow"), "type": "glow", "start": snap(t), "end": snap(end), "radius": r, "softness": soft,
            "color": list(color), "blend": blend, "keys": keys or [{"t": snap(t), "x": x, "y": y}]}


def ground(start, end, y=1560, color=(88, 92, 104)):
    return [{"id": uid("ground"), "type": "solid", "start": snap(start), "end": snap(end),
             "rect": [0, y, 1080, 1920 - y], "color": list(color)},
            *[{"id": uid("lane"), "type": "solid", "start": snap(start), "end": snap(end),
               "rect": [40 + 280 * i, y + 150, 160, 22], "color": [235, 235, 235]} for i in range(4)]]


AUDIO = []


def sfx(name, t, gain):
    AUDIO.append({"src": f"@sfx/{name}", "start": snap(t), "gain_db": gain})


# ------------------------------------------------------------------ scenes
CAR_S = 0.9            # ecar 1000 px asset -> 900 design px


def scene_hook():
    """0 - 'Wäre': Elektroautos dürfen NICHT leise sein."""
    t_end = W("Wäre")
    t_n, t_l = W("nicht"), W("leise")
    car = img("ecar", 0, t_end, [{"t": 0, "x": 420, "y": 1330, "scale": 0.82},
                                 {"t": t_end, "scale": 0.86}])
    cam = camera(0, t_end, [car], punch(t_n, (420, 1330), 1.0, 1.15, t_end), pivot=(420, 1330))
    # the car faces left: the (missing) tailpipe would sit at the rear bumper, bottom right
    a = arrow((835, 1500), 120, t_l, snap(t_end - 3 * FR))
    sfx("ev_hum", 0.0, -14)
    sfx("impact_low", t_n, -4)
    sfx("buzzer", t_n, -13)
    sfx("swoosh", t_l, -12)
    return [cam, a, red_flash(t_n), pop("muted-speaker", t_l, t_end, 300, 520, 0.6, out=False)]


def scene_dumm():
    """'Wäre ja auch dumm, wenn du dir für 50.000 Euro ein Auto fürs Klima kaufst'"""
    t0, t_end = W("Wäre"), W("und", 1)
    t_d, t_50, t_a, t_k = W("dumm"), W("50.000"), W("Auto", 1), W("Klima")
    ch = [pop("face-with-spiral-eyes", t_d, t_50, 540, 520, 0.6),
          pop("euro-banknote", t_50, t_a, 540, 1380, 1.0),
          text("50.000 €", t_50, t_k, 540, 540, size=150),
          pop("ecar", t_a, t_end, 540, 1400, CAR_S, out=False),
          pop("globe-showing-europe-africa", t_k, t_end, 540, 520, 0.55, out=False),
          pop("green-heart", snap(t_k + 4 * FR), t_end, 690, 420, 0.4, out=False)]
    for t in (t_d, t_50, t_a, t_k):
        sfx("pop", t, -11)
    sfx("swoosh", t0, -12)
    return [camera(t0, t_end, ch, push_in(t0))]


def scene_parking():
    """'... und dann auf dem Aldi-Parkplatz lautlos an eine Oma ranrollst, die dich erst bemerkt,
    wenn sie auf deiner Motorhaube sitzt.' + pause"""
    t0, t_end = W("und", 1), W("Deshalb")
    t_p, t_l, t_o, t_b, t_m, t_s = W("Aldi-Parkplatz"), W("lautlos", 1), W("Oma"), W("bemerkt"), \
        W("Motorhaube"), W("sitzt")
    car_y = 1430
    # car rolls in from the right (it faces left) and creeps towards the Oma
    car_keys = [{"t": t0, "x": 1500, "y": car_y, "scale": 0.78},
                {"t": t_l, "x": 760, "y": car_y, "ease": "out"},
                {"t": t_m, "x": 600, "y": car_y},
                {"t": snap(t_m + 6 * FR), "x": 560, "y": car_y, "ease": "out"}]
    car = img("ecar", t0, t_end, car_keys + shake(t_s, snap(t_s + 8 * FR), 560, car_y, 8)[1:])
    mute_keys = [{"t": snap(t_l - FR), "x": 760, "y": 1080, "scale": 0}] + \
        [{"t": snap(t_l + i * FR), "x": 760, "y": 1080, "scale": round(0.45 * f, 3)} for i, f in enumerate(POP)] + \
        [{"t": t_m, "x": 600, "y": 1080}, {"t": snap(t_m + 6 * FR), "x": 560, "y": 1080, "ease": "out"}]
    mute = img("muted-speaker", t_l - FR, t_b, mute_keys + out_keys(t_b, 560, 1080, 0.45)[1:])
    oma_x, oma_y = 190, 1340
    oma = pop("old-woman", t_o, t_b, oma_x, oma_y, 0.5, out=False)
    cart = pop("shopping-cart", snap(t_o + 2 * FR), t_end, 120, 1500, 0.45, out=False)
    # she notices -> screams, then jumps onto the bonnet (left front of the car)
    hood = (330, 1200)
    scream_keys = pop_keys(t_b, oma_x, oma_y, 0.42) + [
        {"t": t_m, "x": oma_x, "y": oma_y, "rot": 0},
        {"t": snap(t_m + 5 * FR), "x": 260, "y": 940, "rot": -20, "ease": "out"},
        {"t": snap(t_s), "x": hood[0], "y": hood[1], "rot": 8, "ease": "in"},
        {"t": snap(t_s + 3 * FR), "x": hood[0], "y": hood[1] + 20, "rot": 0}]
    scream = img("face-screaming-in-fear", t_b - FR, t_end, scream_keys)
    boom = pop("collision", t_s, snap(t_s + 12 * FR), hood[0] + 80, hood[1] + 90, 0.5)
    pause_t = snap(W("sitzt") + 0.32)
    cam = camera(t0, t_end, [*ground(t0, t_end), pop("p_sign", snap(t0 + 3 * FR), t_end, 960, 1080, 0.75,
                                                       out=False), car, mute, cart, oma, scream, boom],
                 push_in(t0) + [{"t": snap(pause_t - FR), "scale": 1.0},
                                {"t": snap(pause_t + 2 * FR), "scale": 1.45}],
                 pivot=(540, 960))
    # zoom on the screaming face during the pause: pivot moves with the keys above
    cam["pivot"] = [hood[0], hood[1]]
    cam["keys"] = [{"t": t0, "x": hood[0] + 1080, "y": hood[1], "scale": 1.0},
                   {"t": snap(t0 + 3 * FR), "x": hood[0], "y": hood[1], "ease": "out3"},
                   {"t": snap(pause_t - FR), "x": hood[0], "y": hood[1], "scale": 1.0},
                   {"t": snap(pause_t + 2 * FR), "x": 540, "y": 1100, "scale": 1.5}]
    sfx("swoosh", t0, -12)
    sfx("ev_hum", snap(t0 + 0.1), -16)
    sfx("pop", t_l, -11)
    sfx("pop", t_o, -11)
    sfx("chirp_up", t_m, -12)
    sfx("impact_low", t_s, -5)
    sfx("boing", snap(t_s + 2 * FR), -12)
    sfx("impact_low", pause_t, -7)
    return [cam]


def scene_law():
    """'Deshalb muss seit Juli 2021 jedes neue E-Auto in der EU künstlich Lärm machen,'"""
    t0, t_end = W("Deshalb"), W("und", 2)
    t_j, t_e, t_eu, t_k, t_lm = W("Juli"), W("E-Auto"), W("EU"), W("künstlich"), W("Lärm", 1)
    ch = [pop("cal_2021", t_j, t_eu, 540, 500, 0.8),
          pop("ecar", t_e, t_end, 540, 1420, CAR_S, out=False),
          pop("eu_flag", t_eu, t_end, 540, 500, 0.75, out=False),
          pop("loudspeaker", t_k, t_end, 470, 1160, 0.42, out=False, extra=[{"t": t_k, "rot": -15}]),
          pop("waves_red", t_lm, t_end, 690, 1140, 0.45, out=False)]
    cam = camera(t0, t_end, ch, [{"t": t0, "x": 540, "y": 1250}] + punch(t_lm, (540, 1250), 1.0, 1.22),
                 pivot=(540, 1250))
    for t in (t_j, t_e, t_eu, t_k):
        sfx("pop", t, -11)
    sfx("swoosh_down", t0, -13)
    sfx("impact_low", t_lm, -5)
    sfx("ev_hum", t_lm, -12)
    return [cam, label("[Q1]", t_eu, t_end)]


def needle_rot(v):
    return round(2.25 * v - 135, 2)


def tacho_layers(t0, t1, keys_v, x=540, y=1330, s=0.85, pop_in=True):
    tk = pop_keys(t0, x, y, s) if pop_in else [{"t": snap(t0), "x": x, "y": y, "scale": s}]
    tach = img("tacho", t0 - FR, t1, tk)
    nk = [dict(k) for k in tk]
    for k in nk:
        k.pop("rot", None)
    nk += [{"t": snap(t), "rot": needle_rot(v), **({"ease": e} if e else {})} for t, v, e in keys_v]
    needle = img("needle", t0 - FR, t1, nk, anchor=[0.5, 380 / 440])
    return [tach, needle]


def scene_speed():
    """'und zwar vom Anfahren bis Tempo 20 und beim Rückwärtsfahren.'"""
    t0, t_end = W("und", 2), W("Darüber")
    t_a, t_20, t_r = W("Anfahren"), W("20", 1), W("Rückwärtsfahren")
    tl = tacho_layers(t0, t_r, [(t0, 0, None), (t_a, 0, None), (snap(t_20 + 6 * FR), 20, "back_out")])
    zone = text("0–20 KM/H", t_20, t_r, 540, 520, size=130, fill=(31, 179, 91))
    rev_car = img("ecar", t_r, t_end, [{"t": t_r, "x": 540, "y": 1400, "scale": CAR_S},
                                        {"t": t_end, "x": 760, "y": 1400, "ease": "inout"}])
    waves = pop("waves", snap(t_r + 3 * FR), t_end, 1000, 1400, 0.45, out=False)
    rtxt = text("R", t_r, t_end, 540, 520, size=220, fill=(255, 255, 255))
    rtxt["style"]["stroke"] = [27, 30, 39]
    sfx("swoosh", t0, -12)
    sfx("pop", t0, -12)
    sfx("chirp_up", t_a, -14)
    sfx("pop", t_20, -10)
    sfx("beep_reverse", t_r, -14)
    return [camera(t0, t_end, tl + [zone, rev_car, waves, rtxt], push_in(t0))]


def scene_tyres():
    """'Darüber nicht mehr, weil dann sowieso die Reifen lauter sind als der Motor.'"""
    t0, t_end = W("Darüber"), W("Bei", 1)
    t_n, t_r, t_lt = W("nicht", 2), W("Reifen"), W("lauter")
    tl = tacho_layers(t0, t_r, [(t0, 20, None), (snap(t_n), 60, "out"), (t_r, 75, None)], pop_in=False)
    mute = pop("muted-speaker", t_n, t_r, 540, 520, 0.6, out=False)
    spin = [{"t": snap(t_r + i * 0.2), "rot": -72 * i * 1.0} for i in range(int((t_end - t_r) / 0.2) + 2)]
    tyre = img("tyre", t_r - FR, t_end, pop_keys(t_r, 480, 1360, 0.95) + spin)
    waves = pop("waves", t_lt, t_end, 900, 1360, 0.7, out=False)
    sfx("buzzer", t_n, -14)
    sfx("pop", t_r, -10)
    sfx("engine_pass", t_lt, -10)
    return [camera(t0, t_end, tl + [mute, tyre, waves]), red_flash(t_n)]


def meter_y(v, y0, s):
    """design y of level v (0..1) on the meter centred at y0 with scale s."""
    return y0 + (520 - 1050 * v) * s


def scene_db():
    """'Bei Tempo 20 müssen es mindestens 56 Dezibel sein, aber nicht mehr als 75,
    sonst wäre es ja wieder Lärm.'"""
    t0, t_end = W("Bei", 1), W("Und", 1)
    t_20, t_56, t_db, t_75, t_lm = W("20", 2), W("56"), W("Dezibel"), W("75"), W("Lärm", 2)
    x, y, s = 300, 1330, 0.85
    off = img("meter_off", t0, t_end, pop_keys(t0, x, y, s))
    on_keys = pop_keys(t0, x, y, s) + [
        {"t": t0, "reveal": 0.0}, {"t": snap(t_56 + 8 * FR), "reveal": 0.56, "ease": "out"},
        {"t": t_75, "reveal": 0.56}, {"t": snap(t_75 + 8 * FR), "reveal": 0.75, "ease": "out"},
        {"t": t_lm, "reveal": 0.75}, {"t": snap(t_lm + 4 * FR), "reveal": 1.05, "ease": "out"}]
    on = img("meter_on", t0, t_end, on_keys, reveal_map="ramp_y", reveal_soft=0.01)
    ch = [off, on,
          text("56 dB", t_56, t_end, 760, meter_y(0.56, y, s), size=110, fill=(31, 179, 91)),
          text("75 dB", t_75, t_end, 760, meter_y(0.75, y, s), size=110, fill=(227, 32, 43)),
          text("TEMPO 20", t_20, t_56, 540, 480, size=120, fill=(27, 30, 39)),
          pop("exploding-head", t_lm, t_end, 760, 470, 0.5, out=False)]
    cam = camera(t0, t_end, ch, push_in(t0) + punch(t_lm, (540, 960), 1.0, 1.12))
    sfx("swoosh", t0, -12)
    sfx("pop", t_20, -12)
    sfx("chirp_up", t_56, -12)
    sfx("chirp_up", t_75, -12)
    sfx("impact_low", t_lm, -4)
    sfx("buzzer", t_lm, -12)
    return [cam, red_flash(t_lm), label("[Q2]", t_db, t_end)]


def scene_pitch():
    """'Und der Ton muss mit der Geschwindigkeit höher werden, damit du hörst,
    ob das Auto bremst oder Gas gibt,'"""
    t0, t_end = W("Und", 1), W("also", 1)
    t_g, t_h, t_b, t_gas = W("Geschwindigkeit"), W("höher", 1), W("bremst"), W("Gas")
    gx, gy, gs = 540, 1390, 0.9

    def on_curve(px, py):          # graph asset px -> design
        return gx + (px - 450) * gs, gy + (py - 380) * gs
    graph = img("graph", t0, t_end, pop_keys(t0, gx, gy, gs))
    curve = img("curve", t0, t_end, [{"t": t0, "x": gx, "y": gy, "scale": gs, "reveal": 0.0},
                                     {"t": t_g, "reveal": 0.0},
                                     {"t": snap(t_h + 6 * FR), "reveal": 1.0}],
                reveal_map="ramp_x", reveal_soft=0.02)
    lo, hi = on_curve(260, 560), on_curve(760, 200)
    note = img("musical-note", t_b - FR, t_end,
               pop_keys(t_b, lo[0], lo[1] - 80, 0.3) + [{"t": t_gas, "x": lo[0], "y": lo[1] - 80},
                                                         {"t": snap(t_gas + 5 * FR), "x": hi[0], "y": hi[1] - 80,
                                                          "ease": "out3"}])
    car = pop("ecar", t_b, t_end, 760, 520, 0.4, out=False)
    sfx("swoosh", t0, -12)
    sfx("pop", t0, -12)
    sfx("chirp_up", t_g, -10)
    sfx("pop", t_b, -11)
    sfx("chirp_up", t_gas, -10)
    return [camera(t0, t_end, [graph, curve, car, note], push_in(t0))]


def scene_bobbycar():
    """'also quasi wie du früher auf dem Bobbycar immer höher „Brrrmmm" gemacht hast,
    je schneller du warst.'"""
    t0, t_end = W("also", 1), W("Wie")
    t_bc, t_br, t_sch = W("Bobbycar"), W("Brrrmmm"), W("schneller")
    bx, by = 540, 1480
    rock = shake(t_br, t_end, bx, by, 6, every=2)
    car = img("bobbycar", t0, t_end, pop_keys(t0, bx, by, 0.95) + rock)
    kid = img("child", t0, t_end, pop_keys(snap(t0 + 3 * FR), 470, 1230, 0.55) +
              shake(t_br, t_end, 470, 1230, 6, every=2))
    bubble = img("bubble", t_br - FR, t_end, pop_keys(t_br, 560, 560, 0.7) +
                 [{"t": snap(t_br + 7 * FR), "scale": 0.7}, {"t": t_end, "scale": 1.0}])
    puff = pop("dashing-away", t_sch, t_end, 1000, 1400, 0.55, out=False)
    sfx("swoosh", t0, -12)
    sfx("pop", t0, -11)
    sfx("pop", t_bc, -12)
    sfx("boing", t_br, -10)
    sfx("ev_hum", t_br, -15)
    sfx("swoosh", t_sch, -13)
    return [camera(t0, t_end, [car, kid, bubble, puff], [{"t": t0, "x": 540, "y": 1300}] +
                   punch(t_bc, (540, 1300), 1.0, 1.12), pivot=(540, 1300))]


def scene_rules():
    """'Wie das klingt, dürfen sich die Hersteller selbst ausdenken, es soll aber nach einem Auto
    klingen und nicht nach Vogelgezwitscher oder Musik.'"""
    t0, t_end = W("Wie"), W("BMW")
    t_h, t_a, t_k, t_n, t_v, t_m = W("Hersteller"), W("Auto", 3), W("klingen"), W("nicht", 4), \
        W("Vogelgezwitscher"), W("Musik", 1)
    ch = [pop("control-knobs", t_h, t_a, 540, 1380, 0.95),
          pop("ecar", t_a, t_end, 540, 1440, 0.8, out=False),
          pop("check-mark-button", t_k, t_end, 870, 1170, 0.5, out=False),
          pop("bird", t_v, t_end, 290, 520, 0.6, out=False),
          pop("ban", snap(t_v + 10 * FR), t_end, 290, 520, 0.6, out=False),
          pop("musical-notes", t_m, t_end, 790, 520, 0.6, out=False),
          pop("ban", snap(t_m + 6 * FR), t_end, 790, 520, 0.6, out=False)]
    for t in (t_h, t_a, t_k, t_v, t_m):
        sfx("pop", t, -11)
    sfx("swoosh", t0, -12)
    sfx("buzzer", snap(t_v + 10 * FR), -13)
    sfx("buzzer", snap(t_m + 6 * FR), -13)
    return [camera(t0, t_end, ch, push_in(t0)), red_flash(t_n), label("[Q1]", t_n, t_end)]


def scene_zimmer():
    """'BMW hat sich dafür trotzdem einfach Hans Zimmer geholt, also den Typen, der die Musik
    für „Interstellar" und „König der Löwen" gemacht hat.'"""
    t0, t_end = W("BMW"), W("Bei", 2)
    t_hz, t_mu, t_i, t_kg = W("Hans"), W("Musik", 2), W("Interstellar"), W("König")
    ch = [pop("ecar", t0, t_end, 540, 1470, 0.8, out=False),
          pop("man-in-tuxedo", t_hz, t_end, 540, 560, 0.6, out=False),
          pop("violin", t_mu, t_end, 170, 1180, 0.42, out=False),
          pop("trumpet", snap(t_mu + 2 * FR), t_end, 910, 1180, 0.42, out=False),
          pop("drum", snap(t_mu + 4 * FR), t_end, 960, 1730, 0.3, out=False),
          pop("ringed-planet", t_i, t_end, 190, 470, 0.45, out=False),
          pop("lion", t_kg, t_end, 890, 470, 0.45, out=False)]
    cam = camera(t0, t_end, ch, push_in(t0) + punch(t_hz, (540, 960), 1.0, 1.08))
    sfx("swoosh", t0, -12)
    sfx("impact_low", t_hz, -6)
    sfx("magic_glide", t_mu, -16)
    for t in (t_i, t_kg):
        sfx("pop", t, -11)
    return [cam, label("[Q3]", t_hz, t_end)]


def scene_hybrid():
    """'Bei Hybriden wird es dann absurd, denn wenn da der Benziner schon läuft, darf das System
    keinen Extra-Ton machen, sonst würde das Auto ja doppelt brummen.'"""
    t0, t_end = W("Bei", 2), W("Und", 2)
    t_hy, t_be, t_k, t_x, t_d = W("Hybriden"), W("Benziner"), W("keinen"), W("Extra-Ton"), W("doppelt")
    puffs = [pop("dashing-away", snap(t_be + i * 0.35), snap(t_be + i * 0.35 + 0.5), 1010, 1500 - 30 * (i % 2),
                 0.4 + 0.05 * (i % 2)) for i in range(int((t_d - t_be) / 0.35))]
    single = [{"t": t0, "x": 540, "y": 1440, "scale": 0.8}] + shake(t_be, t_d, 540, 1440, 4, s=0.8, every=1)
    car = img("automobile", t0, t_d, single)
    duo = [img("automobile", t_d, t_end, pop_keys(t_d, 300, 1450, 0.5) + shake(snap(t_d + 7 * FR), t_end, 300, 1450, 8)),
           img("automobile", t_d, t_end, pop_keys(snap(t_d + 2 * FR), 780, 1450, 0.5) +
               shake(snap(t_d + 9 * FR), t_end, 780, 1450, 8))]
    ch = [pop("hybrid", t_hy, t_k, 540, 520, 0.72),
          car, *puffs, *duo,
          pop("loudspeaker", t_k, t_d, 540, 520, 0.55),
          pop("ban", t_x, t_d, 540, 520, 0.65)]
    cam = camera(t0, t_end, ch, push_in(t0))
    sfx("swoosh", t0, -12)
    sfx("pop", t_hy, -11)
    sfx("engine_pass", t_be, -9)
    sfx("buzzer", t_k, -12)
    sfx("pop", t_x, -11)
    sfx("drone_low", t_d, -13)
    return [cam, red_flash(t_k), label("[Q1]", t_hy, t_end)]


def scene_ending():
    """'Und ältere E-Autos von vor 2021 dürfen übrigens weiterhin komplett lautlos fahren,
    also wenn du auf dem Parkplatz gar nichts hörst, heißt das nicht, dass da nichts kommt, denn …'"""
    t0, t_end = W("Und", 2), DUR
    t_e, t_v, t_l, t_p, t_h, t_k, t_dn = W("ältere"), W("vor"), W("lautlos", 2), W("Parkplatz", 1), \
        W("hörst", 2), W("kommt"), W("denn", 2)
    car = img("ecar", t0, t_p, pop_keys(t_e, 540, 1430, CAR_S) +
              [{"t": t_e, "tint": [140, 140, 140, 0.0]}, {"t": snap(t_e + 6 * FR), "tint": [150, 140, 120, 0.55]}])
    dark = {"id": "night", "type": "solid", "start": t_p, "end": t_end, "color": [14, 18, 38],
            "keys": [{"t": t_p, "opacity": 0.0}, {"t": snap(t_p + 9 * FR), "opacity": 0.82, "ease": "out"}]}
    lights = [glow(t_k, t_end, x, 1450, 60, keys=[{"t": t_k, "x": x, "y": 1450, "radius": 10},
                                                 {"t": snap(t_k + 5 * FR), "x": x, "y": 1450, "radius": 120,
                                                  "ease": "out"}])
              for x in (700, 930)]
    ch = [car,
          pop("cal_old", t_v, t_l, 540, 500, 0.7),
          pop("muted-speaker", t_l, t_p, 540, 500, 0.6),
          *ground(t_p, t_end),
          img("p_sign", t_p, t_end, [{"t": t_p, "x": 160, "y": 1080, "scale": 0.75}]),
          dark,
          pop("ear", t_h, t_k, 540, 520, 0.55),
          *lights]
    cam = camera(t0, t_end, ch, push_in(t0) + [{"t": snap(t_dn - FR), "x": 540, "y": 960, "scale": 1.0},
                                               {"t": snap(t_dn + 2 * FR), "x": 540, "y": 960, "scale": 1.0}])
    cam["pivot"] = [815, 1450]
    cam["keys"] = [{"t": t0, "x": 815 + 1080, "y": 1450, "scale": 1.0},
                   {"t": snap(t0 + 3 * FR), "x": 815, "y": 1450, "ease": "out3"},
                   {"t": snap(t_dn - FR), "x": 815, "y": 1450, "scale": 1.0},
                   {"t": snap(t_dn + 2 * FR), "x": 700, "y": 1250, "scale": 1.6}]
    sfx("swoosh", t0, -12)
    sfx("pop", t_e, -11)
    sfx("pop", t_v, -11)
    sfx("pop", t_l, -11)
    sfx("drone_low", t_p, -16)
    sfx("pop", t_h, -12)
    sfx("ev_hum", t_k, -10)
    sfx("impact_low", t_dn, -5)
    return [cam]


# ------------------------------------------------------------------ captions + assembly
def captions():
    words = []
    for w in WORDS:
        t = w["text"].replace("„", "").replace("“", "").replace('"', "").replace("…", "").strip()
        if not t:
            continue
        item = {"text": t, "start": snap(w["start"]), "end": snap(w["end"])}
        if t.strip(",.").lower() in EMPHASIS:
            item["size"] = "big"
        words.append(item)
    for a, b in zip(words, words[1:]):     # no overlap after frame snapping
        a["end"] = min(a["end"], b["start"])
        if a["end"] <= a["start"]:
            a["end"] = snap(a["start"] + FR)
    words[-1]["end"] = DUR
    return [w for w in words if w["end"] > w["start"]]


def build():
    cap_style = dict(STYLE["caption"])
    layers = [{"id": "bg_stripes", "type": "stripes_bg", **STYLE["stripes_bg"]}]
    for sc in (scene_hook, scene_dumm, scene_parking, scene_law, scene_speed, scene_tyres, scene_db,
               scene_pitch, scene_bobbycar, scene_rules, scene_zimmer, scene_hybrid, scene_ending):
        layers += sc()
    layers.append(credit("GRAFIKEN: MICROSOFT FLUENT EMOJI (MIT) · STIMME: ELEVENLABS", 0, DUR))
    manifest = json.load(open(os.path.join(PROJ, "assets", "manifest.json"), encoding="utf-8"))
    tl = {
        "meta": {"title": "Elektroautos dürfen nicht leise sein", "fps": FPS, "width": 1080, "height": 1920,
                 "duration": DUR},
        "assets": manifest,
        "layers": layers,
        "captions": {"style": cap_style, "words": captions()},
        "audio": [{"id": "voice", "src": "audio/voice.flac", "start": 0.0, "gain_db": 0.0}] +
                 sorted(AUDIO, key=lambda a: a["start"]),
        "sources": {
            "Q1": "Verordnung (EU) Nr. 540/2014, Anhang VIII (AVAS)",
            "Q2": "UN-ECE-Regelung Nr. 138 (Mindest-/Höchstpegel, Frequenzverschiebung)",
            "Q3": "BMW Group PressClub: BMW IconicSounds Electric (Hans Zimmer)",
        },
    }
    out = os.path.join(PROJ, "build", "timeline.json")
    json.dump(tl, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("wrote", out, f"{DUR} s, {len(layers)} layers, {len(AUDIO)} sfx")


if __name__ == "__main__":
    build()
