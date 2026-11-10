"""Replace the procedural islands with the user's aerial pictures.

* every detail tile showing the island gets the island painted out (inpainted ocean, from a kept original)
* the picture is fitted (centre, principal-axis rotation, length) to the island outline of the finest tile
"""
import os
import shutil

import cv2
import numpy as np
from PIL import Image


def axis_fit(mask):
    ys, xs = np.nonzero(mask)
    pts = np.c_[xs, ys].astype(np.float64)
    c = pts.mean(0)
    u, s, vt = np.linalg.svd(pts - c, full_matrices=False)
    v = vt[0]
    proj = (pts - c) @ v
    ang = np.degrees(np.arctan2(v[1], v[0]))
    lo, hi = proj.min(), proj.max()
    c = c + v * (lo + hi) / 2            # centre of the extent along the axis
    return c, hi - lo, ang


def island_mask(rgb, near):
    a = rgb.astype(np.float32)
    ocean = np.median(a.reshape(-1, 3), 0)
    d = np.abs(a - ocean).sum(2)
    m = (cv2.GaussianBlur(((d > 38) * 255).astype(np.uint8), (0, 0), 3) > 100).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
    if n < 2:
        return None
    k = 1 + int(np.argmin([np.hypot(*(cen[i] - near)) - 0.5 * np.sqrt(st[i, 4]) for i in range(1, n)]))
    if np.hypot(*(cen[k] - near)) > 0.25 * max(rgb.shape[:2]):
        return None
    return lab == k


def paint_out(out_dir, tile, meta, island_xy):
    """inpaint the island of one tile (from <tile>_orig.png); returns the island mask in tile px"""
    p = os.path.join(out_dir, tile + ".png")
    orig = os.path.join(out_dir, tile + "_orig.png")
    if not os.path.exists(orig):
        shutil.copy(p, orig)
    im = np.array(Image.open(orig).convert("RGBA"))
    tm = meta[tile]
    near = (np.array(island_xy) - np.array(tm["pos"])) / tm["design_scale"]
    m = island_mask(im[..., :3], near)
    if m is None:
        shutil.copy(orig, p)
        return None
    grow = max(6, int(0.04 * np.sqrt(m.sum())))
    mm = cv2.dilate(m.astype(np.uint8), np.ones((2 * grow + 1, 2 * grow + 1), np.uint8))
    rgb = cv2.inpaint(np.ascontiguousarray(im[..., :3]), mm * 255, 9, cv2.INPAINT_TELEA)
    # bring back fine paper grain: high-pass of a nearby ocean patch would be nicer; noise is enough here
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 2.5, rgb.shape[:2])[..., None]
    rgb = np.where(mm[..., None] > 0, np.clip(rgb + noise, 0, 255), rgb).astype(np.uint8)
    im[..., :3] = rgb
    Image.fromarray(im, "RGBA").save(p)
    return m


def fit(meta, tile, tile_mask, img_path):
    """map-space placement for the cut-out picture (anchor = centre of its island extent)"""
    tm = meta[tile]
    (tx, ty), tl, ta = axis_fit(tile_mask)
    al = np.array(Image.open(img_path))[..., 3] > 128
    (ix, iy), il, ia = axis_fit(al)
    rot = ta - ia
    while rot > 90:
        rot -= 180
    while rot < -90:
        rot += 180
    h, w = al.shape
    return dict(x=float(tm["pos"][0] + tx * tm["design_scale"]), y=float(tm["pos"][1] + ty * tm["design_scale"]),
                scale=float(tl * tm["design_scale"] / il), rot=float(rot), anchor=[float(ix / w), float(iy / h)])
