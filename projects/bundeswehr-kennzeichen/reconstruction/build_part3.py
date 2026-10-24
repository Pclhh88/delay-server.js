"""Proxies + measurements for 40-50.5 s (frames 1190-1515). Same conventions as
build_proxies.py / build_part2.py (reference px, REFERENCE PROXY assets)."""
import json
import os
import sys

import cv2
import numpy as np

import build_proxies as B
from build_proxies import FRAMES

GRAY = lambda n: cv2.cvtColor(FRAMES(n), cv2.COLOR_BGR2GRAY).astype(np.float32)


def phase_dx(a, b, y0, y1, x1=420):
    A, Bb = GRAY(a)[y0:y1, :x1], GRAY(b)[y0:y1, :x1]
    (dx, dy), r = cv2.phaseCorrelate(A, Bb, cv2.createHanningWindow(A.shape[::-1], cv2.CV_32F))
    return dx, r


def build_street(meas):
    out = {}
    e = {"design_scale": 2.25, "license": "reference_proxy"}
    # ---- cloud drift (measured: brute-force shift of the sky band, frame to frame)
    speed = {}
    for n in range(1218, 1352):
        if 1219 <= n <= 1275:
            speed[n] = -4.77          # sub-pixel value from phase correlation vs. 1240
        else:
            speed[n] = 0.0
    cx = {1217: 0.0}
    for n in range(1218, 1352):
        cx[n] = cx[n - 1] + speed[n]
    meas["street_cloud_x"] = {str(k): round(v, 2) for k, v in cx.items()}
    # ---- static ground from 1345 (flattened light at the left road edge masked)
    bg = FRAMES(1345).copy()
    hole = B.overlays(1345)
    hole[:, 425:452] = 255
    hole[255:300, 0:60] = 255
    bg = cv2.inpaint(bg, hole, 5, cv2.INPAINT_TELEA)
    cv2.imwrite(os.path.join(B.OUT, "street2_bg.png"), bg)
    out["street2_bg"] = dict(e, path="assets/proxies/street2_bg.png", source="Referenzframe 1345",
                             replace_with="eigene Illustration: Bürgersteig, Strasse, Wiese (Seitenansicht)")
    # ---- sky strip (sky gradient + clouds) stitched from the drifting sky band
    SKY = 214
    lo = int(np.floor(min(-v for v in cx.values()))) - 2
    hi = int(np.ceil(max(480 - v for v in cx.values()))) + 2
    W = hi - lo
    acc = np.zeros((SKY, W, 3), np.float32)
    cnt = np.zeros((SKY, W), np.float32)
    for n in list(range(1218, 1287)) + list(range(1300, 1352)):
        img = FRAMES(n)[:SKY].astype(np.float32)
        valid = (B.overlays(n)[:SKY] == 0).astype(np.float32)
        valid[:, 420:] = 0
        if n >= 1274:
            valid[:, 0:120] = 0            # traffic light (standing / falling)
        if 1300 <= n <= 1336:
            valid[140:, :] = 0             # tank turret rises into the sky band
        T = np.array([[1, 0, -cx[n] - lo], [0, 1, 0]], np.float32)
        wv = cv2.warpAffine(valid, T, (W, SKY))
        acc += cv2.warpAffine(img, T, (W, SKY)) * wv[..., None]
        cnt += wv
    col = acc / np.maximum(cnt, 1e-3)[..., None]
    sky = B.inpaint_holes(col, (cnt > 0.5).astype(np.float32), 5)
    cv2.imwrite(os.path.join(B.OUT, "street2_sky.png"), sky)
    meas["street2_sky"] = {"x0": lo, "rows": SKY}
    out["street2_sky"] = dict(e, path="assets/proxies/street2_sky.png", source="Referenzframes 1218-1351 (gestitcht)",
                              replace_with="eigener Himmel mit Cartoon-Wolken")
    # ---- tank (side view) cut at 1240 against the static background
    # captions over the tank: merge frames with different words, then cut vs. bg
    imgs = [FRAMES(n) for n in (1240, 1226, 1270, 1302, 1250)]
    masks = [B.caption_text_mask(FRAMES(n)) for n in (1240, 1226, 1270, 1302, 1250)]
    colt, cov = B.merge_static(imgs, masks)
    colt = B.inpaint_holes(colt, cov, 3)
    cred = np.zeros((854, 480), np.uint8)
    cred[:, 426:453] = 255                     # the vertical credit runs through the turret
    colt = cv2.inpaint(colt, cred, 5, cv2.INPAINT_TELEA)
    tdiff = np.abs(colt.astype(np.int16) - bg.astype(np.int16)).max(-1)
    m = (tdiff > 30).astype(np.uint8)
    m[:250] = 0
    m[470:] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = B.fill_mask_holes(B.largest_component(cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))))
    tank = np.dstack([np.clip(colt, 0, 255).astype(np.uint8), cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.7) * 255])
    spr, (x0, y0) = B.crop_to_alpha(tank.astype(np.uint8), 2)
    cv2.imwrite(os.path.join(B.OUT, "tank_side.png"), spr)
    h, w = spr.shape[:2]
    meas["tank_side_center_1240"] = [x0 + w / 2, y0 + h / 2]
    out["tank_side"] = dict(e, path="assets/proxies/tank_side.png", source="Referenzframes 1226-1302",
                            replace_with="Freisteller Leopard 2 Seitenansicht (frei lizenziertes Foto)")
    # ---- traffic light (standing, 1305) and flattened (1345): dark pixels + red lamp
    for name, n, box in (("traffic_light", 1305, (20, 0, 115, 262)), ("traffic_light_flat", 1345, (0, 255, 60, 300))):
        x0, y0, x1, y1 = box
        crop = FRAMES(n)[y0:y1, x0:x1]
        ci = crop.astype(np.int16)
        m = (ci.max(-1) < 70) | ((ci[..., 2] > 150) & (ci[..., 1] < 90))
        m = B.fill_mask_holes(cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)))
        sub = np.dstack([crop, cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.5) * 255]).astype(np.uint8)
        spr, (sx, sy) = B.crop_to_alpha(sub, 1)
        cv2.imwrite(os.path.join(B.OUT, name + ".png"), spr)
        hh, ww = spr.shape[:2]
        meas[name + "_center"] = [x0 + sx + ww / 2, y0 + sy + hh / 2]
        out[name] = dict(e, path=f"assets/proxies/{name}.png", source=f"Referenzframe {n}",
                         replace_with="eigene Grafik: Ampel")
    # first frame with the standing light / first frame with the flattened one
    def light_px(n):
        ci = FRAMES(n)[0:262, 20:115].astype(np.int16)
        return int((ci.max(-1) < 70).sum())
    meas["traffic_light_frames"] = {str(n): light_px(n) for n in range(1280, 1352)}
    # ---- stop sign: opaque only in 1287 (fades out until 1300)
    d = np.abs(FRAMES(1287).astype(np.int16) - FRAMES(1305).astype(np.int16)).max(-1)
    cap = B.caption_text_mask(FRAMES(1287))
    d[cap > 0] = 255
    d[:, 425:452] = np.where(d[:, 425:452] > 0, 255, 0)
    m = B.fill_mask_holes(B.largest_component((d > 40).astype(np.uint8)))
    hole = (cap | B.overlays(1287, red=False)) & (m * 255)
    img = cv2.inpaint(FRAMES(1287), hole, 5, cv2.INPAINT_TELEA)
    spr, (sx, sy) = B.crop_to_alpha(np.dstack([img, cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.6) * 255]).astype(np.uint8), 1)
    cv2.imwrite(os.path.join(B.OUT, "stop_sign.png"), spr)
    hh, ww = spr.shape[:2]
    meas["stop_sign_center"] = [sx + ww / 2, sy + hh / 2]
    meas["stop_sign_alpha"] = {"1287": 1.0, "1288": 0.86, "1289": 0.691, "1290": 0.634, "1291": 0.608,
                               "1292": 0.533, "1293": 0.46, "1294": 0.364, "1295": 0.319, "1296": 0.283,
                               "1297": 0.255, "1298": 0.174, "1299": 0.103, "1300": 0.06, "1301": 0.0}
    out["stop_sign"] = dict(e, path="assets/proxies/stop_sign.png", source="Referenzframe 1287",
                            replace_with="Stoppschild als Vektorgrafik (amtliches Zeichen, gemeinfrei)")
    meas["tank_side_track"] = json.load(open(os.path.join(os.path.dirname(__file__), "tank_side.json")))
    return out


