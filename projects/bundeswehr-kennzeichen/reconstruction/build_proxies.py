"""Build reference proxies + measurements for the Bundeswehr-Kennzeichen reconstruction.

Usage:  python3 -m projects... (or) python3 build_proxies.py [asset ...]

Reads the decoded reference frames from ../analysis/frames (create them with
`python3 -m shortsfactory.tools.extract_frames`), writes PNG proxies to
../assets/proxies and measured transforms to ./measurements.json.

Every asset written here is a REFERENCE PROXY (cut from the reference video).
It is only for side-by-side comparison and must not be published.
"""
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PROJ))
sys.path.insert(0, ROOT)

from shortsfactory.analysis.proxy_tools import (  # noqa: E402
    FrameStore, overlay_mask, caption_mask, red_mask, similarity, decompose,
    build_mosaic, inpaint_holes, largest_component, fill_mask_holes, crop_to_alpha,
    track_arrow, caption_text_mask, merge_static, track_sprite, refine_track)

FRAMES = FrameStore(os.path.join(PROJ, "analysis", "frames", "f%04d.png"))
OUT = os.path.join(PROJ, "assets", "proxies")
MEAS_PATH = os.path.join(HERE, "measurements.json")
os.makedirs(OUT, exist_ok=True)


def load_meas():
    if os.path.exists(MEAS_PATH):
        with open(MEAS_PATH) as f:
            return json.load(f)
    return {}


def _jsonable(o):
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def save_meas(m):
    """Atomic write (a crash while serialising must not destroy the file)."""
    tmp = MEAS_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(m, f, indent=1, default=_jsonable)
    os.replace(tmp, MEAS_PATH)


def camera_track(ref, frames, mask_kw=None):
    """Similarity transforms (ref frame -> frame n) for a flat moving layer."""
    mask_kw = mask_kw or {}
    out = {}
    ea = overlay_mask(FRAMES(ref), red=True, **mask_kw)
    for n in frames:
        if n == ref:
            out[n] = [[1, 0, 0], [0, 1, 0]]
            continue
        eb = overlay_mask(FRAMES(n), red=True, **mask_kw)
        M, inl = similarity(FRAMES(ref), FRAMES(n), ea, eb)
        out[n] = None if M is None else M.tolist()
    return out


