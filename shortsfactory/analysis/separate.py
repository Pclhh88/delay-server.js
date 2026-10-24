"""Split a mix into voice and rest (music/SFX) with UVR-MDX-NET-Voc_FT (sherpa-onnx).

python3 -m shortsfactory.analysis.separate INPUT OUT_PREFIX [--models models]
-> OUT_PREFIX_voice.wav, OUT_PREFIX_rest.wav
"""
import argparse
import os
import subprocess
import wave

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("prefix")
    ap.add_argument("--models", default="models")
    a = ap.parse_args()
    import sherpa_onnx as so
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.src, "-vn", "-ac", "2", "-ar", "44100",
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2).T.copy()
    c = so.OfflineSourceSeparationConfig()
    c.model.uvr.model = os.path.join(a.models, "UVR-MDX-NET-Voc_FT.onnx")
    c.model.num_threads = 4
    res = so.OfflineSourceSeparation(c).process(44100, x)
    for name, st in zip(("voice", "rest"), res.stems):
        d = (np.clip(np.array(st.data), -1, 1) * 32767).astype(np.int16).T
        with wave.open(f"{a.prefix}_{name}.wav", "wb") as w:
            w.setnchannels(d.shape[1])
            w.setsampwidth(2)
            w.setframerate(res.sample_rate)
            w.writeframes(d.tobytes())
        print("wrote", f"{a.prefix}_{name}.wav")


if __name__ == "__main__":
    main()