def build_crossing(meas):
    """Top-down crossing 1352-1392: static background, tank drives up, cyclist."""
    e = {"design_scale": 2.25, "license": "reference_proxy"}
    out = {}
    bg = FRAMES(1352).copy()
    # the tank's barrel already pokes in at the bottom of 1352: rebuild that part of
    # the vertical road from the identical road section at the top (same columns)
    bg[720:854, 188:336] = bg[10:144, 188:336]
    hole = B.overlays(1352)
    hole[:, 425:452] = 255
    hole[716:724, 188:336] = 255
    cap = np.zeros_like(hole)
    bg = cv2.inpaint(bg, hole, 5, cv2.INPAINT_TELEA)
    cv2.imwrite(os.path.join(B.OUT, "crossing_bg.png"), bg)
    out["crossing_bg"] = dict(e, path="assets/proxies/crossing_bg.png", source="Referenzframes 1352/1390",
                              replace_with="eigene Draufsicht: Strasse mit Mittelinseln und Bäumen")
    # tank (top view) at rest, 1385 (+ other caption frames)
    frames = [1385, 1376, 1389, 1380]
    col, cov = B.merge_static([FRAMES(n) for n in frames], [B.caption_text_mask(FRAMES(n)) for n in frames])
    col = B.inpaint_holes(col, cov, 3)
    d = np.abs(col.astype(np.int16) - bg.astype(np.int16)).max(-1)
    m = (d > 30).astype(np.uint8)
    m[:480] = 0
    m[:, :180] = 0
    m[:, 345:] = 0
    m = B.fill_mask_holes(B.largest_component(cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))))
    spr, (x0, y0) = B.crop_to_alpha(np.dstack([col, m * 255]).astype(np.uint8), 1)
    cv2.imwrite(os.path.join(B.OUT, "tank_top.png"), spr)
    h, w = spr.shape[:2]
    c = (x0 + w / 2, y0 + h / 2)
    meas["tank_top_rest_center"] = c
    # vertical position per frame (template on the visible part)
    g = cv2.cvtColor(spr[..., :3], cv2.COLOR_BGR2GRAY)
    ys = {}
    for n in range(1352, 1376):
        G = cv2.cvtColor(FRAMES(n), cv2.COLOR_BGR2GRAY)
        best = None
        for dy in range(0, 330, 1):
            top = int(y0 + dy)
            vis = min(h, 854 - top)
            if vis < 12:
                continue
            a = G[top:top + vis, x0:x0 + w].astype(np.float32)
            b = g[:vis].astype(np.float32)
            mm = spr[:vis, :, 3] > 128
            err = np.abs(a - b)[mm].mean()
            if best is None or err < best[0]:
                best = (err, dy)
        ys[str(n)] = best[1]
    meas["tank_top_dy"] = ys
    print("tank dy", ys)
    out["tank_top"] = dict(e, path="assets/proxies/tank_top.png", source="Referenzframes 1376-1389",
                           replace_with="eigene Draufsicht-Grafik eines Panzers")
    # cyclist at 1386, moves left
    d = np.abs(FRAMES(1386).astype(np.int16) - bg.astype(np.int16)).max(-1)
    m = (d > 40).astype(np.uint8)
    m[:240] = 0
    m[390:] = 0
    m = B.fill_mask_holes(B.largest_component(cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))))
    spr, (cx0, cy0) = B.crop_to_alpha(np.dstack([FRAMES(1386), m * 255]).astype(np.uint8), 1)
    cv2.imwrite(os.path.join(B.OUT, "cyclist.png"), spr)
    ch, cw = spr.shape[:2]
    gx = {}
    gc = cv2.cvtColor(spr[..., :3], cv2.COLOR_BGR2GRAY)
    for n in range(1366, 1393):
        G = cv2.cvtColor(FRAMES(n), cv2.COLOR_BGR2GRAY).astype(np.float32)
        best = None
        for x in range(cx0 - 150, cx0 + 250):
            xa, xb = max(x, 0), min(x + cw, 425)
            if xb - xa < 10:
                continue
            a = G[cy0:cy0 + ch, xa:xb]
            b = gc[:, xa - x:xb - x].astype(np.float32)
            mm = spr[:, xa - x:xb - x, 3] > 128
            if mm.sum() < 30:
                continue
            err = np.abs(a - b)[mm].mean()
            if best is None or err < best[0]:
                best = (err, x)
        gx[str(n)] = None if best is None or best[0] > 25 else best[1] + cw / 2
    meas["cyclist_cx"] = gx
    meas["cyclist_cy"] = cy0 + ch / 2
    print("cyclist", gx)
    out["cyclist"] = dict(e, path="assets/proxies/cyclist.png", source="Referenzframe 1386",
                          replace_with="eigene Grafik: Radfahrer von oben/schräg")
    return out