# --------------------------------------------------------------------- Q1
def build_q1(meas):
    """Hook shot: camo G-Wagen photo on a dark studio backdrop, punch zooms."""
    ref = 20
    # frames where the camera changes (holds in between are constant)
    key_frames = [0, 2, 3, 4, 5, 20, 42, 43, 44, 45, 69, 70, 71, 72, 82, 83]
    M = camera_track(ref, key_frames)
    M[0] = camera_track(ref, [0], {"caption": False})[0]
    # static backdrop plate = frame 84 (jeep gone); overlays inpainted
    f84 = FRAMES(84)
    hole = np.zeros((854, 480), np.uint8)
    hole[:, :34] = 255
    hole |= caption_mask(f84)
    hole |= red_mask(f84, 15)
    hole[:, 425:452] = 255  # burned-in credit text
    plate = cv2.inpaint(f84, hole, 25, cv2.INPAINT_TELEA)
    plate = cv2.GaussianBlur(plate, (0, 0), 1.5)
    cv2.imwrite(os.path.join(OUT, "q1_backdrop.png"), plate)
    platef = plate.astype(np.float32)

    # jeep mosaic: only pixels that differ from the (screen-static) backdrop
    F = 2.2
    origin = (-24.0, -407.0)
    size = (900.0, 1600.0)
    # convex hull of the vehicle in frame 0; sharper sources are only used
    # inside it (the studio floor does not zoom consistently in the reference)
    d0 = np.abs(FRAMES(0).astype(np.float32) - platef).max(-1)
    d0[:, 425:452] = 0
    body = largest_component((d0 > 22).astype(np.uint8))
    hull = cv2.convexHull(cv2.findNonZero(body))
    hull0 = np.zeros((854, 480), np.uint8)
    cv2.fillPoly(hull0, [hull], 255)
    M0 = np.vstack([np.array(M[0]), [0, 0, 1]])
    srcs = []
    for n in [72, 45, 20, 0]:
        img = FRAMES(n)
        ex = overlay_mask(img, caption=(n != 0), red=True)
        if n != 0:
            Mn = np.vstack([np.array(M[n]), [0, 0, 1]]) @ np.linalg.inv(M0)
            hn = cv2.warpAffine(hull0, Mn[:2], (480, 854))
            ex = ex | (255 - hn)
        diff = np.abs(img.astype(np.float32) - platef).max(-1)
        bgm = (diff < 7).astype(np.uint8)
        bgm = cv2.morphologyEx(bgm, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        srcs.append((img, np.array(M[n]), ex, bgm * 255))
    col, cov = build_mosaic([(i, m, e) for i, m, e, _ in srcs], origin, size, F)
    # alpha: first source (in priority) that is valid decides fg/bg
    al, _ = build_mosaic([(np.repeat((255 - b)[..., None], 3, -1), m, e) for _, m, e, b in srcs],
                         origin, size, F)
    alpha = cv2.GaussianBlur(al[..., 0] / 255.0, (0, 0), 1.2) * cov
    img = inpaint_holes(col, cov)
    cv2.imwrite(os.path.join(OUT, "q1_jeep_photo.png"),
                np.dstack([img, (np.clip(alpha, 0, 1) * 255).astype(np.uint8)]))

    meas["q1"] = {"ref_frame": ref, "F": F, "origin": origin, "M": {str(k): v for k, v in M.items()}}
    return {
        "q1_jeep_photo": {"path": "assets/proxies/q1_jeep_photo.png", "design_scale": 2.25 / F,
                          "license": "reference_proxy",
                          "source": "Mosaik aus Referenzframes 0/20/45/72 (Foto laut Einblendung: Wikimedia Commons, Darkone, CC BY-SA 2.5)",
                          "replace_with": "Originalfoto von Wikimedia Commons (Darkone, CC BY-SA 2.5) mit Namensnennung"},
        "q1_backdrop": {"path": "assets/proxies/q1_backdrop.png", "design_scale": 2.25,
                        "license": "reference_proxy",
                        "source": "Hintergrundplatte aus Referenzframes 0/84",
                        "replace_with": "prozeduraler Studio-Verlauf (radial_bg)"},
    }


def track_arrows(meas):
    arrows = {}
    for n in range(0, 630):
        r = track_arrow(FRAMES(n), 1500)
        if r:
            arrows[str(n)] = [round(v, 2) for v in r]
    meas["arrows_raw"] = arrows
    return {}


_BG = {}


def stripes_bg(n):
    """The procedural stripes background exactly as rendered for frame n (BGR, 480x854)."""
    if n not in _BG:
        from shortsfactory.render.engine import Renderer
        style = json.load(open(os.path.join(PROJ, "analysis", "style_measurements.json")))
        r = Renderer({"meta": {"fps": 30}, "layers": [{"type": "stripes_bg", **style["stripes_bg"]}]},
                     PROJ, 480, 854)
        fr = (r.render_frame(n / 30) * 255 + 0.5).astype(np.uint8)
        _BG[n] = cv2.cvtColor(fr, cv2.COLOR_RGB2BGR)
    return _BG[n]


def overlays(n, red=True):
    img = FRAMES(n)
    m = caption_text_mask(img)
    m[:, 425:452] = 255          # vertical credit
    m[:70, 38:88] = 255          # [Qn] label
    if red:
        m |= red_mask(img, 9)
    return m


def extract_on_stripes(frames, thresh=14, close=7, crop=None, red=True):
    """Cut out a static object that sits on the stripes background in all
    `frames` (captions differ between frames and are merged away)."""
    imgs = [FRAMES(n) for n in frames]
    masks = [overlays(n, red=red) for n in frames]
    if crop is not None:
        for m in masks:
            m[:crop[1]] = 255
            m[crop[3]:] = 255
            m[:, :crop[0]] = 255
            m[:, crop[2]:] = 255
    col, cov = merge_static(imgs, masks)
    dif = [np.abs(i.astype(np.float32) - stripes_bg(n).astype(np.float32)).max(-1, keepdims=True)
           for i, n in zip(imgs, frames)]
    dsum, _ = merge_static([np.repeat(d, 3, -1) for d in dif], masks)
    d = dsum[..., 0]
    fg = (d > thresh).astype(np.uint8)
    fg[cov < 0.5] = 0
    fg = largest_component(fg)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((close, close), np.uint8))
    fg = fill_mask_holes(fg)
    hole = ((cov < 0.5) & (cv2.dilate(fg, np.ones((15, 15), np.uint8)) > 0)).astype(np.uint8) * 255
    colu = np.clip(col, 0, 255).astype(np.uint8)
    if hole.any():
        colu = cv2.inpaint(colu, hole, 5, cv2.INPAINT_TELEA)
        # holes inside the object are object
        fg = fill_mask_holes(np.maximum(fg, (hole > 0) & (cv2.dilate(fg, np.ones((25, 25), np.uint8)) > 0)).astype(np.uint8))
    soft = cv2.GaussianBlur(fg.astype(np.float32), (0, 0), 0.8)
    bgra = np.dstack([colu, (soft * 255).astype(np.uint8)])
    spr, (x0, y0) = crop_to_alpha(bgra, 3)
    h, w = spr.shape[:2]
    return spr, (x0 + w / 2, y0 + h / 2)


def save_sprite(name, spr):
    cv2.imwrite(os.path.join(OUT, name + ".png"), spr)


