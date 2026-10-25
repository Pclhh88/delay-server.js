"""Shorts-Pipeline: Stadt-Konfiguration -> fertiges MP4.

    python3 -m cityshorts.pipeline rome                  # alles (Vorschau-Qualität)
    python3 -m cityshorts.pipeline rome --quality final  # 1080x1920, mehr Samples
    python3 -m cityshorts.pipeline --all                 # alle Städte aus cities/index.json
    python3 -m cityshorts.pipeline rome --step plan      # nur Stimme + Zeitplan
    python3 -m cityshorts.pipeline rome --step render --frames 0:300
    python3 -m cityshorts.pipeline rome --step compose   # Frames + Untertitel + Ton -> MP4

Schritte: plan (Stimme, Timing) -> render (Blender) -> audio (Mix) -> compose (MP4).
Jeder Schritt schreibt nach build/<stadt>/ und kann einzeln wiederholt werden;
bereits gerenderte Frames werden übersprungen (Abbruch/Fortsetzen möglich).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

from . import audio, compose, voice

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LEAD_IN, GAP, TAIL = 0.45, 0.32, 1.6


def city_paths(cid):
    cdir = os.path.join(ROOT, "cities", cid)
    bdir = os.path.join(ROOT, "build", cid)
    os.makedirs(bdir, exist_ok=True)
    return cdir, bdir


def make_plan(cid, quality, fps=30):
    cdir, bdir = city_paths(cid)
    city = json.load(open(os.path.join(cdir, "city.json")))
    lo, hi = city.get("target_duration", [60, 70])
    rate = city.get("voice", {}).get("rate", 165)
    for attempt in range(4):
        vs = voice.synthesize(city, cdir, os.path.join(bdir, "voice"), rate)
        total = LEAD_IN + sum(v["speech"][1] - v["speech"][0] + GAP for v in vs) + TAIL
        print(f"[plan] Sprechtempo {rate}: Länge {total:.1f}s (Ziel {lo}-{hi}s)")
        if city.get("voice", {}).get("backend", "espeak") != "espeak" or lo <= total <= hi:
            break
        rate = int(rate * total / (hi - 1.5 if total > hi else lo + 1.5))
    beats, t = [], LEAD_IN
    for b, v in zip(city["beats"], vs):
        s0, s1 = v["speech"]
        b = dict(b)
        b.update({"voice_wav": v["wav"], "voice_start": t - s0, "t0": t if beats else 0.0,
                  "t1": t + (s1 - s0) + GAP, "words": voice.word_times(b["text"], t, t + (s1 - s0))})
        beats.append(b)
        t = b["t1"]
    beats[-1]["t1"] += TAIL
    duration = beats[-1]["t1"]
    plan = {"city": city, "fps": fps, "duration": round(duration, 3), "n_frames": int(duration * fps),
            "quality": quality, "beats": beats, "out_dir": bdir, "transition": 0.8,
            "title": {"text": city["name"].upper(), "sub": city.get("subtitle", "in Miniatur"), "start": 0.15,
                      "end": min(3.2, beats[0]["t1"])}}
    json.dump(plan, open(os.path.join(bdir, "plan.json"), "w"), indent=1, ensure_ascii=False)
    print(f"[plan] {len(beats)} Abschnitte, {duration:.1f}s, {plan['n_frames']} Frames -> {bdir}/plan.json")
    return plan


def blender_cmd(script, args):
    """Blender-Programm (Umgebungsvariable BLENDER) oder Python mit bpy-Modul (BPY_PYTHON)."""
    if os.environ.get("BLENDER"):
        return [os.environ["BLENDER"], "-b", "--python", script, "--"] + args
    py = os.environ.get("BPY_PYTHON") or ("/opt/cityvenv/bin/python" if os.path.exists("/opt/cityvenv/bin/python")
                                         else shutil.which("python3"))
    return [py, script] + args


def render(cid, quality, frames=None, step=1):
    _, bdir = city_paths(cid)
    args = [os.path.join(bdir, "plan.json"), "--quality", quality, "--step", str(step)]
    if frames:
        args += ["--frames", frames]
    cmd = blender_cmd(os.path.join(ROOT, "cityshorts", "blender", "render_city.py"), args)
    print("[render]", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("city", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--quality", default="preview", choices=["draft", "preview", "final"])
    ap.add_argument("--step", default="all", choices=["all", "plan", "render", "audio", "compose"])
    ap.add_argument("--frames")
    ap.add_argument("--every", type=int, default=1, help="nur jeden N-ten Frame rendern (Schnellvorschau)")
    a = ap.parse_args(argv)
    cities = json.load(open(os.path.join(ROOT, "cities", "index.json")))["cities"] if a.all else [a.city]
    for cid in cities:
        _, bdir = city_paths(cid)
        if a.step in ("all", "plan"):
            plan = make_plan(cid, a.quality)
        else:
            plan = json.load(open(os.path.join(bdir, "plan.json")))
        if a.step in ("all", "render"):
            render(cid, a.quality, a.frames, a.every)
        wav = os.path.join(bdir, "mix.wav")
        if a.step in ("all", "audio", "compose"):
            audio.mix(plan, wav)
            print("[audio]", wav)
        if a.step in ("all", "compose"):
            out = os.path.join(bdir, f"{cid}_{a.quality}.mp4")
            compose.compose(plan, os.path.join(bdir, "frames_" + a.quality), wav, out)
            print("[fertig]", out)


if __name__ == "__main__":
    sys.exit(main())
