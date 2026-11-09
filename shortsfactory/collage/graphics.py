"""Procedural collage graphics: labels, halftone accents, torn paper,
newspaper clippings, typewriter strips, page overlay.  All return RGBA uint8."""
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import PALETTE, font
from .vmap import fractal_noise


def _rgba(img):
    return np.asarray(img.convert("RGBA")).copy()


def torn_mask(w, h, depth=10, seed=0, sides="tblr", soft=1.0):
    """Alpha mask of a rectangle with ragged (torn) edges."""
    rng = np.random.default_rng(seed)
    m = np.zeros((h, w), np.float32)
    pad = depth * 2

    def edge(n):
        e = np.cumsum(rng.normal(0, 1, n))
        e = cv2.GaussianBlur(e.reshape(1, -1).astype(np.float32), (0, 0), 3).ravel()
        e += rng.normal(0, 0.6, n).astype(np.float32)
        e = (e - e.min()) / (np.ptp(e) + 1e-6)
        return e * depth

    yy, xx = np.mgrid[0:h, 0:w]
    top = edge(w) + pad if "t" in sides else np.full(w, pad / 2)
    bot = h - pad - edge(w) if "b" in sides else np.full(w, h - pad / 2)
    lef = edge(h) + pad if "l" in sides else np.full(h, pad / 2)
    rig = w - pad - edge(h) if "r" in sides else np.full(h, w - pad / 2)
    d = np.minimum.reduce([yy - top[None, :], bot[None, :] - yy, xx - lef[:, None], rig[:, None] - xx])
    return np.clip(d / soft + 0.5, 0, 1)


def add_shadow(rgba, dx=6, dy=10, blur=8, op=0.45, pad=None):
    pad = pad if pad is not None else int(blur * 3 + max(abs(dx), abs(dy)))
    h, w = rgba.shape[:2]
    big = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.float32)
    big[pad:pad + h, pad:pad + w] = rgba.astype(np.float32) / 255
    a = big[..., 3]
    sh = cv2.GaussianBlur(a, (0, 0), blur)
    sh = cv2.warpAffine(sh, np.float32([[1, 0, dx], [0, 1, dy]]), (a.shape[1], a.shape[0])) * op
    out_a = a + sh * (1 - a)
    rgb = big[..., :3] * a[..., None] + 0.08 * sh[..., None] * (1 - a[..., None])
    rgb = rgb / np.maximum(out_a[..., None], 1e-4)
    return (np.dstack([np.clip(rgb, 0, 1), out_a]) * 255).astype(np.uint8)


