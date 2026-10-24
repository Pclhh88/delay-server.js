"""Image assets for "Elektroautos dürfen nicht leise sein".

* Emoji: Microsoft Fluent Emoji (MIT), SVG sources in ../assets/src/.
* Own graphics (E-Auto badge, EU flag, calendar, tacho, dB meter, tyre, bubble ...)
  are written here as SVG.
Everything is rasterised with the pre-installed Chromium (Playwright) into
../assets/png/ and listed in ../assets/manifest.json.

    python3 projects/elektroauto-sound/build/build_assets.py
"""
import json
import math
import os
import subprocess

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PROJ))
SRC = os.path.join(PROJ, "assets", "src")
PNG = os.path.join(PROJ, "assets", "png")
GEN = os.path.join(HERE, "_svg")
FONT = os.path.join(ROOT, "shortsfactory", "fonts", "league-spartan-latin-{w}-normal.woff")

EMOJI_LICENSE = "MIT (Microsoft Fluent Emoji)"
OWN = "own (generated in build_assets.py)"

FONT_CSS = "".join(
    f"@font-face{{font-family:LS{w};src:url('file://{FONT.format(w=w)}')}}" for w in (400, 700, 800))


def svg(w, h, body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}"><defs><style>{FONT_CSS}</style>{defs}</defs>'
            f'{body}</svg>')


def emoji_inner(name):
    """<svg> element of an emoji (viewBox 32x32) for nesting."""
    s = open(os.path.join(SRC, name + ".svg"), encoding="utf-8").read()
    return s.replace("<svg ", "<svg ", 1)


def nest(name, x, y, size):
    s = emoji_inner(name)
    # unique ids: emoji gradients use ids like "a", "b" ... -> prefix them
    pre = name.replace("-", "_") + "_"
    import re
    s = re.sub(r'id="([^"]+)"', lambda m: f'id="{pre}{m.group(1)}"', s)
    s = re.sub(r'url\(#([^)]+)\)', lambda m: f'url(#{pre}{m.group(1)})', s)
    s = re.sub(r'href="#([^"]+)"', lambda m: f'href="#{pre}{m.group(1)}"', s)
    return s.replace("<svg ", f'<svg x="{x}" y="{y}" width="{size}" height="{size}" ', 1)


def star(cx, cy, r):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.382
        pts.append(f"{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}")
    return " ".join(pts)


# ------------------------------------------------------------------ own graphics
def g_ecar():
    """Fluent car (faces left) with a green "E" lightning badge on the door."""
    bolt = "M0,-30 L-14,4 L-2,4 L-8,30 L14,-6 L2,-6 L8,-30 Z"
    body = (nest("automobile", 0, 0, 1000)
            + '<g transform="translate(560,560)"><circle r="78" fill="#1fb35b" stroke="#fff" stroke-width="12"/>'
              f'<path d="{bolt}" transform="scale(1.9)" fill="#fff"/></g>')
    return svg(1000, 1000, body)


def g_eu_flag():
    stars = "".join(f'<polygon points="{star(450 + 200 * math.cos(i * math.pi / 6), 300 + 200 * math.sin(i * math.pi / 6), 34)}" fill="#FFCC00"/>'
                    for i in range(12))
    return svg(900, 600, f'<rect width="900" height="600" rx="36" fill="#003399"/>{stars}')


def g_calendar(month, year):
    body = (
        '<rect x="20" y="40" width="660" height="700" rx="70" fill="#000" opacity="0.18"/>'
        '<rect x="0" y="20" width="660" height="700" rx="70" fill="#fff"/>'
        '<path d="M0,90 a70,70 0 0 1 70,-70 h520 a70,70 0 0 1 70,70 v130 h-660 Z" fill="#e8343b"/>'
        f'<text x="330" y="185" font-family="LS800" font-size="130" fill="#fff" text-anchor="middle">{month}</text>'
        f'<text x="330" y="560" font-family="LS800" font-size="230" fill="#222" text-anchor="middle">{year}</text>'
        '<circle cx="170" cy="40" r="26" fill="#9aa"/><circle cx="490" cy="40" r="26" fill="#9aa"/>')
    return svg(700, 760, body)


