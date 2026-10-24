# Short „Elektroautos dürfen nicht leise sein"

Erstes neues Video im Stil der Referenz (`references/Bundeswehr-Kennzeichen.mp4`), gebaut mit
denselben Bausteinen wie die Rekonstruktion: Streifen-Hintergrund, Ein-Wort-Untertitel und
Stilwerte aus `projects/bundeswehr-kennzeichen/analysis/style_measurements.json`, Pop-ins mit
gemessenem Überschwinger, Punch-Zooms, roter Blockpfeil, roter Flash + Buzzer bei Verneinungen,
[Qn]-Labels, vertikale Credit-Zeile.

| Datei | Inhalt |
|---|---|
| `output/elektroauto_1080.mp4` | fertiges Video, 1080×1920, 30 fps, 61,4 s |
| `SKRIPT.md` | Sprechertext, Bildideen, Faktencheck, Quellen |
| `audio/voice_take1.mp3` | ElevenLabs-Take 1 („Ed – Sarcastic Funny Narrator", Speed 1,0, 82 s) |
| `audio/voice.flac` | daraus: Pausen gekürzt, Tempo ×1,30, Pausen nach Pointen, −16 LUFS |
| `build/words.json` | jedes gesprochene Wort mit Start/Ende (Parakeet-TDT-Alignment) |
| `build/timeline.json` | Szenen/Layer/Keyframes/Audio |
| `assets/` | Grafiken (`png/`), Quellen (`src/`), `manifest.json` mit Lizenz je Asset |

## Bauen

```bash
tools/setup_models.sh   # + Parakeet-Modell, siehe unten
python3 projects/elektroauto-sound/build/build_voice.py      # Stimme + Wort-Zeitmarken
python3 projects/elektroauto-sound/build/build_assets.py     # Grafiken (Chromium/Playwright)
python3 projects/elektroauto-sound/build/build_timeline.py   # timeline.json
P=projects/elektroauto-sound
python3 -m shortsfactory.audio.mix $P/build/timeline.json $P/output/mix.wav
python3 -m shortsfactory.render $P/build/timeline.json $P/output/elektroauto_1080.mp4 \
        --audio $P/output/mix.wav --publish
```

Wort-Alignment: `shortsfactory/analysis/align.py` braucht
`models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8` (GitHub-Release `asr-models` von k2-fsa/sherpa-onnx).
Alle Bild-Ereignisse hängen an Wortanfängen (`W("Wort", n)` in `build_timeline.py`) – ein neuer
Stimm-Take braucht also nur `build_voice.py` + `build_timeline.py`.

## Rechte

* Grafiken: Microsoft Fluent Emoji (MIT, Lizenztext in `assets/src/`) und eigene SVG-Grafiken.
  Keine Fotos, keine Marken-Logos (BMW nur gesprochen), kein Bild von Hans Zimmer.
* Stimme: ElevenLabs – Nutzungsrechte hängen am ElevenLabs-Tarif des Nutzers (kommerzielle
  Nutzung erst ab bezahltem Plan).
* Soundeffekte: selbst synthetisiert (`shortsfactory/audio/sfx.py`).
* `--publish` beim Rendern: keine Referenz-Platzhalter enthalten.

## Offen

* Satz 7 (Musik/Naturgeräusche unzulässig) und Satz 9 (Hybride) sind noch nicht am
  Verordnungstext geprüft (siehe Faktencheck in `SKRIPT.md`).
