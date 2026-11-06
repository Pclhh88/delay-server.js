"""Turn a cutout PNG into a uniform collage sticker.

* cleans the alpha (removes specks, keeps the main shape)
* adds a cream paper rim if the cutout has none (or `force_rim`)
* warm vintage tone + lifted blacks + paper grain
* soft drop shadow baked in (so every sticker sits on the page the same way)

Returns RGBA uint8 and the anchor (subject centre, 0..1) inside the padded image.
"""
import cv2
import numpy as np
from PIL import Image

from . import PALETTE


def _main_component(alpha):
    m = (alpha > 128).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return alpha
    keep = np.zeros_like(m)
    big = st[1:, 4].max()
    for i in range(1, n):
        if st[i, 4] >= 0.02 * big:
            keep[lab == i] = 1
    keep = cv2.dilate(keep, np.ones((5, 5), np.uint8))
    return np.where(keep > 0, alpha, 0)


def has_rim(rgba):
    """True if the outer band of the cutout is mostly bright (a white paper rim)."""
    a = rgba[..., 3] > 128
    er = cv2.erode(a.astype(np.uint8), np.ones((5, 5), np.uint8), iterations=2)
    band = a & (er == 0)
    if band.sum() == 0:
        return False
    lum = rgba[..., :3].mean(-1)[band]
    return (lum > 225).mean() > 0.6


def make_sticker(rgba, rim=0.012, force_rim=False, tone=0.55, shadow=(0.010, 0.016, 0.012, 0.45),
                 seed=0, max_side=1600):
    rgba = rgba.copy()
    h, w = rgba.shape[:2]
    f0 = 1.0
    if max(h, w) > max_side:
        f0 = max_side / max(h, w)
        rgba = cv2.resize(rgba, (int(w * f0), int(h * f0)), interpolation=cv2.INTER_AREA)
        h, w = rgba.shape[:2]
    rgba[..., 3] = _main_component(rgba[..., 3])
    S = max(h, w)
    rng = np.random.default_rng(seed)
    pad = int(S * (rim + 0.06))
    big = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.uint8)
    big[pad:pad + h, pad:pad + w] = rgba
    rgb = big[..., :3].astype(np.float32) / 255
    a = big[..., 3].astype(np.float32) / 255
    cream = np.array(PALETTE["cream"], np.float32) / 255
    if force_rim or not has_rim(big):
        r = max(2, int(S * rim))
        m = (a > 0.5).astype(np.uint8)
        dil = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
        # slightly irregular scissor edge
        jag = cv2.GaussianBlur(rng.random(dil.shape).astype(np.float32), (0, 0), r * 0.6)
        jag = (jag - jag.mean()) / (jag.std() + 1e-6)
        dist = cv2.distanceTransform(1 - m, cv2.DIST_L2, 5)
        rim_a = np.clip((r * (1 + 0.18 * jag) - dist) / 1.5 + 0.5, 0, 1)
        rim_a = np.maximum(rim_a, a)
        rgb = rgb * a[..., None] + cream * (1 - a[..., None])
        a = rim_a
    # tone: warm, lifted blacks, keep whites creamy
    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    warm = np.stack([lum * 1.0, lum * 0.965, lum * 0.89], -1)
    warm = 0.10 + 0.86 * warm
    rgb = rgb * (1 - tone) + warm * tone
    rgb += rng.normal(0, 0.018, rgb.shape[:2]).astype(np.float32)[..., None]
    rgb = np.clip(rgb, 0, 1)
    # shadow
    dx, dy, blur, op = shadow
    sh = cv2.GaussianBlur(a, (0, 0), max(1, S * blur))
    M = np.float32([[1, 0, S * dx], [0, 1, S * dy]])
    sh = cv2.warpAffine(sh, M, (a.shape[1], a.shape[0])) * op
    out_a = a + sh * (1 - a)
    out_rgb = (rgb * a[..., None] + np.array([0.08, 0.09, 0.08]) * sh[..., None] * (1 - a[..., None]))
    out_rgb = out_rgb / np.maximum(out_a[..., None], 1e-4)
    out = np.dstack([np.clip(out_rgb * 255, 0, 255), np.clip(out_a * 255, 0, 255)]).astype(np.uint8)
    # crop to content
    ys, xs = np.where(out[..., 3] > 2)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    out = out[y0:y1, x0:x1]
    ays, axs = np.where(a[y0:y1, x0:x1] > 0.5)
    anchor = ((axs.min() + axs.max()) / 2 / out.shape[1], (ays.min() + ays.max()) / 2 / out.shape[0])
    make_sticker.last_map = (f0, pad - x0, pad - y0)   # source px -> sticker px: p*f0 + offset
    return out, anchor


def sticker_file(src, dst, **kw):
    rgba = np.asarray(Image.open(src).convert("RGBA"))
    out, anchor = make_sticker(rgba, **kw)
    Image.fromarray(out, "RGBA").save(dst)
    f0, ox, oy = make_sticker.last_map
    return {"anchor": [round(anchor[0], 4), round(anchor[1], 4)], "w": out.shape[1], "h": out.shape[0],
            "src_map": [f0, int(ox), int(oy)]}
