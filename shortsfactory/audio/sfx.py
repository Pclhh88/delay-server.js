"""Procedural sound effects (self-made, no third-party samples).

Every generator returns a float32 stereo array (n, 2) at SR. The designs are
modelled on the measured spectra of the reference video's effect stem (see
docs/STYLE_GUIDE.md, "Sounddesign"), not copied from it.

    python3 -m shortsfactory.audio.sfx OUT_DIR      # writes all presets as WAV
"""
import os
import sys
import wave

import numpy as np

SR = 44100


def _t(dur):
    return np.arange(int(dur * SR)) / SR


def _env(n, attack=0.005, decay=None, release=0.02):
    t = np.arange(n) / SR
    e = np.ones(n)
    a = max(int(attack * SR), 1)
    e[:a] = np.linspace(0, 1, a)
    if decay:
        e *= np.exp(-np.maximum(t - attack, 0) / decay)
    r = max(int(release * SR), 1)
    e[-r:] *= np.linspace(1, 0, r)
    return e


def _stereo(x, width=0.0, seed=0):
    if width <= 0:
        return np.stack([x, x], -1).astype(np.float32)
    rng = np.random.default_rng(seed)
    d = int(0.008 * SR * width)
    y = np.concatenate([np.zeros(d), x[:-d] if d else x]) if d else x
    return np.stack([x, 0.7 * x + 0.3 * y], -1).astype(np.float32)


def _noise(n, seed=1):
    return np.random.default_rng(seed).standard_normal(n)


def _lowpass(x, cutoff):
    """one-pole low-pass (cutoff Hz, may be an array)"""
    cutoff = np.broadcast_to(np.asarray(cutoff, float), x.shape)
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def _bandpass(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def _norm(x, peak=0.9):
    m = np.abs(x).max()
    return x * (peak / m) if m > 0 else x


# ------------------------------------------------------------------ presets
def impact_low(dur=1.1):
    """Dull low 'dunn' hit (energy 250-350 Hz + sub), for punch zooms."""
    t = _t(dur)
    f = 290 * (1 - 0.08 * t / dur)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.35 * np.sin(2 * np.pi * np.cumsum(2 * f) / SR)
    sub = np.sin(2 * np.pi * np.cumsum(70 * (1 - 0.3 * t / dur)) / SR)
    click = _bandpass(_noise(len(t), 3), 800, 9000) * np.exp(-t / 0.012)
    x = (tone * 0.8 + sub * 0.6) * _env(len(t), 0.004, 0.45, 0.08) + click * 0.5
    return _stereo(_norm(x, 0.85))


def swoosh(dur=0.32, up=True, seed=2):
    """Air whoosh: band-passed noise with a moving centre frequency."""
    t = _t(dur)
    n = _noise(len(t), seed)
    p = t / dur
    fc = (500 + 3500 * p) if up else (4000 - 3500 * p)
    x = _lowpass(n, fc) - _lowpass(n, fc * 0.35)
    env = np.sin(np.pi * np.clip(p, 0, 1)) ** 1.5
    return _stereo(_norm(x * env, 0.7), width=1.0, seed=seed)


def pop(dur=0.18):
    """Bubble pop for things appearing (pitch drop 900 -> 300 Hz)."""
    t = _t(dur)
    f = 300 + 600 * np.exp(-t / 0.03)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(len(t), 0.002, 0.05, 0.02)
    return _stereo(_norm(x, 0.8))


def magic_glide(dur=2.1):
    """Slide whistle 1400 -> 1100 Hz, then a soft bell chord (C6 E6 G6 C7)
    with a little arpeggio - the 'Bob Ross paints' moment."""
    t = _t(dur)
    x = np.zeros_like(t)
    g = t < 0.4
    fg = 1400 - 300 * (t[g] / 0.4)
    x[g] += 0.5 * np.sin(2 * np.pi * np.cumsum(fg) / SR) * np.sin(np.pi * t[g] / 0.4)
    notes = [1046.5, 1318.5, 1568.0, 2093.0, 2637.0]
    for i, f in enumerate(notes):
        st = 0.35 + 0.07 * i
        m = t >= st
        tt = t[m] - st
        x[m] += 0.22 * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt)) * np.exp(-tt / 0.9)
    low = np.sin(2 * np.pi * 220 * t) * np.exp(-t / 0.25) * 0.4
    return _stereo(_norm((x + low) * _env(len(t), 0.005, None, 0.15), 0.7), width=0.6, seed=4)


def camera_flash(dur=0.6):
    """Flash 'pshh': broadband noise burst with fast decay."""
    t = _t(dur)
    n = _noise(len(t), 5)
    x = (n - _lowpass(n, 300)) * np.exp(-t / 0.15)
    hi = _bandpass(_noise(len(t), 6), 3000, 12000) * np.exp(-t / 0.05)
    return _stereo(_norm(x + hi, 0.85), width=1.0, seed=5)


