# Paris-Diorama (Blender)

Ziel: Das Referenzbild `reference/reference.png` (Miniatur-Paris mit Eiffelturm) als **echte, vollständig
dreidimensionale Blender-Szene** nachbauen – jedes Haus, jeder Baum, jedes Auto ein eigenes, später
animierbares Objekt. Keine Bildprojektion, keine KI-Standbilder.

* **Exakte Rekonstruktion (aktuell):** Bildanalyse + Blockout: [analysis/REKONSTRUKTION_EXAKT.md](analysis/REKONSTRUKTION_EXAKT.md)
  `blender/measurements.py` (Bildmessungen → 3D-Maße), `blender/blockout.py` → `blockout.blend`, `renders/blockout.png`
* Erste stilistische Version v1 (überholt): [analysis/ANALYSE.md](analysis/ANALYSE.md)
* Ergebnis v1: `renders/render_v1.png`, Vergleich: `renders/compare_v1_*.png`
* Blender-Datei: `paris_diorama.blend` (Blender 5.2, Cycles)

## Szene neu bauen / rendern

```bash
python3 -m venv ~/bvenv && ~/bvenv/bin/pip install bpy==5.2.3 numpy pillow scipy
~/bvenv/bin/python blender/build_scene.py --res 2048 --samples 128 --out renders/render_v1.png
# oder mit installiertem Blender:
blender -b -P blender/build_scene.py -- --res 2048 --samples 128
```

Werkzeuge:
* `blender/fit_camera.py` – Kamera an Bild-Ankerpunkte fitten → `blender/camera.json`
* `blender/overlay_layout.py out.png` – Grundrisse als Drahtgitter über der Vorlage (schneller Abgleich)
* `blender/compare.py ref.png render.png out.png` – Nebeneinander / Überblendung / Kanten

## Aufbau der Szene (Collections)
| Collection | Inhalt |
|---|---|
| Buildings | 7 Haussmann-Häuser, je ein Objekt (Ursprung = Bodenmitte), echte Fensterlaibungen, Balkone, Gauben, Kamine |
| Tower | Eiffelturm aus ~2 500 Einzelstäben |
| Trees | Bäume (rund, dunkel, hoch, Herbst, Blüte), Büsche, Hecken |
| Vehicles | 5 Fahrzeuge |
| Street | Sockelplatte, Ringstraße, Markierungen, Gehweg/Block, Rasen |
| Props | Laternen, Poller, Kuppeltürmchen, Dachpavillon, Dachtechnik, Hofbau |
| Light_Camera | Sonne, Aufhelllicht, Studio-Boden, kalibrierte Kamera |

Alle Gebäude sind über `Building(...)` in `blender/layout.py` parametriert (Grundriss, Geschosse,
Geschosshöhen, Dachform, Fensterraster, Balkone, Fensterläden, Erker …) und damit für neue Szenen
wiederverwendbar.

Hinweis: Die Vorlage (`reference/reference.png`) trägt Freepik-Wasserzeichen und ist nur interne Referenz –
sie ist nicht im Git. Zum Abgleich das Originalbild (2732×2048) links/rechts auf 2048×2048 zuschneiden
(x = 342…2389) und dort ablegen.
