"""Mix the audio track of a timeline.

timeline["audio"] = [
  {"id": "voice", "src": "audio/voice.flac", "start": 0.0, "gain_db": 0.0,
   "trim": [0.0, 20.0], "fade_out": 0.05},
  {"id": "sfx_impact", "src": "@sfx/impact_low", "start": 2.35, "gain_db": -9.0},
  ...
]
"@sfx/<preset>" refers to shortsfactory.audio.sfx presets (rendered on the fly).

    python3 -m shortsfactory.audio.mix TIMELINE.json OUT.wav [--start 0 --end 20]
"""
import argparse
import json
import os
import subprocess

import numpy as np

from . import sfx

SR = sfx.SR


def load_audio(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2)


def mix(timeline, base_dir, start=0.0, end=None):
    end = end if end is not None else timeline["meta"]["duration"]
    n = int(round((end - start) * SR))
    out = np.zeros((n, 2), np.float32)
    cache = {}
    for item in timeline.get("audio", []):
        if item.get("mute"):
            continue
        src = item["src"]
        if src not in cache:
            if src.startswith("@sfx/"):
                cache[src] = sfx.PRESETS[src[5:]]()
            else:
                cache[src] = load_audio(os.path.join(base_dir, src))
        x = cache[src]
        if "trim" in item:
            a, b = item["trim"]
            x = x[int(a * SR):int(b * SR)]
        x = x * (10 ** (item.get("gain_db", 0.0) / 20))
        fo = item.get("fade_out")
        if fo:
            k = min(int(fo * SR), len(x))
            x = x.copy()
            x[-k:] *= np.linspace(1, 0, k)[:, None]
        pos = int(round((item["start"] - start) * SR))
        a0 = max(pos, 0)
        b0 = min(pos + len(x), n)
        if b0 > a0:
            out[a0:b0] += x[a0 - pos:b0 - pos]
    peak = np.abs(out).max()
    if peak > 0.98:
        out *= 0.98 / peak
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline")
    ap.add_argument("out")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=None)
    a = ap.parse_args()
    tl = json.load(open(a.timeline, encoding="utf-8"))
    base = os.path.dirname(os.path.dirname(os.path.abspath(a.timeline)))
    sfx.write_wav(a.out, mix(tl, base, a.start, a.end))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
