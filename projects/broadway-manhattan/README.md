# Referenz 3: „Why Broadway Splits Manhattan" (Karten-Doku-Stil)

Quelle: `references/Broadway-Manhattan.mp4` (720×1280, 30 fps, 78,3 s). Neuer Stil, siehe
`docs/STYLE_GUIDE.md` → „Zweiter Stil: Karten-Doku".

## Stand
* **Phase 1 Analyse: erledigt**
  * `analysis/SPRECHERTEXT.md` – Text mit Zeitmarken + Dramaturgie-Bauplan
  * `analysis/captions.json` – 90 Untertitel-Phrasen, framegenau (±2), inkl. kursiver Zitate
  * `analysis/timeline_analysis.json` – 22 Szenen: Hintergrund, Elemente, Kamera, Übergänge, SFX, Musikpausen
  * `analysis/transcript_asr_raw.json` – Whisper-Rohtranskript
* **Phase 2 Rekonstruktion: erledigt (ganzes Video, 0–78,3 s)**, Phase 3 Abgleich: erledigt (Standbilder, siehe unten)
  * `reconstruction/build_maps.py` – Karten aus freien Daten → `assets/maps/`
  * `reconstruction/track_camera.py` – Kamerafahrt des Originals vermessen → `analysis/camera_track*.json`
    (SIFT auf Atlas, Fehler < 1 px; Lücken: Verkettung Bild-zu-Bild)
  * `reconstruction/refine_camera.py` – Versuch, Nahaufnahmen per Render-Abgleich zu verfeinern (bei 10-m-Satellit erfolglos)
  * `reconstruction/build_timeline.py` – Grafiken (`assets/gen/`) + `reconstruction/timeline.json`
  * Rendern:
    ```
    python3 projects/broadway-manhattan/reconstruction/build_timeline.py
    python3 -m shortsfactory.audio.mix projects/broadway-manhattan/reconstruction/timeline.json projects/broadway-manhattan/output/mix.wav
    python3 -m shortsfactory.render projects/broadway-manhattan/reconstruction/timeline.json projects/broadway-manhattan/output/broadway.mp4 --audio projects/broadway-manhattan/output/mix.wav
    ```

## Bekannte Abweichungen vom Original
* Satellit nur 10 m/px (Sentinel-2): Nahaufnahmen (0–0,5 s, 68–73 s) unschärfer als im Original.
* 68,3–73,2 s: Kamera nur ungefähr (Verkettung driftet, Zoom von Hand korrigiert).
* 13,8–16,6 s (Überblendung Satellit→Papier) und 34,5–38 s (Zoom aufs Schild): Kamera interpoliert.
* Figuren/Requisiten: eigene, einfachere Comic-Grafiken (Platzhalter-Qualität), Fotokarten am Ende
  aus dem Satellitenbild statt echter Fotos, „Commissioners' Map" aus echten Straßendaten nachgezeichnet.
* Stimme = getrennte Originalstimme (Referenz-Platzhalter, nicht veröffentlichen), Musik = eigenes Musikbett.

## Vorgehen Rekonstruktion
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
