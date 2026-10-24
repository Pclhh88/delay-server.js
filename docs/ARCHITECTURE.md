# Shorts-Factory – Architektur

Ziel: ein Produktionssystem für YouTube Shorts im Stil des Referenzvideos
`references/Bundeswehr-Kennzeichen.mp4`. Zuerst wird das Referenzvideo
rekonstruiert (Stand: **komplett, 0–50,5 s**), danach wird daraus ein Template
abgeleitet (Phase 4) und ein Themen-Workflow gebaut (Phase 5).

```
references/                         Referenzvideo(s)
shortsfactory/                      wiederverwendbarer Code
  render/engine.py                  Timeline-JSON -> Frames -> MP4 (Layer, Gruppen, Kamera, Blend-Modes)
  render/keyframes.py               Keyframe-Interpolation + Easings
  render/shapes.py                  prozedurale Layer: stripes_bg, radial_bg, solid, arrow, glow, light_cone, polygon, text, grade
                                    (+ engine: image, sequence = animierte Bildfolge, group mit clip/isolate)
  render/text.py                    Wort-für-Wort-Untertitel + Textlayer (League Spartan, OFL)
  audio/sfx.py                      selbst synthetisierte Soundeffekte (keine Fremd-Samples)
  audio/mix.py                      Audio-Mix aus timeline["audio"]
  analysis/proxy_tools.py           Messwerkzeuge: SIFT-Kamera-Tracking, Sprite-Tracking (maskierte SSD),
                                    Mosaik aus Zoomstufen, Freistellen, Untertitel-Masken, Pfeil-Tracking
  analysis/compare.py               Render vs. Original: Metriken, Schnitterkennung, Vergleichsbilder
  fonts/                            League Spartan (SIL OFL)
projects/bundeswehr-kennzeichen/
  analysis/                         Phase 1: Messdaten
    timeline_analysis.json          Szenen, Bildelemente, Bewegungen, Gags, SFX (maschinenlesbar)
    captions.json                   jedes eingeblendete Wort mit Start/Ende (framegenau)
    transcript_asr_raw.json         Whisper-Transkript (Rohfassung, enthält Erkennungsfehler)
    style_measurements.json         gemessene Stilparameter (Hintergrund, Untertitel, Labels, Flash ...)
  reconstruction/
    build_proxies.py                baut Assets + Messungen (measurements.json) aus den Referenzframes
    build_timeline.py               baut timeline.json aus den Messungen
    timeline.json                   die Rekonstruktion als steuerbare Szenen/Layer/Keyframes/Audio
  assets/manifest.json              jedes Asset mit Herkunft + Lizenzstatus + Ersatz-Hinweis
  assets/proxies/                   aus dem Referenzvideo geschnittene Platzhalter (NICHT veröffentlichen)
  audio/voice_reference_proxy.flac  per KI getrennte Sprecherspur des Originals (NICHT veröffentlichen)
  output/                           Renderings + Vergleichsbilder
```

## Datenfluss

1. `ffmpeg` → Frames (`analysis/frames/`, nicht im Git).
2. `build_proxies.py` misst (Kamera, Sprites, Pfeile, Flashes, Tönung …) und
   schneidet Platzhalter-Assets aus. Alle Messwerte landen in `measurements.json`.
3. `build_timeline.py` übersetzt Messwerte in Layer + Keyframes (`timeline.json`).
4. `python3 -m shortsfactory.audio.mix timeline.json mix.wav` mischt Stimme + SFX.
5. `python3 -m shortsfactory.render timeline.json out.mp4 --audio mix.wav` rendert.
6. `python3 -m shortsfactory.analysis.compare ref.mp4 out.mp4 dir` vergleicht.

## Timeline-Format (Kurzfassung)

```json
{
  "meta": {"fps": 30, "width": 1080, "height": 1920, "duration": 20.0},
  "assets": {"id": {"path": "...", "design_scale": 2.25, "license": "..."}},
  "layers": [ {"id": "...", "type": "image|group|solid|arrow|glow|stripes_bg|...",
               "start": 0.0, "end": 2.8, "blend": "normal|screen|add|multiply",
               "keys": [{"t": 0.0, "x": 540, "y": 960, "scale": 1, "rot": 0, "opacity": 1,
                         "ease": "linear|out|inout|out3|back_out|hold"}]} ],
  "captions": {"style": {...}, "words": [{"text": "NICHT.", "start": 2.367, "end": 2.733, "size": "big"}]},
  "audio": [{"src": "@sfx/buzzer", "start": 14.87, "gain_db": -12}]
}
```

* Koordinaten sind Design-Einheiten auf 1080×1920; die Ausgabeauflösung ist frei.
* Gruppen sind „Kameras": ihre Keys transformieren alle Kinder (Zooms, Schwenks).
* `image` kann `reveal_map` + Key `reveal` nutzen (Pinsel-/Übermal-Effekt), Key `tint`
  färbt (z. B. Jeep wird buschgrün).
* Untertitel liegen über allen Layern (wie im Original).

## Rechte / Assets

`assets/manifest.json` führt für jedes Asset `license`:

* `reference_proxy` – aus dem Referenzvideo geschnitten. Nur für den 1:1-Abgleich.
  `python3 -m shortsfactory.render … --publish` verweigert solche Assets.
* `derived_measurement` – Messdaten (z. B. Lichtkarte, Reveal-Karte), kein Bildinhalt Dritter.
* Selbst erzeugt: Hintergrund, Pfeile, Flashes, Glow, Logo-Platzhalter, alle Soundeffekte, Untertitel.

Das Senderlogo des Originals wird bewusst **nicht** nachgebaut (neutraler Platzhalter mit
identischem Timing). Memes (Drake, Bob-Ross-Rage-Comic, Minecraft-Figur, Katze) und Fotos
müssen für eine Veröffentlichung durch lizenzierte oder eigene Assets ersetzt werden –
der jeweilige Ersatz steht im Manifest unter `replace_with`.

## Benötigte Werkzeuge

Python 3 mit `numpy`, `opencv-python-headless`, `pillow`; `ffmpeg`.
Nur für die Analyse: `sherpa-onnx` (Whisper-ASR, Silero-VAD, UVR-Stimmtrennung);
Modelle über `tools/setup_models.sh` (GitHub-Releases von k2-fsa/sherpa-onnx).