def track_range(spr, frames, start_guess, scales, radius=60, rots=(0.0,), min_overlap=0.35,
                start_scale=None, fast_tol=0.002):
    """Track a sprite through `frames`. Tries a local refinement around the
    previous result first (static / slow objects), falls back to a coarse
    half-resolution global search + refinement."""
    out = {}
    g = start_guess
    prev = None
    half = cv2.resize(spr, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    for n in frames:
        ex = overlays(n)
        fr = FRAMES(n)
        r = None
        if prev is not None:
            s0 = prev["scale"]
            r = refine_track(fr, spr, (prev["cx"], prev["cy"]), (s0 * 0.98, s0 * 1.02), 3,
                             (prev["rot"],), radius=6, exclude=ex, min_overlap=min_overlap)
            if r is None or r["err"] > fast_tol:
                r = None
        if r is None:
            frh = cv2.resize(fr, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
            exh = cv2.resize(ex, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_NEAREST)
            gh = (g[0] / 2, g[1] / 2) if g else None
            c = track_sprite(frh, half, scales, rots, guess=gh, radius=radius / 2 if radius else None,
                             exclude=exh, min_overlap=min_overlap)
            s0 = c["scale"]
            r = refine_track(fr, spr, (c["cx"] * 2, c["cy"] * 2), (s0 * 0.95, s0 * 1.05), 7, (c["rot"],),
                             radius=6, exclude=ex, min_overlap=min_overlap)
            if len(rots) > 1:
                r2 = refine_track(fr, spr, (r["cx"], r["cy"]), (r["scale"] * 0.99, r["scale"] * 1.01), 3,
                                  (r["rot"] - 2, r["rot"], r["rot"] + 2), radius=4, exclude=ex,
                                  min_overlap=min_overlap)
                if r2["err"] < r["err"]:
                    r = r2
        out[str(n)] = {k: round(v, 4) for k, v in r.items()}
        prev = r
        g = (r["cx"], r["cy"])
        print(n, out[str(n)], flush=True)
    return out


def warp_into_sprite(n, track, spr_shape, spr_center_ref):
    """Map frame n into sprite pixel space using a track entry (centre/scale/rot
    of the sprite in frame n)."""
    h, w = spr_shape[:2]
    s, r = track["scale"], track["rot"]
    # sprite px -> frame px:  R(r) S(s) (q - (w/2,h/2)) + (cx, cy)
    c, si = np.cos(np.radians(r)), np.sin(np.radians(r))
    A = np.array([[s * c, -s * si, 0], [s * si, s * c, 0]])
    A[:, 2] = np.array([track["cx"], track["cy"]]) - A[:, :2] @ np.array([w / 2, h / 2])
    img = cv2.warpAffine(FRAMES(n), A, (w, h), flags=cv2.INTER_AREA | cv2.WARP_INVERSE_MAP)
    ov = overlays(n)
    m = cv2.warpAffine(ov, A, (w, h), flags=cv2.INTER_NEAREST | cv2.WARP_INVERSE_MAP, borderValue=255)
    return img, m


def build_s3(meas):
    """Gradient scene with the grey G-Wagen (pop-in), later painted camo."""
    frames = [106, 110, 116, 122, 127]
    spr, c = extract_on_stripes(frames)
    meas["s3_jeep_grey_ref"] = {"frame": 106, "center": c}
    tr = track_range(spr, list(range(97, 130)), c, list(np.linspace(0.15, 1.6, 30)), radius=200)
    # second pass: fill the caption band from the enlarged pop-in frames
    h, w = spr.shape[:2]
    imgs, masks = [], []
    for n in frames:
        t = dict(tr[str(n)])
        im, m = warp_into_sprite(n, t, spr.shape, c)
        imgs.append(im)
        masks.append(m)
    for n in [100, 101, 99, 102]:
        im, m = warp_into_sprite(n, tr[str(n)], spr.shape, c)
        imgs.append(im)
        masks.append(m)
    col, cov = merge_static(imgs, masks)
    colu = np.clip(col, 0, 255).astype(np.uint8)
    hole = ((cov < 0.5) & (spr[..., 3] > 0)).astype(np.uint8) * 255
    if hole.any():
        colu = cv2.inpaint(colu, hole, 5, cv2.INPAINT_TELEA)
    spr = np.dstack([colu, spr[..., 3]])
    save_sprite("s3_jeep_grey", spr)
    meas["s3_jeep_grey_track"] = tr
    return {"s3_jeep_grey": {"path": "assets/proxies/s3_jeep_grey.png", "design_scale": 2.25,
                             "license": "reference_proxy", "source": "Referenzframes 99-127, Untertitel herausgerechnet",
                             "replace_with": "lizenziertes Foto eines grauen Mercedes G (Wolf) als Freisteller"}}


def _static_sprite_colors(alpha_spr, frames, center, lower_cut=None, fallback=None):
    """Colours of a static sprite (same placement as `alpha_spr`) merged from
    several frames; rows below `lower_cut` (frame y) are ignored for frames
    listed in lower_cut[1]."""
    t = {"cx": center[0], "cy": center[1], "scale": 1.0, "rot": 0.0}
    imgs, masks = [], []
    for n in frames:
        im, m = warp_into_sprite(n, t, alpha_spr.shape, center)
        if lower_cut and n in lower_cut[1]:
            m = m.copy()
            m[int(lower_cut[0] - (center[1] - alpha_spr.shape[0] / 2)):] = 255
        imgs.append(im)
        masks.append(m)
    if fallback is not None:
        imgs.append(fallback[..., :3])
        masks.append(np.zeros(alpha_spr.shape[:2], np.uint8))
    col, cov = merge_static(imgs, masks)
    colu = np.clip(col, 0, 255).astype(np.uint8)
    hole = ((cov < 0.5) & (alpha_spr[..., 3] > 0)).astype(np.uint8) * 255
    if hole.any():
        colu = cv2.inpaint(colu, hole, 5, cv2.INPAINT_TELEA)
    return np.dstack([colu, alpha_spr[..., 3]])


def build_s3_paint(meas):
    """Bob Ross 'paints' the jeep: grey -> painted (brush reveal, frames
    126-170) -> real camo photo (hard switch at frame 184)."""
    grey = cv2.imread(os.path.join(OUT, "s3_jeep_grey.png"), -1)
    c = (233.5, 433.5)
    camo = _static_sprite_colors(grey, [185, 186, 184], c, (555, [184]))
    cv2.imwrite(os.path.join(OUT, "s3_jeep_camo.png"), camo)
    painted = _static_sprite_colors(grey, [183, 180, 176, 172, 170], c, (555, [183, 180, 176, 172, 170]),
                                    fallback=camo)
    cv2.imwrite(os.path.join(OUT, "s3_jeep_painted.png"), painted)

    G = grey[..., :3].astype(np.float32)
    P = painted[..., :3].astype(np.float32)
    A = grey[..., 3] > 200
    h, w = A.shape
    t = {"cx": c[0], "cy": c[1], "scale": 1.0, "rot": 0.0}
    frames = list(range(126, 172))
    state = np.full((len(frames), h, w), np.nan, np.float32)
    dc = P - G
    den = (dc * dc).sum(-1) + 1e-3
    for i, n in enumerate(frames):
        im, m = warp_into_sprite(n, t, grey.shape, c)
        I = im.astype(np.float32)
        mix = ((I - G) * dc).sum(-1) / den
        res = np.abs(I - (G + np.clip(mix, 0, 1)[..., None] * dc)).sum(-1)
        ok = A & (m == 0) & (np.abs(dc).sum(-1) > 30) & (res < 45)
        state[i][ok] = (mix[ok] > 0.5)
    idx = np.arange(len(frames))[:, None, None]
    last0 = np.where(state == 0, idx, -1).max(0)
    known = ~np.isnan(state).all(0)
    rev = np.array(frames)[np.clip(last0 + 1, 0, len(frames) - 1)].astype(np.float32)
    rev[last0 == -1] = frames[0]
    norm = np.clip((rev - frames[0]) / (frames[-1] - frames[0]), 0, 1)
    m8 = (norm * 255).astype(np.uint8)
    m8 = cv2.inpaint(m8, ((~known) & A).astype(np.uint8) * 255, 7, cv2.INPAINT_TELEA)
    bs = 16
    small = np.zeros(((h + bs - 1) // bs, (w + bs - 1) // bs), np.uint8)
    for by in range(small.shape[0]):
        for bx in range(small.shape[1]):
            blk = m8[by * bs:(by + 1) * bs, bx * bs:(bx + 1) * bs]
            am = A[by * bs:(by + 1) * bs, bx * bs:(bx + 1) * bs]
            small[by, bx] = np.median(blk[am]) if am.sum() > 20 else 0
    m8 = cv2.GaussianBlur(cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC), (0, 0), 6)
    cv2.imwrite(os.path.join(OUT, "s3_paint_reveal_map.png"), m8)
    meas["s3_paint"] = {"reveal_frames": [frames[0], frames[-1]], "camo_switch_frame": 184, "center": c}
    entry = {"design_scale": 2.25, "license": "reference_proxy"}
    return {
        "s3_jeep_camo": dict(entry, path="assets/proxies/s3_jeep_camo.png", source="Referenzframes 184-186",
                             replace_with="Foto des Jeeps in Flecktarn, gleiche Perspektive"),
        "s3_jeep_painted": dict(entry, path="assets/proxies/s3_jeep_painted.png", source="Referenzframes 170-183",
                                replace_with="grau mit aufgemalten Tarnflecken (Bild-Edit)"),
        "s3_paint_reveal_map": {"path": "assets/proxies/s3_paint_reveal_map.png", "design_scale": 2.25,
                                "license": "derived_measurement",
                                "source": "gemessene Übermal-Reihenfolge (0 = früh, 1 = spät)"},
    }


def composite_sprite(bg, spr, center, scale=1.0):
    """Paste a BGRA sprite (scaled) centred at `center` onto a BGR frame."""
    sp = cv2.resize(spr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale != 1 else spr
    h, w = sp.shape[:2]
    A = np.array([[1, 0, center[0] - w / 2], [0, 1, center[1] - h / 2]], np.float32)
    big = cv2.warpAffine(sp, A, (bg.shape[1], bg.shape[0]))
    a = big[..., 3:4].astype(np.float32) / 255
    return (bg.astype(np.float32) * (1 - a) + big[..., :3].astype(np.float32) * a).astype(np.uint8)


def build_s3_bob(meas):
    """Bob-Ross rage-comic meme; cut out at frame 176 against the rebuilt
    background (stripes + painted jeep), then tracked through 126-186."""
    painted = cv2.imread(os.path.join(OUT, "s3_jeep_painted.png"), -1)
    n = 176
    bg = composite_sprite(stripes_bg(n), painted, (233.5, 433.5))
    img = FRAMES(n)
    d = np.abs(img.astype(np.float32) - bg.astype(np.float32)).max(-1)
    d[caption_text_mask(img) > 0] = 0
    fg = (d > 40).astype(np.uint8)
    fg[:500] = 0
    fg = largest_component(fg)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    fg = fill_mask_holes(fg)
    soft = cv2.GaussianBlur(fg.astype(np.float32), (0, 0), 0.7)
    spr, (x0, y0) = crop_to_alpha(np.dstack([img, (soft * 255).astype(np.uint8)]), 3)
    save_sprite("s3_bob", spr)
    h, w = spr.shape[:2]
    c = (x0 + w / 2, y0 + h / 2)
    meas["s3_bob_ref"] = {"frame": n, "center": c, "bottom_cut": bool(y0 + h >= 853)}
    print("bob sprite", spr.shape, c)
    return {"s3_bob": {"path": "assets/proxies/s3_bob.png", "design_scale": 2.25, "license": "reference_proxy",
                       "source": f"Referenzframe {n}",
                       "replace_with": "eigene Zeichnung im Rage-Comic-Stil (Maler mit Afro, Pinsel) oder lizenziertes Meme"}}


def build_s3_bob_track(meas):
    spr = cv2.imread(os.path.join(OUT, "s3_bob.png"), -1)
    c = meas["s3_bob_ref"]["center"]
    tr = {}
    # backwards from the reference frame (Bob is easiest to find there)
    tr.update(track_range(spr, list(range(176, 125, -1)), c, list(np.linspace(0.6, 1.5, 19)), radius=140,
                          rots=(-10, -5, 0, 5, 10), min_overlap=0.2))
    tr.update(track_range(spr, list(range(177, 187)), c, list(np.linspace(0.6, 1.5, 19)), radius=140,
                          rots=(-10, -5, 0, 5, 10), min_overlap=0.1))
    meas["s3_bob_track"] = tr
    return {}


def green_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    g = ((hsv[..., 0] > 30) & (hsv[..., 0] < 80) & (hsv[..., 1] > 90) & (hsv[..., 2] > 60)).astype(np.uint8)
    return g


def build_bush_track(meas):
    """Similarity transforms of the cartoon bush (ref frame 205) for 186-316."""
    ref = 205
    out = {}
    def mask_for(n):
        img = FRAMES(n)
        g = cv2.dilate(green_mask(img), np.ones((9, 9), np.uint8))
        ex = overlays(n) | ((1 - g) * 255).astype(np.uint8)
        return ex
    ea = mask_for(ref)
    for n in range(186, 317):
        M, inl = similarity(FRAMES(ref), FRAMES(n), ea, mask_for(n))
        out[str(n)] = None if M is None else {"M": M.tolist(), "inliers": inl}
        if M is not None:
            s_, r_, tx, ty = decompose(M)
            print(n, round(s_, 4), round(r_, 2), round(tx, 1), round(ty, 1), inl, flush=True)
        else:
            print(n, None, flush=True)
    meas["bush_track"] = out
    return {}


def jeep_tint_series(meas, frames, place):
    """Fit k in  I = (1-k)*J + k*G  (jeep colour pulled towards bush green G)
    over the visible jeep pixels. place(n) -> (cx, cy, scale) of the jeep sprite."""
    camo = cv2.imread(os.path.join(OUT, "s3_jeep_camo.png"), -1)
    G = np.array(meas.get("bush_green", [52, 176, 76]), np.float32)  # BGR
    out = {}
    for n in frames:
        cx, cy, sc = place(n)
        t = {"cx": cx, "cy": cy, "scale": sc, "rot": 0.0}
        im, m = warp_into_sprite(n, t, camo.shape, None)
        J = camo[..., :3].astype(np.float32)
        I = im.astype(np.float32)
        ok = (camo[..., 3] > 250) & (m == 0)
        ok[:, int(ok.shape[1] * 0.55):] = False   # right part may be behind the front bush
        d = (G - J)
        k = ((I - J) * d).sum(-1) / ((d * d).sum(-1) + 1e-3)
        res = np.abs(I - (J + np.clip(k, 0, 1)[..., None] * d)).sum(-1)
        good = ok & (res < 40) & (np.abs(I - G).max(-1) > 20)
        out[str(n)] = round(float(np.median(k[good])), 3) if good.sum() > 200 else None
    return out


def build_world(meas):
    """Bush (back + front piece), jeep placement and tint for frames 185-316.
    World coordinates = reference frame 205."""
    bt = meas["bush_track"]
    f205 = FRAMES(205)
    # --- jeep placement in world coords (plate tracking: plate centre at 193.5,489 in 205)
    jeep_world = (193.5 + (203.5 - 107.0), 489.0 + (146.5 - 201.5))
    camo = cv2.imread(os.path.join(OUT, "s3_jeep_camo.png"), -1)
    # bush green
    gm = green_mask(f205)
    meas["bush_green"] = [int(v) for v in np.median(f205[gm > 0], 0)]
    # --- bush mosaic (world coords), F = 1.2
    F = 1.2
    origin = (-460.0, -425.0)
    size = (940.0, 1630.0)
    # jeep alpha in frame 205
    ja = np.zeros((854, 480), np.float32)
    h, w = camo.shape[:2]
    A = np.array([[1, 0, jeep_world[0] - w / 2], [0, 1, jeep_world[1] - h / 2]], np.float32)
    ja = cv2.warpAffine(camo[..., 3], A, (480, 854)) > 128
    # front bush = flat, untextured bush green inside the jeep silhouette
    G = np.array(meas["bush_green"], np.float32)
    f32 = f205.astype(np.float32)
    dist = np.abs(f32 - G).max(-1)
    # front piece: everything right of the bush outline that passes in front
    # of the jeep (contour traced by hand on frame 205, reference px)
    contour = [(355, -500), (355, 150), (358, 280), (340, 295), (318, 315), (300, 340), (307, 370),
               (317, 385), (335, 400), (355, 415), (370, 430), (355, 450), (365, 475), (355, 500),
               (362, 520), (358, 900), (2000, 900), (2000, -500)]
    meas["bush_front_contour_ref205"] = contour
    front = np.zeros((854, 480), np.uint8)
    cv2.fillPoly(front, [np.array(contour, np.int32)], 1)
    bush0 = fill_mask_holes(cv2.morphologyEx(gm, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))) > 0
    front = (front > 0) & bush0
    ghost = ja & ~front
    # bush alpha in 205: green + enclosed outlines
    bush = fill_mask_holes(cv2.morphologyEx(gm, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)))
    bush = np.maximum(bush, ja.astype(np.uint8))
    back_src = f205.copy()
    holes = (ghost | (overlays(205) > 0)) & (bush > 0)
    back_src = cv2.inpaint(back_src, cv2.dilate(holes.astype(np.uint8) * 255, np.ones((5, 5), np.uint8)),
                           9, cv2.INPAINT_TELEA)
    # frame 216 for the parts outside frame 205
    f216 = FRAMES(216)
    gm216 = green_mask(f216)
    b216 = fill_mask_holes(cv2.morphologyEx(gm216, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)))
    b216[:, :150] = 0   # pillager / ground left part are not bush
    b216[705:] = 0       # ground
    M216 = np.array(bt["216"]["M"])
    ex216 = overlays(216) | ((1 - b216) * 255).astype(np.uint8)
    # world->216 mapping is M216 (205 coords == world)
    ident = np.array([[1, 0, 0], [0, 1, 0]], np.float64)
    ex205 = ((1 - bush) * 255).astype(np.uint8)
    col, cov = build_mosaic([(back_src, ident, ex205), (f216, M216, ex216)], origin, size, F)
    al, _ = build_mosaic([(np.full_like(f205, 255), ident, ex205), (np.full_like(f216, 255), M216, ex216)],
                         origin, size, F)
    alpha = cv2.GaussianBlur((al[..., 0] / 255.0) * cov, (0, 0), 0.8)
    img = inpaint_holes(col, cov)
    cv2.imwrite(os.path.join(OUT, "bush_back.png"), np.dstack([img, (np.clip(alpha, 0, 1) * 255).astype(np.uint8)]))
    # front piece (only from frame 205)
    fsrc = cv2.inpaint(f205, overlays(205) & (front.astype(np.uint8) * 255), 7, cv2.INPAINT_TELEA)
    colf, covf = build_mosaic([(fsrc, ident, ((1 - front) * 255).astype(np.uint8))], origin, size, F)
    cv2.imwrite(os.path.join(OUT, "bush_front.png"),
                np.dstack([inpaint_holes(colf, covf),
                           (np.clip(cv2.GaussianBlur(covf, (0, 0), 0.8), 0, 1) * 255).astype(np.uint8)]))
    meas["world"] = {"ref_frame": 205, "F": F, "origin": origin, "jeep_center": jeep_world}

    # --- jeep tint per frame
    def place(n):
        if n <= 193:
            x = 137.0 + 7.0 * (n - 185)  # plate x during the slide
            return (min(x, 193.5) + 96.5, 434.0, 1.0)
        M = np.array(bt[str(n)]["M"])
        p = M @ np.array([jeep_world[0], jeep_world[1], 1.0])
        return (p[0], p[1], float(np.hypot(M[0, 0], M[1, 0])))
    meas["jeep_tint"] = jeep_tint_series(meas, list(range(184, 236)) + list(range(283, 300)), place)
    print(meas["jeep_tint"])
    e = {"design_scale": 2.25 / F, "license": "reference_proxy"}
    return {"bush_back": dict(e, path="assets/proxies/bush_back.png", source="Referenzframes 205/216",
                              replace_with="eigener Cartoon-Busch (Vektor), gleiche Silhouette"),
            "bush_front": dict(e, path="assets/proxies/bush_front.png", source="Referenzframe 205",
                               replace_with="Teil des eigenen Cartoon-Buschs, der vor dem Jeep liegt")}


def build_pillager(meas):
    """Minecraft-style figure (two poses) on the sky/ground world (frames 216-282)."""
    f = FRAMES(225)
    sky = [int(v) for v in np.median(f[60:200, 150:300].reshape(-1, 3), 0)]
    ground = [int(v) for v in np.median(f[760:850, 150:300].reshape(-1, 3), 0)]
    col = f[:, 200].astype(int)
    gl = int(np.argmax(np.abs(col - np.array(ground)).max(-1) < 12))
    meas["world_sky_bgr"], meas["world_ground_bgr"], meas["world_ground_line_216"] = sky, ground, gl
    out = {}
    for name, frames in (("pillager_idle", [222, 226, 232, 218]), ("pillager_torch", [245, 268, 276, 280, 260])):
        imgs = [FRAMES(n) for n in frames]
        masks = [overlays(n) for n in frames]
        colr, cov = merge_static(imgs, masks)
        colu = np.clip(colr, 0, 255).astype(np.uint8)
        d_sky = np.abs(colu.astype(np.int16) - np.array(sky)).max(-1)
        d_gr = np.abs(colu.astype(np.int16) - np.array(ground)).max(-1)
        fg = ((d_sky > 30) & (d_gr > 30)).astype(np.uint8)
        fg[:, 235:] = 0
        fg[gl:] = 0
        fg[cov < 0.5] = 0
        fg = largest_component(fg)
        fg = fill_mask_holes(cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)))
        # torch glow on the phone: very bright pixels touching the figure
        glow = (colu.min(-1) > 225) & (cv2.dilate(fg, np.ones((9, 9), np.uint8)) > 0)
        fg = np.maximum(fg, glow.astype(np.uint8))
        spr, (x0, y0) = crop_to_alpha(np.dstack([colu, fg * 255]), 2)
        save_sprite(name, spr)
        h, w = spr.shape[:2]
        meas[name + "_ref"] = {"frame": frames[0], "center_216": [x0 + w / 2, y0 + h / 2]}
        out[name] = {"path": f"assets/proxies/{name}.png", "design_scale": 2.25, "license": "reference_proxy",
                     "source": f"Referenzframes {frames}",
                     "replace_with": "eigene Voxel-/Pixel-Figur (kein Minecraft-Asset: Markenrecht Mojang/Microsoft)"}
    print(sky, ground, gl)
    return out


