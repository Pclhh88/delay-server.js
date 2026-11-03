# „Der See, der niemandem gehört" (Bodensee) – erstes eigenes Video im Stil map_doc

* Skript: `SKRIPT.md` (Endfassung = Aufnahme; Zitate im Dialekt, Deutschland Hochdeutsch; Loop: letzter Satz führt in den ersten)
* Stimme: `audio/voice.mp3` (Aufnahme des Nutzers, ElevenLabs), 73,9 s
* Karten: `build_maps.py` → `assets/maps/` (Sentinel-2-Mosaik 10 m + 40 m, Europa/Region aus Höhendaten eingefärbt,
  Papier-Relief, Vektoren: See, Ufer je Land, Grenze Untersee aus OSM, Mittellinie Obersee von Hand, Europa-Grenzen)
* Timeline: `build_timeline.py` → `build/timeline.json` (Szenen nach den Sprachsegmenten, Untertitel aus Skript-Phrasen
  + ASR-Zeiten, eigene Figuren/Symbole in `assets/gen/`)
* Rendern:
  ```
  python3 projects/bodensee/build_timeline.py
  python3 -m shortsfactory.audio.mix projects/bodensee/build/timeline.json projects/bodensee/build/mix.wav
  python3 -m shortsfactory.render projects/bodensee/build/timeline.json projects/bodensee/build/bodensee.mp4 --audio projects/bodensee/build/mix.wav
  ```
* Ergebnis: `output/bodensee.mp4`

## Offen / Platzhalter
* Figuren (Schweizer, Österreicher, Beamter) und Symbole sind einfache eigene Grafiken – Nutzer will ggf. eigene Modelle liefern.
* Fakten vor Veröffentlichung prüfen (siehe `SKRIPT.md`, Abschnitt „Vor der Veröffentlichung prüfen").
* Quellenangaben für die Beschreibung: Copernicus Sentinel data 2024/2025; © OpenStreetMap contributors, Overture Maps Foundation;
  AWS Terrain Tiles.
