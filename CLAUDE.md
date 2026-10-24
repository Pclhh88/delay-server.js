# Übergabe für neue Sitzungen

Sprache mit dem Nutzer: Deutsch.

## Ziel
Wiederverwendbares Produktionssystem für YouTube Shorts im Stil von
`references/Bundeswehr-Kennzeichen.mp4` (nicht nur ein einzelnes Video).
Phasen: 1 Analyse → 2 Rekonstruktion → 3 Abgleich → 4 Template → 5 „Neues Video über: …".

## Stand
* Phasen 1–3 für **0–40 s erledigt** (0–20 s vom Nutzer gut befunden), siehe
  `projects/bundeswehr-kennzeichen/README.md`. Nicht neu nachbauen. Offen: 40–50,5 s.
* Messungen/Assets: `reconstruction/build_proxies.py` (0–20 s), `build_part2.py` (20–40 s);
  Timeline: `build_timeline.py` + `timeline_part2.py` → `timeline.json`.
* Code: `shortsfactory/` (Renderer, Audio, Analyse-Tools). Doku: `docs/ARCHITECTURE.md`,
  Stilregeln: `docs/STYLE_GUIDE.md`.
* 17 Bild-Assets + Stimme sind Referenz-Platzhalter (aus dem Original geschnitten),
  nicht veröffentlichen – siehe `projects/bundeswehr-kennzeichen/assets/manifest.json`.

## Offene Entscheidungen (beim Nutzer nachfragen)
* Nächster Schritt: 40–50,5 s nachbauen, dann Template herauslösen (Phase 4) und
  Themen-Workflow (Phase 5).
* Stimme für neue Themen: eigene Aufnahme des Nutzers oder TTS-Dienst (hier keiner eingerichtet).
* Bildquellen: freie Fotos / eigene Grafiken; bekannte Memes (Drake, Minecraft) rechtlich heikel.

## Nicht im Git (bei Bedarf neu erzeugen)
* Referenzframes: `ffmpeg -i references/Bundeswehr-Kennzeichen.mp4 -map 0:v:0 projects/bundeswehr-kennzeichen/analysis/frames/f%04d.png`
* Analyse-Modelle (ASR, Stimmtrennung): `tools/setup_models.sh` (+ `pip install sherpa-onnx opencv-python-headless`)
* Netz: HuggingFace und Wikimedia waren in der Umgebung gesperrt; GitHub, PyPI und npm gehen.
