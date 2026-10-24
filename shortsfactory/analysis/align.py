"""Word timestamps for a voice track (Parakeet TDT v3 via sherpa-onnx + Silero VAD).

The recogniser's words are mapped onto the known script, so the captions keep the
script's spelling while the timing comes from the audio.

python3 -m shortsfactory.analysis.align AUDIO OUT.json [--script SCRIPT.txt] [--models models]
"""
import argparse
import difflib
import json
import os
import re

import numpy as np

from .transcribe import load_16k


def recognise_words(path, models="models"):
    """[{"text", "start", "end"}] straight from the recogniser."""
    import sherpa_onnx
    d = os.path.join(models, "sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8")
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=f"{d}/encoder.int8.onnx", decoder=f"{d}/decoder.int8.onnx",
        joiner=f"{d}/joiner.int8.onnx", tokens=f"{d}/tokens.txt",
        model_type="nemo_transducer", num_threads=4)
    cfg = sherpa_onnx.VadModelConfig()
    cfg.silero_vad.model = os.path.join(models, "silero_vad.onnx")
    cfg.silero_vad.min_silence_duration = 0.08
    cfg.silero_vad.min_speech_duration = 0.1
    cfg.silero_vad.max_speech_duration = 25
    cfg.silero_vad.threshold = 0.4
    cfg.sample_rate = 16000
    vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=600)
    a = load_16k(path)
    words = []

    def drain():
        while not vad.empty():
            seg = vad.front
            st = seg.start / 16000
            samples = np.array(seg.samples)
            s = rec.create_stream()
            s.accept_waveform(16000, samples)
            rec.decode_stream(s)
            res = s.result
            seg_end = st + len(samples) / 16000
            cur = None
            for tok, ts in zip(res.tokens, res.timestamps):
                if tok.startswith("▁") or tok.startswith(" ") or cur is None:
                    if cur:
                        words.append(cur)
                    cur = {"text": tok.lstrip("▁ "), "start": st + ts}
                else:
                    cur["text"] += tok
            if cur:
                words.append(cur)
            # word end = next word start (inside a segment) or segment end
            seg_words = [w for w in words if "end" not in w]
            for w, nxt in zip(seg_words, seg_words[1:] + [None]):
                w["end"] = nxt["start"] if nxt else seg_end
            vad.pop()
    ws = cfg.silero_vad.window_size
    for i in range(0, len(a), ws):
        vad.accept_waveform(a[i:i + ws])
        drain()
    vad.flush()
    drain()
    return [w for w in words if w["text"]]


def _norm(w):
    return re.sub(r"[^0-9a-zäöüß]", "", w.lower())


def map_to_script(rec_words, script_words):
    """Give every script word a start/end from the matched recogniser words;
    unmatched runs are spread over the gap by character length."""
    a = [_norm(w["text"]) for w in rec_words]
    b = [_norm(w) for w in script_words]
    out = [None] * len(script_words)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for tag, i0, i1, j0, j1 in sm.get_opcodes():
        if tag == "equal":
            for k in range(j1 - j0):
                out[j0 + k] = (rec_words[i0 + k]["start"], rec_words[i0 + k]["end"])
        elif tag == "replace" and i1 > i0:
            t0, t1 = rec_words[i0]["start"], rec_words[i1 - 1]["end"]
            lens = np.array([max(len(b[j]), 1) for j in range(j0, j1)], float)
            edges = t0 + (t1 - t0) * np.concatenate([[0], np.cumsum(lens) / lens.sum()])
            for k in range(j1 - j0):
                out[j0 + k] = (edges[k], edges[k + 1])
    # words still missing (inserted in the script, not heard): squeeze between neighbours
    for j, v in enumerate(out):
        if v is None:
            prev = next((out[k][1] for k in range(j - 1, -1, -1) if out[k]), 0.0)
            nxt = next((out[k][0] for k in range(j + 1, len(out)) if out[k]), prev + 0.2)
            out[j] = (prev, max(nxt, prev + 0.05))
    # overlapping runs (a squeezed word sharing its neighbour's start): split the
    # run's span by character length so every word gets its own slot
    j = 0
    while j < len(out):
        k = j
        while k + 1 < len(out) and out[k + 1][0] < out[k][1] - 1e-6 and out[k + 1][0] <= out[j][0] + 1e-6:
            k += 1
        if k > j:
            t0, t1 = out[j][0], max(e for _, e in out[j:k + 1])
            lens = np.array([max(len(b[i]), 1) for i in range(j, k + 1)], float)
            edges = t0 + (t1 - t0) * np.concatenate([[0], np.cumsum(lens) / lens.sum()])
            for i in range(j, k + 1):
                out[i] = (edges[i - j], edges[i - j + 1])
        j = k + 1
    return [{"text": w, "start": round(s, 3), "end": round(e, 3)}
            for w, (s, e) in zip(script_words, out)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--script", default=None, help="plain text; whitespace-separated words")
    ap.add_argument("--models", default="models")
    a = ap.parse_args()
    words = recognise_words(a.src, a.models)
    if a.script:
        words = map_to_script(words, open(a.script, encoding="utf-8").read().split())
    json.dump(words, open(a.out, "w"), ensure_ascii=False, indent=1)
    for w in words:
        print(f"{w['start']:6.2f}-{w['end']:6.2f} {w['text']}")
