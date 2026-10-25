"""Musik (prozeduraler Platzhalter), Soundeffekte und Mix.

Alles selbst synthetisiert -> keine Lizenzfragen. Für echte Produktionen
lizenzfreie Musik (z. B. YouTube Audio Library) in city.json -> "music":
{"file": "pfad.mp3"} eintragen.
"""
import numpy as np

from shortsfactory.audio import sfx as base_sfx
from shortsfactory.audio.sfx import write_wav  # noqa: F401

from .voice import SR, load


def _note(f):
    return 440.0 * 2 ** ((f - 69) / 12)


def pluck(freq, dur, bright=1.0):
    t = np.arange(int(dur * SR)) / SR
    x = np.zeros_like(t)
    for h in range(1, 7):
        x += (0.9 ** h) * np.sin(2 * np.pi * freq * h * t) * np.exp(-t * (3.5 + h * 1.6 / bright))
    a = int(0.004 * SR)
    x[:a] *= np.linspace(0, 1, a)
    return x


def music(duration, bpm=112, seed=0):
    """Leichter, verspielter Mandolinen-Groove (Dur, I-vi-IV-V) mit Tremolo-Akzenten."""
    rng = np.random.default_rng(seed)
    n = int(duration * SR) + SR
    out = np.zeros((n, 2))
    beat = 60.0 / bpm
    chords = [[60, 64, 67], [57, 60, 64], [53, 57, 60], [55, 59, 62]]  # C Am F G
    pattern = [0, 2, 1, 2, 0, 2, 1, 2]
    t, bar = 0.0, 0
    while t < duration + 1:
        ch = chords[bar % 4]
        # Bass
        b = pluck(_note(ch[0] - 24), beat * 2, 0.6) * 0.55
        i = int(t * SR)
        out[i:i + len(b)] += b[:n - i, None] * [1, 1]
        b = pluck(_note(ch[2] - 24), beat * 2, 0.6) * 0.45
        i = int((t + 2 * beat) * SR)
        out[i:i + len(b)] += b[:max(n - i, 0), None] * [1, 1]
        # Achtel-Arpeggio (Mandoline), leicht gestreut im Stereobild
        for k, p in enumerate(pattern):
            note = ch[p] + 12 + (12 if (bar % 8 >= 4 and k in (3, 7)) else 0)
            x = pluck(_note(note), beat * 0.9, 1.4) * (0.32 if k % 2 == 0 else 0.22)
            i = int((t + k * beat / 2 + rng.uniform(0, 0.008)) * SR)
            pan = 0.35 + 0.3 * (k % 2)
            seg = x[:max(n - i, 0)]
            out[i:i + len(seg), 0] += seg * (1 - pan)
            out[i:i + len(seg), 1] += seg * pan
        # Shaker auf den Offbeats
        for k in range(8):
            if k % 2:
                sh = np.random.default_rng(bar * 8 + k).standard_normal(int(0.05 * SR))
                sh = np.diff(sh, prepend=0) * np.exp(-np.arange(len(sh)) / (0.012 * SR)) * 0.05
                i = int((t + k * beat / 2) * SR)
                seg = sh[:max(n - i, 0)]
                out[i:i + len(seg)] += seg[:, None]
        t += 4 * beat
        bar += 1
    out = out[:int(duration * SR)]
    fade = int(1.5 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return (out / (np.abs(out).max() + 1e-9) * 0.8).astype(np.float32)


# --- zusätzliche Effekte -------------------------------------------------
def coins(dur=2.6):
    x = np.zeros(int(dur * SR))
    for k, t0 in enumerate([0.0, 0.45, 0.9, 1.35, 1.8]):
        t = np.arange(int(0.5 * SR)) / SR
        f = 2900 + 300 * (k % 3)
        y = (np.sin(2 * np.pi * f * t) + 0.6 * np.sin(2 * np.pi * f * 2.76 * t) + 0.3 * np.sin(2 * np.pi * f * 5.4 * t))
        y *= np.exp(-t * 14)
        i = int((t0 + 0.75) * SR)  # Aufprall nach der Flugzeit
        y = y[:len(x) - i]
        x[i:i + len(y)] += y * 0.5
        # kleines Platschen
        s = base_sfx._noise(int(0.15 * SR), seed=k) * np.exp(-np.arange(int(0.15 * SR)) / (0.03 * SR))
        s = base_sfx._bandpass(s, 600, 4000) * 0.35
        x[i:i + len(s)] += s[:len(x) - i]
    return base_sfx._stereo(base_sfx._norm(x, 0.8), 0.6)


def water(dur=9.0):
    x = base_sfx._bandpass(base_sfx._noise(int(dur * SR), 3), 300, 3500)
    mod = 1 + 0.25 * np.sin(2 * np.pi * 0.7 * np.arange(len(x)) / SR)
    env = np.minimum(1, np.minimum(np.arange(len(x)) / (1.0 * SR), (len(x) - np.arange(len(x))) / (1.5 * SR)))
    return base_sfx._stereo(base_sfx._norm(x * mod * env, 0.45), 0.8)


def rain(dur=7.0):
    n = int(dur * SR)
    x = base_sfx._bandpass(base_sfx._noise(n, 5), 1500, 9000) * 0.25
    rng = np.random.default_rng(1)
    for i in rng.integers(0, n - 2000, 260):  # Tropfen
        x[i:i + 300] += np.sin(np.arange(300) * rng.uniform(0.15, 0.4)) * np.exp(-np.arange(300) / 60) * 0.5
    env = np.minimum(1, np.minimum(np.arange(n) / (0.8 * SR), (n - np.arange(n)) / (1.5 * SR)))
    return base_sfx._stereo(base_sfx._norm(x * env, 0.5), 0.8)


def bell(dur=4.0):
    t = np.arange(int(dur * SR)) / SR
    f = 196.0
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d) for r, a, d in
            [(0.5, 0.6, 0.8), (1.0, 1.0, 1.0), (1.19, 0.6, 1.4), (1.5, 0.4, 1.6), (2.0, 0.5, 2.0), (2.74, 0.3, 3.0)])
    return base_sfx._stereo(base_sfx._norm(x, 0.7), 0.3)


