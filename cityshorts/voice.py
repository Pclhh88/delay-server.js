"""Sprecherstimme pro Abschnitt (beat) + geschätzte Wort-Zeitstempel.

Backends (city.json -> "voice": {"backend": ...}):
  espeak      kostenlos, offline, klingt robotisch – PLATZHALTER (Standard)
  files       eigene Aufnahmen: cities/<id>/voice/<beat_id>.wav (beste Qualität, kostenlos)
  elevenlabs  TTS-Dienst, kostenpflichtig, braucht ELEVENLABS_API_KEY (+ voice_id)

Wort-Zeitstempel werden aus der Silbenzahl innerhalb der hörbaren Sprechdauer
geschätzt. Für eigene Aufnahmen oder ElevenLabs ist das gut genug für
Untertitel; framegenau ginge es mit ASR (siehe shortsfactory/analysis).
"""
import json
import os
import re
import subprocess
import urllib.request

import numpy as np

SR = 44100


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def speech_span(x, thresh_db=-38):
    """Start/Ende der hörbaren Sprache (Sekunden)."""
    win = int(0.02 * SR)
    n = len(x) // win
    if n == 0:
        return 0.0, len(x) / SR
    rms = np.sqrt((x[:n * win].reshape(n, win) ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms / (rms.max() + 1e-12))
    on = np.where(db > thresh_db)[0]
    if len(on) == 0:
        return 0.0, len(x) / SR
    return on[0] * win / SR, (on[-1] + 1) * win / SR


def tts_text(text):
    """Untertiteltext -> sprechbarer Text (Zahlen mit Punkt: 50.000 -> 50000)."""
    return re.sub(r"(\d)\.(\d{3})", r"\1\2", text)


def synth_espeak(text, out, cfg, rate):
    voice = cfg.get("voice", "mb-de6")
    cmd = ["espeak-ng", "-v", voice, "-s", str(int(rate)), "-p", str(cfg.get("pitch", 45)), "-w", out, tts_text(text)]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0 or not os.path.exists(out) or os.path.getsize(out) < 1000:
        cmd[2] = "de"  # MBROLA-Stimme fehlt -> Standardstimme
        subprocess.run(cmd, check=True, capture_output=True)


def synth_elevenlabs(text, out, cfg, rate):
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise SystemExit("ELEVENLABS_API_KEY fehlt (kostenpflichtiger Dienst, siehe README).")
    vid = cfg.get("voice_id") or os.environ.get("ELEVENLABS_VOICE_ID")
    body = json.dumps({"text": tts_text(text), "model_id": cfg.get("model_id", "eleven_multilingual_v2"),
                       "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35,
                                          "speed": rate / cfg.get("rate", 165)}}).encode()
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=mp3_44100_128",
                                 data=body, headers={"xi-api-key": key, "Content-Type": "application/json"})
    mp3 = out[:-4] + ".mp3"
    with urllib.request.urlopen(req, timeout=120) as r, open(mp3, "wb") as f:
        f.write(r.read())
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", mp3, out], check=True)


def synth_files(text, out, cfg, rate, beat_id=None, city_dir=None):
    src = os.path.join(city_dir, "voice", beat_id + ".wav")
    if not os.path.exists(src):
        raise SystemExit(f"Aufnahme fehlt: {src}")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-ac", "1", "-ar", str(SR), out], check=True)


def syllables(word):
    return max(1, len(re.findall(r"[aeiouyäöü]+", word.lower())) + (2 * len(re.findall(r"\d", word))))


def word_times(text, t0, t1):
    words = text.split()
    w = [syllables(x) + (1.2 if x[-1] in ".,:?!" else 0) for x in words]  # Pausen an Satzzeichen
    tot = sum(w)
    out, t = [], t0
    for word, k in zip(words, w):
        d = (t1 - t0) * k / tot
        out.append({"text": word, "start": round(t, 3), "end": round(t + d, 3)})
        t += d
    return out


def synthesize(city, city_dir, out_dir, rate=None):
    """-> [{"id", "wav", "dur", "speech": [s0, s1]}] pro Beat."""
    cfg = city.get("voice", {})
    backend = cfg.get("backend", "espeak")
    rate = rate or cfg.get("rate", 165)
    os.makedirs(out_dir, exist_ok=True)
    res = []
    for b in city["beats"]:
        out = os.path.join(out_dir, b["id"] + ".wav")
        if backend == "espeak":
            synth_espeak(b["text"], out, cfg, rate)
        elif backend == "elevenlabs":
            synth_elevenlabs(b["text"], out, cfg, rate)
        elif backend == "files":
            synth_files(b["text"], out, cfg, rate, b["id"], city_dir)
        else:
            raise SystemExit("unbekanntes voice-backend " + backend)
        x = load(out)
        s0, s1 = speech_span(x)
        res.append({"id": b["id"], "wav": out, "dur": len(x) / SR, "speech": [s0, s1]})
    return res