def g_tacho():
    """Speedo 0-120 km/h over 270 degrees, green band 0-20."""
    cx = cy = 450
    R = 400
    a0, sweep, vmax = 135.0, 270.0, 120.0

    def pt(v, r):
        a = math.radians(a0 + sweep * v / vmax)
        return cx + r * math.cos(a), cy + r * math.sin(a)

    def arc(v0, v1, r):
        x0, y0 = pt(v0, r)
        x1, y1 = pt(v1, r)
        large = 1 if sweep * (v1 - v0) / vmax > 180 else 0
        return f"M{x0:.1f},{y0:.1f} A{r},{r} 0 {large} 1 {x1:.1f},{y1:.1f}"

    b = [f'<circle cx="{cx}" cy="{cy}" r="{R + 30}" fill="#2b2f3a"/>',
         f'<circle cx="{cx}" cy="{cy}" r="{R + 10}" fill="#11141b"/>',
         f'<path d="{arc(0, 20, R - 40)}" stroke="#2ee66b" stroke-width="56" fill="none"/>']
    for v in range(0, 121, 5):
        r0 = R - 10
        r1 = R - (70 if v % 20 == 0 else 45)
        x0, y0 = pt(v, r0)
        x1, y1 = pt(v, r1)
        b.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="#fff" '
                 f'stroke-width="{10 if v % 20 == 0 else 5}"/>')
        if v % 20 == 0:
            tx, ty = pt(v, R - 125)
            b.append(f'<text x="{tx:.1f}" y="{ty + 22:.1f}" font-family="LS700" font-size="64" fill="#fff" '
                     f'text-anchor="middle">{v}</text>')
    b.append(f'<text x="{cx}" y="{cy + 250}" font-family="LS700" font-size="60" fill="#9aa3b5" text-anchor="middle">km/h</text>')
    return svg(900, 900, "".join(b))


def g_needle():
    """Needle pointing up, pivot at (60, 380)."""
    return svg(120, 440, '<polygon points="60,0 82,380 38,380" fill="#ff2a2a"/>'
                         '<circle cx="60" cy="380" r="50" fill="#e6e8ee"/><circle cx="60" cy="380" r="22" fill="#2b2f3a"/>')


def g_meter(on):
    """Vertical level meter, 0 dB bottom .. 100 dB top, 25 segments."""
    b = ['<rect width="360" height="1160" rx="50" fill="#1b1e27"/>']
    n = 25
    for i in range(n):
        v = (i + 0.5) / n
        col = "#2ee66b" if v < 0.56 else ("#ffd23f" if v < 0.75 else "#ff3b3b")
        y = 1100 - (i + 1) * 42
        b.append(f'<rect x="50" y="{y + 6}" width="260" height="32" rx="8" fill="{col}" opacity="{1 if on else 0.18}"/>')
    return svg(360, 1160, "".join(b))


def g_tyre():
    b = ['<circle cx="400" cy="400" r="390" fill="#1d1d22"/>',
         '<circle cx="400" cy="400" r="380" fill="none" stroke="#33343c" stroke-width="18" stroke-dasharray="30 26"/>',
         '<circle cx="400" cy="400" r="230" fill="#c9ced8"/>',
         '<circle cx="400" cy="400" r="200" fill="#9aa1ad"/>']
    for i in range(5):
        a = math.radians(-90 + 72 * i)
        b.append(f'<line x1="400" y1="400" x2="{400 + 190 * math.cos(a):.1f}" y2="{400 + 190 * math.sin(a):.1f}" '
                 'stroke="#dfe3ea" stroke-width="58" stroke-linecap="round"/>')
    b.append('<circle cx="400" cy="400" r="70" fill="#5b616d"/><circle cx="400" cy="400" r="30" fill="#2b2f3a"/>')
    return svg(800, 800, "".join(b))


def g_waves(color="#ffffff"):
    """Three sound-wave arcs ")))" opening to the right, origin left-centre."""
    b = []
    for i, r in enumerate((120, 240, 360)):
        a = math.radians(40)
        x0, y0 = 40 + r * math.cos(-a), 400 + r * math.sin(-a)
        x1, y1 = 40 + r * math.cos(a), 400 + r * math.sin(a)
        b.append(f'<path d="M{x0:.1f},{y0:.1f} A{r},{r} 0 0 1 {x1:.1f},{y1:.1f}" stroke="#1b1e27" stroke-width="64" '
                 'fill="none" stroke-linecap="round"/>')
        b.append(f'<path d="M{x0:.1f},{y0:.1f} A{r},{r} 0 0 1 {x1:.1f},{y1:.1f}" stroke="{color}" stroke-width="40" '
                 'fill="none" stroke-linecap="round"/>')
    return svg(440, 800, "".join(b))


