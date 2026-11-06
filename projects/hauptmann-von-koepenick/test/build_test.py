"""Stickman-Test (≈6 s, 9:16): Voigt läuft ins Bild, hat eine Idee, zeigt: „Ihr kommt jetzt mit!"

python3 projects/hauptmann-von-koepenick/test/build_test.py
python3 -m shortsfactory.audio.mix projects/hauptmann-von-koepenick/test/test_timeline.json /tmp/mix.wav
python3 -m shortsfactory.render projects/hauptmann-von-koepenick/test/test_timeline.json \
        projects/hauptmann-von-koepenick/output/voigt_test.mp4 --audio /tmp/mix.wav
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", ".."))
from shortsfactory.stickman.rig import DEFAULT_SPEC, _ik  # noqa: E402

S = DEFAULT_SPEC
FEET_Y, SCALE = 1880, 0.85
HEAD = (540, FEET_Y + S["head_y"] * SCALE)          # head centre in design px


def arm_angles(target, side=1):
    """Shoulder/elbow angles that put the hand on `target` (local units)."""
    sh = (side * S["shoulder_x"], S["shoulder_y"])
    el, wr = _ik(sh[0], sh[1], target[0], target[1], S["upper_arm"], S["forearm"], side)
    a = math.degrees(math.atan2((el[0] - sh[0]) * side, el[1] - sh[1]))
    b = math.degrees(math.atan2((wr[0] - el[0]) * side, wr[1] - el[1]))
    return a, b - a


chin_a, chin_e = arm_angles((30, -690))

# Untertitel-Stil wie in den Referenzvideos (docs/STYLE_GUIDE.md)
CAPTION_STYLE = {"font": "league-spartan-700", "size": 64, "sizes": {"big": 96}, "y": 961,
                 "fill": [255, 255, 255], "stroke": [25, 25, 25], "stroke_w": 2.25,
                 "shadow": {"dx": 2.5, "dy": 3.5, "blur": 1.5, "color": [0, 0, 0], "alpha": 0.8},
                 "uppercase": True}

voigt_keys = [
    # walk in
    {"t": 0.0, "x": -160, "y": FEET_Y, "scale": SCALE, "walk": 1.0, "facing": 1, "look": 0.55,
     "expression": "grim", "arm_r": 9, "elbow_r": 4, "arm_l": 9, "lean": 3, "head_rot": 0,
     "handshape_r": "open", "thought": 0.0},
    {"t": 2.0, "x": 540, "ease": "out"},
    {"t": 1.85, "walk": 1.0},
    {"t": 2.15, "walk": 0.0, "lean": 0, "ease": "out"},
    {"t": 2.1, "facing": 0},
    {"t": 2.0, "look": 0.55},
    {"t": 2.25, "look": 0.0, "ease": "out"},
    # idea: hand to chin, thought bubble
    {"t": 2.35, "arm_r": 9, "elbow_r": 4, "expression": "grim", "head_rot": 0, "thought": 0.0},
    {"t": 2.65, "arm_r": chin_a, "elbow_r": chin_e, "head_rot": -7, "ease": "back_out"},
    {"t": 2.5, "thought": 0.0},
    {"t": 2.75, "thought": 1.0, "ease": "back_out"},
    {"t": 3.05, "expression": "sly", "look": 0.0},
    {"t": 3.35, "look": 0.35, "ease": "inout"},
    {"t": 3.55, "thought": 1.0},
    {"t": 3.68, "thought": 0.0, "ease": "in"},
    # command: point + shout
    {"t": 3.6, "arm_r": chin_a, "elbow_r": chin_e, "head_rot": -7, "lean": 0},
    {"t": 3.72, "arm_r": 84, "elbow_r": 2, "head_rot": 5, "lean": -4, "look": 0.45, "ease": "out3"},
    {"t": 3.7, "expression": "angry", "handshape_r": "point"},
    {"t": 5.0, "head_rot": 5},
    {"t": 5.25, "head_rot": 0, "lean": 0, "ease": "inout"},
    {"t": 5.15, "expression": "angry"},
    {"t": 5.3, "expression": "sly"},
]

camera = [  # punch zoom on the command (2 frames, linear), relative to the head
    {"t": 0.0, "scale": 1.0},
    {"t": 3.72, "scale": 1.0},
    {"t": 3.79, "scale": 1.32},
    {"t": 5.2, "scale": 1.32},
    {"t": 5.27, "scale": 1.0},
]

words = [  # (text, start, end, size)
    ("WILHELM", 0.25, 0.7), ("VOIGT.", 0.7, 1.2), ("SCHUSTER.", 1.3, 1.8), ("PLEITE.", 1.85, 2.3, "big"),
    ("UND", 2.45, 2.62), ("DANN", 2.62, 2.85), ("HAT", 2.85, 3.0), ("ER", 3.0, 3.12), ("'NE", 3.12, 3.3),
    ("IDEE.", 3.3, 3.62, "big"),
    ("IHR", 3.75, 4.0), ("KOMMT", 4.0, 4.3), ("JETZT", 4.3, 4.62), ("MIT!", 4.62, 5.15, "big"),
]

tl = {
    "meta": {"fps": 30, "width": 1080, "height": 1920, "duration": 6.0},
    "assets": {},
    "layers": [
        {"id": "camera", "type": "group", "pivot": list(HEAD),
         "keys": [dict(k, x=HEAD[0], y=HEAD[1]) for k in camera],
         "children": [
             {"id": "street", "type": "scene_street", "ground": FEET_Y,
              "keys": [{"t": 0.0, "pan": 0.0}, {"t": 2.0, "pan": 260.0, "ease": "out"}]},
             {"id": "voigt", "type": "stickman", "character": "characters/voigt_zivil.json",
              "auto": {"blink": True, "breathe": True, "talk": [[3.75, 5.1]], "seed": 3},
              "keys": voigt_keys},
         ]},
    ],
    "captions": {"style": CAPTION_STYLE,
                 "words": [{"text": w[0], "start": w[1], "end": w[2], **({"size": w[3]} if len(w) > 3 else {})}
                           for w in words]},
    "audio": [
        {"src": "@sfx/swoosh", "start": 0.0, "gain_db": -16},
        {"src": "@sfx/pop", "start": 2.55, "gain_db": -8},
        {"src": "@sfx/swoosh", "start": 3.62, "gain_db": -10},
        {"src": "@sfx/impact_low", "start": 3.72, "gain_db": -6},
    ],
}

# keys must be time-sorted for the interpolator
tl["layers"][0]["children"][1]["keys"].sort(key=lambda k: k["t"])
out = os.path.join(HERE, "test_timeline.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(tl, f, ensure_ascii=False, indent=1)
print("wrote", out)