def obj_mask_on_stripes(n, thresh=18):
    """uint8 mask (255) of pixels that are NOT background stripes / overlays."""
    img = FRAMES(n)
    d = np.abs(img.astype(np.int16) - stripes_bg(n).astype(np.int16)).max(-1)
    m = (d > thresh).astype(np.uint8) * 255
    m[overlays(n) > 0] = 0
    return m


def track_flat(ref, frames, extra_exclude=None, color_reject=None):
    """SIFT similarity of a flat object (ref -> n) on the stripes background."""
    out = {}
    def ex(n):
        e = 255 - obj_mask_on_stripes(n)
        if color_reject is not None:
            e |= color_reject(FRAMES(n))
        if extra_exclude:
            e |= extra_exclude(n)
        return e
    ea = ex(ref)
    for n in frames:
        M, inl = similarity(FRAMES(ref), FRAMES(n), ea, ex(n))
        out[str(n)] = None if (M is None or inl < 12) else {"M": M.tolist(), "inliers": inl}
        if out[str(n)]:
            s_, r_, tx, ty = decompose(M)
            print(n, round(s_, 4), round(r_, 2), round(tx, 1), round(ty, 1), inl, flush=True)
        else:
            print(n, None, inl, flush=True)
    return out


def orange_reject(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] < 25) & (hsv[..., 1] > 120)).astype(np.uint8) * 255   # Drake jacket / skin
    return cv2.dilate(m, np.ones((15, 15), np.uint8))


