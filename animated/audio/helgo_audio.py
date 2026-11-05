"""Helgoland short: original score + synthesized SFX + voice -> mix.wav (48 kHz, 96.0 s, -14 LUFS, <= -1 dBTP).

python3 audio/helgo_audio.py <voice.mp3> <out_dir>
All event times are frames from src/videos/helgoland/story.ts / cast.ts (30 fps).
"""
import json
import os
import subprocess
import sys

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsp import (SR, TAU, ns, tt, rng, lp, hp, bp, colored, smooth_noise, fades, pan, st, place, widen, make_ir, convolve_st,
                 integrated, true_peak, dbg, write_wav, phase, modal)
import instruments as I
from sfx_gen import whoosh, rattle, clink, babble, hurrah, applause, flag_flutter, breeze, stroll_step

FPS = 30
TOTAL = 2880
DUR = TOTAL / FPS
N = ns(DUR)
F = lambda f: f / FPS

CUTS = [155, 308, 368, 436, 539, 595, 647, 720, 787, 866, 940, 1019, 1050, 1183, 1276, 1352, 1456, 1532, 1668, 1768, 1862, 1916, 2088, 2244,
        2320, 2412, 2526, 2643, 2726]
SHOTS = [(0, 155), (155, 228), (228, 368), (368, 436), (436, 720), (720, 866), (866, 940), (940, 1050), (1050, 1183), (1183, 1352),
         (1352, 1456), (1456, 1668), (1668, 1768), (1768, 1916), (1916, 2088), (2088, 2320), (2320, 2412), (2412, 2526), (2526, 2726), (2726, 2880)]
OUTDOOR_SEA = [1, 2, 3, 7, 9, 10, 11, 12, 13, 15, 16, 18, 19, 20]  # shot ids with sea ambience


def shot_of(f):
    for i, (a, b) in enumerate(SHOTS):
        if a <= f < b:
            return i + 1
    return 20


# ================================================================ SFX
def boom(r, size=1.0, dur=5.0):
    t = tt(dur)
    sub = np.sin(phase(38 + 30 * np.exp(-t / 0.25))) * np.exp(-t / (0.9 * size)) * 1.6
    body = lp(colored(len(t), r, 1.2), 900, 2) * np.exp(-t / (0.55 * size)) * 2.2
    roar = lp(colored(len(t), r, 0.8), 2400, 2) * np.exp(-t / (1.6 * size)) * 0.5 * (1 - np.exp(-t / 0.08))
    crack = hp(r.standard_normal(len(t)), 1500) * np.exp(-t / 0.02) * 1.2
    y = (sub + body + roar + crack) * size
    deb = rattle(min(3.5, dur - 0.6), r, 22, np.exp(-np.linspace(0, 4, ns(min(3.5, dur - 0.6)))), heavy=True) * 0.35 * size
    out = widen(y, r, 14, 0.7)
    place(out, widen(deb, r, 9, 0.8), 0.5)
    return fades(out, 0.0, 0.5)


def gull(r):
    d = r.uniform(0.35, 0.6)
    t = tt(d)
    f0 = 1300 + 900 * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 0.7 * r.uniform(0.8, 1.2)
    ph = phase(f0)
    y = sum((0.6 / k) * np.sin(k * ph) for k in range(1, 6))
    env = np.sin(np.pi * t / d) ** 1.5 * (0.6 + 0.4 * np.sin(phase(np.full(len(t), r.uniform(18, 26)))))
    return bp(y * env, 700, 6000, 1) * 0.5


def gulls(buf, r, t0, t1, rate=0.7, gain=0.18, p0=-0.6, p1=0.6):
    t = t0 + r.exponential(1 / rate)
    while t < t1:
        place(buf, pan(gull(r), r.uniform(p0, p1)), t, gain * r.uniform(0.5, 1.0))
        if r.random() < 0.5:
            place(buf, pan(gull(r), r.uniform(p0, p1)), t + r.uniform(0.25, 0.45), gain * 0.6)
        t += r.exponential(1 / rate)


def sea(dur, r, level=1.0):
    n = ns(dur)
    out = np.zeros((2, n))
    sw = 0.55 + 0.45 * np.sin(phase(np.full(n, 0.11))) * (0.7 + 0.3 * smooth_noise(n, r, 0.3))
    for ch in range(2):
        w = lp(colored(n, r, 1.0), 700, 2) * sw
        w += 0.35 * bp(colored(n, r, 0.4), 1500, 6000, 1) * sw ** 3
        out[ch] = w * level
    return out


