"""Proxies + measurements for 20-40 s (frames 600-1200). Same conventions as
build_proxies.py (reference px, REFERENCE PROXY assets)."""
import json
import os
import sys

import cv2
import numpy as np

from build_proxies import *  # noqa: F401,F403  (FRAMES, OUT, helpers)
from build_proxies import track_range  # noqa: E402
import build_proxies as B


def rectify_alpha(name, x_max=None):
    """Plates are rectangles: replace the alpha by its dominant row/column extent
    (removes holes left by masked overlays such as the [Qn] label)."""
    path = os.path.join(B.OUT, name + ".png")
    im = cv2.imread(path, -1)
    a = im[..., 3] > 128
    rows = np.where(a.mean(1) > 0.5 * a.mean(1).max())[0]
    cols = np.where(a.mean(0) > 0.3 * a.mean(0).max())[0]   # spans the masked credit column
    na = np.zeros(a.shape, np.uint8)
    x1 = cols[-1] + 1 if x_max is None else x_max
    na[rows[0]:rows[-1] + 1, cols[0]:x1] = 255
    im[..., 3] = na
    cv2.imwrite(path, im)


def build_seal_plate(meas):
    """Close-up plate 598-642: TUEV sticker (until 609) -> Bundeswehr seal (610+)."""
    tr = B.track_flat(620, list(range(598, 643)), extra_exclude=lambda n: B.red_mask(FRAMES(n), 15))
    # 600 is a motion frame the tracker cannot lock: interpolate 599 -> 601
    m599, m601 = np.array(tr["599"]["M"]), np.array(tr["601"]["M"])
    tr["600"] = {"M": ((m599 + m601) / 2).tolist(), "inliers": 0, "interpolated": True}
    meas["seal_plate_track"] = tr
    o, sz = (-20.0, -10.0), (520.0, 420.0)
    meas["seal_plate"] = {"ref_frame": 620, "F": 1.0, "origin": o}
    B.flat_mosaic("plate_close_tuev", tr, [605, 603, 607], o, sz, 1.0, alpha_sources=[605, 603, 607])
    B.flat_mosaic("plate_close_seal", tr, [620, 630, 615], o, sz, 1.0, alpha_sources=[620, 630, 615])
    # the light plate is hard to separate from the pale stripes near the right
    # frame edge; it runs past the frame edge (x=480 -> mosaic x=500)
    rectify_alpha("plate_close_tuev", 500)
    rectify_alpha("plate_close_seal", 500)
    e = {"design_scale": 2.25, "license": "reference_proxy"}
    return {"plate_close_tuev": dict(e, path="assets/proxies/plate_close_tuev.png", source="Referenzframes 603-607",
                                     replace_with="Nahaufnahme Kennzeichen mit TÜV-Plakette (Foto)"),
            "plate_close_seal": dict(e, path="assets/proxies/plate_close_seal.png", source="Referenzframes 615-630",
                                     replace_with="Nahaufnahme Bundeswehr-Kennzeichen mit Siegelplakette (Foto)")}


HOUSE_PLATE_FRAME = 885     # wide street shot, no vehicles


def fg_mask(n, plate, thr=25, ymin=0, ymax=854):
    d = np.abs(FRAMES(n).astype(np.int16) - plate.astype(np.int16)).max(-1)
    m = (d > thr).astype(np.uint8)
    m[B.overlays(n, red=False) > 0] = 0
    m[:ymin] = 0
    m[ymax:] = 0
    return m


def horizontal_track(frames, plate, ymin, ymax):
    """x position of a horizontally moving object (frame 0 of the list = 0),
    from phase correlation of consecutive foreground-masked frames."""
    xs = [0.0]
    for a, b in zip(frames, frames[1:]):
        ga = cv2.cvtColor(FRAMES(a), cv2.COLOR_BGR2GRAY).astype(np.float32) * fg_mask(a, plate, ymin=ymin, ymax=ymax)
        gb = cv2.cvtColor(FRAMES(b), cv2.COLOR_BGR2GRAY).astype(np.float32) * fg_mask(b, plate, ymin=ymin, ymax=ymax)
        win = cv2.createHanningWindow(ga.shape[::-1], cv2.CV_32F)
        (dx, dy), resp = cv2.phaseCorrelate(ga, gb, win)
        xs.append(xs[-1] + dx)
    # while the object enters/leaves, the correlation locks on 0: continue the
    # neighbouring constant speed instead (the reference uses linear motion)
    d = np.diff(xs)
    moving = np.abs(d) > 1
    if moving.any():
        first, last = np.argmax(moving), len(d) - 1 - np.argmax(moving[::-1])
        d[:first] = d[first]
        d[last + 1:] = d[last]
    return [0.0] + list(np.cumsum(d))