def build_blitzer(meas):
    """Speed camera scene 1393-1461 and the final jeep photo 1462-1515."""
    e = {"design_scale": 2.25, "license": "reference_proxy"}
    out = {}
    # wide shot background (1440: no jeep, no flash) incl. the speed camera
    bg = FRAMES(1440).copy()
    hole = B.overlays(1440)
    hole[:, 425:452] = 255
    bg = cv2.inpaint(bg, hole, 5, cv2.INPAINT_TELEA)
    cv2.imwrite(os.path.join(B.OUT, "blitzer_bg.png"), bg)
    out["blitzer_bg"] = dict(e, path="assets/proxies/blitzer_bg.png", source="Referenzframe 1440",
                             replace_with="eigene Illustration: Strasse + Blitzersäule (Seitenansicht)")
    # close-up of the speed camera (scale 2.0): high-res plate from 1393-1416
    frames = [1395, 1400, 1405, 1410, 1415, 1399]
    col, cov = B.merge_static([FRAMES(n) for n in frames], [B.overlays(n) for n in frames])
    close = B.inpaint_holes(col, cov, 5)
    cv2.imwrite(os.path.join(B.OUT, "blitzer_close.png"), close)
    M, _ = B.similarity(FRAMES(1430), FRAMES(1405), B.overlays(1430), B.overlays(1405))
    meas["blitzer_close_M"] = M.tolist()
    out["blitzer_close"] = dict(e, path="assets/proxies/blitzer_close.png", source="Referenzframes 1395-1415",
                                replace_with="Nahaufnahme der eigenen Blitzersäule")
    # jeep passing (1431-1434): drives right -> left (~230 px/frame); the whole car
    # is only visible in 1432 (flash frame): remove the measured white lift first
    a32 = 0.355
    I = np.clip((FRAMES(1432).astype(np.float32) - a32 * 255) / (1 - a32), 0, 255)
    d = np.abs(I - FRAMES(1440).astype(np.float32)).max(-1)
    d[B.overlays(1432) > 0] = 0
    d[:200] = 0
    d[370:] = 0
    m = (d > 45).astype(np.uint8)
    m = B.largest_component(cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)))
    # the light canvas top matches the sky: a car body is (nearly) convex
    hull = cv2.convexHull(cv2.findNonZero(m))
    hm = np.zeros_like(m)
    cv2.fillPoly(hm, [hull], 1)
    # hull only for the canvas roof (behind the windscreen); body and wheels keep the real mask
    ys, xs = np.where(m)
    roof = np.zeros_like(m)
    xmid = int(xs.min() + 0.45 * (xs.max() - xs.min()))
    roof[:int(ys.min() + 0.45 * (ys.max() - ys.min())), xmid:] = 1
    m = np.maximum(m, hm & roof)
    m = B.fill_mask_holes(m)
    Iu = I.astype(np.uint8)
    spr, (x0, y0) = B.crop_to_alpha(np.dstack([Iu, m * 255]).astype(np.uint8), 1)
    cv2.imwrite(os.path.join(B.OUT, "jeep_pass.png"), spr)
    meas["jeep_pass_1432"] = {"x0": int(x0), "y0": int(y0), "w": int(spr.shape[1]), "h": int(spr.shape[0])}
    # front edge per frame: 1431 left edge 283, 1432 measured, 1433/1434 by the same speed
    x32 = int(x0)
    speed = (283 - x32)
    meas["jeep_pass_left_x"] = {"1431": 283, "1432": x32, "1433": x32 - speed, "1434": x32 - 2 * speed}
    meas["flash_white"] = {"1431": 0.0, "1432": 0.355, "1433": 0.213, "1434": 0.071, "1435": 0.0}
    meas["flash_centre"] = [182, 120]
    print("jeep pass left x", meas["jeep_pass_left_x"], spr.shape)
    out["jeep_pass"] = dict(e, path="assets/proxies/jeep_pass.png", source="Referenzframe 1432 (Blitz herausgerechnet)",
                            replace_with="Freisteller Mercedes G (Wolf) Seitenansicht")
    # final jeep photo (full frame at 1500) + framed version scale
    col, cov = B.merge_static([FRAMES(n) for n in (1500, 1490, 1510, 1495)],
                              [B.overlays(n) for n in (1500, 1490, 1510, 1495)])
    final = B.inpaint_holes(col, cov, 5)
    cv2.imwrite(os.path.join(B.OUT, "final_jeep.png"), final)
    tr = {}
    for n in (1462, 1463, 1464, 1465, 1466, 1467, 1468, 1470, 1482, 1483, 1484, 1485):
        M, inl = B.similarity(FRAMES(1500), FRAMES(n), B.overlays(1500), B.overlays(n))
        tr[str(n)] = None if M is None else M.tolist()
    meas["final_jeep_track"] = tr
    out["final_jeep"] = dict(e, path="assets/proxies/final_jeep.png", source="Referenzframes 1490-1510",
                             replace_with="Foto Mercedes G (Wolf) im Studio (Darkone, CC2.5 mit Nennung)")
    # road background behind the framed photo (1452-1461 after the pan)
    rb = FRAMES(1461).copy()
    rb = cv2.inpaint(rb, B.overlays(1461) | np.pad(np.full((854, 27), 255, np.uint8), ((0, 0), (425, 28))), 5,
                     cv2.INPAINT_TELEA)
    cv2.imwrite(os.path.join(B.OUT, "road_blur_bg.png"), rb)
    out["road_blur_bg"] = dict(e, path="assets/proxies/road_blur_bg.png", source="Referenzframe 1461",
                               replace_with="eigene Strassen-Illustration, weichgezeichnet")
    # frame border of the photo card: white, 4 px (measured)
    meas["photo_card_border"] = 4
    return out