def hum(dur, r, f0=55, level=0.3):
    t = tt(dur)
    y = sum((1 / k) * np.sin(TAU * f0 * k * t + r.uniform(0, TAU)) for k in range(1, 5))
    y = lp(y + 0.3 * colored(len(t), r, 1.5), 400) * level
    return st(y)


def tick(r):
    return modal(0.08, [(3200, 0.6, 0.006), (5400, 0.4, 0.004)], r) + hp(r.standard_normal(ns(0.08)), 3000) * np.exp(-tt(0.08) / 0.002) * 0.3


def clank(r, big=1.0):
    return modal(1.2, [(r.uniform(180, 240), 1.0, 0.25), (r.uniform(410, 520), 0.7, 0.18), (r.uniform(900, 1100), 0.45, 0.1), (2300, 0.25, 0.05)], r) * big


def thump(r, f=70, d=0.4, g=1.0):
    t = tt(d)
    return (np.sin(phase(f * (1 + 0.6 * np.exp(-t / 0.02)))) * np.exp(-t / 0.09) + lp(r.standard_normal(len(t)), 500) * np.exp(-t / 0.03)) * g


def poof(r):
    t = tt(0.6)
    return (lp(r.standard_normal(len(t)), 900) * np.exp(-t / 0.12) * 0.8 + thump(r, 60, 0.6, 0.7))


def shatter(r):
    d = 1.6
    out = np.zeros(ns(d))
    t = tt(d)
    out += hp(r.standard_normal(len(t)), 2500) * np.exp(-t / 0.05) * 1.2
    for _ in range(45):
        c = modal(0.25, [(r.uniform(3000, 9000), 1.0, r.uniform(0.02, 0.08)), (r.uniform(5000, 11000), 0.5, 0.03)], r)
        i = ns(r.exponential(0.25))
        if i < len(out) - len(c):
            out[i:i + len(c)] += c * r.uniform(0.1, 0.4)
    return widen(fades(out, 0.0, 0.2), r, 7, 0.9)


def plunger(r):
    t = tt(0.5)
    slide = bp(r.standard_normal(len(t)), 600, 3000, 1) * np.clip(t / 0.12, 0, 1) * (t < 0.13) * 0.4
    hit = thump(r, 110, 0.5, 0.9)
    c = clink(r, 2400, 0.15)
    hit[:len(c)] += 0.6 * c[:len(hit)]
    y = np.zeros(ns(0.7))
    y[:len(slide)] += slide
    y[ns(0.13):ns(0.13) + len(hit)] += hit
    return y


def plane(dur, r):
    t = tt(dur)
    f = 92 * (1 + 0.04 * np.sin(TAU * 0.3 * t))
    saw = sum((1 / k) * np.sin(k * phase(f)) for k in range(1, 14))
    prop = 0.6 + 0.4 * np.sin(phase(f * 0.5))
    y = lp(saw * prop, 1500) + 0.3 * bp(colored(len(t), r, 0.6), 400, 2000)
    return y


def bomb_whistle(r, d=0.73):
    t = tt(d)
    y = np.sin(phase(2200 * np.exp(-t * 1.6))) * np.clip(t / 0.1, 0, 1)
    return y * 0.35


def splash_small(r):
    t = tt(0.5)
    return bp(r.standard_normal(len(t)), 500, 5000, 1) * np.exp(-t / 0.09) * 0.5 + lp(r.standard_normal(len(t)), 300) * np.exp(-t / 0.05) * 0.3


def pop(r):
    t = tt(0.12)
    return np.sin(phase(r.uniform(500, 900) * (1 + 2 * np.exp(-t / 0.01)))) * np.exp(-t / 0.03) * 0.5


def ding(r, f=1760):
    return I.glock(f, 0.7, r, 1.4)