def stitch_moving(name, frames, xs, plate, ymin, ymax, x_left_ref, extra_ex=None):
    """Mosaic of a horizontally moving sprite; returns sprite + its x offset:
    sprite pixel u sits at frame x = u + sprite_x0 + xs[i] for frames[i]."""
    lo = int(np.floor(min(-x for x in xs))) - 2
    hi = int(np.ceil(max(480 - x for x in xs))) + 2
    W = hi - lo
    H = ymax - ymin
    col = np.zeros((H, W, 3), np.float32)
    acc = np.zeros((H, W), np.float32)
    al = np.zeros((H, W), np.float32)
    for n, x in zip(frames, xs):
        img = FRAMES(n)[ymin:ymax].astype(np.float32)
        m = fg_mask(n, plate, ymin=0, ymax=854)[ymin:ymax].astype(np.float32)
        ov = B.overlays(n, red=False)
        if extra_ex and n in extra_ex:
            ov = ov | extra_ex[n]
        valid = (ov[ymin:ymax] == 0).astype(np.float32)
        T = np.array([[1, 0, -x - lo], [0, 1, 0]], np.float32)   # frame -> sprite px
        wi = cv2.warpAffine(img, T, (W, H))
        wm = cv2.warpAffine(m, T, (W, H))
        wv = cv2.warpAffine(valid, T, (W, H))
        # interior frames (not at the frame border) get more weight
        col += wi * wv[..., None]
        acc += wv
        al += wm * wv
    col /= np.maximum(acc, 1e-3)[..., None]
    alpha = al / np.maximum(acc, 1e-3)
    # vehicles are opaque: camo parts that match the grey street leave holes
    a = (alpha > 0.35).astype(np.uint8)
    a = cv2.morphologyEx(a, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    a = B.largest_component(cv2.morphologyEx(a, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)))
    a = B.fill_mask_holes(a)
    hole = ((acc < 0.5) & (a > 0)).astype(np.uint8) * 255
    colu = np.clip(col, 0, 255).astype(np.uint8)
    if hole.any():
        colu = cv2.inpaint(colu, hole, 5, cv2.INPAINT_TELEA)
    bgra = np.dstack([colu, (cv2.GaussianBlur(a.astype(np.float32), (0, 0), 0.7) * 255).astype(np.uint8)])
    spr, (x0, y0) = B.crop_to_alpha(bgra, 2)
    cv2.imwrite(os.path.join(B.OUT, name + ".png"), spr)
    return spr, (x0 + lo, y0 + ymin)


def build_vehicles(meas):
    plate = FRAMES(HOUSE_PLATE_FRAME)
    out = {}
    specs = {"truck1": list(range(729, 750)), "crane": list(range(751, 774)), "truck3": list(range(773, 794)),
             "tank_street": list(range(811, 877))}
    res = {}
    for name, frames in specs.items():
        xs = horizontal_track(frames, plate, 250, 854)
        use, use_x, ex = frames, xs, None
        if name == "tank_street":
            # the seal stamp sits on the turret from 840 on: build the clean tank from
            # the frames before it, plus the exit frames with the stamp masked
            sx, sy = meas.get("seal_stamp_845", (312.0, 461.0))
            x845 = xs[frames.index(845)]
            use = [n for n in frames if n <= 829 or n >= 862]
            use_x = [xs[frames.index(n)] for n in use]
            ex = {}
            for n in use:
                if n >= 862:
                    mm = np.zeros((854, 480), np.uint8)
                    cx = int(sx + xs[frames.index(n)] - x845)
                    mm[int(sy) - 28:int(sy) + 28, max(cx - 45, 0):max(cx + 45, 0)] = 255
                    ex[n] = mm
        spr, (sx0, sy0) = stitch_moving("street_" + name, use, use_x, plate, 250, 854, 0, extra_ex=ex)
        res[name] = {"frames": frames, "x": [round(float(x), 2) for x in xs], "sprite_x0": int(sx0), "sprite_y0": int(sy0),
                     "w": int(spr.shape[1]), "h": int(spr.shape[0])}
        print(name, spr.shape, "dx per frame", [round(b - a, 1) for a, b in zip(xs, xs[1:])], flush=True)
        out["street_" + name] = {"path": f"assets/proxies/street_{name}.png", "design_scale": 2.25,
                                 "license": "reference_proxy", "source": f"Referenzframes {frames[0]}-{frames[-1]} (gestitcht)",
                                 "replace_with": "Freisteller-Foto eines Bundeswehrfahrzeugs (Seitenansicht)"}
    meas["street_vehicles"] = res
    return out


