"""Prozedurale Comic-Grafiken im Stil map_doc (Referenz 3): Kegel-Figuren mit großem Kopf,
dünner dunkler Umriss, leichte Schattierung; Requisiten im selben Stil.

Alles wird 4x überabgetastet gezeichnet und verkleinert (glatte Kanten). Rückgabe: PIL RGBA.
Eigene Zeichnungen -> frei verwendbar.
"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SS = 4
OUTLINE = (52, 36, 28, 255)
FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")


def _font(name, px):
    import glob
    return ImageFont.truetype(glob.glob(os.path.join(FONT_DIR, name + "*"))[0], int(px))


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.im = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def s(self, pts):
        return [(x * SS, y * SS) for x, y in pts]

    def poly(self, pts, fill, outline=OUTLINE, width=2.2):
        self.d.polygon(self.s(pts), fill=fill)
        if outline:
            p = self.s(pts)
            self.d.line(p + [p[0]], fill=outline, width=int(width * SS), joint="curve")

    def ellipse(self, box, fill, outline=OUTLINE, width=2.2):
        x0, y0, x1, y1 = box
        self.d.ellipse([x0 * SS, y0 * SS, x1 * SS, y1 * SS], fill=fill,
                       outline=outline, width=int(width * SS) if outline else 0)

    def line(self, pts, fill=OUTLINE, width=2.0):
        self.d.line(self.s(pts), fill=fill, width=max(1, int(width * SS)), joint="curve")

    def text(self, xy, txt, font, px, fill, anchor="mm"):
        self.d.text((xy[0] * SS, xy[1] * SS), txt, font=_font(font, px * SS), fill=fill, anchor=anchor)

    def done(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)


def _bezier(p0, p1, p2, n=16):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in [i / n for i in range(n + 1)]]


def _shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3]) + (255,)


# --------------------------------------------------------------------------- figure
def figure(kind="lenape", w=120, h=210):
    """Kegel-Figur. kind: lenape | dutch | british"""
    c = Canvas(w, h)
    cx = w / 2
    skin = {"lenape": (176, 118, 82), "dutch": (246, 226, 208), "british": (246, 226, 208)}[kind]
    body = {"lenape": (196, 160, 118), "dutch": (34, 30, 30), "british": (178, 40, 38)}[kind]
    top, bot = h * 0.53, h * 0.97
    # Körper: abgerundeter Kegel
    left = _bezier((cx - w * 0.20, top), (cx - w * 0.30, h * 0.70), (cx - w * 0.36, bot))
    right = _bezier((cx + w * 0.36, bot), (cx + w * 0.30, h * 0.70), (cx + w * 0.20, top))
    bottom = _bezier((cx - w * 0.36, bot), (cx, bot + h * 0.04), (cx + w * 0.36, bot))
    c.poly(left + bottom[1:-1] + right, fill=body + (255,))
    # Schattenseite
    sh = _bezier((cx + w * 0.10, top + 4), (cx + w * 0.20, h * 0.72), (cx + w * 0.22, bot))
    c.poly(sh + right[::-1][1:], fill=_shade(body, 0.85), outline=None)
    if kind == "lenape":
        c.line([(cx - w * 0.17, top + h * 0.08), (cx, top + h * 0.20), (cx + w * 0.17, top + h * 0.08)],
               fill=(120, 84, 52, 255), width=2)
        for i in range(6):
            x = cx - w * 0.30 + i * w * 0.12
            c.line([(x, bot - h * 0.06), (x + 2, bot)], fill=(150, 112, 70, 255), width=1.5)
    elif kind == "dutch":
        c.poly([(cx - w * 0.12, top + 2), (cx + w * 0.12, top + 2), (cx, top + h * 0.12)], fill=(250, 250, 245, 255), width=1.5)
        c.poly([(cx - w * 0.08, top + h * 0.12), (cx + w * 0.08, top + h * 0.12), (cx + w * 0.12, bot - 6),
                (cx - w * 0.12, bot - 6)], fill=(70, 50, 36, 255), width=1.5)
    elif kind == "british":
        c.poly([(cx - w * 0.12, top + 2), (cx + w * 0.12, top + 2), (cx + w * 0.14, bot - 4), (cx - w * 0.14, bot - 4)],
               fill=(246, 236, 220, 255), width=1.5)
        for i in range(5):
            y = top + h * 0.06 + i * h * 0.075
            c.ellipse((cx - 2.2, y - 2.2, cx + 2.2, y + 2.2), fill=(200, 170, 80, 255), outline=None)
        c.line([(cx - w * 0.30, top + h * 0.30), (cx + w * 0.28, top + h * 0.05)], fill=(88, 58, 34, 255), width=4)
        c.line([(cx + w * 0.18, top + h * 0.11), (cx + w * 0.40, top - h * 0.02)], fill=(90, 90, 96, 255), width=2.5)
    # Kopf
    r = w * 0.27
    hy = h * 0.40
    c.ellipse((cx - r, hy - r, cx + r, hy + r), fill=skin + (255,))
    c.ellipse((cx - r * 0.15, hy - r * 0.95, cx + r * 0.95, hy + r * 0.9), fill=_shade(skin, 0.93), outline=None)
    c.ellipse((cx - r, hy - r, cx + r, hy + r), fill=None)
    # Gesicht
    for dx in (-0.35, 0.35):
        c.ellipse((cx + dx * r - 2.6, hy - 3.2, cx + dx * r + 2.6, hy + 2.6), fill=(30, 22, 20, 255), outline=None)
    c.line(_bezier((cx - r * 0.18, hy + r * 0.38), (cx, hy + r * 0.46), (cx + r * 0.18, hy + r * 0.38), 6), width=1.6)
    if kind == "lenape":
        hair = (34, 26, 24, 255)
        c.d.pieslice([(cx - r) * SS, (hy - r) * SS, (cx + r) * SS, (hy + r) * SS], 180, 360, fill=hair)
        c.poly([(cx - r, hy), (cx - r * 1.05, hy + r * 1.4), (cx - r * 0.7, hy + r * 1.3), (cx - r * 0.8, hy)], fill=hair, width=1.5)
        c.poly([(cx - r * 1.02, hy - r * 0.35), (cx + r * 1.02, hy - r * 0.35), (cx + r * 0.98, hy - r * 0.12),
                (cx - r * 0.98, hy - r * 0.12)], fill=(200, 150, 90, 255), width=1.5)
        for i in range(5):
            x = cx - r * 0.8 + i * r * 0.4
            c.line([(x, hy - r * 0.30), (x + 3, hy - r * 0.17)], fill=(170, 50, 40, 255), width=1.5)
        # Feder
        c.poly([(cx + r * 0.8, hy - r * 0.3), (cx + r * 1.25, hy - r * 1.35), (cx + r * 1.0, hy - r * 0.25)],
               fill=(250, 248, 240, 255), width=1.5)
    elif kind == "dutch":
        c.d.chord([(cx - r) * SS, (hy - r) * SS, (cx + r) * SS, (hy + r * 0.9) * SS], 190, 350, fill=(70, 46, 30, 255))
        c.ellipse((cx - r * 1.55, hy - r * 0.95, cx + r * 1.55, hy - r * 0.45), fill=(24, 22, 24, 255))
        c.poly([(cx - r * 0.85, hy - r * 0.75), (cx - r * 0.7, hy - r * 2.0), (cx + r * 0.7, hy - r * 2.0),
                (cx + r * 0.85, hy - r * 0.75)], fill=(24, 22, 24, 255))
        c.line(_bezier((cx - r * 0.45, hy + r * 0.25), (cx, hy + r * 0.05), (cx + r * 0.45, hy + r * 0.25), 8), width=3)
        c.line([(cx, hy + r * 0.55), (cx, hy + r * 0.8)], width=2.5)
    elif kind == "british":
        c.d.chord([(cx - r) * SS, (hy - r) * SS, (cx + r) * SS, (hy + r * 0.9) * SS], 190, 350, fill=(236, 232, 226, 255))
        c.poly([(cx - r * 1.45, hy - r * 0.55), (cx, hy - r * 1.75), (cx + r * 1.45, hy - r * 0.55), (cx, hy - r * 0.8)],
               fill=(26, 24, 28, 255))
        c.line([(cx - r * 1.35, hy - r * 0.6), (cx, hy - r * 0.86), (cx + r * 1.35, hy - r * 0.6)],
               fill=(220, 190, 90, 255), width=2)
    return c.done()


# --------------------------------------------------------------------------- props
def tipi(w=150, h=170):
    c = Canvas(w, h)
    cx = w / 2
    base, apex = h * 0.95, h * 0.18
    for dx in (-0.12, -0.04, 0.05, 0.13):
        c.line([(cx, apex + 6), (cx + dx * w * 1.4, h * 0.02)], fill=(110, 70, 40, 255), width=2.4)
    c.poly([(cx, apex), (cx + w * 0.46, base), (cx - w * 0.46, base)], fill=(232, 202, 160, 255))
    c.poly([(cx, apex), (cx + w * 0.46, base), (cx + w * 0.05, base)], fill=(214, 182, 140, 255), outline=None)
    for y0, col in ((0.38, (196, 70, 40, 255)), (0.80, (196, 70, 40, 255))):
        y = apex + (base - apex) * y0
        half = (y - apex) / (base - apex) * w * 0.46
        c.poly([(cx - half, y), (cx + half, y), (cx + half * 1.06, y + h * 0.05), (cx - half * 1.06, y + h * 0.05)],
               fill=col, width=1.4)
        for i in range(5):
            x = cx - half * 0.8 + i * half * 0.4
            c.poly([(x, y + 1), (x + 4, y + h * 0.025), (x, y + h * 0.045), (x - 4, y + h * 0.025)], fill=(240, 200, 90, 255), outline=None)
    c.poly([(cx, apex + h * 0.25), (cx + w * 0.15, base), (cx - w * 0.15, base)], fill=(90, 52, 34, 255))
    c.poly([(cx, apex), (cx + w * 0.46, base), (cx - w * 0.46, base)], fill=None)
    return c.done()


def tree(w=120, h=220, seed=0):
    import random
    rnd = random.Random(seed)
    c = Canvas(w, h)
    cx = w / 2
    c.poly([(cx - 4, h * 0.98), (cx + 4, h * 0.98), (cx + 2, h * 0.25), (cx - 2, h * 0.25)], fill=(120, 74, 40, 255), width=1.5)
    greens = [(88, 150, 40), (110, 175, 50), (140, 200, 70)]
    for i in range(14):
        y = h * (0.12 + 0.5 * rnd.random())
        x = cx + (rnd.random() - 0.5) * w * 0.7
        r = w * (0.13 + 0.08 * rnd.random())
        col = greens[min(2, int(rnd.random() * 3))] + (255,)
        c.ellipse((x - r, y - r * 0.8, x + r, y + r * 0.8), fill=col, outline=(50, 80, 30, 255), width=1.2)
    return c.done()


def rocks(w=160, h=110):
    c = Canvas(w, h)
    for (x, y, s) in ((0.30, 0.62, 0.30), (0.62, 0.55, 0.36), (0.48, 0.80, 0.28)):
        cx, cy, r = x * w, y * h, s * w * 0.6
        pts = [(cx - r, cy + r * 0.3), (cx - r * 0.7, cy - r * 0.6), (cx + r * 0.1, cy - r * 0.9),
               (cx + r * 0.9, cy - r * 0.3), (cx + r, cy + r * 0.4), (cx, cy + r * 0.7)]
        c.poly(pts, fill=(150, 152, 158, 255))
        c.poly([pts[1], pts[2], (cx + r * 0.1, cy - r * 0.1), (cx - r * 0.5, cy)], fill=(196, 198, 204, 255), outline=None)
        c.poly(pts, fill=None)
    return c.done()


def cliff(w=150, h=200):
    c = Canvas(w, h)
    pts = [(w * 0.05, h * 0.98), (w * 0.55, h * 0.05), (w * 0.95, h * 0.98)]
    c.poly(pts, fill=(80, 80, 84, 255))
    c.poly([(w * 0.55, h * 0.05), (w * 0.95, h * 0.98), (w * 0.62, h * 0.98)], fill=(56, 56, 60, 255), outline=None)
    for i in range(10):
        x = w * (0.2 + 0.06 * i)
        c.line([(x, h * 0.95), (w * 0.55 + (x - w * 0.55) * 0.3, h * 0.35)], fill=(120, 120, 126, 255), width=1)
    c.poly(pts, fill=None)
    return c.done()


def swamp(w=260, h=170, seed=1):
    import random
    rnd = random.Random(seed)
    c = Canvas(w, h)
    pts = []
    for i in range(18):
        a = i / 18 * 2 * math.pi
        r = 0.42 + 0.06 * math.sin(i * 2.3) + 0.03 * rnd.random()
        pts.append((w / 2 + math.cos(a) * w * r, h * 0.62 + math.sin(a) * h * r * 0.6))
    c.poly(pts, fill=(78, 64, 40, 255), outline=(50, 40, 26, 255))
    for i in range(30):
        x, y = w * (0.2 + 0.6 * rnd.random()), h * (0.45 + 0.35 * rnd.random())
        c.ellipse((x - 3, y - 2, x + 3, y + 2), fill=(96, 100, 52, 255), outline=None)
    for i in range(6):
        x = w * (0.25 + 0.1 * i + 0.03 * rnd.random())
        y = h * (0.45 + 0.1 * rnd.random())
        c.line([(x, y), (x - 2, y - h * 0.32)], fill=(90, 110, 50, 255), width=1.6)
        c.ellipse((x - 4, y - h * 0.38, x + 2, y - h * 0.26), fill=(120, 80, 40, 255), outline=None)
    return c.done()


def footprint(w=18, h=30, flip=False):
    c = Canvas(w, h)
    c.ellipse((w * 0.2, h * 0.3, w * 0.8, h * 0.98), fill=(92, 62, 40, 230), outline=None)
    for i in range(4):
        x = w * (0.22 + 0.17 * i)
        c.ellipse((x - 2, h * 0.08, x + 2, h * 0.24), fill=(92, 62, 40, 230), outline=None)
    im = c.done()
    return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im


def sign(text_lines=("Wickquasgeck", "Trail"), w=260, h=300):
    c = Canvas(w, h)
    wood, dark = (214, 132, 62, 255), (160, 90, 40, 255)
    c.poly([(w * 0.46, h * 0.18), (w * 0.54, h * 0.18), (w * 0.54, h * 0.98), (w * 0.46, h * 0.98)], fill=wood, width=1.6)
    bw, bh = w * 0.92, h * 0.26
    x0, y0 = (w - bw) / 2, h * 0.08
    c.poly([(x0, y0), (x0 + bw, y0 + 4), (x0 + bw - 3, y0 + bh), (x0 + 2, y0 + bh - 3)], fill=wood, width=1.8)
    for i in range(3):
        y = y0 + bh * (0.25 + 0.25 * i)
        c.line([(x0 + 8, y), (x0 + bw - 10, y + 2)], fill=dark, width=1)
    for i, t in enumerate(text_lines):
        c.text((w / 2, y0 + bh * (0.33 + 0.40 * i)), t, "playfair-display-latin-700", bh * 0.34, (72, 40, 22, 255))
    return c.done()


def barrel(w=70, h=86):
    c = Canvas(w, h)
    body = (150, 92, 48, 255)
    c.poly([(w * 0.18, h * 0.12), (w * 0.82, h * 0.12), (w * 0.92, h * 0.5), (w * 0.82, h * 0.9),
            (w * 0.18, h * 0.9), (w * 0.08, h * 0.5)], fill=body)
    for y in (0.25, 0.75):
        c.line([(w * 0.12, h * y), (w * 0.88, h * y)], fill=(70, 50, 40, 255), width=2.5)
    for x in (0.35, 0.55, 0.72):
        c.line([(w * x, h * 0.14), (w * x, h * 0.88)], fill=(120, 72, 36, 255), width=1)
    c.ellipse((w * 0.18, h * 0.04, w * 0.82, h * 0.20), fill=(186, 120, 66, 255))
    return c.done()


def crate(w=80, h=70):
    c = Canvas(w, h)
    c.poly([(4, h * 0.3), (w * 0.55, h * 0.3), (w * 0.55, h - 3), (4, h - 3)], fill=(132, 92, 58, 255))
    c.poly([(w * 0.55, h * 0.3), (w - 3, h * 0.12), (w - 3, h * 0.8), (w * 0.55, h - 3)], fill=(104, 70, 44, 255))
    c.poly([(4, h * 0.3), (w * 0.4, h * 0.12), (w - 3, h * 0.12), (w * 0.55, h * 0.3)], fill=(160, 116, 74, 255))
    return c.done()


def ruler(length=900, width=110):
    c = Canvas(width, length)
    c.poly([(0, 0), (width, 0), (width, length), (0, length)], fill=(250, 212, 30, 255), outline=(60, 50, 10, 255), width=2)
    n = 100
    for i in range(n + 1):
        y = length - 30 - i * (length - 60) / n
        L = width * (0.42 if i % 10 == 0 else 0.26 if i % 5 == 0 else 0.15)
        c.line([(0, y), (L, y)], fill=(20, 20, 20, 255), width=2.4 if i % 10 == 0 else 1.4)
        if i % 10 == 0:
            c.text((width * 0.66, y), str(i // 10), "roboto-latin-700-normal", width * 0.32, (20, 20, 20, 255))
    im = c.done()
    return im


def pencil(length=520, width=40):
    c = Canvas(length, width)
    y0, y1 = width * 0.15, width * 0.85
    c.poly([(length * 0.14, y0), (length * 0.92, y0), (length * 0.92, y1), (length * 0.14, y1)], fill=(250, 196, 40, 255), width=1.6)
    c.poly([(length * 0.14, width * 0.5), (length * 0.92, width * 0.5), (length * 0.92, y1), (length * 0.14, y1)], fill=(232, 168, 30, 255), outline=None)
    c.poly([(length * 0.92, y0), (length, y0), (length, y1), (length * 0.92, y1)], fill=(240, 150, 160, 255), width=1.6)
    c.poly([(length * 0.88, y0), (length * 0.93, y0), (length * 0.93, y1), (length * 0.88, y1)], fill=(190, 190, 196, 255), width=1.2)
    c.poly([(length * 0.14, y0), (length * 0.14, y1), (length * 0.01, width * 0.5)], fill=(236, 200, 150, 255), width=1.6)
    c.poly([(length * 0.05, width * 0.42), (length * 0.05, width * 0.58), (0, width * 0.5)], fill=(40, 40, 40, 255), outline=None)
    return c.done()


def question(px=160, color=(250, 230, 40)):
    w = int(px * 0.8)
    h = int(px * 1.2)
    c = Canvas(w, h)
    sh = Image.new("RGBA", c.im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((w / 2 * SS + 6 * SS, h / 2 * SS + 6 * SS), "?", font=_font("roboto-latin-700-normal", px * SS),
                            fill=(0, 0, 0, 120), anchor="mm")
    c.im = Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4 * SS)), c.im)
    c.d = ImageDraw.Draw(c.im)
    c.text((w / 2, h / 2), "?", "roboto-latin-700-normal", px, color + (255,))
    return c.done()


def photo_card(img_bgr, title, w=300, h=210):
    """Weiß gerahmte Bildkarte mit gelbem Titel (Endszene)."""
    import cv2
    import numpy as np
    pad = 6
    im = cv2.resize(img_bgr, (w - 2 * pad, h - 2 * pad), interpolation=cv2.INTER_AREA)
    card = Image.new("RGBA", (w, h + 50), (0, 0, 0, 0))
    frame = Image.new("RGBA", (w, h), (250, 250, 250, 255))
    frame.paste(Image.fromarray(cv2.cvtColor(im, cv2.COLOR_BGR2RGB)), (pad, pad))
    card.paste(frame, (0, 50))
    d = ImageDraw.Draw(card)
    f = _font("roboto-latin-700-normal", 30)
    d.text((w / 2 + 2, 32), title, font=f, fill=(0, 0, 0, 160), anchor="mm")
    d.text((w / 2, 30), title, font=f, fill=(250, 226, 30, 255), anchor="mm")
    return card


def ellipse_stroke(w=300, h=900, color=(250, 230, 40), width=7, gap_deg=40):
    """Freihand-Ellipse (offen, wie mit Marker gezogen)."""
    c = Canvas(w, h)
    pts = []
    for i in range(181):
        a = math.radians(-90 + gap_deg / 2 + i / 180 * (360 - gap_deg))
        wob = 1 + 0.02 * math.sin(a * 3)
        pts.append((w / 2 + math.cos(a) * (w / 2 - width) * wob, h / 2 + math.sin(a) * (h / 2 - width) * wob))
    c.line(pts, fill=color + (255,), width=width)
    return c.done()


# --------------------------------------------------------------------------- Länderfiguren
def country_figure(kind="swiss", w=240, h=420):
    """Kegel-Figur mit Länder-Merkmal: swiss (rot, weißes Kreuz), austrian (Trachtenhut, grün),
    german (Beamter: grauer Anzug, Krawatte, Brille, Aktenordner)."""
    base = figure("dutch", w, h)  # Proportionen wiederverwenden, dann neu einfärben/übermalen
    c = Canvas(w, h)
    c.im = base.resize((w * SS, h * SS), Image.LANCZOS)
    c.d = ImageDraw.Draw(c.im)
    cx = w / 2
    top, bot = h * 0.53, h * 0.97
    r = w * 0.27
    hy = h * 0.40
    body = {"swiss": (212, 36, 40), "austrian": (70, 104, 64), "german": (120, 124, 132)}[kind]
    left = _bezier((cx - w * 0.20, top), (cx - w * 0.30, h * 0.70), (cx - w * 0.36, bot))
    right = _bezier((cx + w * 0.36, bot), (cx + w * 0.30, h * 0.70), (cx + w * 0.20, top))
    bottom = _bezier((cx - w * 0.36, bot), (cx, bot + h * 0.04), (cx + w * 0.36, bot))
    c.poly(left + bottom[1:-1] + right, fill=body + (255,))
    sh = _bezier((cx + w * 0.10, top + 4), (cx + w * 0.20, h * 0.72), (cx + w * 0.22, bot))
    c.poly(sh + right[::-1][1:], fill=_shade(body, 0.85), outline=None)
    skin = (246, 224, 204)
    # Kopf neu
    c.ellipse((cx - r * 1.6, hy - r * 2.2, cx + r * 1.6, hy - r * 0.5), fill=(0, 0, 0, 0), outline=None)
    c.d.rectangle([0, 0, w * SS, (hy + r * 0.2) * SS], fill=(0, 0, 0, 0))
    c.ellipse((cx - r, hy - r, cx + r, hy + r), fill=skin + (255,))
    c.ellipse((cx - r * 0.15, hy - r * 0.95, cx + r * 0.95, hy + r * 0.9), fill=_shade(skin, 0.94), outline=None)
    c.ellipse((cx - r, hy - r, cx + r, hy + r), fill=None)
    for dx in (-0.35, 0.35):
        c.ellipse((cx + dx * r - 2.6 * w / 120, hy - 3.2 * w / 120, cx + dx * r + 2.6 * w / 120, hy + 2.6 * w / 120),
                  fill=(30, 22, 20, 255), outline=None)
    c.line(_bezier((cx - r * 0.2, hy + r * 0.4), (cx, hy + r * 0.52), (cx + r * 0.2, hy + r * 0.4), 6), width=1.6 * w / 120)
    lw = w / 120
    if kind == "swiss":
        # weißes Kreuz auf der Brust, rote Mütze
        bx, by, s = cx, top + h * 0.17, w * 0.10
        c.poly([(bx - s, by - s * 0.35), (bx + s, by - s * 0.35), (bx + s, by + s * 0.35), (bx - s, by + s * 0.35)],
               fill=(255, 255, 255, 255), outline=None)
        c.poly([(bx - s * 0.35, by - s), (bx + s * 0.35, by - s), (bx + s * 0.35, by + s), (bx - s * 0.35, by + s)],
               fill=(255, 255, 255, 255), outline=None)
        c.d.chord([(cx - r * 1.02) * SS, (hy - r * 1.15) * SS, (cx + r * 1.02) * SS, (hy + r * 0.5) * SS], 180, 360,
                  fill=(200, 30, 34, 255), outline=OUTLINE, width=int(2 * lw * SS))
        c.ellipse((cx - r * 0.18, hy - r * 1.32, cx + r * 0.18, hy - r * 0.98), fill=(255, 255, 255, 255), width=1.5 * lw)
    elif kind == "austrian":
        c.d.chord([(cx - r) * SS, (hy - r) * SS, (cx + r) * SS, (hy + r * 0.85) * SS], 190, 350, fill=(110, 72, 40, 255))
        c.ellipse((cx - r * 1.35, hy - r * 0.9, cx + r * 1.35, hy - r * 0.5), fill=(56, 82, 50, 255), width=2 * lw)
        c.poly([(cx - r * 0.8, hy - r * 0.72), (cx - r * 0.6, hy - r * 1.75), (cx + r * 0.6, hy - r * 1.75),
                (cx + r * 0.8, hy - r * 0.72)], fill=(66, 96, 58, 255), width=2 * lw)
        c.line([(cx - r * 0.78, hy - r * 0.95), (cx + r * 0.78, hy - r * 0.95)], fill=(160, 40, 36, 255), width=3 * lw)
        c.poly([(cx + r * 0.55, hy - r * 1.0), (cx + r * 1.15, hy - r * 2.35), (cx + r * 0.75, hy - r * 0.95)],
               fill=(250, 248, 240, 255), width=1.5 * lw)  # Feder
        # Hosenträger
        for dx in (-0.12, 0.12):
            c.line([(cx + dx * w, top + 2), (cx + dx * w * 1.3, bot - 6)], fill=(110, 72, 40, 255), width=4 * lw)
        c.line([(cx - w * 0.14, top + h * 0.12), (cx + w * 0.14, top + h * 0.12)], fill=(110, 72, 40, 255), width=4 * lw)
    elif kind == "german":
        c.d.chord([(cx - r) * SS, (hy - r) * SS, (cx + r) * SS, (hy + r * 0.7) * SS], 185, 355, fill=(96, 70, 52, 255))
        # Brille
        for dx in (-0.35, 0.35):
            c.ellipse((cx + dx * r - r * 0.24, hy - r * 0.22, cx + dx * r + r * 0.24, hy + r * 0.2), fill=None, width=1.8 * lw)
        c.line([(cx - r * 0.11, hy - r * 0.02), (cx + r * 0.11, hy - r * 0.02)], width=1.8 * lw)
        # Hemd + Krawatte
        c.poly([(cx - w * 0.10, top + 2), (cx + w * 0.10, top + 2), (cx, top + h * 0.12)], fill=(250, 250, 250, 255), width=1.5 * lw)
        c.poly([(cx - w * 0.025, top + h * 0.03), (cx + w * 0.025, top + h * 0.03), (cx + w * 0.04, top + h * 0.22),
                (cx, top + h * 0.26), (cx - w * 0.04, top + h * 0.22)], fill=(40, 60, 120, 255), width=1.2 * lw)
        # Aktenordner im Arm
        c.poly([(cx + w * 0.08, top + h * 0.14), (cx + w * 0.40, top + h * 0.10), (cx + w * 0.42, top + h * 0.34),
                (cx + w * 0.10, top + h * 0.38)], fill=(40, 90, 170, 255), width=2 * lw)
        c.poly([(cx + w * 0.20, top + h * 0.18), (cx + w * 0.34, top + h * 0.16), (cx + w * 0.35, top + h * 0.22),
                (cx + w * 0.21, top + h * 0.24)], fill=(250, 250, 250, 255), width=1 * lw)
    return c.done()


def castle(w=200, h=200):
    c = Canvas(w, h)
    stone, dark = (186, 176, 160, 255), (150, 140, 124, 255)
    c.poly([(w * 0.15, h * 0.95), (w * 0.15, h * 0.45), (w * 0.85, h * 0.45), (w * 0.85, h * 0.95)], fill=stone)
    for x0 in (0.05, 0.62):
        c.poly([(w * x0, h * 0.95), (w * x0, h * 0.25), (w * (x0 + 0.33), h * 0.25), (w * (x0 + 0.33), h * 0.95)], fill=stone)
        for k in range(3):
            xa = w * (x0 + 0.01 + k * 0.11)
            c.poly([(xa, h * 0.25), (xa, h * 0.17), (xa + w * 0.08, h * 0.17), (xa + w * 0.08, h * 0.25)], fill=stone)
        c.poly([(w * (x0 + 0.13), h * 0.45), (w * (x0 + 0.2), h * 0.45), (w * (x0 + 0.2), h * 0.55), (w * (x0 + 0.13), h * 0.55)], fill=(60, 50, 44, 255))
    c.d.chord([w * 0.4 * SS, h * 0.68 * SS, w * 0.6 * SS, h * 1.0 * SS], 180, 360, fill=(90, 60, 40, 255))
    c.poly([(w * 0.4, h * 0.84), (w * 0.6, h * 0.84), (w * 0.6, h * 0.95), (w * 0.4, h * 0.95)], fill=(90, 60, 40, 255), outline=None)
    c.line([(w * 0.21, h * 0.25), (w * 0.21, h * 0.03)], width=2)
    c.poly([(w * 0.21, h * 0.03), (w * 0.36, h * 0.07), (w * 0.21, h * 0.12)], fill=(200, 40, 40, 255), width=1.5)
    return c.done()


def church(w=180, h=230):
    c = Canvas(w, h)
    wall, roof = (236, 226, 206, 255), (170, 70, 50, 255)
    c.poly([(w * 0.1, h * 0.95), (w * 0.1, h * 0.55), (w * 0.62, h * 0.55), (w * 0.62, h * 0.95)], fill=wall)
    c.poly([(w * 0.05, h * 0.57), (w * 0.36, h * 0.38), (w * 0.67, h * 0.57)], fill=roof)
    c.poly([(w * 0.62, h * 0.95), (w * 0.62, h * 0.3), (w * 0.88, h * 0.3), (w * 0.88, h * 0.95)], fill=wall)
    c.poly([(w * 0.6, h * 0.31), (w * 0.75, h * 0.08), (w * 0.9, h * 0.31)], fill=roof)
    c.line([(w * 0.75, h * 0.08), (w * 0.75, h * 0.0)], width=2)
    c.line([(w * 0.71, h * 0.03), (w * 0.79, h * 0.03)], width=2)
    c.d.chord([w * 0.68 * SS, h * 0.4 * SS, w * 0.82 * SS, h * 0.52 * SS], 180, 360, fill=(70, 60, 60, 255))
    c.d.chord([w * 0.28 * SS, h * 0.72 * SS, w * 0.44 * SS, h * 1.0 * SS], 180, 360, fill=(110, 70, 44, 255))
    return c.done()


def town(w=240, h=180):
    c = Canvas(w, h)
    cols = [(232, 214, 184), (220, 196, 160), (240, 228, 206), (226, 206, 176)]
    xs = [0.05, 0.27, 0.49, 0.71]
    for i, x in enumerate(xs):
        top = h * (0.4 + 0.08 * (i % 2))
        c.poly([(w * x, h * 0.95), (w * x, top), (w * (x + 0.22), top), (w * (x + 0.22), h * 0.95)], fill=cols[i] + (255,))
        c.poly([(w * (x - 0.01), top + 1), (w * (x + 0.11), top - h * 0.2), (w * (x + 0.23), top + 1)], fill=(176, 72, 52, 255))
        c.poly([(w * (x + 0.07), top + h * 0.12), (w * (x + 0.14), top + h * 0.12), (w * (x + 0.14), top + h * 0.22),
                (w * (x + 0.07), top + h * 0.22)], fill=(80, 90, 110, 255), width=1)
    c.poly([(0, h * 0.82), (w, h * 0.82), (w, h * 0.97), (0, h * 0.97)], fill=(170, 160, 146, 255))
    return c.done()


def fish(w=200, h=110):
    c = Canvas(w, h)
    c.poly([(w * 0.08, h * 0.5)] + _bezier((w * 0.08, h * 0.5), (w * 0.4, h * 0.0), (w * 0.75, h * 0.5))
           + _bezier((w * 0.75, h * 0.5), (w * 0.4, h * 1.0), (w * 0.08, h * 0.5))[1:], fill=(120, 170, 200, 255))
    c.poly([(w * 0.72, h * 0.5), (w * 0.97, h * 0.2), (w * 0.97, h * 0.8)], fill=(100, 150, 186, 255))
    c.ellipse((w * 0.18, h * 0.38, w * 0.26, h * 0.48), fill=(20, 20, 20, 255), outline=None)
    c.line(_bezier((w * 0.33, h * 0.3), (w * 0.38, h * 0.5), (w * 0.33, h * 0.7), 8), width=1.5)
    return c.done()


def ship(w=260, h=170):
    c = Canvas(w, h)
    c.poly([(w * 0.02, h * 0.6), (w * 0.98, h * 0.6), (w * 0.85, h * 0.9), (w * 0.12, h * 0.9)], fill=(240, 240, 240, 255))
    c.poly([(w * 0.08, h * 0.74), (w * 0.92, h * 0.74), (w * 0.88, h * 0.82), (w * 0.11, h * 0.82)], fill=(40, 70, 130, 255), outline=None)
    c.poly([(w * 0.22, h * 0.6), (w * 0.22, h * 0.38), (w * 0.72, h * 0.38), (w * 0.72, h * 0.6)], fill=(250, 250, 250, 255))
    for i in range(5):
        x = w * (0.26 + i * 0.09)
        c.ellipse((x, h * 0.44, x + w * 0.05, h * 0.52), fill=(70, 110, 160, 255), width=1)
    c.poly([(w * 0.42, h * 0.38), (w * 0.42, h * 0.18), (w * 0.52, h * 0.18), (w * 0.52, h * 0.38)], fill=(200, 50, 40, 255))
    return c.done()


def drop(w=120, h=170):
    c = Canvas(w, h)
    pts = _bezier((w * 0.5, h * 0.03), (w * 0.95, h * 0.62), (w * 0.5, h * 0.96), 20)[:-1] + \
        _bezier((w * 0.5, h * 0.96), (w * 0.05, h * 0.62), (w * 0.5, h * 0.03), 20)
    c.poly(pts, fill=(70, 150, 230, 255))
    c.ellipse((w * 0.3, h * 0.5, w * 0.42, h * 0.7), fill=(200, 230, 255, 255), outline=None)
    return c.done()


def stamp(text="KEINE AUSSAGE", w=560, h=170, color=(210, 30, 30)):
    """Roter Behördenstempel (leicht unregelmäßig)."""
    import random
    rnd = random.Random(4)
    c = Canvas(w, h)
    col = color + (235,)
    c.d.rounded_rectangle([8 * SS, 8 * SS, (w - 8) * SS, (h - 8) * SS], radius=14 * SS, outline=col, width=9 * SS)
    c.d.rounded_rectangle([22 * SS, 22 * SS, (w - 22) * SS, (h - 22) * SS], radius=8 * SS, outline=col, width=3 * SS)
    c.text((w / 2, h / 2 + 4), text, "roboto-latin-700-normal", h * 0.36, col)
    im = c.done()
    # Stempel-Ausfransung
    a = np.asarray(im).copy()
    noise = np.array([[rnd.random() for _ in range(w)] for _ in range(h)])
    a[..., 3] = (a[..., 3] * (noise > 0.12)).astype(np.uint8)
    return Image.fromarray(a, "RGBA")


import numpy as np  # noqa: E402  (für stamp)
