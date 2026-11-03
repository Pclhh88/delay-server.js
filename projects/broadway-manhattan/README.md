# Referenz 3: „Why Broadway Splits Manhattan" (Karten-Doku-Stil)

Quelle: `references/Broadway-Manhattan.mp4` (720×1280, 30 fps, 78,3 s). Neuer Stil, siehe
`docs/STYLE_GUIDE.md` → „Zweiter Stil: Karten-Doku".

## Stand
* **Phase 1 Analyse: erledigt**
  * `analysis/SPRECHERTEXT.md` – Text mit Zeitmarken + Dramaturgie-Bauplan
  * `analysis/captions.json` – 90 Untertitel-Phrasen, framegenau (±2), inkl. kursiver Zitate
  * `analysis/timeline_analysis.json` – 22 Szenen: Hintergrund, Elemente, Kamera, Übergänge, SFX, Musikpausen
  * `analysis/transcript_asr_raw.json` – Whisper-Rohtranskript
* Phase 2 Rekonstruktion: offen (Plan unten)

## Plan Rekonstruktion
Jede Szenenart einmal genau, Wiederholungen nicht doppelt; Figuren/Requisiten als eigene
einfache Ersatzgrafiken (nicht aus dem Original geschnitten).

Freie Datenquellen (in dieser Umgebung erreichbar):
* Satellit: Sentinel-2 L2A (AWS `sentinel-cogs`, Kachel 18TWL) – Copernicus-Lizenz, Nennung nötig
* Straßen/Küste: Overture Maps (AWS, ODbL/OSM) – Nennung „© OpenStreetMap contributors"
* Relief: AWS Terrain Tiles (Terrarium, offen)

Neue Renderer-Bausteine: Karten-Kamera (große Karte + Zoom/Neigung), Neon-Pfadlinie mit
Zeichen-Animation, Raster-Einblendung, Flächen-Glow, Papier-Relief-Look, Crossfade-/Tinten-Übergang,
Phrasen-Untertitel (Roboto), Pop-Animation für Figuren.

## Neu erzeugen (nicht im Git)
```
ffmpeg -i references/Broadway-Manhattan.mp4 -map 0:v:0 projects/broadway-manhattan/analysis/frames/f%04d.png
```