WIN_CLOSE = (106, 411, 375, 679)   # window interior in close-up frames (x0, y0, x1, y1)


def build_house(meas):
    """Bundeswehr building: camera track (world = wide frame 760), high-res
    facade mosaic from the close-ups, villager poses, flying seal."""
    ref = 760
    ea = B.overlays(ref)
    ea[150:, :] = 255
    tr = {}
    for n in list(range(642, 730)) + list(range(880, 914)):
        M, inl = B.similarity(FRAMES(ref), FRAMES(n), ea, B.overlays(n))
        tr[str(n)] = None if M is None or inl < 12 else {"M": M.tolist(), "inliers": inl}
    # the close-up camera is one fixed framing: average the holds
    hold = [np.array(tr[str(n)]["M"]) for n in list(range(650, 720)) + list(range(896, 912)) if tr.get(str(n))]
    Mc = np.mean(hold, 0)
    for n in list(range(643, 720)) + list(range(893, 913)):
        tr[str(n)] = {"M": Mc.tolist(), "inliers": -1}
    for n in list(range(722, 891)):
        tr[str(n)] = {"M": [[1, 0, 0], [0, 1, 0]], "inliers": -1}
    meas["house_track"] = tr
    meas["house_close_M"] = Mc.tolist()
    sc = float(np.hypot(Mc[0, 0], Mc[1, 0]))
    print("close-up scale", sc, "t", Mc[:, 2])

    # facade mosaic, F = close-up scale
    F = round(sc, 4)
    origin, size = (-10.0, -10.0), (500.0, 874.0)
    win_mask = np.zeros((854, 480), np.uint8)
    x0, y0, x1, y1 = WIN_CLOSE
    srcs = []
    for n in (650, 660, 700, 905):
        ex = B.overlays(n)
        if n != 650 and n != 660:
            ex[y0 - 3:y1 + 3, x0 - 3:x1 + 3] = 255      # villager inside
        srcs.append((FRAMES(n), np.array(tr[str(n)]["M"]), ex))
    # wide shot (no vehicles) for everything outside the close-up
    exw = B.overlays(885)
    wx0, wy0 = np.linalg.solve(Mc[:, :2], np.array([x0, y0]) - Mc[:, 2])
    wx1, wy1 = np.linalg.solve(Mc[:, :2], np.array([x1, y1]) - Mc[:, 2])
    exw[int(wy0) - 2:int(wy1) + 3, int(wx0) - 2:int(wx1) + 3] = 255
    srcs.append((FRAMES(885), np.array([[1, 0, 0], [0, 1, 0]], float), exw))
    col, cov = B.build_mosaic(srcs, origin, size, F)
    img = B.inpaint_holes(col, cov)
    cv2.imwrite(os.path.join(B.OUT, "house_world.png"), img)
    meas["house_world"] = {"F": F, "origin": origin, "window_wide": [float(wx0), float(wy0), float(wx1), float(wy1)]}

    # villager poses (close-up px), cut against the empty window (frame 650)
    empty = FRAMES(650).astype(np.int16)
    out = {}
    for name, frames in (("villager_idle", [680, 896, 908, 912, 893]), ("villager_seal", [705, 712, 718])):
        imgs = [FRAMES(n) for n in frames]
        masks = [B.overlays(n) for n in frames]
        colr, cv_ = B.merge_static(imgs, masks)
        d = np.abs(colr.astype(np.int16) - empty).max(-1)
        m = np.zeros((854, 480), np.uint8)
        m[y0:y1, x0:x1] = (d[y0:y1, x0:x1] > 20)
        # caption remnants above the beret are light / thin: drop bright pixels, open
        m[colr.min(-1) > 190] = 0
        m[y0:y0 + 18] = 0               # inner shadow line of the window frame
        m[y0:y0 + 60, x0:x0 + 6] = 0
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        m = B.fill_mask_holes(cv2.morphologyEx(B.largest_component(m), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)))
        hole = ((cv_ < 0.5) & (m > 0)).astype(np.uint8) * 255
        colu = cv2.inpaint(np.clip(colr, 0, 255).astype(np.uint8), hole, 5, cv2.INPAINT_TELEA)
        bgra = np.dstack([colu, m * 255])
        spr, (sx, sy) = B.crop_to_alpha(bgra, 1)
        cv2.imwrite(os.path.join(B.OUT, name + ".png"), spr)
        h, w = spr.shape[:2]
        meas[name + "_close_center"] = [sx + w / 2, sy + h / 2]
        out[name] = {"path": f"assets/proxies/{name}.png", "design_scale": 2.25 / F, "license": "reference_proxy",
                     "source": f"Referenzframes {frames}",
                     "replace_with": "eigene Voxel-Figur mit rotem Barett (kein Minecraft-Asset)"}
    # rise into the window: top of the red beret per frame (close-up px)
    def beret_top(n):
        hsv = cv2.cvtColor(FRAMES(n)[300:760, 80:400], cv2.COLOR_BGR2HSV).astype(int)
        red = ((hsv[..., 0] < 8) | (hsv[..., 0] > 170)) & (hsv[..., 1] > 120) & (hsv[..., 2] > 60)
        ys = np.where(red.sum(1) > 3)[0]
        return 300 + int(ys.min()) if len(ys) else None
    rest = beret_top(680)
    rise = {str(n): (beret_top(n) - rest if beret_top(n) is not None else None) for n in (671, 672, 673, 674)}
    meas["villager_rise_dy"] = rise
    print("rise", rise)
    out["house_world"] = {"path": "assets/proxies/house_world.png", "design_scale": 2.25 / F,
                          "license": "reference_proxy", "source": "Mosaik Referenzframes 650/660/700/905/885",
                          "replace_with": "eigene Illustration: Haus mit Bundeswehr-Schild, Strasse, Himmel"}
    return out