def g_bobbycar():
    b = ['<ellipse cx="450" cy="470" rx="380" ry="26" fill="#000" opacity="0.18"/>',
         '<path d="M90,330 C90,250 150,220 240,215 L520,205 C600,200 650,170 700,170 C790,170 840,240 840,320 '
         'C840,380 800,400 760,400 L140,400 C110,400 90,380 90,330 Z" fill="#e3202b"/>',
         '<path d="M240,215 L520,205 C560,203 590,195 620,185 L600,250 L250,262 Z" fill="#ff5a5f" opacity="0.6"/>',
         '<rect x="640" y="70" width="26" height="130" rx="12" fill="#222" transform="rotate(-18 653 200)"/>',
         '<ellipse cx="625" cy="70" rx="80" ry="24" fill="#f4f4f4" stroke="#222" stroke-width="12" transform="rotate(-18 625 70)"/>',
         '<rect x="110" y="300" width="70" height="40" rx="12" fill="#ffd23f"/>']
    for x in (230, 690):
        b.append(f'<circle cx="{x}" cy="410" r="72" fill="#1d1d22"/><circle cx="{x}" cy="410" r="30" fill="#e6e8ee"/>')
    return svg(900, 500, "".join(b))


def g_bubble(text):
    b = ('<path d="M120,40 H900 a90,90 0 0 1 90,90 V330 a90,90 0 0 1 -90,90 H330 L170,520 L210,420 H120 '
         'a90,90 0 0 1 -90,-90 V130 a90,90 0 0 1 90,-90 Z" fill="#fff" stroke="#1b1e27" stroke-width="18"/>'
         f'<text x="510" y="290" font-family="LS800" font-size="170" fill="#e3202b" text-anchor="middle">{text}</text>')
    return svg(1020, 540, b)


def g_graph():
    """Axes for "Tonhöhe über Tempo"."""
    b = ['<rect width="900" height="760" rx="50" fill="#ffffff" opacity="0.92"/>',
         '<line x1="120" y1="640" x2="840" y2="640" stroke="#1b1e27" stroke-width="14" stroke-linecap="round"/>',
         '<line x1="120" y1="640" x2="120" y2="80" stroke="#1b1e27" stroke-width="14" stroke-linecap="round"/>',
         '<polygon points="860,640 815,615 815,665" fill="#1b1e27"/><polygon points="120,60 95,105 145,105" fill="#1b1e27"/>',
         '<text x="840" y="720" font-family="LS800" font-size="60" fill="#1b1e27" text-anchor="end">TEMPO</text>',
         '<text x="70" y="360" font-family="LS800" font-size="60" fill="#1b1e27" text-anchor="middle" '
         'transform="rotate(-90 70 360)">TON</text>']
    return svg(900, 760, "".join(b))


def g_curve():
    """Rising pitch curve, same frame as g_graph."""
    return svg(900, 760, '<path d="M130,600 C330,560 520,420 820,130" stroke="#e3202b" stroke-width="30" '
                         'fill="none" stroke-linecap="round"/>')


def g_pole_sign():
    return svg(400, 1100, '<rect x="185" y="300" width="30" height="800" fill="#7d8594"/>'
                          + nest("p-button", 0, 0, 400))


def g_hybrid():
    """Fuel pump and plug side by side with a plus."""
    return svg(1100, 560, nest("fuel-pump", 0, 30, 500) +
               '<text x="550" y="340" font-family="LS800" font-size="220" fill="#1b1e27" text-anchor="middle">+</text>'
               + nest("electric-plug", 600, 30, 500))


def g_ban():
    """Red 'no' sign with a transparent centre (the crossed-out object stays visible)."""
    return svg(700, 700, '<circle cx="350" cy="350" r="300" fill="none" stroke="#1b1e27" stroke-width="96" opacity="0.25"/>'
                         '<circle cx="350" cy="350" r="300" fill="none" stroke="#ff2d3b" stroke-width="70"/>'
                         '<line x1="138" y1="138" x2="562" y2="562" stroke="#ff2d3b" stroke-width="70"/>')


def g_ramp(axis, w, h):
    """Reveal map: 0 at the start, 1 at the end (x: left->right, y: bottom->top)."""
    if axis == "x":
        a = np.tile(np.linspace(0, 1, w), (h, 1))
    else:
        a = np.tile(np.linspace(1, 0, h)[:, None], (1, w))
    return (a * 255).astype(np.uint8)


