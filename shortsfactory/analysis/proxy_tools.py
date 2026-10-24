"""Tools to measure the reference video and to build *reference proxies*.

Reference proxies are cut-outs taken from the reference video. They exist only
so that a reconstruction can be compared 1:1 against the original. They are
marked with license "reference_proxy" in the asset manifest and must be
replaced by licensed or self-made assets before anything is published.
"""
import cv2
import numpy as np

REF_W, REF_H = 480, 854
DESIGN_K = 1080 / REF_W  # 2.25 design units per reference pixel


class FrameStore:
    """Random access to decoded reference frames (PNG sequence, 1-based files)."""

    def __init__(self, pattern):
        self.pattern = pattern
        self._c = {}

    def __call__(self, n):
        if n not in self._c:
            im = cv2.imread(self.pattern % (n + 1))
            if im is None:
                raise FileNotFoundError(self.pattern % (n + 1))
            self._c[n] = im
        return self._c[n]


# ----------------------------------------------------------------- masks
def caption_mask(img, band=(395, 462)):
    """Mask (uint8 255) of the burned-in caption: the whole caption band."""
    m = np.zeros(img.shape[:2], np.uint8)
    m[band[0]:band[1], :] = 255
    return m


def red_mask(img, dilate=9):
    red = (img[..., 2] > 170) & (img[..., 1] < 90) & (img[..., 0] < 90)
    m = red.astype(np.uint8) * 255
    if dilate:
        m = cv2.dilate(m, np.ones((dilate, dilate), np.uint8))
    return m


def overlay_mask(img, caption=True, credit=True, label=True, red=False):
    """Everything that is an overlay in the reference (not part of a layer)."""
    m = np.zeros(img.shape[:2], np.uint8)
    if caption:
        m |= caption_mask(img)
    if credit:
        m[:, 425:452] = 255
    if label:
        m[:70, :125] = 255
    if red:
        m |= red_mask(img)
    return m


# ----------------------------------------------------------------- motion
def similarity(img_a, img_b, mask_a=None, mask_b=None, nfeat=4000, ratio=0.75):
    """Similarity transform M (2x3) with  p_b = M p_a  from SIFT matches."""
    sift = cv2.SIFT_create(nfeat)
    ga = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
    gb = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)
    ka, da = sift.detectAndCompute(ga, None if mask_a is None else 255 - mask_a)
    kb, db = sift.detectAndCompute(gb, None if mask_b is None else 255 - mask_b)
    if da is None or db is None or len(ka) < 6 or len(kb) < 6:
        return None, 0
    ms = [x for x, y in cv2.BFMatcher().knnMatch(da, db, k=2) if x.distance < ratio * y.distance]
    if len(ms) < 6:
        return None, len(ms)
    pa = np.float32([ka[m.queryIdx].pt for m in ms])
    pb = np.float32([kb[m.trainIdx].pt for m in ms])
    M, inl = cv2.estimateAffinePartial2D(pa, pb, ransacReprojThreshold=2.0, maxIters=5000)
    return M, int(inl.sum()) if inl is not None else 0


def decompose(M):
    s = float(np.hypot(M[0, 0], M[1, 0]))
    rot = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
    return s, rot, float(M[0, 2]), float(M[1, 2])


# ----------------------------------------------------------------- mosaic
def build_mosaic(sources, origin, size_ref, F):
    """Fuse several frames of the same (flat) layer into one high-res image.

    sources: list of (img_bgr, M_ref_to_frame (2x3), exclude_mask_uint8)
             ordered by priority (sharpest first).
    origin:  (ox, oy) of the mosaic in reference-frame coordinates.
    size_ref:(w, h) mosaic extent in reference-frame units.
    F:       mosaic pixels per reference unit.
    Returns BGRA mosaic, coverage mask.
    """
    W, H = int(round(size_ref[0] * F)), int(round(size_ref[1] * F))
    out = np.zeros((H, W, 3), np.float32)
    cov = np.zeros((H, W), np.float32)
    # mosaic px -> ref coords: p = m/F + o
    A = np.array([[1 / F, 0, origin[0]], [0, 1 / F, origin[1]], [0, 0, 1]])
    for img, M, excl in sources:
        M3 = np.vstack([M, [0, 0, 1]])
        T = (M3 @ A)[:2]  # mosaic px -> frame px
        valid = np.full(img.shape[:2], 255, np.uint8)
        if excl is not None:
            valid = cv2.subtract(valid, excl)
        valid = cv2.erode(valid, np.ones((3, 3), np.uint8))
        warped = cv2.warpAffine(img.astype(np.float32), T, (W, H),
                                flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP)
        vm = cv2.warpAffine(valid, T, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                            borderValue=0).astype(np.float32) / 255
        vm = (vm > 0.99).astype(np.float32)
        take = vm * (1 - cov)
        out += warped * take[..., None]
        cov = np.maximum(cov, vm)
    return out, cov