def render_sfx(r):
    out = np.zeros((2, N))
    # ---- beds per shot ----
    for i, (a, b) in enumerate(SHOTS):
        sid = i + 1
        d = F(b - a) + 0.4
        if sid in OUTDOOR_SEA:
            lev = 0.10 if sid in (7, 8, 11) else 0.14
            place(out, fades(sea(d, r, lev), 0.15, 0.25), F(a) - 0.1)
            place(out, fades(breeze(d, r, 0.05), 0.15, 0.25), F(a) - 0.1)
        if sid in (5, 6) and not (sid == 6 and a >= 787):
            place(out, fades(hum(min(d, F(787 - a) + 0.3) if sid == 6 else d, r, 50, 0.08), 0.1, 0.25), F(a))
        if sid in (7, 8, 11):
            place(out, fades(hum(d, r, 42, 0.12), 0.15, 0.25), F(a))
    place(out, fades(sea(F(787 - 720) + 0.3, r, 0.0), 0.1, 0.1), F(720))
    place(out, fades(sea(F(866 - 787) + 0.3, r, 0.12), 0.1, 0.2), F(787))
    # ---- whooshes on cuts ----
    for f in CUTS:
        place(out, widen(whoosh(0.55, r, 0.28, 300, 1800, 0.8, 0.18), r, 8, 0.7), F(f) - 0.28, 0.12)
    place(out, widen(whoosh(0.9, r, 0.2, 1500, 6000, 0.6, 0.3, 0.4), r, 8, 0.9), F(226) - 0.2, 0.25)  # flash shimmer
    # ---- gulls ----
    gulls(out, r, 0.2, 7.5, 0.6, 0.12)
    gulls(out, r, 7.8, 14.4, 0.9, 0.13)
    gulls(out, r, 43.0, 45.0, 0.8, 0.10)
    gulls(out, r, 80.5, 95.5, 0.9, 0.12)
    # ---- the blasts ----
    place(out, boom(r, 0.9, 4.5), F(30), 0.9)
    place(out, boom(r, 1.3, 7.0), F(1052), 1.2)
    place(out, widen(rattle(3.0, r, 18, np.exp(-np.linspace(0, 3, ns(3.0))), heavy=True), r, 9, 0.8), F(1060), 0.35)
    # ---- bunker inserts: metal clanks ----
    for f in (539, 595, 647):
        place(out, pan(clank(r, 0.6), r.uniform(-0.4, 0.4)), F(f) + 0.02, 0.25)
    # cable reel ratchet (shot 6a) + footsteps of sailors on the plateau (6b)
    for k in range(int(F(787 - 722) * 14)):
        place(out, pan(clink(r, r.uniform(2600, 3400), 0.04), 0.3), F(722) + k / 14, 0.05)
    for k in range(10):
        place(out, pan(stroll_step(r, 0.3), -0.2 + 0.04 * k), F(790) + k * 0.6, 0.06)
    # ---- the watch ticks, the plunger ----
    for s in np.arange(F(940) + 0.15, F(1019), 1.0):
        place(out, st(tick(r)), s, 0.25)
    place(out, pan(plunger(r), 0.15), F(1047) - 0.13, 0.7)
    # ---- pores pop open, the shock fizzles ----
    for i in range(14):
        place(out, pan(pop(r), r.uniform(-0.5, 0.5)), F(1594 + i * 2), 0.12)
    for i in range(12):
        place(out, pan(pop(r), r.uniform(-0.5, 0.5)), F(1643 + i * 2), 0.12)
    place(out, widen(whoosh(2.4, r, 0.15, 2500, 300, 0.9, 0.8, 0.2), r, 8, 0.9), F(1678), 0.35)
    for i in range(10):
        place(out, pan(lp(r.standard_normal(ns(0.3)), 1200) * np.exp(-tt(0.3) / 0.06) * 0.4, -0.7 + 0.14 * i), F(1690) + i * 0.2, 0.15)
    # ---- cushion vs glass ----
    place(out, widen(whoosh(0.5, r, 0.4, 400, 2500, 0.7, 0.05), r, 6, 0.5), F(1832) - 0.4, 0.3)
    place(out, st(poof(r)), F(1832), 0.6)
    place(out, widen(whoosh(0.5, r, 0.4, 400, 2500, 0.7, 0.05), r, 6, 0.5), F(1891) - 0.4, 0.3)
    place(out, shatter(r), F(1891), 0.55)
    place(out, st(thump(r, 90, 0.3, 0.6)), F(1891), 0.6)
    # ---- planes + practice bombs ----
    pd = F(2088 - 1916) + 0.5
    pl = plane(pd, r)
    env = np.interp(np.arange(len(pl)) / SR, [0, 1.5, pd - 1.5, pd], [0.2, 1, 1, 0])
    pn = np.interp(np.arange(len(pl)) / SR, [0, pd], [-0.8, 0.8])
    stereo = np.stack([pl * env * np.cos((pn + 1) * np.pi / 4), pl * env * np.sin((pn + 1) * np.pi / 4)]) * np.sqrt(2)
    place(out, stereo, F(1916), 0.16)
    for fr in (1990, 2012, 2034):
        place(out, st(bomb_whistle(r)), F(fr), 0.25)
        place(out, boom(r, 0.45, 2.5), F(fr + 22), 0.55)
    # ---- the rowing boat ----
    for k in range(int(F(2244 - 2088) / 1.5)):
        place(out, pan(splash_small(r), -0.3), F(2088) + 0.4 + k * 1.5, 0.22)
        place(out, pan(splash_small(r), 0.3), F(2088) + 0.45 + k * 1.5, 0.18)
    place(out, pan(fades(flag_flutter(F(2320 - 2262), r), 0.2, 0.3), 0.3), F(2262), 0.12)
    place(out, pan(fades(flag_flutter(F(2526 - 2484), r), 0.2, 0.3), -0.2), F(2484), 0.1)
    # ---- crowds ----
    place(out, widen(fades(babble(F(2412 - 2320), r, 150, 1.0, 4.5, 0.8), 0.2, 0.3), r, 10, 0.8), F(2320), 0.10)
    place(out, widen(fades(babble(F(2412 - 2320), r, 210, 1.15, 4.0, 0.7), 0.2, 0.3), r, 13, 0.8), F(2320), 0.08)
    place(out, applause(F(2526 - 2500) + 0.6, r, 24), F(2500), 0.22)
    for k in range(4):
        place(out, pan(hurrah(r, r.uniform(120, 220), r.uniform(0.9, 1.15)), r.uniform(-0.6, 0.6)), F(2502) + k * 0.18, 0.12)
    place(out, widen(fades(babble(F(2643 - 2526), r, 170, 1.0, 4.0, 0.5), 0.3, 0.3), r, 10, 0.8), F(2526), 0.05)
    for k in range(int(F(2643 - 2526) / 0.45)):
        place(out, pan(stroll_step(r, 0.4), r.uniform(-0.5, 0.5)), F(2526) + k * 0.45 + r.uniform(0, 0.1), 0.04)
    place(out, st(ding(r, 2093)), F(2664), 0.25)
    place(out, st(ding(r, 2637)), F(2664) + 0.09, 0.18)  # till "ka-ching"
    return out


