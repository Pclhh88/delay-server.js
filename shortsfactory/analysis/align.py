"""Word timing for a known script (no forced-alignment model needed).

Speech is split into voiced segments by an energy envelope; the script's words
are distributed over these segments with a dynamic programme that matches
segment durations to the words' estimated syllable counts.  Inside a group of
words the time is split by syllables.  Accuracy is typically ±0.1 s, enough for
one-word captions that switch on the word.

    python3 -m shortsfactory.analysis.align voice.wav script.txt words.json [whisper_model_dir]

With a Whisper model dir (sherpa-onnx export, see tools/setup_models.sh) each
pause-delimited chunk is transcribed first, which pins the words to the right
chunk; without it only durations are used (good for clean, evenly read text).
"""
import json
import re
import subprocess
import sys

import numpy as np

NUM_WORDS = {
    "1937": "neunzehnhundertsiebenunddreissig",
    "2018": "zweitausendachtzehn",
    "GPS": "gepeess",
    "1872": "achtzehnhundertzweiundsiebzig",
    "1.700": "siebzehnhundert",
}


def syllables(word):
    w = NUM_WORDS.get(word.strip(".,:;!?„“\"…"), word).lower()
    w = re.sub(r"[^a-zäöüß]", "", w)
    if not w:
        return 1
    groups = re.findall(r"(?:ei|ie|eu|äu|au|aa|ee|oo|[aeiouyäöü])", w)
    return max(1, len(groups))


def load_audio(path, sr=16000):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr),
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768, sr


