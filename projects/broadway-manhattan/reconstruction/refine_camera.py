"""Verfeinert die Kamera in einem Zeitbereich: rendert die eigene Karte (Satellit + weißes Raster +
Broadway) mit der aktuellen Kamera und gleicht sie per SIFT mit dem Originalframe ab.
Nützlich, wo die Atlas-Verortung versagt und die Verkettung driftet (starke Nahaufnahmen).

python3 projects/broadway-manhattan/reconstruction/refine_camera.py 68.4 73.1 [--iters 2]
-> analysis/camera_track_refine.json (überschreibt die Werte dieser Frames)
"""
import argparse
import json
import math
import os
import sys

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(__file__))
import build_timeline as B  # noqa: E402
from shortsfactory.analysis.map_track import fit_camera  # noqa: E402
from shortsfactory.render.engine import Renderer  # noqa: E402
from shortsfactory.render.maplayer import camera_matrix  # noqa: E402

P = B.P


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("t0", type=float)
    ap.add_argument("t1", type=float)
    ap.add_argument("--iters", type=int, default=2)
    a = ap.parse_args()
    B._CAM = B.camera_keys()
    tl = {"meta": {"fps": 30, "width": 1080, "height": 1920, "duration": 80},
          "maps": {"nyc": {"rasters": {"sat": "assets/maps/sat.json", "sat_wide": "assets/maps/sat_wide.json"},
                           "vectors": "assets/maps/vectors.json"}}, "assets": {}, "layers": []}
    items = [{"kind": "raster", "src": "sat_wide"}, {"kind": "raster", "src": "sat"},
             {"kind": "lines", "src": "grid", "width": 2.0, "color": [255, 255, 255], "alpha": 0.9},
             {"kind": "lines", "src": "grid_outer", "width": 2.0, "color": [255, 255, 255], "alpha": 0.8},
             {"kind": "path", "src": "broadway", "core_width": 3, "glows": [{"width": 14, "blur": 3, "color": [255, 40, 50]}]}]
    r = Renderer(tl, P, 720, 1280)
    from shortsfactory.render.maplayer import MapRenderer
    mr = MapRenderer(r)
    sift = cv2.SIFT_create(6000)
    mask = np.full((1280, 720), 255, np.uint8)
    mask[880:990] = 0
    out_p = os.path.join(P, "analysis", "camera_track_refine.json")
    out = json.load(open(out_p)) if os.path.exists(out_p) else {}
    n0, n1 = int(a.t0 * 30) + 1, int(a.t1 * 30) + 1
    for n in range(n0, n1 + 1, 3):
        t = (n - 1) / 30
        cam = dict(B.cam_at(t))
        orig = cv2.imread(os.path.join(P, "analysis", "frames", f"f{n:04d}.png"))
        ko, do = sift.detectAndCompute(cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY), mask)
        for it in range(a.iters):
            rgb, _ = mr.render({"map": "nyc", "items": items}, cam, t)
            me = (np.clip(rgb, 0, 1)[..., ::-1] * 255).astype(np.uint8)
            km, dm = sift.detectAndCompute(cv2.cvtColor(me, cv2.COLOR_BGR2GRAY), None)
            m = cv2.BFMatcher().knnMatch(do, dm, k=2)
            good = [x for x, y in (p for p in m if len(p) == 2) if x.distance < 0.8 * y.distance]
            if len(good) < 25:
                break
            Hm, inl = cv2.findHomography(np.float32([ko[g.queryIdx].pt for g in good]),
                                         np.float32([km[g.trainIdx].pt for g in good]), cv2.USAC_MAGSAC, 4.0)
            if Hm is None or inl.sum() < 25:
                break
            # Original-Pixel -> eigenes Render-Pixel -> Welt
            Hc = camera_matrix(cam, 720 / 1080, 1280 / 1920)
            W = np.linalg.inv(Hc) @ Hm
            c = fit_camera(W, 720, 1280, guess=[cam["cx"], cam["cy"], math.log(cam["mpp"]), cam["rot"], max(cam.get("tilt", 0), 0.5)])
            if c["err_px"] > 3:
                break
            cam.update({k: c[k] for k in ("cx", "cy", "mpp", "rot", "tilt")})
            rec = {"t": round(t, 3), "map": "sat", "how": "refine", "inliers": int(inl.sum()), **{k: round(v, 3) for k, v in c.items()}}
            out[str(n)] = rec
        print(n, out.get(str(n)), flush=True)
    json.dump(out, open(out_p, "w"), indent=0)


if __name__ == "__main__":
    main()