def build_tank_far(meas):
    """Whole tank (scale 0.8) stitched from 1321-1338 while it drives off to the
    left at 24.7 px/frame (its rear is never visible in the close shot)."""
    bg = cv2.imread(os.path.join(B.OUT, "street2_bg.png")).astype(np.int16)
    frames = list(range(1321, 1339))
    cx0 = 84.5                                   # tank centre x at 1321 (template match)
    xs = [cx0 - 24.7 * (n - 1321) for n in frames]
    W, H0, H1 = 700, 120, 470
    acc = np.zeros((H1 - H0, W, 3), np.float32)
    al = np.zeros((H1 - H0, W), np.float32)
    cnt = np.zeros((H1 - H0, W), np.float32)
    for n, x in zip(frames, xs):
        img = FRAMES(n)[H0:H1].astype(np.float32)
        d = np.abs(FRAMES(n).astype(np.int16) - bg).max(-1)[H0:H1]
        m = (d > 30).astype(np.float32)
        valid = (B.overlays(n)[H0:H1] == 0).astype(np.float32)
        valid[:, :125] = 0                        # traffic light / falling light
        T = np.array([[1, 0, W / 2 - x], [0, 1, 0]], np.float32)   # frame -> tank-centred
        wv = cv2.warpAffine(valid, T, (W, H1 - H0))
        acc += cv2.warpAffine(img, T, (W, H1 - H0)) * wv[..., None]
        al += cv2.warpAffine(m, T, (W, H1 - H0)) * wv
        cnt += wv
    col = acc / np.maximum(cnt, 1e-3)[..., None]
    a = (al / np.maximum(cnt, 1e-3) > 0.5).astype(np.uint8)
    a = B.fill_mask_holes(B.largest_component(cv2.morphologyEx(a, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))))
    colu = B.inpaint_holes(col, (cnt > 0.5).astype(np.float32), 3)
    spr, (x0, y0) = B.crop_to_alpha(np.dstack([colu, cv2.GaussianBlur(a.astype(np.float32), (0, 0), 0.7) * 255]).astype(np.uint8), 2)
    cv2.imwrite(os.path.join(B.OUT, "tank_side_far.png"), spr)
    h, w = spr.shape[:2]
    # sprite centre in frame coords at frame n: (x(n) - W/2 + x0 + w/2, H0 + y0 + h/2)
    meas["tank_far"] = {"cx_1321": float(cx0 - W / 2 + x0 + w / 2), "cy": float(H0 + y0 + h / 2), "speed": -24.7}
    print("tank far", spr.shape, meas["tank_far"])
    return {"tank_side_far": {"path": "assets/proxies/tank_side_far.png", "design_scale": 2.25,
                              "license": "reference_proxy", "source": "Referenzframes 1321-1338 (gestitcht)",
                              "replace_with": "Freisteller Leopard 2 Seitenansicht"}}