def voiced_segments(x, sr, hop=0.01, min_gap=0.07, min_seg=0.06, rel_db=-32):
    n = int(sr * hop)
    frames = x[: len(x) // n * n].reshape(-1, n)
    db = 20 * np.log10(np.sqrt((frames ** 2).mean(1)) + 1e-6)
    thr = np.percentile(db, 95) + rel_db
    v = db > thr
    segs, i = [], 0
    while i < len(v):
        if v[i]:
            j = i
            while j < len(v) and v[j]:
                j += 1
            segs.append([i * hop, j * hop])
            i = j
        else:
            i += 1
    merged = []
    for s in segs:
        if merged and s[0] - merged[-1][1] < min_gap:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    return [s for s in merged if s[1] - s[0] >= min_seg]


PUNCT = tuple(".,:;!?…\"“")


def align(words, segs, max_w=8, max_s=6, long_gap=0.3):
    """Each group = consecutive words over consecutive segments.  Long pauses
    must fall on punctuation, and no long pause may sit inside a group."""
    syl = np.array([syllables(w) for w in words], float)
    gaps = [segs[j + 1][0] - segs[j][1] for j in range(len(segs) - 1)] + [9.9]
    k = sum(b - a for a, b in segs) / syl.sum()
    nW, nS = len(words), len(segs)
    INF = 1e18
    cost = np.full((nW + 1, nS + 1), INF)
    back = {}
    cost[0, 0] = 0
    csyl = np.concatenate([[0], np.cumsum(syl)])
    for i in range(nW + 1):
        for j in range(nS + 1):
            c0 = cost[i, j]
            if c0 >= INF:
                continue
            for di in range(1, max_w + 1):
                if i + di > nW:
                    break
                exp = k * (csyl[i + di] - csyl[i])
                for dj in range(1, max_s + 1):
                    if j + dj > nS:
                        break
                    dur = sum(b - a for a, b in segs[j:j + dj])
                    c = c0 + (dur - exp) ** 2 / (exp + 0.15) + 0.03 * (dj - 1) + 0.01
                    punct = words[i + di - 1].endswith(PUNCT)
                    if gaps[j + dj - 1] >= long_gap and not punct:
                        c += 3.0
                    if gaps[j + dj - 1] >= long_gap and punct:
                        c -= 0.3
                    c += 3.0 * sum(g >= long_gap for g in gaps[j:j + dj - 1])
                    if c < cost[i + di, j + dj]:
                        cost[i + di, j + dj] = c
                        back[(i + di, j + dj)] = (i, j)
    if cost[nW, nS] >= INF:
        raise RuntimeError("alignment failed (more segments than words?)")
    out, cur = [], (nW, nS)
    groups = []
    while cur != (0, 0):
        prev = back[cur]
        groups.append((prev, cur))
        cur = prev
    for (i0, j0), (i1, j1) in reversed(groups):
        a, b = segs[j0][0], segs[j1 - 1][1]
        tot = csyl[i1] - csyl[i0]
        for i in range(i0, i1):
            s = a + (b - a) * (csyl[i] - csyl[i0]) / tot
            e = a + (b - a) * (csyl[i + 1] - csyl[i0]) / tot
            out.append({"text": words[i], "start": round(s, 3), "end": round(e, 3)})
    return out


def _norm(w):
    return re.sub(r"[^a-z0-9äöüß]", "", w.lower())


def align_with_asr(words, x, sr, segs, model_dir, long_gap=0.3):
    """Split at long pauses, transcribe each chunk with Whisper (sherpa-onnx)
    and use the transcripts to decide which script words belong to which chunk;
    inside a chunk the syllable DP places the words."""
    import difflib
    import glob
    import os
    import sherpa_onnx
    enc = sorted(glob.glob(os.path.join(model_dir, "*encoder*.onnx")))[-1]
    dec = sorted(glob.glob(os.path.join(model_dir, "*decoder*.onnx")))[-1]
    tok = glob.glob(os.path.join(model_dir, "*tokens.txt"))[0]
    rec = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=enc, decoder=dec, tokens=tok,
                                                     language="de", num_threads=4)
    chunks, cur = [], [segs[0]]
    for a, b in zip(segs, segs[1:]):
        if b[0] - a[1] >= long_gap:
            chunks.append(cur)
            cur = []
        cur.append(b)
    chunks.append(cur)
    asr, owner = [], []
    for ci, ch in enumerate(chunks):
        st = rec.create_stream()
        st.accept_waveform(sr, x[int(max(0, ch[0][0] - 0.05) * sr):int((ch[-1][1] + 0.05) * sr)])
        rec.decode_stream(st)
        for w in st.result.text.split():
            if _norm(w):
                asr.append(_norm(w))
                owner.append(ci)
    ref = [_norm(w) for w in words]
    sm = difflib.SequenceMatcher(None, ref, asr, autojunk=False)
    wchunk = [None] * len(words)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("equal", "replace"):
            for k in range(i2 - i1):
                jj = j1 + min(k * max(1, j2 - j1) // max(1, i2 - i1), j2 - j1 - 1)
                wchunk[i1 + k] = owner[jj]
    # fill gaps, keep monotonic
    last = 0
    for i in range(len(words)):
        if wchunk[i] is None or wchunk[i] < last:
            wchunk[i] = last
        last = wchunk[i]
    out = []
    for ci, ch in enumerate(chunks):
        ws = [w for w, c in zip(words, wchunk) if c == ci]
        if not ws:
            continue
        if len(ch) > len(ws):  # merge closest segments until it fits
            ch = [list(s) for s in ch]
            while len(ch) > len(ws):
                g = min(range(len(ch) - 1), key=lambda j: ch[j + 1][0] - ch[j][1])
                ch[g][1] = ch[g + 1][1]
                del ch[g + 1]
        out += align(ws, ch, max_w=len(ws), max_s=len(ch))
    return out


def main():
    audio, script, out = sys.argv[1:4]
    model = sys.argv[4] if len(sys.argv) > 4 else None
    x, sr = load_audio(audio)
    words = open(script, encoding="utf-8").read().split()
    segs = voiced_segments(x, sr)
    res = align_with_asr(words, x, sr, segs, model) if model else align(words, segs)
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(words)} words, {len(segs)} segments -> {out}")


if __name__ == "__main__":
    main()
