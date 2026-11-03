"""Kamera-Tracking für Karten-Videos: verortet Frames eines Referenzvideos auf einer Atlaskarte
(SIFT + RANSAC-Homographie) und passt die Kameraparameter der Karten-Ebene an
(cx, cy, mpp, rot, tilt; siehe render/maplayer.py).

Verwendung im Projekt-Skript:
    atlas = Atlas.from_rasters([...json...], res=20)      # Welt <-> Atlas-Pixel
    trk = atlas.locate(frame_bgr)                          # Homographie Frame -> Welt
    cam = fit_camera(trk, frame_w, frame_h)               # Parameter für 1080x1920-Design
"""
import json
import math
import os

import cv2
import numpy as np


class Atlas:
    def __init__(self, img, world_from_px):
        self.img = img
        self.A = world_from_px  # 3x3: Atlas-Pixel -> Welt (Meter)
        self.sift = cv2.SIFT_create(nfeatures=40000, contrastThreshold=0.02)
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        g = cv2.createCLAHE(2.0, (8, 8)).apply(g)
        self.kp, self.des = self.sift.detectAndCompute(g, None)
        self.matcher = cv2.FlannBasedMatcher({"algorithm": 1, "trees": 5}, {"checks": 64})

    @classmethod
    def from_rasters(cls, base_dir, metas, res, bounds):
        """Setzt Raster (Liste von JSON-Pfaden, grob -> fein) auf ein gemeinsames Gitter (res m/px)."""
        x0, y0, x1, y1 = bounds
        W, H = int((x1 - x0) / res), int((y1 - y0) / res)
        A = np.array([[res, 0, x0], [0, -res, y1], [0, 0, 1]], np.float64)
        out = np.zeros((H, W, 3), np.uint8)
        for mp in metas:
            m = json.load(open(os.path.join(base_dir, mp)))
            img = cv2.imread(os.path.join(base_dir, m["path"]))
            a, b, c, d, e, f = m["transform"]
            R = np.array([[a, b, c], [d, e, f], [0, 0, 1]])
            M = np.linalg.inv(A) @ R
            w = cv2.warpPerspective(img, M, (W, H), flags=cv2.INTER_AREA)
            cov = cv2.warpPerspective(np.full(img.shape[:2], 255, np.uint8), M, (W, H))
            cov = cv2.erode(cov, np.ones((5, 5), np.uint8))
            out[cov > 0] = w[cov > 0]
        return cls(out, A)

    def locate(self, frame, mask=None, min_inliers=25):
        """Frame (BGR) -> 3x3 Homographie Frame-Pixel -> Welt, oder None."""
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        g = cv2.createCLAHE(2.0, (8, 8)).apply(g)
        kp, des = self.sift.detectAndCompute(g, mask)
        if des is None or len(kp) < 20:
            return None, 0
        m = self.matcher.knnMatch(des, self.des, k=2)
        good = [a for a, b in (x for x in m if len(x) == 2) if a.distance < 0.78 * b.distance]
        if len(good) < min_inliers:
            return None, len(good)
        src = np.float32([kp[x.queryIdx].pt for x in good])
        dst = np.float32([self.kp[x.trainIdx].pt for x in good])
        Hm, inl = cv2.findHomography(src, dst, cv2.USAC_MAGSAC, 4.0, maxIters=5000, confidence=0.999)
        if Hm is None or inl.sum() < min_inliers:
            return None, int(inl.sum()) if inl is not None else 0
        return self.A @ Hm, int(inl.sum())


def fit_camera(world_from_frame, fw, fh, focal=1400.0, guess=None):
    """Passt (cx, cy, mpp, rot, tilt) so an, dass die Karten-Kamera (Design 1080x1920)
    dieselben Punkte trifft wie die gemessene Homographie (Frame fw x fh)."""
    from scipy.optimize import least_squares
    from ..render.maplayer import camera_matrix, project
    k = fw / 1080.0
    gx, gy = np.meshgrid(np.linspace(0.1, 0.9, 7) * fw, np.linspace(0.08, 0.92, 9) * fh)
    scr = np.stack([gx.ravel(), gy.ravel()], 1)
    q = np.c_[scr, np.ones(len(scr))] @ world_from_frame.T
    wpts = q[:, :2] / q[:, 2:3]
    c = project(world_from_frame, [[fw / 2, fh / 2]])[0][0]
    d = project(world_from_frame, [[fw / 2, fh / 2], [fw / 2 + 10, fh / 2]])[0]
    mpp0 = np.hypot(*(d[1] - d[0])) / 10 * k
    ang0 = math.degrees(math.atan2(d[1][1] - d[0][1], d[1][0] - d[0][0]))
    x0 = list(guess or [c[0], c[1], math.log(mpp0), ang0, 5.0])
    x0[3] = (x0[3] + 180) % 360 - 180
    x0[4] = min(max(x0[4], 0.5), 60)
    x0[2] = min(max(x0[2], -4.9), 9.9)

    def res(x):
        p = {"cx": x[0], "cy": x[1], "mpp": math.exp(x[2]), "rot": x[3], "tilt": x[4], "focal": focal}
        H = camera_matrix(p, k, k)
        s, _ = project(H, wpts)
        return (s - scr).ravel()
    r = least_squares(res, x0, bounds=([-1e9, -1e9, -5, -720, 0], [1e9, 1e9, 10, 720, 70]))
    x = r.x
    err = float(np.sqrt(np.mean(r.fun ** 2)))
    return {"cx": float(x[0]), "cy": float(x[1]), "mpp": float(math.exp(x[2])), "rot": float(x[3]),
            "tilt": float(x[4]), "err_px": err}