EXTRA = {"coins": coins, "water": water, "rain": rain, "bell": bell}
GAINS = {"swoosh": -10, "swoosh_down": -12, "pop": -9, "coins": -12, "water": -20, "rain": -17, "bell": -14}


def get_sfx(name):
    if name in EXTRA:
        return EXTRA[name]()
    return base_sfx.PRESETS[name]()


def _add(out, x, start, gain_db=0.0):
    i = int(start * SR)
    if i >= len(out):
        return
    seg = x[:len(out) - i] * 10 ** (gain_db / 20)
    out[i:i + len(seg)] += seg


def mix(plan, out_path):
    dur = plan["duration"]
    n = int(dur * SR)
    voice = np.zeros((n, 2), np.float32)
    for b in plan["beats"]:
        v = load(b["voice_wav"])
        _add(voice, np.stack([v, v], -1), b["voice_start"], 0.0)
    fx = np.zeros((n, 2), np.float32)
    for b in plan["beats"]:
        for s in b.get("sfx", []):
            _add(fx, get_sfx(s["name"]), b["t0"] + s.get("at", 0), s.get("gain_db", GAINS.get(s["name"], -12)))
    mcfg = plan["city"].get("music", {})
    if mcfg.get("file"):
        m = load(mcfg["file"])
        m = np.stack([m, m], -1)[:n]
        m = np.pad(m, ((0, n - len(m)), (0, 0)))
    else:
        m = music(dur, mcfg.get("bpm", 112))
    # Ducking: Musik unter der Stimme leiser
    win = int(0.05 * SR)
    env = np.convolve(np.abs(voice[:, 0]), np.ones(win) / win, "same")
    duck = 1 - 0.45 * np.clip(env / (env.max() + 1e-9) * 4, 0, 1)
    duck = np.convolve(duck, np.ones(win * 4) / (win * 4), "same")
    out = voice + fx + m * 10 ** (mcfg.get("gain_db", -20) / 20) * 2.2 * duck[:, None]
    peak = np.abs(out).max()
    if peak > 0.95:
        out *= 0.95 / peak
    write_wav(out_path, out.astype(np.float32))
    return out_path