def inpaint_holes(bgr, cov, radius=5):
    hole = ((cov < 0.5) * 255).astype(np.uint8)
    img = np.clip(bgr, 0, 255).astype(np.uint8)
    if hole.any():
        img = cv2.inpaint(img, hole, radius, cv2.INPAINT_TELEA)
    return img


# ----------------------------------------------------------------- alpha
def alpha_from_background(img, bg, thresh=10, soft=8, close=5, fill_holes=True):
    """Alpha matte by difference against a known clean background."""
    d = np.abs(img.astype(np.float32) - bg.astype(np.float32)).max(-1)
    a = np.clip((d - thresh) / soft, 0, 1)
    m = (a > 0.5).astype(np.uint8)
    if close:
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((close, close), np.uint8))
    if fill_holes:
        m = fill_mask_holes(m)
    a = np.maximum(a, m.astype(np.float32))
    a = cv2.GaussianBlur(a, (3, 3), 0.7)
    return a


def fill_mask_holes(m):
    """Fill enclosed holes of a binary mask (border-connected 0s stay 0)."""
    h, w = m.shape
    ff = np.zeros((h + 2, w + 2), np.uint8)
    ff[1:-1, 1:-1] = (m > 0).astype(np.uint8) * 255
    pad = np.zeros((h + 4, w + 4), np.uint8)
    cv2.floodFill(ff, pad, (0, 0), 128)
    return (ff[1:-1, 1:-1] != 128).astype(np.uint8)


def largest_component(m):
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8))
    if n <= 1:
        return m
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return (lab == i).astype(np.uint8)


def to_bgra(bgr, alpha):
    a = (np.clip(alpha, 0, 1) * 255).astype(np.uint8)
    return np.dstack([np.clip(bgr, 0, 255).astype(np.uint8), a])


def crop_to_alpha(bgra, pad=2):
    ys, xs = np.where(bgra[..., 3] > 0)
    if len(xs) == 0:
        return bgra, (0, 0)
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, bgra.shape[1])
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, bgra.shape[0])
    return bgra[y0:y1, x0:x1], (x0, y0)


# ----------------------------------------------------------------- arrows
def track_arrow(img, min_area=3000):
    """Return (tip_x, tip_y, angle_deg, area) of the big red arrow or None."""
    m = red_mask(img, dilate=0)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return None
    c = max(cs, key=cv2.contourArea)
    area = cv2.contourArea(c)
    if area < min_area:
        return None
    pts = c.reshape(-1, 2).astype(np.float64)
    # principal axis
    mu = pts.mean(0)
    u, s, vt = np.linalg.svd(pts - mu, full_matrices=False)
    ax = vt[0]
    proj = (pts - mu) @ ax
    perp = (pts - mu) @ vt[1]
    # the head is the wider end: compare width near both ends
    lo = proj < np.percentile(proj, 25)
    hi = proj > np.percentile(proj, 75)
    w_lo = np.ptp(perp[lo]) if lo.any() else 0
    w_hi = np.ptp(perp[hi]) if hi.any() else 0
    if w_lo > w_hi:
        ax = -ax
        proj = -proj
    tip = pts[np.argmax(proj)]
    ang = float(np.degrees(np.arctan2(ax[1], ax[0])))
    return float(tip[0]), float(tip[1]), ang, float(area)