def build_card(meas):
    """Framed photo card 1462-1482 (white border); it shows a wider crop of the
    photo than the full-screen shot after it."""
    frames = [1475, 1470, 1480, 1472]
    col, cov = B.merge_static([FRAMES(n) for n in frames], [B.overlays(n) for n in frames])
    col = B.inpaint_holes(col, cov, 3)
    card = col[124:413, 34:447]
    cv2.imwrite(os.path.join(B.OUT, "photo_card.png"), card)
    # measured card boxes (white border): centre / scale (width / 413)
    meas["photo_card_keys"] = {"1462": [239.0, 277.0, 0.291], "1463": [238.0, 268.5, 0.83],
                               "1464": [238.0, 264.7, 1.102], "1465": [237.5, 264.0, 1.085],
                               "1466": [237.5, 265.0, 1.051], "1467": [239.0, 268.0, 1.02],
                               "1468": [240.5, 268.5, 1.0], "1482": [240.5, 268.5, 1.0]}
    return {"photo_card": {"path": "assets/proxies/photo_card.png", "design_scale": 2.25, "license": "reference_proxy",
                           "source": "Referenzframes 1470-1480", "replace_with": "Foto Mercedes G (Wolf), weisser Rahmen"}}


BUILDERS3 = {"street": build_street, "crossing": build_crossing, "blitzer": build_blitzer, "tank_far": build_tank_far, "card": build_card}


def main(names):
    meas = B.load_meas()
    mp = os.path.join(B.PROJ, "assets", "manifest.json")
    manifest = json.load(open(mp)) if os.path.exists(mp) else {}
    for n in names or BUILDERS3:
        print("building", n, flush=True)
        manifest.update(BUILDERS3[n](meas))
        B.save_meas(meas)
        with open(mp, "w") as f:
            json.dump(manifest, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1:])