def tinnitus(dur=1.5):
    """Ringing 'eeee' after a blinding flash: 6.4 kHz + 3.5 kHz sines."""
    t = _t(dur)
    x = 0.6 * np.sin(2 * np.pi * 6400 * t) + 0.4 * np.sin(2 * np.pi * 3500 * t)
    return _stereo(_norm(x * _env(len(t), 0.08, None, 0.35), 0.35))


def buzzer(dur=0.55):
    """Game-show 'wrong' buzzer: two detuned square waves, band-limited."""
    t = _t(dur)
    x = np.sign(np.sin(2 * np.pi * 150 * t)) + 0.7 * np.sign(np.sin(2 * np.pi * 157 * t))
    x = _bandpass(x, 120, 4500)
    return _stereo(_norm(x * _env(len(t), 0.004, None, 0.05), 0.6))


def engine_pass(dur=1.0):
    """Vehicle driving by: low rumble (60-450 Hz noise + 2-stroke-ish pulses), swell."""
    t = _t(dur)
    n = _bandpass(_noise(len(t), 11), 50, 450)
    pulse = 0.5 + 0.5 * np.sin(2 * np.pi * 28 * t)
    hiss = _bandpass(_noise(len(t), 12), 1500, 6000) * 0.15
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.8
    return _stereo(_norm((n * (0.6 + 0.4 * pulse) + hiss) * env, 0.8), width=1.0, seed=11)


def chirp_up(dur=0.35):
    """Rising chirps 1000 -> 2400 Hz (something flies towards the camera)."""
    t = _t(dur)
    f = 1000 + 1400 * (t / dur)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 14 * t)))
    return _stereo(_norm(x * _env(len(t), 0.005, None, 0.05), 0.6))


def drone_low(dur=1.5):
    """Sustained low tone ~250 Hz with slow wobble (tension / panic)."""
    t = _t(dur)
    f = 250 + 6 * np.sin(2 * np.pi * 5 * t)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.3 * np.sin(2 * np.pi * np.cumsum(2 * f) / SR)
    return _stereo(_norm(x * _env(len(t), 0.03, None, 0.1), 0.7))


def boing(dur=0.45):
    """Cartoon stretch 'boing': vibrato tone gliding up."""
    t = _t(dur)
    f = 300 + 500 * (t / dur) + 60 * np.sin(2 * np.pi * 18 * t)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(len(t), 0.003, 0.25, 0.05)
    return _stereo(_norm(x, 0.7))


def wasted(dur=1.6):
    """GTA-like 'wasted' sting: broadband noise burst + low boom, long tail."""
    t = _t(dur)
    burst = _bandpass(_noise(len(t), 13), 300, 9000) * np.exp(-t / 0.18)
    boom = np.sin(2 * np.pi * np.cumsum(300 - 120 * t / dur) / SR) * np.exp(-t / 0.8)
    return _stereo(_norm(burst * 0.8 + boom * 0.7, 0.9), width=1.0, seed=13)


def beep_reverse(dur=1.2):
    """Reversing beeper: three 1.1 kHz beeps."""
    t = _t(dur)
    gate = (np.mod(t, 0.4) < 0.2).astype(float)
    x = np.sin(2 * np.pi * 1100 * t) * gate
    return _stereo(_norm(_lowpass(x, 6000) * _env(len(t), 0.003, None, 0.02), 0.5))


def ev_hum(dur=1.4):
    """Synthetic e-car drive sound: two detuned saws gliding up an octave."""
    t = _t(dur)
    f = 180 * 2 ** (t / dur)
    ph = np.cumsum(f) / SR
    x = (np.mod(ph, 1) - 0.5) + 0.6 * (np.mod(ph * 1.503, 1) - 0.5)
    x = _lowpass(x, 900 + 1800 * t / dur)
    return _stereo(_norm(x * _env(len(t), 0.08, None, 0.3), 0.6), width=0.5, seed=21)


PRESETS = {
    "beep_reverse": beep_reverse,
    "ev_hum": ev_hum,
    "impact_low": impact_low,
    "swoosh": swoosh,
    "swoosh_down": lambda: swoosh(up=False, seed=7),
    "pop": pop,
    "magic_glide": magic_glide,
    "camera_flash": camera_flash,
    "tinnitus": tinnitus,
    "buzzer": buzzer,
    "engine_pass": engine_pass,
    "chirp_up": chirp_up,
    "drone_low": drone_low,
    "boing": boing,
    "wasted": wasted,
}


def write_wav(path, x, sr=SR):
    x = np.clip(x, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(x.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for name, fn in PRESETS.items():
        write_wav(os.path.join(out_dir, name + ".wav"), fn())
        print("wrote", name)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "sfx")
