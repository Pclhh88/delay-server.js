"""Untertitel (ASS) aus voice/words.json nach docs/STYLE_GUIDE.md: ein Wort pro Einblendung, Versalien,
League Spartan 700, weiß mit dunkler Kontur + weichem Schatten, harte Wechsel zum Wortbeginn, Betonungswörter 1,35x (lange 1,15x).
Position: horizontal zentriert, vertikal bei 68 % (Cartoon-Format: Gesichter sitzen in der Bildmitte).

python3 projects/helgoland/make_subs.py  ->  projects/helgoland/subs.ass
Einbrennen: ffmpeg -i video.mp4 -vf "subtitles=projects/helgoland/subs.ass:fontsdir=shortsfactory/fonts" ...
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
words = json.load(open(os.path.join(HERE, "voice", "words.json")))

# Zahlen: <= 12 als Wort, sonst Ziffern (STYLE_GUIDE)
NUM = {"siebentausend": "7.000", "viertausend": "4.000", "neuntausend": "9.000", "neunzigtausend": "90.000", "dreizehn": "13"}
EMPH = {"STEHEN", "KNOPF", "GESCHICHTE", "WEG", "STEHT", "PORÖS", "SOFAKISSEN", "GLASSCHEIBE", "ZURÜCK", "ZOLLFREI", "FLAGGEN"}

def label(w):
    core = re.sub(r"[.,:;–!]+$", "", w)
    q = core.endswith("?")
    core = core.rstrip("?")
    core = NUM.get(core.lower(), core)
    return core.upper() + ("?" if q else "")

def ts(t):
    t = max(0.0, t)
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"

lines = []
for i, w in enumerate(words):
    s = w["s"]
    nxt = words[i + 1]["s"] if i + 1 < len(words) else w["e"] + 0.3
    e = nxt if nxt - w["e"] < 0.35 else w["e"] + 0.12   # Sprechpause = Untertitel-Lücke
    txt = label(w["w"])
    size = (r"{\fscx135\fscy135}" if len(txt) <= 7 else r"{\fscx115\fscy115}") if txt.rstrip("?") in EMPH else ""
    lines.append(f"Dialogue: 0,{ts(s)},{ts(e)},Word,,0,0,0,,{{\\pos(540,1306)}}{size}{txt}")

head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Word,League Spartan,118,&H00FFFFFF,&H00FFFFFF,&H00261A22,&H96000000,-1,0,0,0,100,100,1,0,1,6,4,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
open(os.path.join(HERE, "subs.ass"), "w").write(head + "\n".join(lines) + "\n")
print(len(lines), "Einblendungen")