def build_plate_y_track(meas):
    ref = 380
    meas["plate_y_track"] = track_flat(ref, list(range(355, 553)), color_reject=orange_reject)
    return {}


def flat_mosaic(name, track, sources, origin, size, F, thresh=18, extra_ex=None, alpha_sources=None, red=True):
    """Mosaic + alpha (vs. stripes) of a flat object from tracked frames.
    `alpha_sources`: frames that show the whole object (closed outline);
    the alpha is taken from those only."""
    srcs, als = [], []
    for n in sources:
        M = np.array(track[str(n)]["M"]) if str(n) in track and track[str(n)] else np.array([[1, 0, 0], [0, 1, 0]], float)
        ex = overlays(n, red=red)
        if extra_ex:
            ex = ex | extra_ex(n)
        obj = obj_mask_on_stripes(n, thresh)
        obj = fill_mask_holes((obj > 0).astype(np.uint8)) * 255
        srcs.append((FRAMES(n), M, ex))
        if alpha_sources is None or n in alpha_sources:
            als.append((np.repeat(obj[..., None], 3, -1), M, ex))
    col, cov = build_mosaic(srcs, origin, size, F)
    al, _ = build_mosaic(als, origin, size, F)
    a = (al[..., 0] / 255.0) * (cov if alpha_sources is None else 1.0)
    a = largest_component((a > 0.5).astype(np.uint8))
    a = fill_mask_holes(a).astype(np.float32)
    a = cv2.GaussianBlur(a, (0, 0), 0.8)
    img = inpaint_holes(col, cov)
    bgra = np.dstack([img, (a * 255).astype(np.uint8)])
    cv2.imwrite(os.path.join(OUT, name + ".png"), bgra)
    return bgra


