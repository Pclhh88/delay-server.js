"""Testvideo Flensburg (12 s): 3D-Stadtflug (shortsfactory/city) + Titel, Label, Untertitel, SFX.

    node shortsfactory/city/render.js projects/flensburg-highlights/shots/test.json \
         projects/flensburg-highlights/output/frames_test
    python3 projects/flensburg-highlights/test/build_timeline.py
    python3 -m shortsfactory.audio.mix projects/flensburg-highlights/test/timeline.json \
         projects/flensburg-highlights/output/test_mix.wav
    python3 -m shortsfactory.render projects/flensburg-highlights/test/timeline.json \
         projects/flensburg-highlights/output/flensburg_test.mp4 \
         --audio projects/flensburg-highlights/output/test_mix.wav
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
FRAMES = "output/frames_test"

overlay = json.load(open(os.path.join(BASE, FRAMES, "overlay.json")))
fps = overlay["fps"]
n = len(overlay["frames"])
dur = n / fps

TITLE = {"font": "league-spartan-700", "fill": [255, 255, 255], "stroke": [25, 25, 25],
         "stroke_w": 3.0, "shadow": {"dx": 3, "dy": 5, "blur": 2.0, "color": [0, 0, 0], "alpha": 0.7}}
LABEL = {"font": "league-spartan-700", "fill": [255, 204, 46], "stroke": [25, 25, 25],
         "stroke_w": 3.0, "shadow": {"dx": 3, "dy": 4, "blur": 1.5, "color": [0, 0, 0], "alpha": 0.8}}


def follow(key, t0, t1, dy=0.0):
    """Keyframes, die der Bildschirmposition eines Wahrzeichens folgen"""
    keys = []
    for f in overlay["frames"]:
        if t0 - 1e-6 <= f["t"] <= t1 + 1e-6 and f["lm"].get(key):
            x, y = f["lm"][key]["top"]
            keys.append({"t": round(f["t"], 4), "x": round(x, 1), "y": round(y + dy, 1)})
    return keys


def pop_in(keys, t, dur=0.35):
    """Skalierungs-Pop über bestehende Positionskeys legen"""
    out = []
    for k in keys:
        k = dict(k)
        dt = k["t"] - t
        if dt < 0:
            k["scale"] = 0.0
        elif dt < dur:
            p = dt / dur
            c1, c3 = 1.70158, 2.70158
            k["scale"] = round(1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2, 4)
        else:
            k["scale"] = 1.0
        out.append(k)
    return out


T_POP = 6.25
label_keys = pop_in(follow("nordertor", T_POP, dur, dy=-95), T_POP)
pin_keys = pop_in(follow("nordertor", T_POP, dur, dy=-40), T_POP)

layers = [
    {"id": "city", "type": "sequence", "asset": "city", "start": 0, "end": dur, "fps": fps,
     "anchor": [0, 0], "keys": [{"t": 0, "x": 0, "y": 0}]},
    # Titel
    {"id": "title", "type": "text", "text": "FLENSBURG", "start": 0.15, "end": 2.6, "size": 150,
     "style": TITLE, "keys": [
         {"t": 0.15, "x": 540, "y": 360, "scale": 0.0},
         {"t": 0.5, "x": 540, "y": 360, "scale": 1.0, "ease": "back_out"},
         {"t": 2.3, "x": 540, "y": 360, "scale": 1.0},
         {"t": 2.6, "x": 540, "y": 360, "scale": 0.0, "ease": "in"}]},
    {"id": "subtitle", "type": "text", "text": "IN 60 SEKUNDEN", "start": 0.45, "end": 2.6, "size": 70,
     "style": dict(TITLE, fill=[255, 204, 46]), "keys": [
         {"t": 0.45, "x": 540, "y": 480, "scale": 0.0},
         {"t": 0.8, "x": 540, "y": 480, "scale": 1.0, "ease": "back_out"},
         {"t": 2.3, "x": 540, "y": 480, "scale": 1.0},
         {"t": 2.6, "x": 540, "y": 480, "scale": 0.0, "ease": "in"}]},
    # Label über dem Nordertor
    {"id": "label_nordertor", "type": "text", "text": "NORDERTOR", "start": T_POP, "end": dur, "size": 84,
     "style": LABEL, "keys": label_keys},
    # Pfeil (Dreieck mit dunkler Kontur) zeigt auf die Spitze
    {"id": "pin_nordertor_outline", "type": "polygon", "start": T_POP, "end": dur, "color": [25, 25, 25],
     "points": [[506, 938], [574, 938], [540, 988]], "keys": pin_keys},
    {"id": "pin_nordertor", "type": "polygon", "start": T_POP, "end": dur, "color": [255, 204, 46],
     "points": [[513, 942], [567, 942], [540, 981]], "keys": pin_keys},
]

# Untertitel Wort für Wort (Stil der Referenz: Großbuchstaben, Mitte unten)
words = [("DAS", 6.6), ("WAHRZEICHEN", 6.85), ("DER", 7.45), ("STADT.", 7.65, "big"),
         ("GEBAUT", 8.6), ("1595", 9.0, "big"), ("–", 9.6), ("UND", 9.75), ("BIS", 10.0),
         ("HEUTE", 10.2), ("DAS", 10.6), ("TOR", 10.8), ("ZUR", 11.05), ("ALTSTADT.", 11.25, "big")]
cap = []
for i, w in enumerate(words):
    end = words[i + 1][1] if i + 1 < len(words) else dur
    cap.append({"text": w[0], "start": w[1], "end": end, **({"size": w[2]} if len(w) > 2 else {})})

timeline = {
    "meta": {"fps": fps, "width": 1080, "height": 1920, "duration": dur,
             "title": "Flensburg – Testvideo (Isometrische Stadt)",
             "attribution": "Kartendaten © OpenStreetMap-Mitwirkende, Overture Maps Foundation (ODbL)"},
    "base_dir": ".",
    "assets": {"city": {"path": FRAMES + "/f{i:05d}.png", "frames": n, "design_scale": 1080 / overlay["width"],
                        "license": "own_render_odbl_data"}},
    "layers": layers,
    "captions": {"style": {"size": 64, "sizes": {"big": 92}, "y": 1480}, "words": cap},
    "audio": [
        {"src": "@sfx/pop", "start": 0.15, "gain_db": -8},
        {"src": "@sfx/pop", "start": 0.45, "gain_db": -10},
        {"src": "@sfx/swoosh", "start": 2.45, "gain_db": -10},
        {"src": "@sfx/swoosh", "start": 4.8, "gain_db": -13},
        {"src": "@sfx/impact_low", "start": T_POP, "gain_db": -10},
        {"src": "@sfx/pop", "start": T_POP + 0.05, "gain_db": -7},
    ],
}
out = os.path.join(HERE, "timeline.json")
json.dump(timeline, open(out, "w"), indent=1)
print("wrote", out, f"({n} Frames, {dur:.2f} s)")