FLIGHTS = {"seal1": [731, 732, 733, 734], "seal2": [754, 755, 756, 757, 758], "seal3": [779, 780, 781, 782, 783],
           "seal4": [826, 827, 828, 829, 830, 831, 832, 833, 834, 835, 836, 837, 838, 839]}


def blob_near(n, ref_img, guess, radius=70, thr=40):
    d = np.abs(FRAMES(n).astype(np.int16) - ref_img.astype(np.int16)).max(-1)
    d[B.overlays(n, red=False) > 0] = 0
    m = (d > thr).astype(np.uint8)
    yy, xx = np.mgrid[0:854, 0:480]
    m[(xx - guess[0]) ** 2 + (yy - guess[1]) ** 2 > radius ** 2] = 0
    nl, lab, st, cen = cv2.connectedComponentsWithStats(m)
    if nl <= 1:
        return None
    i = 1 + int(np.argmax(st[1:, 4]))
    return float(cen[i][0]), float(cen[i][1]), int(st[i][4]), st[i][:4].tolist()


def build_seals(meas):
    """Flying seal coin (projectile), its flights, and the stamp on the tank."""
    out = {}
    # coin sprite: frame 833 against 824 (no coin in flight, same tank/house)
    b = blob_near(833, FRAMES(824), (272, 214), 60)
    x, y, w, h = b[3]
    img = FRAMES(833)
    d = np.abs(img.astype(np.int16) - FRAMES(824).astype(np.int16)).max(-1)
    m = (d > 30).astype(np.uint8)
    pad = 3
    crop = img[y - pad:y + h + pad, x - pad:x + w + pad]
    mc = B.fill_mask_holes(B.largest_component(m[y - pad:y + h + pad, x - pad:x + w + pad]))
    coin = np.dstack([crop, cv2.GaussianBlur(mc.astype(np.float32), (0, 0), 0.7) * 255]).astype(np.uint8)
    cv2.imwrite(os.path.join(B.OUT, "seal_coin.png"), coin)
    coin_area = float(mc.sum())
    print("coin", coin.shape, coin_area)
    flights = {}
    plate = FRAMES(885)
    for name, frames in FLIGHTS.items():
        pts = []
        refimg = FRAMES(frames[0] - 2)
        g = (256, 190)
        for n in frames:
            bb = blob_near(n, refimg if name != "seal4" else FRAMES(824), g, 90)
            if bb is None:
                break
            pts.append([n, round(bb[0], 1), round(bb[1], 1), round(float(np.sqrt(bb[2] / coin_area)), 3)])
            g = bb[:2]
        flights[name] = pts
        print(name, pts)
    meas["seal_flights"] = flights
    # stamp on the tank: frame 845 vs 829 (tank stationary in both)
    d = np.abs(FRAMES(845).astype(np.int16) - FRAMES(829).astype(np.int16)).max(-1)
    d[B.overlays(845) > 0] = 0
    d[B.overlays(829) > 0] = 0
    d[:250] = 0
    m = B.largest_component((d > 30).astype(np.uint8))
    m = B.fill_mask_holes(cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)))
    ys, xs = np.where(m > 0)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    stamp = np.dstack([FRAMES(845)[y0:y1, x0:x1], m[y0:y1, x0:x1] * 255])
    cv2.imwrite(os.path.join(B.OUT, "seal_stamp.png"), stamp)
    meas["seal_stamp_845"] = [float((x0 + x1) / 2), float((y0 + y1) / 2)]
    print("stamp", stamp.shape, meas["seal_stamp_845"])
    e = {"design_scale": 2.25, "license": "reference_proxy"}
    out["seal_coin"] = dict(e, path="assets/proxies/seal_coin.png", source="Referenzframe 833",
                            replace_with="eigene Grafik: graues Dienstsiegel (Bundesadler gemeinfrei)")
    out["seal_stamp"] = dict(e, path="assets/proxies/seal_stamp.png", source="Referenzframe 845",
                             replace_with="eigene Grafik: Stempelabdruck Dienstsiegel")
    return out


