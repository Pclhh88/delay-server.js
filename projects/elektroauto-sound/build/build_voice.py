"""Voice track + word timings for "Elektroautos dürfen nicht leise sein".

ElevenLabs take 1 (speed 1.0, 82 s) -> pauses cut to <= 0.15 s, tempo x1.30,
pauses re-inserted after the punchlines, loudness -16 LUFS.
Writes ../audio/voice.flac and ../build/words.json (one entry per caption word).

    python3 projects/elektroauto-sound/build/build_voice.py
"""
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PROJ))
sys.path.insert(0, ROOT)
from shortsfactory.analysis.align import recognise_words, map_to_script  # noqa: E402

SR = 44100
TEMPO = 1.30
# extra silence (s) after these script words (index of the word's occurrence, pause)
PAUSES = {"sitzt.": 0.30, "Lärm.": 0.15, "Musik.": 0.10}
TAIL = 0.35        # silence after the last word ("denn ...") before the cut


def run(*cmd):
    subprocess.run(cmd, check=True)


def read_wav(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def main():
    tmp = os.path.join(HERE, "_voice_fast.wav")
    run("ffmpeg", "-v", "error", "-y", "-i", os.path.join(PROJ, "audio", "voice_take1.mp3"), "-af",
        f"silenceremove=stop_periods=-1:stop_duration=0.15:stop_threshold=-38dB,atempo={TEMPO}",
        "-ar", str(SR), "-ac", "1", tmp)
    script = open(os.path.join(HERE, "script.txt"), encoding="utf-8").read().split()
    words = map_to_script(recognise_words(tmp, os.path.join(ROOT, "models")), script)
    x = read_wav(tmp)
    os.remove(tmp)

    # the recogniser's word end runs up to the next word; the last word ends at the audio end
    words[-1]["end"] = min(words[-1]["end"], len(x) / SR)
    # insert pauses (cut points = start of the following word)
    pieces, shift, pos = [], 0.0, 0
    out_words = []
    for i, w in enumerate(words):
        w = dict(w, start=round(w["start"] + shift, 3), end=round(w["end"] + shift, 3))
        out_words.append(w)
        p = PAUSES.get(words[i]["text"])
        if p and i + 1 < len(words):
            cut = int(words[i + 1]["start"] * SR)
            pieces += [x[pos:cut], np.zeros(int(p * SR), np.float32)]
            pos = cut
            w["end"] = round(words[i + 1]["start"] + shift, 3)   # caption off during the pause
            w["pause_after"] = p
            shift += p
    pieces += [x[pos:], np.zeros(int(TAIL * SR), np.float32)]
    y = np.concatenate(pieces)

    raw = os.path.join(HERE, "_voice_join.wav")
    from shortsfactory.audio.sfx import write_wav
    write_wav(raw, np.stack([y, y], -1))
    run("ffmpeg", "-v", "error", "-y", "-i", raw, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", str(SR),
        "-ac", "1", os.path.join(PROJ, "audio", "voice.flac"))
    os.remove(raw)
    meta = {"duration": round(len(y) / SR, 3), "tempo": TEMPO, "source": "audio/voice_take1.mp3",
            "words": out_words}
    json.dump(meta, open(os.path.join(HERE, "words.json"), "w"), ensure_ascii=False, indent=1)
    print(f"voice {meta['duration']} s, {len(out_words)} words")


if __name__ == "__main__":
    main()