def build_plates(meas):
    out = {}
    e = {"license": "reference_proxy"}
    # Y-751 957 (Bundeswehr plate), reference frame 380 (close-up, s=1)
    tr = meas["plate_y_track"]
    F = 1.0
    o, sz = (-30.0, 90.0), (1150.0, 360.0)
    def arrow_only(n):
        m = red_mask(FRAMES(n), 15)
        m[:, :110] = 0          # keep the flag (red stripe) - the arrow is right of it
        return m
    flat_mosaic("plate_y", tr, [380, 362, 470], o, sz, F, extra_ex=arrow_only, alpha_sources=[362, 470],
                red=False)
    meas["plate_y"] = {"ref_frame": 380, "F": F, "origin": o}
    out["plate_y"] = dict(e, path="assets/proxies/plate_y.png", design_scale=2.25 / F,
                          source="Referenzframes 362/380/470 (Foto laut Einblendung: Wikimedia Commons, Thorsten S., CC3)",
                          replace_with="Wikimedia-Foto mit Namensnennung oder selbst gerendertes Kennzeichen (FE-Schrift)")
    # X-75.. plate, ref 515
    trx = track_flat(515, list(range(500, 548)), color_reject=orange_reject)
    meas["plate_x_track"] = trx
    flat_mosaic("plate_x", trx, [515, 512], (-40.0, -20.0), (900.0, 300.0), 1.0,
                extra_ex=lambda n: orange_reject(FRAMES(n)))
    meas["plate_x"] = {"ref_frame": 515, "F": 1.0, "origin": (-40.0, -20.0)}
    out["plate_x"] = dict(e, path="assets/proxies/plate_x.png", design_scale=2.25,
                          source="Referenzframes 512/515", replace_with="Foto/Render eines X-Kennzeichens (NATO)")
    # TUEV close-up, ref 560
    trt = track_flat(560, list(range(548, 631)), extra_exclude=lambda n: red_mask(FRAMES(n), 15))
    meas["plate_tuev_track"] = trt
    flat_mosaic("plate_tuev", trt, [560, 575, 548], (-60.0, 0.0), (1100.0, 400.0), 1.0,
                extra_ex=lambda n: red_mask(FRAMES(n), 15), alpha_sources=[548])
    meas["plate_tuev"] = {"ref_frame": 560, "F": 1.0, "origin": (-60.0, 0.0)}
    out["plate_tuev"] = dict(e, path="assets/proxies/plate_tuev.png", design_scale=2.25,
                             source="Referenzframes 560/575", replace_with="Foto Kennzeichen mit TÜV-Plakette")
    return out