RED_TINT_C = np.array([88, 88, 200], np.float32)        # BGR, fitted on background pixels
RED_TINT_KEYS = [(923, 0.0), (950, 0.369), (960, 0.58), (968, 0.75), (973, 0.75)]


def red_tint_alpha(n):
    fr = [p[0] for p in RED_TINT_KEYS]
    return float(np.interp(n, fr, [p[1] for p in RED_TINT_KEYS])) if fr[0] <= n <= fr[-1] else 0.0


def build_sweat_meme(meas):
    """Animated 'sweating man' meme (924-973): per-frame cut-outs, red tint
    removed (it is re-applied as its own overlay layer)."""
    seq_dir = os.path.join(B.OUT, "sweat_meme")
    os.makedirs(seq_dir, exist_ok=True)
    frames = list(range(924, 974))
    for i, n in enumerate(frames):
        a = red_tint_alpha(n)
        img = (FRAMES(n).astype(np.float32) - a * RED_TINT_C) / (1 - a)
        bg = B.stripes_bg(n).astype(np.float32)
        d = np.abs(img - bg).max(-1)
        cap = B.caption_text_mask(FRAMES(n))
        d[cap > 0] = 255                       # captions sit on top of the meme
        # background = bg-like pixels connected to the top/left/right border
        # (face areas are enclosed by the black outlines of the drawing)
        bgl = (d < 32).astype(np.uint8)
        bgl[cap > 0] = 0
        nl, lab = cv2.connectedComponents(bgl)
        border = set(np.unique(np.concatenate([lab[0], lab[:, 0], lab[:, -1]]))) - {0}
        bgm = np.isin(lab, list(border))
        m = (~bgm).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        m = B.largest_component(m)
        imgu = np.clip(img, 0, 255).astype(np.uint8)
        hole = cv2.dilate(cap, np.ones((3, 3), np.uint8)) & (m * 255)
        if hole.any():
            imgu = cv2.inpaint(imgu, hole, 5, cv2.INPAINT_TELEA)
        alpha = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.8)
        cv2.imwrite(os.path.join(seq_dir, f"{i:03d}.png"), np.dstack([imgu, (alpha * 255).astype(np.uint8)]))
    meas["sweat_meme"] = {"first_frame": frames[0], "frames": len(frames)}
    meas["red_tint"] = {"color_bgr": RED_TINT_C.tolist(), "keys": RED_TINT_KEYS}
    return {"sweat_meme": {"path": "assets/proxies/sweat_meme/{i:03d}.png", "frames": len(frames),
                           "design_scale": 2.25, "license": "reference_proxy",
                           "source": "Referenzframes 924-973, Freisteller pro Frame, Rottönung herausgerechnet",
                           "replace_with": "eigene Animation: schwitzender Mann wischt sich die Stirn (Cartoon)"}}


