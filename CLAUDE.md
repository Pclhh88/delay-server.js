# Übergabe für neue Sitzungen

Sprache mit dem Nutzer: Deutsch.

## Ziel
Wiederverwendbares Produktionssystem für YouTube Shorts im Stil von
`references/Bundeswehr-Kennzeichen.mp4` (nicht nur ein einzelnes Video).
Phasen: 1 Analyse → 2 Rekonstruktion → 3 Abgleich → 4 Template → 5 „Neues Video über: …".

## Stand
* Phasen 1–3 **komplett erledigt** (ganzes Video, 0–50,5 s), siehe
  `projects/bundeswehr-kennzeichen/README.md`. Nicht neu nachbauen.
* Messungen/Assets: `reconstruction/build_proxies.py` (0–20 s), `build_part2.py` (20–40 s),
  `build_part3.py` (40–50,5 s); Timeline: `build_timeline.py` + `timeline_part2.py` +
  `timeline_part3.py` → `timeline.json`.
* Sprechertext + Tonfall/Bauplan für neue Skripte:
  `projects/bundeswehr-kennzeichen/analysis/SPRECHERTEXT.md`.
* Referenz 2 `references/Burj-Khalifa.mp4` ausgewertet (nicht nachgebaut):
  `projects/burj-khalifa/analysis/` (Sprechertext, Untertitel). Vergleich beider Videos =
  feste Stilregeln: Abschnitt „Abgleich mit Referenz 2" in `docs/STYLE_GUIDE.md`.
* Code: `shortsfactory/` (Renderer, Audio, Analyse-Tools). Doku: `docs/ARCHITECTURE.md`,
  Stilregeln: `docs/STYLE_GUIDE.md`.
* 17 Bild-Assets + Stimme sind Referenz-Platzhalter (aus dem Original geschnitten),
  nicht veröffentlichen – siehe `projects/bundeswehr-kennzeichen/assets/manifest.json`.

## Neues Format: Städte-Highlights (isometrische 3D-Stadt)
* Idee des Nutzers: 60-s-Shorts „Highlights einer Stadt“, Stadt im Stil einer isometrischen
  Illustration (bunte Häuser mit Details), echte Kartendaten. Erstes Projekt: Flensburg.
* Pipeline: `shortsfactory/geo/overture.py` (Overture Maps = OSM-Daten via S3; OSM selbst ist
  gesperrt) → `shortsfactory/geo/scene.py` (scene.json) → `shortsfactory/city/render.js`
  (three.js in headless Chromium, Detail-Fassaden in `detail.js`, Detailzonen per shot.json)
  → Frames → Timeline (`projects/flensburg-highlights/test/build_timeline.py`) → Engine.
* Stand: 12-s-Test (Überblick → Nordertor). Nutzer wünscht liebevolle Häuser wie im Beispiel
  (Fenster, Markisen, Balkone, Pflanzen …) – umgesetzt, Feedback steht aus.
* Pflicht bei Veröffentlichung: „© OpenStreetMap-Mitwirkende“.

## Offene Entscheidungen (beim Nutzer nachfragen)
* Nächster Schritt: Template herauslösen (Phase 4) und Themen-Workflow (Phase 5).
* Stimme für neue Themen: eigene Aufnahme des Nutzers oder TTS-Dienst (hier keiner eingerichtet).
* Bildquellen: freie Fotos / eigene Grafiken; bekannte Memes (Drake, Minecraft) rechtlich heikel.

## Nicht im Git (bei Bedarf neu erzeugen)
* Referenzframes: `ffmpeg -i references/Bundeswehr-Kennzeichen.mp4 -map 0:v:0 projects/bundeswehr-kennzeichen/analysis/frames/f%04d.png`
* Analyse-Modelle (ASR, Stimmtrennung): `tools/setup_models.sh` (+ `pip install sherpa-onnx opencv-python-headless`)
* Netz: HuggingFace und Wikimedia waren in der Umgebung gesperrt; GitHub, PyPI und npm gehen.
