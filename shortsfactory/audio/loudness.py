"""Loudness normalisation (EBU R128, two-pass ffmpeg loudnorm).

YouTube plays back at about -14 LUFS; quieter uploads simply sound weaker.

    python3 -m shortsfactory.audio.loudness IN.wav OUT.wav [--lufs -14 --tp -1]
"""
import argparse
import json
import re
import subprocess


def measure(path, lufs=-14.0, tp=-1.0, lra=11.0):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af",
                        f"loudnorm=I={lufs}:TP={tp}:LRA={lra}:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    return json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S).group(0))


def normalize(src, dst, lufs=-14.0, tp=-1.0, lra=11.0):
    m = measure(src, lufs, tp, lra)
    af = (f"loudnorm=I={lufs}:TP={tp}:LRA={lra}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
          "linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", af, "-ar", "44100", dst], check=True)
    after = measure(dst, lufs, tp, lra)
    return float(m["input_i"]), float(after["input_i"]), float(after["input_tp"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--lufs", type=float, default=-14.0)
    ap.add_argument("--tp", type=float, default=-1.0)
    a = ap.parse_args()
    before, after, peak = normalize(a.src, a.dst, a.lufs, a.tp)
    print(f"{before:.1f} LUFS -> {after:.1f} LUFS (true peak {peak:.1f} dBTP) -> {a.dst}")