# ================================================================ music (original)
Q = 0.5  # 120 bpm
D_MIN = {"Dm": [50, 53, 57], "Bb": [46, 50, 53], "C": [48, 52, 55], "A": [45, 49, 52], "Gm": [43, 46, 50], "F": [41, 45, 48]}
# our own 8-bar tune (MIDI, beats): mischievous, steps then leaps
TUNE = [(62, 1), (65, 0.5), (64, 0.5), (62, 1), (57, 1), (58, 1), (62, 0.5), (60, 0.5), (57, 2),
        (55, 1), (58, 0.5), (57, 0.5), (55, 1), (53, 1), (52, 1), (55, 0.5), (57, 0.5), (50, 2)]
PROG = ["Dm", "Dm", "Bb", "A", "Gm", "C", "A", "Dm"]


def music(r):
    out = np.zeros((2, N))
    ir = make_ir(1.1, 5)

    def add(x, t, p=0.0, g=1.0):
        place(out, pan(x, p) if np.ndim(x) == 1 else x, t, g)

    def bars(t0, nb, vel=0.6, tune=True, tuba=True, pizz=True, glock_oct=12, snare=False):
        for b in range(nb):
            tb = t0 + b * 4 * Q
            ch = D_MIN[PROG[b % 8]]
            if tuba:
                add(I.brass(I.m2f(ch[0] - 12), Q * 0.8, vel * 0.8, r, "tuba"), tb, -0.1, 0.5)
                add(I.brass(I.m2f(ch[2] - 12), Q * 0.8, vel * 0.7, r, "tuba"), tb + 2 * Q, -0.1, 0.45)
            if pizz:
                for k in (1, 3):
                    for m in ch:
                        add(I.pluck(I.m2f(m + 12), vel * 0.5, r, 0.4), tb + k * Q, 0.25, 0.22)
            if snare:
                for k in range(8):
                    add(I.brush(vel * (0.7 if k % 2 else 0.4), r), tb + k * Q / 2, 0.1, 0.25)
        if tune:
            t = t0
            for rep in range(nb // 8 or 1):
                for m, d in TUNE:
                    if t >= t0 + nb * 4 * Q:
                        break
                    add(I.glock(I.m2f(m + glock_oct), vel, r, 1.2), t, 0.15, 0.35)
                    add(I.fife(I.m2f(m + glock_oct), d * Q * 0.9, vel * 0.55, r), t, -0.2, 0.18)
                    t += d * Q

    # hook: low pulse + rising roll into the flash
    for k in range(14):
        add(I.timpani(I.m2f(38), 0.35 + 0.03 * k, r, 1.0), k * Q, 0, 0.35)
    def roll(t0, t1, v0, v1, g=0.3):
        for tr, vr in I.snare_roll(t0, t1, v0, v1, r):
            add(I.snare(vr, r, 0.2), tr, 0.05, g)

    roll(4.8, 7.55, 0.15, 0.8)
    add(I.cymbal(0.8, r, 2.4), F(228), 0, 0.35)
    # story march: 7.6 s -> 33.6 s (13 bars)
    bars(F(228), 13, 0.6, snare=True)
    # tension: timpani + roll toward the plunger
    for k in range(6):
        add(I.timpani(I.m2f(45), 0.5 + 0.08 * k, r, 0.8), 32.0 + k * Q * 0.5, 0, 0.4)
    roll(33.0, 34.85, 0.25, 1.0, 0.35)
    # after the blast: silence until "Steht noch" -> sting
    add(I.glock(I.m2f(74), 0.8, r, 2.0), F(1326), 0.2, 0.5)
    add(I.glock(I.m2f(81), 0.8, r, 2.0), F(1334), -0.2, 0.5)
    add(I.pad([I.m2f(m) for m in (50, 57, 62, 65)], 2.5, 0.35, r), F(1326), 0, 0.25)
    # curious section: pizz + glock, no tuba (48.6 -> 63.6)
    bars(F(1458), 7, 0.5, tuba=False, snare=False, glock_oct=12)
    # bombers: tuba + snare, darker (64 -> 69.6)
    bars(F(1921), 3, 0.65, tune=False, snare=True)
    # students + Germany + 1952: full march warmer (69.6 -> 84.2)
    bars(F(2090), 7, 0.62, snare=True)
    add(I.cymbal(0.7, r, 2.0), F(2496), 0, 0.3)
    # today: bright finale (84.3 -> 96), ends on the last word with a cymbal
    bars(F(2528), 6, 0.68, snare=True, glock_oct=24)
    add(I.brass(I.m2f(38), 1.2, 0.8, r, "tuba"), F(2867), 0, 0.6)
    add(I.cymbal(0.9, r, 2.0), F(2867), 0, 0.3)
    return convolve_st(out, ir) * 0.25 + out


# ================================================================ mix
def main():
    voice_src, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", voice_src, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    v = np.frombuffer(raw, np.float32).astype(np.float64)
    voice = np.zeros(N); voice[:min(N, len(v))] = v[:N]
    voice = st(voice)
    r = rng(1947)
    sfx = render_sfx(r)
    mus = music(rng(1952))
    # ducking from the word timings
    words = json.load(open(os.path.join(os.path.dirname(voice_src), "words.json")))
    key = np.zeros(N)
    for w in words:
        key[ns(w["s"]):ns(w["e"] + 0.08)] = 1
    key = signal.filtfilt(*signal.butter(1, 4 / (SR / 2)), key)
    duck = dbg(-4.0 * np.clip(key, 0, 1))
    vl = integrated(voice)
    mus = mus * dbg(vl - 11.0 - integrated(mus)) * duck
    sfx = sfx * dbg(vl - 9.0 - integrated(sfx))
    mix = voice + mus + sfx
    mix *= dbg(-14.0 - integrated(mix))
    # look-ahead limiter (true-peak via 4x oversampling), iterated with loudness normalisation
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    ceil = dbg(-1.6)
    for _ in range(4):
        up = signal.resample_poly(mix, 4, 1, axis=-1)
        pk = np.abs(up).max(axis=0)[: 4 * N].reshape(-1, 4).max(axis=1)
        g = np.minimum(1, ceil / np.maximum(pk, 1e-9))
        g = uniform_filter1d(minimum_filter1d(g, 721), 481)
        mix = mix * g[None, :]
        mix *= dbg(-14.0 - integrated(mix))
    write_wav(os.path.join(outdir, "mix.wav"), mix)
    write_wav(os.path.join(outdir, "stem_music.wav"), mus)
    write_wav(os.path.join(outdir, "stem_sfx.wav"), sfx)
    print(f"mix: {integrated(mix):.1f} LUFS, TP {true_peak(mix):.1f} dBTP, {mix.shape[1] / SR:.3f} s")


if __name__ == "__main__":
    main()