def build_leo_track(meas):
    """Leopard 2 scene: sprite on stripes (995-1029) + camera track of the
    tank/world for 981-1141 (reference = frame 1040)."""
    spr, c = B.extract_on_stripes([1000, 1010, 1020, 1026, 995], red=False)
    B.save_sprite("leo_small", spr)
    meas["leo_small_center_1000"] = c
    ref = 1040
    def ex(n):
        e = B.overlays(n)
        e |= B.red_mask(FRAMES(n), 15)
        return e
    tr = {}
    ea = ex(ref)
    for n in range(981, 1142):
        M, inl = B.similarity(FRAMES(ref), FRAMES(n), ea, ex(n))
        tr[str(n)] = None if M is None or inl < 10 else {"M": M.tolist(), "inliers": inl}
        if M is not None:
            sc, r, tx, ty = B.decompose(M)
            print(n, round(sc, 4), round(r, 2), round(tx, 1), round(ty, 1), inl, flush=True)
        else:
            print(n, None, inl, flush=True)
    meas["leo_track"] = tr
    return {}


def M3(m):
    return np.vstack([np.array(m, float), [0, 0, 1]])


def build_leo_assets(meas):
    tr = meas["leo_track"]
    # chain the muzzle close-ups (ref 1085) onto the main reference (1040)
    def ex(n):
        return B.overlays(n)
    # 1060-1072 is a uniform pan (few features): fit scale/translation linearly
    raw = {}
    for n in range(1060, 1073):
        M, inl = B.similarity(FRAMES(1040), FRAMES(n), ex(1040), ex(n))
        if M is not None and inl >= 5:
            raw[n] = M
    ns = np.array(sorted(raw))
    fit = [np.polyfit(ns, [raw[n][i // 3, i % 3] for n in ns], 1) for i in range(6)]
    for n in range(1060, 1073):
        tr[str(n)] = {"M": np.array([np.polyval(f, n) for f in fit]).reshape(2, 3).tolist(), "inliers": -1,
                      "linear_fit": True}
    M85_72, _ = B.similarity(FRAMES(1085), FRAMES(1072), ex(1085), ex(1072), nfeat=6000, ratio=0.8)
    M40_85 = np.linalg.inv(M3(M85_72)) @ M3(tr["1072"]["M"])
    for n in range(1073, 1105):
        if n >= 1103:
            continue
        M, inl = B.similarity(FRAMES(1085), FRAMES(n), ex(1085), ex(n), nfeat=6000, ratio=0.8)
        tr[str(n)] = {"M": (M3(M) @ M40_85)[:2].tolist(), "inliers": inl, "chained": 1085}
    # 1103/1104 (zoom out): from the 1040 reference directly
    meas["leo_track"] = tr

    # tank sprite (same coordinates as 1040: frames 1007-1029 have s = 1)
    tank, c = B.extract_on_stripes([1010, 1015, 1020, 1026, 1012], red=False)
    B.save_sprite("leo_tank", tank)
    meas["leo_tank_center"] = c
    th, tw = tank.shape[:2]
    tmask = np.zeros((854, 480), np.uint8)
    A = np.array([[1, 0, c[0] - tw / 2], [0, 1, c[1] - th / 2]], np.float32)
    tmask = cv2.warpAffine(tank[..., 3], A, (480, 854))
    tmask = cv2.dilate((tmask > 20).astype(np.uint8) * 255, np.ones((7, 7), np.uint8))

    # world (sky / hills / road): frames 1030-1056 without the tank and the arrow
    imgs, masks = [], []
    for n in (1040, 1032, 1050, 1036, 1054):
        m = B.overlays(n) | tmask | B.red_mask(FRAMES(n), 15)
        imgs.append(FRAMES(n))
        masks.append(m)
    col, cov = B.merge_static(imgs, masks)
    world = B.inpaint_holes(col, cov)
    cv2.imwrite(os.path.join(B.OUT, "leo_world.png"), world)

    # high-res cannon patch from the close-ups (F = 4.3, region around the barrel)
    F = 4.3
    srcs = []
    for n in (1095, 1066, 1060, 1072, 1059, 1058):
        if not tr.get(str(n)):
            continue
        e = B.overlays(n)
        srcs.append((FRAMES(n), np.array(tr[str(n)]["M"]), e))
    xs, ys = [], []
    for n in (1058, 1060, 1066, 1072, 1095):
        Mi = np.linalg.inv(M3(tr[str(n)]["M"]))
        for p in ((0, 0), (480, 0), (0, 854), (480, 854)):
            q = Mi @ np.array([p[0], p[1], 1.0])
            xs.append(q[0])
            ys.append(q[1])
    ox, oy = max(min(xs), -20), max(min(ys), -20)
    ex_, ey_ = min(max(xs), 500), min(max(ys), 874)
    colh, covh = B.build_mosaic(srcs, (ox, oy), (ex_ - ox, ey_ - oy), F)
    imgh = B.inpaint_holes(colh, covh)
    alpha = cv2.GaussianBlur((covh > 0.5).astype(np.float32), (0, 0), 3) * (covh > 0.5)
    cv2.imwrite(os.path.join(B.OUT, "leo_cannon_hr.png"),
                np.dstack([imgh, (alpha * 255).astype(np.uint8)]))
    meas["leo_cannon_hr"] = {"F": F, "origin": [float(ox), float(oy)]}
    print("hr patch", imgh.shape, (ox, oy))

    # CE sticker: 1080 vs 1095 (same camera)
    d = np.abs(FRAMES(1080).astype(np.int16) - FRAMES(1095).astype(np.int16)).max(-1)
    d[B.overlays(1080) > 0] = 0
    d[B.overlays(1095) > 0] = 0
    # C and E are separate shapes: keep every sizeable component
    nl, lab, st, _ = cv2.connectedComponentsWithStats((d > 40).astype(np.uint8))
    m = np.isin(lab, [j for j in range(1, nl) if st[j, 4] >= 40]).astype(np.uint8)
    ys_, xs_ = np.where(m)
    x0, x1, y0, y1 = xs_.min() - 2, xs_.max() + 3, ys_.min() - 2, ys_.max() + 3
    ce = np.dstack([FRAMES(1080)[y0:y1, x0:x1], cv2.GaussianBlur(m[y0:y1, x0:x1].astype(np.float32), (0, 0), 0.6) * 255])
    cv2.imwrite(os.path.join(B.OUT, "ce_mark.png"), ce.astype(np.uint8))
    # visibility of the CE mark per frame
    vis = []
    for n in range(1070, 1105):
        dd = np.abs(FRAMES(n).astype(np.int16) - FRAMES(1095).astype(np.int16)).max(-1)[y0:y1, x0:x1]
        vis.append((n, round(float((dd > 40).mean()), 3)))
    meas["ce_mark"] = {"center_1080": [float((x0 + x1) / 2), float((y0 + y1) / 2)], "visibility": vis}
    print("ce", ce.shape, vis)

    # arrow 1040-1057
    arr = {}
    for n in range(1036, 1060):
        r = B.track_arrow(FRAMES(n), 1500)
        if r:
            arr[str(n)] = [round(v, 2) for v in r]
    meas["leo_arrow"] = arr
    print("arrow", {k: v[:3] for k, v in arr.items()})
    e = {"license": "reference_proxy"}
    return {"leo_tank": dict(e, path="assets/proxies/leo_tank.png", design_scale=2.25, source="Referenzframes 1010-1026",
                             replace_with="Foto Leopard 2 (frei lizenziert, z. B. Wikimedia Commons, Sonaz CC3 mit Nennung)"),
            "leo_world": dict(e, path="assets/proxies/leo_world.png", design_scale=2.25, source="Referenzframes 1032-1054",
                              replace_with="eigene Illustration: Himmel, Hügel, Strasse"),
            "leo_cannon_hr": dict(e, path="assets/proxies/leo_cannon_hr.png", design_scale=2.25 / F,
                                  source="Mosaik Referenzframes 1058-1095", replace_with="hochaufgelöstes Panzerfoto"),
            "ce_mark": dict(e, path="assets/proxies/ce_mark.png", design_scale=2.25, source="Referenzframe 1080",
                            replace_with="CE-Zeichen als Vektorgrafik (gemeinfrei)")}


def build_leo_pop(meas):
    spr = cv2.imread(os.path.join(B.OUT, "leo_tank.png"), -1)
    c = meas["leo_tank_center"]
    tr = track_range(spr, list(range(981, 1008)), c, list(np.linspace(0.3, 1.6, 27)), radius=150,
                     min_overlap=0.3)
    meas["leo_pop"] = tr
    return {}


def build_leo_pop_affine(meas):
    """Pop-in + 'BREITER' stretch: full affine of the tank, ref frame 1015."""
    sift = cv2.SIFT_create(4000)
    def feats(n):
        g = cv2.cvtColor(FRAMES(n), cv2.COLOR_BGR2GRAY)
        m = 255 - B.overlays(n, red=False)
        m = cv2.bitwise_and(m, cv2.dilate(B.obj_mask_on_stripes(n, 18), np.ones((5, 5), np.uint8)))
        return sift.detectAndCompute(g, m)
    ka, da = feats(1015)
    out = {}
    for n in range(981, 1008):
        kb, db = feats(n)
        ms = [x for x, y in cv2.BFMatcher().knnMatch(da, db, k=2) if x.distance < 0.8 * y.distance]
        pa = np.float32([ka[m.queryIdx].pt for m in ms])
        pb = np.float32([kb[m.trainIdx].pt for m in ms])
        M, inl = cv2.estimateAffine2D(pa, pb, ransacReprojThreshold=2.5)
        out[str(n)] = {"M": M.tolist(), "inliers": int(inl.sum())}
    meas["leo_pop_affine"] = out
    return {}


def build_wasted_and_stvo(meas):
    out = {}
    e = {"design_scale": 2.25, "license": "reference_proxy"}
    # "wasted" lettering (screen space): red glyphs + black outline, frame 1114
    f = FRAMES(1114)
    fi = f.astype(np.int16)
    red = (fi[..., 2] > 140) & (fi[..., 1] < 70) & (fi[..., 0] < 70)
    red[:300] = False
    red[440:] = False
    near = cv2.dilate(red.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    dark = fi.max(-1) < 70
    m = (red | (dark & near)).astype(np.uint8)
    m = B.fill_mask_holes(cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)))
    cap = B.caption_text_mask(f)
    fc = cv2.inpaint(f, cap & (m * 255), 3, cv2.INPAINT_TELEA)
    ys, xs = np.where(m)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    spr = np.dstack([fc[y0:y1, x0:x1], cv2.GaussianBlur(m[y0:y1, x0:x1].astype(np.float32), (0, 0), 0.6) * 255])
    cv2.imwrite(os.path.join(B.OUT, "wasted_text.png"), spr.astype(np.uint8))
    meas["wasted_text_center"] = [float((x0 + x1) / 2), float((y0 + y1) / 2)]
    out["wasted_text"] = dict(e, path="assets/proxies/wasted_text.png", source="Referenzframe 1114",
                              replace_with="eigener Schriftzug im GTA-Stil (freie Schrift, z. B. Pricedown-Alternative)")
    # StVO web page. Captions change every few frames, the page does not: the
    # per-pixel median over the static frames removes them.
    marked = np.median(np.stack([FRAMES(n) for n in range(1157, 1190)]), 0).astype(np.uint8)
    plain = marked.copy()
    pre = np.median(np.stack([FRAMES(n) for n in range(1143, 1153)]), 0).astype(np.uint8)
    plain[178:222, 100:376] = pre[178:222, 100:376]          # before the highlight
    cv2.imwrite(os.path.join(B.OUT, "stvo_page_marked.png"), marked)
    cv2.imwrite(os.path.join(B.OUT, "stvo_page.png"), plain)
    for name in ("stvo_page", "stvo_page_marked"):
        out[name] = dict(e, path=f"assets/proxies/{name}.png", source="Median Referenzframes 1143-1189",
                         replace_with="eigener Screenshot von gesetze-im-internet.de (§ 35 StVO, amtliches Werk)")
    # horizontal wipe map for the highlight (x 112 -> 363)
    xs_ = np.arange(480, dtype=np.float32)
    g = np.clip((xs_ - 112) / (363 - 112), 0, 1)
    cv2.imwrite(os.path.join(B.OUT, "wipe_lr_112_363.png"), np.tile((g * 255).astype(np.uint8), (854, 1)))
    out["wipe_lr_112_363"] = {"path": "assets/proxies/wipe_lr_112_363.png", "design_scale": 2.25,
                              "license": "derived_measurement", "source": "lineare Wischmaske"}
    return out


BUILDERS2 = {"seal_plate": build_seal_plate, "vehicles": build_vehicles, "house": build_house, "seals": build_seals, "sweat_meme": build_sweat_meme, "leo_track": build_leo_track, "leo_assets": build_leo_assets, "leo_pop": build_leo_pop, "leo_pop_affine": build_leo_pop_affine, "wasted_stvo": build_wasted_and_stvo}


def main(names):
    meas = B.load_meas()
    mp = os.path.join(B.PROJ, "assets", "manifest.json")
    manifest = json.load(open(mp)) if os.path.exists(mp) else {}
    for n in names or BUILDERS2:
        print("building", n, flush=True)
        manifest.update(BUILDERS2[n](meas))
        B.save_meas(meas)
        with open(mp, "w") as f:
            json.dump(manifest, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1:])