def build_plate_pushes(meas):
    """Horizontal push transitions: Y plate out (503-507), X plate in/out."""
    def pos_of(asset, M, origin, F, n_list, scale_ref):
        spr = cv2.imread(os.path.join(OUT, asset + ".png"), -1)
        res = {}
        for n in n_list:
            r = track_sprite(FRAMES(n), spr, [scale_ref], (0.0,), min_overlap=0.05, exclude=overlays(n))
            res[str(n)] = {k: round(v, 3) for k, v in r.items()}
            print(asset, n, res[str(n)], flush=True)
        return res
    py = meas["plate_y"]
    M = np.array(meas["plate_y_track"]["470"]["M"])
    s = float(np.hypot(M[0, 0], M[1, 0]))
    meas["plate_y_push"] = pos_of("plate_y", M, py["origin"], py["F"], [470, 503, 504, 505, 506, 507], s / py["F"])
    meas["plate_x_push"] = pos_of("plate_x", None, None, None, [515, 505, 506, 507, 508, 542, 543, 544, 545], 1.0)
    pt = meas["plate_tuev"]
    M = np.array(meas["plate_tuev_track"]["548"]["M"])
    s = float(np.hypot(M[0, 0], M[1, 0]))
    meas["plate_tuev_push"] = pos_of("plate_tuev", M, pt["origin"], pt["F"], [548, 542, 543, 544, 545, 546, 547], s / pt["F"])
    return {}


