"""Speech-to-text with segment timestamps (Whisper small via sherpa-onnx + Silero VAD).

python3 -m shortsfactory.analysis.transcribe AUDIO_OR_VIDEO OUT.json [--models models] [--lang de]
"""
import argparse
import json
import os
import subprocess

import numpy as np


def load_16k(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000",
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def transcribe(path, models="models", lang="de"):
    import sherpa_onnx
    w = os.path.join(models, "sherpa-onnx-whisper-small")
    rec = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=f"{w}/small-encoder.int8.onnx", decoder=f"{w}/small-decoder.int8.onnx",
        tokens=f"{w}/small-tokens.txt", language=lang, task="transcribe", num_threads=4)
    cfg = sherpa_onnx.VadModelConfig()
    cfg.silero_vad.model = os.path.join(models, "silero_vad.onnx")
    cfg.silero_vad.min_silence_duration = 0.15
    cfg.silero_vad.min_speech_duration = 0.1
    cfg.silero_vad.threshold = 0.4
    cfg.sample_rate = 16000
    vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=600)
    a = load_16k(path)
    out = []

    def drain():
        while not vad.empty():
            seg = vad.front
            st = seg.start / 16000
            samples = np.array(seg.samples)
            s = rec.create_stream()
            s.accept_waveform(16000, samples)
            rec.decode_stream(s)
            out.append({"start": round(st, 2), "end": round(st + len(samples) / 16000, 2),
                        "text": s.result.text.strip()})
            vad.pop()
    ws = cfg.silero_vad.window_size
    for i in range(0, len(a), ws):
        vad.accept_waveform(a[i:i + ws])
        drain()
    vad.flush()
    drain()
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--models", default="models")
    ap.add_argument("--lang", default="de")
    a = ap.parse_args()
    segs = transcribe(a.src, a.models, a.lang)
    json.dump(segs, open(a.out, "w"), ensure_ascii=False, indent=1)
    for s in segs:
        print(f"[{s['start']:6.2f}-{s['end']:6.2f}] {s['text']}")