def label(text, color="black", size=120, fg=(255, 255, 255), pad=(0.32, 0.12), rim=7, seed=0):
    """Text block like a cut-out magazine label: Anton caps on a coloured box,
    ragged edges, thin white rim, drop shadow."""
    f = ImageFont.truetype(font("label"), size)
    text = text.upper()
    bb = f.getbbox(text)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    px, py = int(size * pad[0]), int(size * pad[1]) + 6
    w, h = tw + 2 * px, th + 2 * py
    W, H = w + 2 * rim + 20, h + 2 * rim + 20
    col = PALETTE[color] if isinstance(color, str) else color
    rng = np.random.default_rng(seed)
    box = np.zeros((H, W, 4), np.float32)
    outer = torn_mask(W, H, depth=4, seed=seed, soft=1.2)
    inner = np.zeros((H, W), np.float32)
    inner[10 + rim:10 + rim + h, 10 + rim:10 + rim + w] = torn_mask(w, h, depth=3, seed=seed + 1, soft=1.0)
    cream = np.array(PALETTE["cream"], np.float32) / 255
    c = np.array(col, np.float32) / 255
    n = fractal_noise(H, W, seed, octaves=(60, 15, 4), weights=(0.5, 0.3, 0.2))
    fill = c[None, None] * (0.93 + 0.12 * n[..., None])
    rgb = cream[None, None] * (1 - inner[..., None]) + fill * inner[..., None]
    box[..., :3] = rgb
    box[..., 3] = outer
    img = Image.fromarray((box * 255).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(img)
    d.text((10 + rim + px - bb[0], 10 + rim + py - bb[1]), text, font=f, fill=tuple(fg) + (255,))
    arr = _rgba(img).astype(np.float32)
    arr[..., :3] += rng.normal(0, 4, arr.shape[:2])[..., None]
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return add_shadow(arr, dx=5, dy=8, blur=6, op=0.4)


def halftone(mask, cell=14, color="orange", max_r=0.62, angle=20, gamma=1.0):
    """Dots on a rotated grid, radius from mask value (0..1). Returns RGBA uint8."""
    h, w = mask.shape
    col = PALETTE[color] if isinstance(color, str) else color
    ss = 3
    out = np.zeros((h * ss, w * ss), np.uint8)
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    diag = int(math.hypot(w, h) / cell) + 2
    cx, cy = w / 2, h / 2
    for i in range(-diag, diag + 1):
        for j in range(-diag, diag + 1):
            u, v = i * cell, j * cell
            x = cx + u * ca - v * sa
            y = cy + u * sa + v * ca
            if 0 <= x < w and 0 <= y < h:
                val = mask[int(y), int(x)] ** gamma
                r = val * max_r * cell
                if r > 0.4:
                    cv2.circle(out, (int(x * ss), int(y * ss)), int(r * ss), 255, -1, cv2.LINE_AA)
    out = cv2.resize(out, (w, h), interpolation=cv2.INTER_AREA)
    rgba = np.zeros((h, w, 4), np.uint8)
    rgba[..., :3] = col
    rgba[..., 3] = out
    return rgba


def halftone_burst(size=900, cell=18, color="orange", seed=0):
    """Irregular blob of dots, dense in the middle (smoke/explosion accent)."""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    r = np.hypot(xx - size / 2, yy - size / 2) / (size / 2)
    n = fractal_noise(size, size, seed, octaves=(200, 60), weights=(0.7, 0.3))
    m = np.clip(1.15 - r - 0.45 * (n - 0.5), 0, 1)
    return halftone(m, cell=cell, color=color, max_r=0.6, gamma=0.8)


def halftone_arc(size=700, width=0.18, span=120, cell=12, color="orange"):
    """One radio-wave arc (part of a ring), dots fade towards the arc ends."""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    c = size / 2
    r = np.hypot(xx - c, yy - c) / c
    ang = np.degrees(np.arctan2(yy - c, xx - c))
    ring = np.clip(1 - np.abs(r - (1 - width)) / width, 0, 1)
    fade = np.clip(1 - np.abs(ang) / (span / 2), 0, 1) ** 0.6
    return halftone(ring * fade, cell=cell, color=color, max_r=0.62)


def paper(w, h, color="paper", seed=0, depth=12, sides="tblr", stains=True):
    col = np.array(PALETTE[color] if isinstance(color, str) else color, np.float32) / 255
    n = fractal_noise(h, w, seed, octaves=(300, 80, 20, 4), weights=(0.4, 0.3, 0.2, 0.1))
    rgb = col[None, None] * (0.9 + 0.16 * n[..., None])
    if stains:
        s = fractal_noise(h, w, seed + 5, octaves=(250, 60), weights=(0.7, 0.3))
        rgb *= (1 - 0.12 * np.clip(s - 0.55, 0, 1) * 4)[..., None]
    rgb += np.random.default_rng(seed).normal(0, 0.02, (h, w))[..., None]
    a = torn_mask(w, h, depth=depth, seed=seed, sides=sides, soft=1.2)
    # torn fibre edge: brighter rim
    er = cv2.erode((a > 0.5).astype(np.uint8), np.ones((5, 5), np.uint8), iterations=1)
    rim = ((a > 0.5) & (er == 0)).astype(np.float32)
    rim = cv2.GaussianBlur(rim, (0, 0), 1.2)[..., None]
    rgb = rgb * (1 - rim * 0.6) + 1.0 * rim * 0.6
    return (np.dstack([np.clip(rgb, 0, 1), a]) * 255).astype(np.uint8)


FILLER = ("The flier said the trip had gone well and that the plane was in fine shape. "
          "Officials at the field expect the next hop to begin at dawn if the weather holds. "
          "Crowds gathered early along the runway to watch the silver monoplane take off. "
          "Radio operators along the route report steady contact with the aircraft. ")


def newspaper(w=760, h=980, headline="WOMAN FLIER\nSETS RECORD", date="JUNE 1937", seed=0):
    img = Image.fromarray(paper(w, h, seed=seed, depth=14), "RGBA")
    d = ImageDraw.Draw(img)
    ink = PALETTE["ink"] + (235,)
    fh = ImageFont.truetype(font("serif"), int(w * 0.105))
    fs = ImageFont.truetype(font("serif"), int(w * 0.03))
    fb = ImageFont.truetype(font("serif_italic"), int(w * 0.028))
    y = int(h * 0.06)
    d.text((w * 0.07, y), date, font=fs, fill=ink)
    y += int(w * 0.05)
    d.line([(w * 0.06, y), (w * 0.94, y)], fill=ink, width=3)
    y += 14
    for line in headline.split("\n"):
        d.text((w * 0.07, y), line, font=fh, fill=ink)
        y += int(w * 0.115)
    y += 8
    d.line([(w * 0.06, y), (w * 0.94, y)], fill=ink, width=2)
    y += 16
    colw = (w * 0.88 - 20) / 2
    words = (FILLER * 6).split()
    for col in range(2):
        x0 = w * 0.06 + col * (colw + 20)
        yy = y
        line = ""
        while yy < h * 0.92:
            nxt = (line + " " + words[0]).strip()
            if fb.getlength(nxt) > colw:
                d.text((x0, yy), line, font=fb, fill=ink)
                yy += int(w * 0.036)
                line = ""
            else:
                line = nxt
                words.append(words.pop(0))
    arr = _rgba(img)
    return add_shadow(arr, dx=6, dy=10, blur=9, op=0.4)


def typewriter_strip(text, width=960, size=50, seed=0, words_visible=None, line_gap=1.35):
    """Torn paper strip with typed text; `words_visible` limits the typed words
    (for word-synchronous typing).  Layout is identical for every prefix."""
    f = ImageFont.truetype(font("typewriter"), size)
    words = text.split()
    lines, cur = [], []
    maxw = width - 2 * int(size * 0.9)
    for wd in words:
        if f.getlength(" ".join(cur + [wd])) > maxw and cur:
            lines.append(cur)
            cur = []
        cur.append(wd)
    lines.append(cur)
    lh = int(size * line_gap)
    h = lh * len(lines) + int(size * 1.6)
    base = paper(width, h, color="cream", seed=seed, depth=9, sides="tb")
    img = Image.fromarray(base, "RGBA")
    d = ImageDraw.Draw(img)
    ink = PALETTE["ink"] + (240,)
    n = 0
    y = int(size * 0.75)
    for ln in lines:
        x = int(size * 0.9)
        for wd in ln:
            if words_visible is not None and n >= words_visible:
                break
            d.text((x, y), wd, font=f, fill=ink)
            x += f.getlength(wd + " ")
            n += 1
        y += lh
    return add_shadow(_rgba(img), dx=5, dy=9, blur=8, op=0.4)


def page_overlay(w=1080, h=1920, seed=0, vignette=0.35):
    """Full-frame multiply layer: paper grain + vignette (values near 1 = no change)."""
    n = fractal_noise(h, w, seed, octaves=(300, 60, 8), weights=(0.5, 0.3, 0.2))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2)) / math.sqrt(2)
    v = 1 - vignette * np.clip(r - 0.35, 0, 1) ** 1.5 * 1.8
    g = np.random.default_rng(seed).normal(0, 0.03, (h, w)).astype(np.float32)
    m = np.clip(v * (0.95 + 0.06 * n) + g, 0, 1)
    rgb = np.stack([m, m * 0.99, m * 0.96], -1)
    return (np.dstack([rgb, np.ones((h, w))]) * 255).astype(np.uint8)