EMOJI = {  # name -> render size (px)
    "old-woman": 700, "face-screaming-in-fear": 900, "shopping-cart": 600, "muted-speaker": 600,
    "loudspeaker": 700, "money-bag": 700, "globe-showing-europe-africa": 600, "green-heart": 400,
    "exploding-head": 900, "musical-note": 500, "musical-notes": 600, "child": 600, "control-knobs": 700,
    "check-mark-button": 400, "bird": 600, "prohibited": 700, "man-in-tuxedo": 800, "ringed-planet": 600,
    "lion": 600, "violin": 500, "trumpet": 500, "drum": 500, "fuel-pump": 600, "electric-plug": 600,
    "dashing-away": 500, "ear": 600, "ninja": 700, "collision": 600, "eyes": 500, "automobile": 1000,
    "anger-symbol": 400, "euro-banknote": 700, "face-with-spiral-eyes": 700, "speaker-high-volume": 600,
}

OWN_ASSETS = {  # name -> (svg, (w, h))
    "ecar": (g_ecar, (1000, 1000)),
    "eu_flag": (g_eu_flag, (900, 600)),
    "cal_2021": (lambda: g_calendar("JULI", "2021"), (700, 760)),
    "cal_old": (lambda: g_calendar("VOR", "2021"), (700, 760)),
    "tacho": (g_tacho, (900, 900)),
    "needle": (g_needle, (120, 440)),
    "meter_off": (lambda: g_meter(False), (360, 1160)),
    "meter_on": (lambda: g_meter(True), (360, 1160)),
    "tyre": (g_tyre, (800, 800)),
    "waves": (g_waves, (440, 800)),
    "waves_red": (lambda: g_waves("#ff3b3b"), (440, 800)),
    "bobbycar": (g_bobbycar, (900, 500)),
    "bubble": (lambda: g_bubble("BRRRMMM!"), (1020, 540)),
    "graph": (g_graph, (900, 760)),
    "curve": (g_curve, (900, 760)),
    "p_sign": (g_pole_sign, (400, 1100)),
    "hybrid": (g_hybrid, (1100, 560)),
    "ban": (g_ban, (700, 700)),
}


def main():
    os.makedirs(PNG, exist_ok=True)
    os.makedirs(GEN, exist_ok=True)
    jobs = []
    manifest = {}
    for name, size in EMOJI.items():
        p = os.path.join(GEN, f"{name}.svg")
        s = open(os.path.join(SRC, name + ".svg"), encoding="utf-8").read()
        open(p, "w", encoding="utf-8").write(s.replace("<svg ", f'<svg width="{size}" height="{size}" ', 1))
        jobs.append({"svg": p, "png": os.path.join(PNG, f"{name}.png"), "w": size, "h": size})
        manifest[name] = {"path": f"assets/png/{name}.png", "design_scale": 1.0, "license": EMOJI_LICENSE,
                          "source": f"assets/src/{name}.svg"}
    for name, (fn, (w, h)) in OWN_ASSETS.items():
        p = os.path.join(GEN, f"{name}.svg")
        open(p, "w", encoding="utf-8").write(fn())
        jobs.append({"svg": p, "png": os.path.join(PNG, f"{name}.png"), "w": w, "h": h})
        manifest[name] = {"path": f"assets/png/{name}.png", "design_scale": 1.0,
                          "license": OWN + ("; contains Fluent Emoji (MIT)" if name in ("ecar", "p_sign", "hybrid") else "")}
    for name, (axis, w, h) in {"ramp_x": ("x", 900, 760), "ramp_y": ("y", 360, 1160)}.items():
        Image.fromarray(g_ramp(axis, w, h)).save(os.path.join(PNG, f"{name}.png"))
        manifest[name] = {"path": f"assets/png/{name}.png", "design_scale": 1.0, "license": OWN}
    jf = os.path.join(GEN, "jobs.json")
    json.dump(jobs, open(jf, "w"))
    subprocess.run(["node", os.path.join(HERE, "render_svgs.js"), jf], check=True)
    json.dump(manifest, open(os.path.join(PROJ, "assets", "manifest.json"), "w"), indent=1, ensure_ascii=False)
    print(f"{len(manifest)} assets")


if __name__ == "__main__":
    main()
