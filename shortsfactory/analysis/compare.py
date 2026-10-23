"""Compare a render against the reference video frame by frame.

python3 -m shortsfactory.analysis.compare REF.mp4 RENDER.mp4 OUTDIR \
        [--start 0 --end 20] [--frames 0,45,90 ...]

Writes:
  OUTDIR/metrics.json      per-frame mean abs diff (0..255) + PSNR, scene cuts
  OUTDIR/compare_XXXX.png  [reference | render | diff heat] at requested frames
  OUTDIR/overview.png      contact sheet of the requested frames
"""
import argparse
import json
import os
import subprocess

import cv2
import numpy as np


def read_frames(path, w, h, start, end):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-i", path, "-map", "0:v:0", "-t", str(end - start),
           "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


def cuts(frames, thresh=40.0):
    out = []
    for i in range(1, len(frames)):
        d = np.abs(frames[i].astype(np.int16) - frames[i - 1].astype(np.int16)).mean()
        if d > thresh:
            out.append(i)
    return out


def heat(a, b):
    d = np.abs(a.astype(np.int16) - b.astype(np.int16)).max(-1).astype(np.uint8)
    return cv2.applyColorMap(np.clip(d.astype(np.int32) * 3, 0, 255).astype(np.uint8), cv2.COLORMAP_INFERNO)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref")
    ap.add_argument("render")
    ap.add_argument("outdir")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=20.0)
    ap.add_argument("--frames", default="")
    ap.add_argument("--w", type=int, default=480)
    ap.add_argument("--h", type=int, default=854)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    R = read_frames(a.ref, a.w, a.h, a.start, a.end)
    X = read_frames(a.render, a.w, a.h, a.start, a.end)
    n = min(len(R), len(X))
    n0 = int(round(a.start * 30))
    per = []
    for i in range(n):
        d = np.abs(R[i].astype(np.int16) - X[i].astype(np.int16)).astype(np.float32)
        mse = float((d ** 2).mean())
        per.append({"frame": n0 + i, "mad": round(float(d.mean()), 2),
                    "psnr": round(10 * np.log10(255 ** 2 / max(mse, 1e-6)), 2)})
    rc, xc = cuts(R[:n]), cuts(X[:n])
    res = {"frames": per, "ref_cuts": [n0 + c for c in rc], "render_cuts": [n0 + c for c in xc],
           "mean_mad": round(float(np.mean([p["mad"] for p in per])), 2),
           "mean_psnr": round(float(np.mean([p["psnr"] for p in per])), 2)}
    with open(os.path.join(a.outdir, "metrics.json"), "w") as f:
        json.dump(res, f, indent=1)
    sel = [int(x) for x in a.frames.split(",") if x.strip()] if a.frames else list(range(n0, n0 + n, 15))
    tiles = []
    for fno in sel:
        i = fno - n0
        if not 0 <= i < n:
            continue
        row = np.concatenate([R[i], X[i], heat(R[i], X[i])], 1)
        cv2.putText(row, f"{fno} ({fno / 30:.2f}s) mad {per[i]['mad']}", (8, 22), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 255), 2)
        cv2.imwrite(os.path.join(a.outdir, f"compare_{fno:04d}.png"), row)
        tiles.append(cv2.resize(row, None, fx=0.5, fy=0.5))
    if tiles:
        cols = 2
        while len(tiles) % cols:
            tiles.append(np.zeros_like(tiles[0]))
        rows = [np.concatenate(tiles[i:i + cols], 1) for i in range(0, len(tiles), cols)]
        cv2.imwrite(os.path.join(a.outdir, "overview.png"), np.concatenate(rows, 0))
    print(json.dumps({k: v for k, v in res.items() if k != "frames"}))


if __name__ == "__main__":
    main()