def dot_marker(r=26, color="orange"):
    s = r * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = PALETTE[color]
    d.ellipse([s / 2 - r - 6, s / 2 - r - 6, s / 2 + r + 6, s / 2 + r + 6], fill=PALETTE["cream"] + (255,))
    d.ellipse([s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r], fill=col + (255,))
    return add_shadow(_rgba(img), dx=3, dy=5, blur=4, op=0.4)


def stamp(text, color=(178, 40, 40), size=150, seed=0):
    """Rubber stamp: double frame + caps, worn ink (random gaps)."""
    f = ImageFont.truetype(font("label"), size)
    bb = f.getbbox(text)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad = int(size * 0.28)
    w, h = tw + 2 * pad + 40, th + 2 * pad + 40
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    lw = max(4, size // 14)
    d.rounded_rectangle([20, 20, w - 20, h - 20], radius=size // 8, outline=255, width=lw)
    d.rounded_rectangle([20 + lw * 2, 20 + lw * 2, w - 20 - lw * 2, h - 20 - lw * 2], radius=size // 10,
                        outline=255, width=max(2, lw // 2))
    d.text((w / 2, h / 2), text, font=f, fill=255, anchor="mm")
    m = np.asarray(img).astype(np.float32) / 255
    wear = fractal_noise(h, w, seed, octaves=(40, 10, 3), weights=(0.4, 0.35, 0.25))
    m *= np.clip((wear - 0.16) * 5, 0, 1) * 0.92
    rgba = np.zeros((h, w, 4), np.uint8)
    rgba[..., :3] = color
    rgba[..., 3] = (m * 255).astype(np.uint8)
    return rgba


def bone(length=520, seed=0):
    """Simple bone cut-out (cream, ink outline, halftone shading) on paper rim."""
    s = 3
    L, R = length * s, int(length * 0.11) * s
    w, h = L + 6 * R, 6 * R
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    cy = h / 2
    x0, x1 = 3 * R, w - 3 * R
    d.rounded_rectangle([x0, cy - R * 0.62, x1, cy + R * 0.62], radius=R * 0.6, fill=255)
    for x in (x0, x1):
        for dy in (-0.8, 0.8):
            d.ellipse([x - R * 1.15, cy + dy * R - R * 1.05, x + R * 1.15, cy + dy * R + R * 1.05], fill=255)
    m = np.asarray(img.resize((w // s, h // s), Image.LANCZOS)).astype(np.float32) / 255
    hh, ww = m.shape
    rim = cv2.dilate((m > 0.5).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
    edge = cv2.morphologyEx((m > 0.5).astype(np.uint8) * 255, cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8))
    yy = np.linspace(-1, 1, hh)[:, None] * np.ones((1, ww))
    shade = np.clip(yy * 0.9, 0, 1) * m
    ht = halftone(shade, cell=7, color=(120, 100, 80), max_r=0.55)[..., 3].astype(np.float32) / 255
    bone_col = np.array([236, 226, 200], np.float32) / 255
    rgb = np.ones((hh, ww, 3), np.float32) * np.array(PALETTE["cream"], np.float32) / 255
    rgb = rgb * (1 - m[..., None]) + bone_col * m[..., None]
    rgb = rgb * (1 - 0.6 * ht[..., None]) + np.array([0.45, 0.38, 0.3]) * 0.6 * ht[..., None]
    e = (edge.astype(np.float32) / 255)[..., None]
    rgb = rgb * (1 - e) + np.array([0.2, 0.17, 0.14]) * e
    a = np.maximum(rim.astype(np.float32), m)
    out = (np.dstack([np.clip(rgb, 0, 1), a]) * 255).astype(np.uint8)
    return add_shadow(out, dx=5, dy=8, blur=6, op=0.4)


def star(size=160, color="orange"):
    s = size * 3
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = s / 2
    pts = []
    for k in range(10):
        r = c * (0.95 if k % 2 == 0 else 0.4)
        a = math.radians(-90 + k * 36)
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    d.polygon(pts, fill=PALETTE["cream"] + (255,))
    inner = [(c + (x - c) * 0.78, c + (y - c) * 0.78) for x, y in pts]
    col = PALETTE[color] if isinstance(color, str) else color
    d.polygon(inner, fill=col + (255,))
    img = img.resize((size, size), Image.LANCZOS)
    return add_shadow(_rgba(img), dx=3, dy=5, blur=4, op=0.35)


def tape_x(size=700, color="orange", seed=0):
    """Two crossed strips of coloured tape with torn ends (strike-out)."""
    W = int(size * 1.15)
    strip_w, strip_h = int(size * 1.05), int(size * 0.17)
    canvas = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    col = PALETTE[color] if isinstance(color, str) else color
    for k, ang in enumerate((40, -40)):
        a = torn_mask(strip_w, strip_h, depth=6, seed=seed + k, sides="lr", soft=1.0)
        n = fractal_noise(strip_h, strip_w, seed + k, octaves=(40, 8), weights=(0.6, 0.4))
        rgb = np.array(col, np.float32)[None, None] / 255 * (0.92 + 0.12 * n[..., None])
        st = Image.fromarray((np.dstack([np.clip(rgb, 0, 1), a * 0.96]) * 255).astype(np.uint8), "RGBA")
        st = st.rotate(ang, expand=True, resample=Image.BICUBIC)
        canvas.alpha_composite(st, ((W - st.width) // 2, (W - st.height) // 2))
    return add_shadow(_rgba(canvas), dx=4, dy=6, blur=5, op=0.35)


def ocean_strip(w=1300, h=420, seed=0):
    """Torn strip of petrol halftone 'sea' (like the reference's water band)."""
    base = np.zeros((h, w), np.float32) + 1.0
    dots = halftone(base * 0.75, cell=16, color=(240, 236, 222), max_r=0.42, angle=45)
    col = np.array(PALETTE["petrol"], np.float32) / 255
    n = fractal_noise(h, w, seed, octaves=(120, 30), weights=(0.6, 0.4))
    rgb = col[None, None] * (0.9 + 0.15 * n[..., None])
    da = dots[..., 3:4].astype(np.float32) / 255
    rgb = rgb * (1 - da * 0.55) + np.array([0.94, 0.93, 0.87]) * da * 0.55
    a = torn_mask(w, h, depth=16, seed=seed, sides="tb", soft=1.2)
    er = cv2.erode((a > 0.5).astype(np.uint8), np.ones((9, 9), np.uint8))
    rim = ((a > 0.5) & (er == 0)).astype(np.float32)[..., None]
    rgb = rgb * (1 - rim) + np.array(PALETTE["cream"], np.float32) / 255 * rim
    out = (np.dstack([np.clip(rgb, 0, 1), a]) * 255).astype(np.uint8)
    return add_shadow(out, dx=0, dy=-8, blur=8, op=0.35)


def scribble_note(w=560, h=420, seed=0, lines=6):
    """Paper note with handwritten-looking calculation scribbles (abstract)."""
    img = Image.fromarray(paper(w, h, color="cream", seed=seed, depth=8), "RGBA")
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(seed)
    ink = (40, 50, 90, 225)
    y = h * 0.16
    for i in range(lines):
        x = w * 0.1
        x_end = w * rng.uniform(0.55, 0.88)
        pts = []
        while x < x_end:
            pts.append((x, y + rng.normal(0, 3) + 6 * math.sin(x * 0.18 + i)))
            x += rng.uniform(4, 9)
        d.line(pts, fill=ink, width=3, joint="curve")
        if i == lines - 2:
            d.line([(w * 0.1, y + 26), (w * 0.8, y + 26)], fill=ink, width=3)
        y += (h * 0.7) / lines
    d.ellipse([w * 0.58, y - 70, w * 0.9, y - 5], outline=PALETTE["orange"] + (230,), width=5)
    return add_shadow(_rgba(img), dx=5, dy=9, blur=8, op=0.4)


def city_label(name, size=44, ink=(64, 46, 28), halo=(246, 240, 226)):
    """Map city marker: ringed dot + serif name with a paper halo.
    Returns (rgba, anchor) – anchor (0..1) is the dot centre."""
    f = ImageFont.truetype(font("serif"), size)
    r = max(4, int(size * 0.24))
    tw = f.getlength(name)
    asc, desc = f.getmetrics()
    pad = int(size * 0.45)
    Wd = int(2 * pad + 2 * r + size * 0.35 + tw)
    Hd = int(2 * pad + max(asc + desc, 2 * r))
    img = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = pad + r, Hd / 2
    d.ellipse([cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3], fill=tuple(halo) + (255,))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=tuple(ink) + (255,))
    d.ellipse([cx - r * 0.55, cy - r * 0.55, cx + r * 0.55, cy + r * 0.55], fill=PALETTE["orange"] + (255,))
    d.text((cx + r + size * 0.35, cy), name, font=f, fill=tuple(ink) + (255,), anchor="lm",
           stroke_width=max(2, size // 11), stroke_fill=tuple(halo) + (235,))
    blur, dx, dy = 3, 2, 3
    pad_s = int(blur * 3 + max(dx, dy))
    out = add_shadow(_rgba(img), dx=dx, dy=dy, blur=blur, op=0.3, pad=pad_s)
    return out, [(cx + pad_s) / out.shape[1], (cy + pad_s) / out.shape[0]]
