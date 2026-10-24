"""Procedural layer types.

Every drawer returns a premultiplied float32 RGBA frame (H, W, 4) in output
pixels, or None. `M` maps the layer's parent design space to output pixels.
"""
import math

import cv2
import numpy as np

# Block arrow measured from the reference (design units, tip at origin,
# pointing along +x).  length 436, shaft 160, head width 308, head length 220.
ARROW = dict(length=436.0, shaft=160.0, head_w=308.0, head_l=220.0)


def _empty(r):
    return np.zeros((r.H, r.W, 4), np.float32)


def _apply(M, pts):
    pts = np.asarray(pts, np.float64)
    h = np.c_[pts, np.ones(len(pts))]
    return (M @ h.T).T[:, :2]


def _local(r, layer, p):
    return r._local_matrix(layer, p)


def _fill_poly(r, pts_out, color, feather=0.0):
    """Antialiased polygon fill (supersampled mask)."""
    ss = 4
    mask = np.zeros((r.H * ss, r.W * ss), np.uint8)
    cv2.fillPoly(mask, [np.round(pts_out * ss).astype(np.int32)], 255, lineType=cv2.LINE_AA)
    mask = cv2.resize(mask, (r.W, r.H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    if feather > 0:
        k = max(1, int(feather * r.k)) | 1
        mask = cv2.GaussianBlur(mask, (0, 0), feather * r.k)
    out = np.empty((r.H, r.W, 4), np.float32)
    col = np.array(color[:3], np.float32) / 255.0
    a = mask * (color[3] if len(color) > 3 else 1.0)
    out[..., :3] = col * a[..., None]
    out[..., 3] = a
    return out


def _gradient_rows(stops, n):
    """stops: [[pos 0..1, [r,g,b]], ...] -> (n,3) float colours 0..1."""
    pos = np.array([s[0] for s in stops], np.float64)
    cols = np.array([s[1] for s in stops], np.float64) / 255.0
    y = (np.arange(n) + 0.5) / n
    return np.stack([np.interp(y, pos, cols[:, c]) for c in range(3)], -1).astype(np.float32)


def stripes_bg(r, layer, p, t, M):
    """Vertical two-tone gradient with slanted, scrolling stripes."""
    cache = layer.setdefault("_cache", {})
    key = (r.W, r.H)
    if key not in cache:
        L = _gradient_rows(layer["light"], r.H)
        D = _gradient_rows(layer["dark"], r.H)
        ys, xs = np.mgrid[0:r.H, 0:r.W].astype(np.float32)
        cache[key] = (L, D, xs / r.k, ys / r.ky)
    L, D, xd, yd = cache[key]
    period = layer.get("period", 639.0)
    dark_frac = layer.get("dark_frac", 155.0 / 284.0)
    slope = layer.get("slope", -0.175)
    speed = layer.get("speed", 87.75)
    x0, y0, t0 = layer.get("edge0", [24.75, 1755.0, 88 / 30])
    e = x0 + speed * (t - t0) + slope * (yd - y0)
    ph = np.mod(xd - e, period) / period
    dark = (ph < dark_frac)[..., None]
    rgb = np.where(dark, D[:, None, :], L[:, None, :])
    out = np.empty((r.H, r.W, 4), np.float32)
    out[..., :3] = rgb
    out[..., 3] = 1
    return out


def radial_bg(r, layer, p, t, M):
    """Studio backdrop: radial falloff from an inner to an outer colour."""
    cx, cy = layer.get("center", [540, 980])
    rx, ry = layer.get("radius", [760, 1150])
    inner = np.array(layer.get("inner", [52, 52, 52]), np.float32) / 255
    outer = np.array(layer.get("outer", [8, 8, 8]), np.float32) / 255
    gamma = layer.get("gamma", 1.0)
    Mi = np.linalg.inv(M @ _local(r, layer, p) @ np.array([[1, 0, -540], [0, 1, -960], [0, 0, 1]]))
    ys, xs = np.mgrid[0:r.H, 0:r.W].astype(np.float32)
    dx = Mi[0, 0] * xs + Mi[0, 1] * ys + Mi[0, 2]
    dy = Mi[1, 0] * xs + Mi[1, 1] * ys + Mi[1, 2]
    d = np.sqrt(((dx - cx) / rx) ** 2 + ((dy - cy) / ry) ** 2)
    d = np.clip(d, 0, 1) ** gamma
    out = np.empty((r.H, r.W, 4), np.float32)
    out[..., :3] = inner * (1 - d[..., None]) + outer * d[..., None]
    out[..., 3] = 1
    return out


def solid(r, layer, p, t, M):
    x, y, w, h = layer.get("rect", [0, 0, 1080, 1920])
    pts = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
    Mt = M @ _local(r, layer, p) @ np.array([[1, 0, -540], [0, 1, -960], [0, 0, 1]])
    col = list(layer.get("color", [255, 255, 255]))
    if len(col) == 3:
        col.append(1.0)
    return _fill_poly(r, _apply(Mt, pts), col, layer.get("feather", 0))


def arrow(r, layer, p, t, M):
    a = dict(ARROW)
    a.update(layer.get("shape", {}))
    L, sw, hw, hl = a["length"], a["shaft"], a["head_w"], a["head_l"]
    pts = [[-L, -sw / 2], [-hl, -sw / 2], [-hl, -hw / 2], [0, 0],
           [-hl, hw / 2], [-hl, sw / 2], [-L, sw / 2]]
    Mt = M @ _local(r, layer, p)
    col = list(layer.get("color", [255, 0, 0])) + [1.0]
    return _fill_poly(r, _apply(Mt, pts), col)


def glow(r, layer, p, t, M):
    """Soft disc (lens flash / glint). `radius`, `softness`, sx/sy keyable;
    sx != sy gives an elliptical flare streak."""
    rad = p.get("radius", layer.get("radius", 60))
    soft = p.get("softness", layer.get("softness", 0.3))
    Mt = M @ _local(r, layer, p) @ np.array([[rad, 0, 0], [0, rad, 0], [0, 0, 1]])
    Mi = np.linalg.inv(Mt)
    ys, xs = np.mgrid[0:r.H, 0:r.W].astype(np.float32)
    lx = Mi[0, 0] * xs + Mi[0, 1] * ys + Mi[0, 2]
    ly = Mi[1, 0] * xs + Mi[1, 1] * ys + Mi[1, 2]
    d = np.sqrt(lx * lx + ly * ly)
    edge = max(soft, 1e-3)
    a = np.clip((1 - d) / edge, 0, 1)
    col = np.array(layer.get("color", [255, 255, 255]), np.float32) / 255
    out = np.empty((r.H, r.W, 4), np.float32)
    out[..., :3] = col * a[..., None]
    out[..., 3] = a
    return out


def polygon(r, layer, p, t, M):
    Mt = M @ _local(r, layer, p) @ np.array([[1, 0, -540], [0, 1, -960], [0, 0, 1]])
    col = list(layer.get("color", [255, 255, 255]))
    if len(col) == 3:
        col.append(1.0)
    return _fill_poly(r, _apply(Mt, layer["points"]), col, layer.get("feather", 0))


def light_cone(r, layer, p, t, M):
    """Torch beam: a wedge from an apex, fading with distance, blurred."""
    Mt = M @ _local(r, layer, p)
    length = p.get("length", layer.get("length", 900))
    spread = p.get("spread", layer.get("spread", 22))  # half angle (deg)
    th = math.radians(spread)
    n = 24
    pts = [[0, 0]] + [[length * math.cos(a), length * math.sin(a)]
                      for a in np.linspace(-th, th, n)]
    pts_o = _apply(Mt, pts)
    ss = 2
    mask = np.zeros((r.H * ss, r.W * ss), np.uint8)
    cv2.fillPoly(mask, [np.round(pts_o * ss).astype(np.int32)], 255, lineType=cv2.LINE_AA)
    mask = cv2.resize(mask, (r.W, r.H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    apex = pts_o[0]
    ys, xs = np.mgrid[0:r.H, 0:r.W].astype(np.float32)
    sc = math.sqrt(abs(np.linalg.det(Mt[:2, :2])))
    d = np.sqrt((xs - apex[0]) ** 2 + (ys - apex[1]) ** 2) / max(length * sc, 1)
    fall = layer.get("falloff", 0.35)
    a = mask * np.clip(1 - d * fall, 0, 1)
    blur = layer.get("blur", 30) * r.k
    if blur > 0:
        a = cv2.GaussianBlur(a, (0, 0), blur)
    a *= layer.get("strength", 0.6)
    col = np.array(layer.get("color", [255, 250, 200]), np.float32) / 255
    out = np.empty((r.H, r.W, 4), np.float32)
    out[..., :3] = col * a[..., None]
    out[..., 3] = a
    return out


def grade(r, layer, p, t, M):
    """Colour grade of everything below: saturation / value (keyable).
    Handled in the engine (needs the canvas), see Renderer.render_layer."""
    return None


def text(r, layer, p, t, M):
    return r.text.draw_text_layer(r, layer, p, M)


DRAWERS = {
    "stripes_bg": stripes_bg,
    "radial_bg": radial_bg,
    "solid": solid,
    "arrow": arrow,
    "glow": glow,
    "polygon": polygon,
    "light_cone": light_cone,
    "text": text,
    "grade": grade,
}


def draw(typ, layer, p, t, M, r):
    if typ not in DRAWERS:
        raise ValueError(f"unknown layer type {typ}")
    return DRAWERS[typ](r, layer, p, t, M)