# ----------------------------------------------------------------- captions
def caption_text_mask(img, band=(380, 485), grow=4):
    """Pixels of the burned-in caption word (white text + dark outline/shadow)."""
    m = np.zeros(img.shape[:2], np.uint8)
    sub = img[band[0]:band[1]].astype(np.int16)
    white = sub.min(-1) > 225
    dark = sub.max(-1) < 110
    near_dark = cv2.dilate(dark.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    text = (white & near_dark).astype(np.uint8)
    if text.any():
        # glyph interiors: close horizontally, then grow over outline + shadow
        text = cv2.morphologyEx(text, cv2.MORPH_CLOSE, np.ones((3, 9), np.uint8))
        text = cv2.dilate(text, np.ones((2 * grow + 1, 2 * grow + 1), np.uint8))
    m[band[0]:band[1]] = text * 255
    return m


def merge_static(frames_imgs, masks):
    """Per-pixel merge of several frames of a static shot, skipping masked
    pixels (e.g. caption words that differ between the frames)."""
    acc = np.zeros(frames_imgs[0].shape, np.float32)
    cov = np.zeros(frames_imgs[0].shape[:2], np.float32)
    for img, m in zip(frames_imgs, masks):
        ok = (m == 0).astype(np.float32) * (1 - cov)
        acc += img.astype(np.float32) * ok[..., None]
        cov = np.maximum(cov, (m == 0).astype(np.float32))
    return acc, cov


# ----------------------------------------------------------------- sprite tracking
def _corr(img, tpl):
    return cv2.matchTemplate(img, tpl, cv2.TM_CCORR)


def _masked_ssd_valid(frame, spr, p, valid):
    """Mean squared error of `spr` at every placement over the pixels where
    `valid` is 1 (padding/off-screen and excluded pixels are 0).
    Index (y, x) of the result = sprite top-left at (x - p, y - p)."""
    H, W = frame.shape[:2]
    I = np.zeros((H + 2 * p, W + 2 * p, 3), np.float32)
    I[p:p + H, p:p + W] = frame.astype(np.float32) / 255
    T = spr[..., :3].astype(np.float32) / 255
    m = (spr[..., 3].astype(np.float32) / 255 > 0.5).astype(np.float32)
    N = _corr(valid, m)
    err = np.zeros_like(N)
    for c in range(3):
        Ic, Tc = I[..., c], T[..., c]
        err += _corr(valid * Ic * Ic, m) - 2 * _corr(valid * Ic, m * Tc) + _corr(valid, m * Tc * Tc)
    return err / np.maximum(N, 1), N / max(m.sum(), 1)


def transform_sprite(sprite_bgra, s, r):
    spr = cv2.resize(sprite_bgra, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)
    if r:
        h, w = spr.shape[:2]
        Mr = cv2.getRotationMatrix2D((w / 2, h / 2), -r, 1.0)
        cos, sin = abs(Mr[0, 0]), abs(Mr[0, 1])
        nw, nh = int(h * sin + w * cos) + 2, int(h * cos + w * sin) + 2
        Mr[0, 2] += nw / 2 - w / 2
        Mr[1, 2] += nh / 2 - h / 2
        spr = cv2.warpAffine(spr, Mr, (nw, nh))
    return spr


def track_sprite(frame, sprite_bgra, scales, rots=(0.0,), min_overlap=0.35, guess=None, radius=None,
                 exclude=None):
    """Best placement of a sprite in a frame (sprite may be partly off-screen).

    Returns dict(cx, cy, scale, rot, err, overlap) with the sprite centre in
    frame pixels. `exclude` (uint8 mask) marks frame pixels to ignore.
    """
    H, W = frame.shape[:2]
    best = None
    for s in scales:
        for r in rots:
            spr = transform_sprite(sprite_bgra, s, r)
            h, w = spr.shape[:2]
            p = max(h, w)
            valid = np.zeros((H + 2 * p, W + 2 * p), np.float32)
            valid[p:p + H, p:p + W] = 1
            if exclude is not None:
                valid[p:p + H, p:p + W] *= (exclude == 0)
            err, ov = _masked_ssd_valid(frame, spr, p, valid)
            err[ov < min_overlap] = np.inf
            if guess is not None and radius is not None:
                yy, xx = np.mgrid[0:err.shape[0], 0:err.shape[1]]
                d2 = (xx - p + w / 2 - guess[0]) ** 2 + (yy - p + h / 2 - guess[1]) ** 2
                err[d2 > radius ** 2] = np.inf
            y, x = np.unravel_index(np.argmin(err), err.shape)
            e = float(err[y, x])
            if best is None or e < best["err"]:
                best = {"cx": float(x - p + w / 2), "cy": float(y - p + h / 2), "scale": float(s),
                        "rot": float(r), "err": e, "overlap": float(ov[y, x])}
    return best


def refine_track(frame, sprite_bgra, guess, scale_range=(0.9, 1.1), steps=9, rots=(0.0,), radius=40,
                 exclude=None, min_overlap=0.35):
    lo, hi = scale_range
    scales = list(np.linspace(lo, hi, steps))
    return track_sprite(frame, sprite_bgra, scales, rots, min_overlap=min_overlap, guess=guess,
                        radius=radius, exclude=exclude)
