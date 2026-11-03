"""Misst die Kamerafahrt des Originals: jeder 3. Frame wird auf dem Satelliten- bzw.
Papier-Atlas verortet, dann werden Kameraparameter angepasst.

python3 projects/broadway-manhattan/reconstruction/track_camera.py [--frames 1-2348] [--step 3]
-> analysis/camera_track.json
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
from shortsfactory.analysis.map_track import Atlas, fit_camera  # noqa: E402

P = os.path.join(ROOT, "projects", "broadway-manhattan")
BOUNDS = (560000, 4490500, 609000, 4545000)
# welche Karte im Original zu sehen ist (aus timeline_analysis.json)
PAPER = [(13.9, 67.4)]


FINE = (578000, 4502000, 597000, 4530000)
_sift = None


def frame_to_frame(cur, prev, mask):
    """Homographie cur-Pixel -> prev-Pixel (beide Originalframes)."""
    global _sift
    _sift = _sift or cv2.SIFT_create(8000)
    k1, d1 = _sift.detectAndCompute(cv2.cvtColor(cur, cv2.COLOR_BGR2GRAY), mask)
    k2, d2 = _sift.detectAndCompute(cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY), mask)
    if d1 is None or d2 is None:
        return None, 0
    m = cv2.BFMatcher().knnMatch(d1, d2, k=2)
    good = [a for a, b in (x for x in m if len(x) == 2) if a.distance < 0.75 * b.distance]
    if len(good) < 30:
        return None, len(good)
    H, inl = cv2.findHomography(np.float32([k1[g.queryIdx].pt for g in good]),
                                np.float32([k2[g.trainIdx].pt for g in good]), cv2.USAC_MAGSAC, 2.0)
    return (H, int(inl.sum())) if H is not None and inl.sum() >= 30 else (None, 0)


def kind_at(t):
    return "paper" if any(a <= t < b for a, b in PAPER) else "sat"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="1-2348")
    ap.add_argument("--step", type=int, default=3)
    ap.add_argument("--out", default="camera_track.json")
    a = ap.parse_args()
    f0, f1 = map(int, a.frames.split("-"))
    atl = {}
    out_p = os.path.join(P, "analysis", a.out)
    track = json.load(open(out_p)) if os.path.exists(out_p) else {}
    mask = np.full((1280, 720), 255, np.uint8)
    mask[880:990] = 0  # Untertitel ausblenden
    prev = {}
    last = None
    for n in range(f0, f1 + 1, a.step):
        t = (n - 1) / 30
        kd = kind_at(t)
        if kd not in atl:
            metas = ["assets/maps/sat_wide.json", "assets/maps/sat.json"] if kd == "sat" else \
                ["assets/maps/paper_wide.json", "assets/maps/paper.json"]
            atl[kd] = Atlas.from_rasters(P, metas, 20.0, BOUNDS)
        if kd + "_fine" not in atl:
            metas = ["assets/maps/sat.json"] if kd == "sat" else ["assets/maps/paper.json"]
            atl[kd + "_fine"] = Atlas.from_rasters(P, metas, 7.0, FINE)
        fr = cv2.imread(os.path.join(P, "analysis", "frames", f"f{n:04d}.png"))
        Hw, inl = atl[kd].locate(fr, mask)
        how = "atlas"
        if Hw is None:
            Hw, inl = atl[kd + "_fine"].locate(fr, mask)
            how = "atlas_fine"
        if Hw is None and last is not None and last[2] == kd:
            Hrel, inl = frame_to_frame(fr, last[0], mask)
            if Hrel is not None:
                Hw = last[1] @ Hrel
                how = "chain"
        rec = {"t": round(t, 3), "map": kd, "inliers": inl, "how": how}
        if Hw is not None:
            last = (fr, Hw, kd)
        if Hw is not None:
            best = None
            for g in ([prev.get(kd)] if prev.get(kd) else []) + [None]:
                try:
                    c = fit_camera(Hw, 720, 1280, guess=g)
                except (ValueError, OverflowError):
                    continue
                for flip in (0, 180):
                    if g is None and flip:
                        c2 = fit_camera(Hw, 720, 1280, guess=[c["cx"], c["cy"], math.log(c["mpp"]), c["rot"] + 180, 5])
                        c = c2 if c2["err_px"] < c["err_px"] else c
                if best is None or c["err_px"] < best["err_px"]:
                    best = c
            if best is not None:
                rec.update({k: round(v, 3) for k, v in best.items()})
            if best is not None and best["err_px"] < 3:
                prev[kd] = [best["cx"], best["cy"], math.log(best["mpp"]), best["rot"], max(best["tilt"], 1)]
            else:
                last = None  # unplausible Homographie: nicht als Anker für die Verkettung verwenden
        track[str(n)] = rec
        print(n, rec, flush=True)
        if len(track) % 30 == 0:
            json.dump(track, open(out_p, "w"), indent=0)
    json.dump(track, open(out_p, "w"), indent=0)


if __name__ == "__main__":
    main()
