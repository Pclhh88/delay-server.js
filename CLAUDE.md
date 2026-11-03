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
* Referenz 3 `references/Broadway-Manhattan.mp4` = **zweiter Stil (Karten-Doku)**, Nutzer will
  diesen Stil als Template. Phasen 1–3 erledigt (ganzes Video): `projects/broadway-manhattan/README.md`
  (Pipeline, bekannte Abweichungen). Neue Bausteine: `shortsfactory/render/maplayer.py` (Karten-Ebene),
  `shortsfactory/geo/` (freie Kartendaten), `shortsfactory/assets_gen/figures.py`, `analysis/map_track.py`.
  Erstes eigenes Video im Karten-Stil: `projects/bodensee/` („Der See, der niemandem gehört", Stimme vom
  Nutzer per ElevenLabs, Loop-Ende). Nutzer-Feedback: Linien einzeln zeichnen, bessere Animationen,
  Figuren ggf. vom Nutzer geliefert; Themen brauchen starken Hook.
* Code: `shortsfactory/` (Renderer, Audio, Analyse-Tools). Doku: `docs/ARCHITECTURE.md`,
  Stilregeln: `docs/STYLE_GUIDE.md`.
* 17 Bild-Assets + Stimme sind Referenz-Platzhalter (aus dem Original geschnitten),
  nicht veröffentlichen – siehe `projects/bundeswehr-kennzeichen/assets/manifest.json`.

## Offene Entscheidungen (beim Nutzer nachfragen)
* Nächster Schritt: Template herauslösen (Phase 4) und Themen-Workflow (Phase 5).
* Stimme: Nutzer vertont selbst (ElevenLabs) und schickt MP3 – Skript daher ohne Regiezeichen liefern.
* Bildquellen: freie Fotos / eigene Grafiken; bekannte Memes (Drake, Minecraft) rechtlich heikel.

## Nicht im Git (bei Bedarf neu erzeugen)
* Referenzframes: `ffmpeg -i references/Bundeswehr-Kennzeichen.mp4 -map 0:v:0 projects/bundeswehr-kennzeichen/analysis/frames/f%04d.png`
* Analyse-Modelle (ASR, Stimmtrennung): `tools/setup_models.sh` (+ `pip install sherpa-onnx opencv-python-headless`)
* Netz: HuggingFace, Wikimedia, OSM-Tiles, NASA GIBS gesperrt; GitHub, PyPI, npm und AWS S3
  (Sentinel-2 `sentinel-cogs`, Overture Maps, Terrain Tiles) gehen.