def build_memes_q3(meas):
    """Drake (Bundeswehr shirt), Drake (NATO shirt) and the Germany flag map."""
    out = {}
    e = {"design_scale": 2.25, "license": "reference_proxy"}
    specs = [
        ("drake_bw", [415, 422, 430, 440], (0, 430, 480, 854), list(range(404, 461)), "Drake-Meme mit Bundeswehr-Shirt"),
        ("drake_nato", [528, 536, 540], (0, 215, 480, 854), list(range(519, 547)), "Drake-Meme mit NATO-Shirt"),
        ("germany_map", [482, 490, 496], (0, 230, 480, 854), list(range(462, 504)), "Deutschlandkarte in Flaggenfarben"),
    ]
    for name, frames, crop, track_frames, desc in specs:
        spr, c = extract_on_stripes(frames, crop=crop, red=False)
        save_sprite(name, spr)
        meas[name + "_ref"] = {"frames": frames, "center": c}
        print(name, spr.shape, c, flush=True)
        tr = {}
        ref = frames[0]
        i0 = track_frames.index(ref) if ref in track_frames else 0
        tr.update(track_range(spr, track_frames[i0::-1], c, list(np.linspace(0.3, 1.5, 25)), radius=300,
                              min_overlap=0.15))
        tr.update(track_range(spr, track_frames[i0:], c, list(np.linspace(0.3, 1.5, 25)), radius=300,
                              min_overlap=0.15))
        meas[name + "_track"] = tr
        out[name] = dict(e, path=f"assets/proxies/{name}.png", source=f"Referenzframes {frames}",
                         replace_with=("eigene Vektorgrafik (Umriss gemeinfrei)" if name == "germany_map"
                                       else desc + ": lizenzierte Meme-Vorlage oder eigene Zeichnung im selben Gestus"))
    return out


def build_cat(meas):
    """Over-exposed white cat (blinded) - full-frame image on white, frame 354."""
    img = FRAMES(354).copy()
    hole = caption_text_mask(img)
    hole[:, 425:452] = 255
    hole = cv2.dilate(hole, np.ones((5, 5), np.uint8))
    img = cv2.inpaint(img, hole, 7, cv2.INPAINT_TELEA)
    cv2.imwrite(os.path.join(OUT, "blinded_cat.png"), img)
    # torch apex: brightest blob of the torch sprite
    spr = cv2.imread(os.path.join(OUT, "pillager_torch.png"), -1)
    g = cv2.cvtColor(spr[..., :3], cv2.COLOR_BGR2GRAY).astype(np.float32) * (spr[..., 3] > 0)
    ys, xs = np.where(g >= g.max() - 10)
    h, w = spr.shape[:2]
    c216 = meas["pillager_torch_ref"]["center_216"]
    apex216 = (c216[0] - w / 2 + xs.mean(), c216[1] - h / 2 + ys.mean())
    meas["torch_apex_216"] = apex216
    print("torch apex (frame 216 px)", apex216)
    return {"blinded_cat": {"path": "assets/proxies/blinded_cat.png", "design_scale": 2.25,
                            "license": "reference_proxy", "source": "Referenzframe 354",
                            "replace_with": "Foto einer weissen Katze (lizenziert), stark ueberbelichtet"}}


def build_torch_light(meas):
    """Torch light as a measured screen-blend light map: L = (lit - unlit) / (255 - unlit)
    between frame 230 (before) and 260 (torch on), same camera. Frame-216 px."""
    unlit = FRAMES(230).astype(np.float32)
    lit = FRAMES(260).astype(np.float32)
    L = np.clip((lit - unlit) / np.maximum(255 - unlit, 8), 0, 1).mean(-1)
    bad = (overlays(260) > 0) | (overlays(230) > 0)
    bad[:, :int(meas["torch_apex_216"][0]) - 4] = True      # the figure itself
    bad[int(meas["world_ground_line_216"]) - 2:] = True
    L[bad] = 0
    L8 = (L * 255).astype(np.uint8)
    hole = bad.astype(np.uint8) * 255
    hole[:, :int(meas["torch_apex_216"][0]) - 4] = 0
    L8 = cv2.inpaint(L8, hole, 9, cv2.INPAINT_TELEA)
    L8 = cv2.GaussianBlur(L8, (0, 0), 3)
    # store as white light with alpha = intensity (for "screen" blending)
    rgba = np.dstack([np.full_like(L8, 255), np.full_like(L8, 252), np.full_like(L8, 230), L8])
    rgba[..., 0] = 205  # B
    cv2.imwrite(os.path.join(OUT, "torch_light_216.png"), rgba)
    meas["torch_light"] = {"frame_space": 216, "max": float(L.max())}
    return {"torch_light_216": {"path": "assets/proxies/torch_light_216.png", "design_scale": 2.25,
                                "license": "derived_measurement",
                                "source": "Lichtkarte aus Differenz Frame 260 vs. 230",
                                "replace_with": "prozeduraler Lichtkegel (light_cone) mit diesen Parametern"}}


BUILDERS = {"q1": build_q1, "arrows": track_arrows, "s3": build_s3, "s3_paint": build_s3_paint, "s3_bob": build_s3_bob, "s3_bob_track": build_s3_bob_track, "bush_track": build_bush_track, "world": build_world, "pillager": build_pillager, "plate_y_track": build_plate_y_track, "plates": build_plates, "plate_pushes": build_plate_pushes, "memes_q3": build_memes_q3, "cat": build_cat, "torch_light": build_torch_light}


def main(names):
    meas = load_meas()
    manifest_path = os.path.join(PROJ, "assets", "manifest.json")
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}
    for n in names or BUILDERS:
        print("building", n)
        manifest.update(BUILDERS[n](meas))
        save_meas(meas)
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1:])
