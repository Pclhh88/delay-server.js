"""Prepare recorded/generated sound effects for the mix.

For every audio file in IN_DIR: trim leading/trailing silence (onset exact to
a few ms, so effects can be placed on the frame), short fade-out, normalise
peak to -1 dBFS, write 44.1 kHz stereo WAV to OUT_DIR with the same name.
Prints onset/duration so the timeline can be tuned.

    python3 -m shortsfactory.audio.prep_sfx IN_DIR OUT_DIR
"""
import glob
import os
import subprocess
import sys

import numpy as np

from .sfx import SR, write_wav


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2)


def prep(x, on_rel=0.04, off_rel=0.004, pre=0.004, fade=0.05):
    mono = np.abs(x).max(1)
    peak = mono.max()
    if peak <= 0:
        return x, 0.0
    env = np.convolve(mono, np.ones(64) / 64, mode="same")
    above = np.where(env > peak * on_rel)[0]
    i0 = max(0, above[0] - int(pre * SR))
    tail = np.where(env > peak * off_rel)[0]
    i1 = min(len(x), tail[-1] + int(0.02 * SR))
    y = x[i0:i1].copy()
    k = min(int(fade * SR), len(y))
    y[-k:] *= np.linspace(1, 0, k)[:, None]
    y *= 10 ** (-1 / 20) / np.abs(y).max()
    return y, i0 / SR


def main(src, dst):
    os.makedirs(dst, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(src, "*"))):
        if not f.lower().endswith((".mp3", ".wav", ".flac", ".ogg", ".m4a")):
            continue
        y, onset = prep(load(f))
        name = os.path.splitext(os.path.basename(f))[0]
        write_wav(os.path.join(dst, name + ".wav"), y)
        print(f"{name:20s} onset_trimmed={onset:5.2f}s  dur={len(y) / SR:5.2f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
