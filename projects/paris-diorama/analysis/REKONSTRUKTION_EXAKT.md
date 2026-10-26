# Exakte Rekonstruktion – Schritt 1 (Bildanalyse) und Schritt 2 (Blockout)

Ziel: dieses eine Bild möglichst deckungsgleich nachbauen, ohne freie Interpretation.
Methode: jede Maßzahl ist ein abgelesener Bildpunkt (Zoom-Ausschnitte mit 10-px-Raster,
`blender/measure_crop.py`). Daraus werden mit der kalibrierten Kamera die 3D-Maße zurückgerechnet
(`blender/measurements.py`), dann wird ein Blockout gebaut (`blender/blockout.py`) und über die
Vorlage gelegt (`blender/compare_blockout.py`).

## 1. Bildanalyse

### Kamera
| Befund | Messung | Folgerung |
|---|---|---|
| Senkrechte bleiben senkrecht | linke Hauskante bei x=350 px von y=1000 bis 1200: Abweichung < 2 px | Bildebene senkrecht (Shift-/Architekturkamera) |
| Horizontale werden nach oben flacher | Kanten parallel zur linken Plattformkante: Steigung 0,53 unten, 0,41 an den Traufen oben | echte Perspektive, keine Orthografie |
| Fit (`fit_camera.py`) | Plattform-Oberkanten, 3 Extrempunkte der Eckrundungen, 11 Trauf-/Dachkanten | **150 mm KB, Shift Y 1,99, Azimut −47,3°**; Restfehler Plattform 6,1 px, Kanten 3,3 px RMS |

Die vorige Version (v1) nutzte 120 mm ohne Shift; die Plattform passte, die oberen Bildteile wichen
deshalb systematisch ab (Häuser wirkten verdreht und zu hoch).

### Plattform & Straßenquerschnitt (Helligkeitsprofile bei x=560 und x=1560)
Plattform 24 × 24, Eckradius **5,3** (gefittet). Querschnitt von außen: Randkante 0–0,55 ·
Fahrbahn 0,55–2,35 (weiße Randlinie bei 0,75) · Bordstein 2,35–2,5 · Gehweg 2,5 bis zur Häuserflucht (≈ 4,3).

### Gebäudemassen (aus Bildpunkten zurückgerechnet)
Vordere Ecke, sichtbare Fassadenlängen, Drehung und Traufhöhe (über Block), Einheiten = Plattform/24:

| Gebäude | vordere Ecke (x, y) | Länge x | Länge y | Drehung | Traufe |
|---|---|---|---|---|---|
| A_corner_front | (4.47, 4.43) | 2.82 | 2.67 | -1.0° | 3.65 |
| B_red_roof | (3.95, 7.73) | verdeckt | 3.53 | 2.7° | 2.48 |
| C_blue_mansard | (8.67, 4.29) | 2.60 | 3.91 | 0.5° | 4.17 |
| D_shutters | (11.48, 4.52) | 2.80 | verdeckt | -0.9° | 4.38 |
| E_left_large | (6.42, 15.05) | 2.62 | 5.52 | 0.2° | 4.00 |
| F_right_dome | (17.75, 6.82) | 3.52 | 5.21 | -1.1° | 5.04 |
| G_back_left | (12.65, 19.52) | 4.14 | 3.83 | -8.7° | 4.78 |
Nicht messbar und deshalb begründet gesetzt (in `blockout.py`, `SPEC[..]['override']`):
* **B** Tiefe x = 3,3 (Front verdeckt), **D** Tiefe y = 3,0 (linke Seite verdeckt).
* **G** Fuß verdeckt → Traufhöhe so gewählt, dass das Kuppeltürmchen (Bildpunkt 735/640) auf dem Dach
  steht und das Haus hinter dem Turm liegt (4,78). Die Vorlage ist bei G **in sich widersprüchlich**:
  Dachkante (−0,48) und Gesims (−0,27) derselben Fassade haben unterschiedliche Richtungen.
* **F** Die Vorlage zeigt die rechte Wand bei x≈1758 px und den Dachpavillon mittig auf dem Dach.
  Beides geht nur mit Länge x = 4,4, d. h. das Haus reicht über den (verdeckten) hinteren Gehweg.
* Dachformen: Mansardhöhe/-rücksprung aus den Dachplattform-Ecken (B 1,9/0,78, D 0,5/0,25),
  sonst am Umriss-Overlay angepasst (A 1,0/0,35, C 1,1/0,55, E 1,0/0,35, F 1,8/0,8 geschwungen, G Attika 0,65).

### Eiffelturm (Profil aus 15 Höhen-/Breitenmarken)
Fußmitte (16,99 / 16,93), Höhe bis Fahne **15,4**. Halbe Breite: Fuß 2,37 · 1. Etage 1,77 (z 2,7–3,3) ·
zwischen den Etagen 1,16 (z 4,5) · 2. Etage 0,94 (z 5,5) · Schaft 0,82 → 0,34 (z 5,8 → 12,6) ·
3. Etage 0,47 (z 12,7–13,1) · Kuppel 0,41 (z 13,7).
Achtung: Die Vorlage hat **keine realen Proportionen** – die 1. Etage liegt zu hoch, der obere Schaft ist gestreckt.
Nachgebaut wird das Bild, nicht der echte Turm.

### Kleinbauten / Dachaufbauten
Anbau links am großen Haus (Bildpunkt 345/1170), niedriger Bau mit blauem Pultdach zwischen großem Haus
und rotem Dach (800/1150), Kuppeltürmchen auf G, Pavillon mit Kupferdach auf F, drei Kaminblöcke auf C.

## 2. Blockout – Abgleich (`renders/compare_blockout_*.png`, lokal)

| Kriterium | Ergebnis |
|---|---|
| Kamerawinkel | deckungsgleich: Plattform-Umriss liegt auf der Vorlage (≈ 6 px), Fluchtrichtungen ≈ 3 px |
| Gebäudepositionen | A, B, C, D, E, G: Umrisse innerhalb ≈ 10–20 px; F: rechte Wand ≈ 30 px zu weit links |
| Proportionen | Traufhöhen gemessen; Dachhöhen von F und E noch ± 0,2 unsicher (geschwungene Mansarde) |
| Silhouette | Turm-Umriss folgt der Vorlage über die ganze Höhe; Blockout-Turm noch massiv (Bögen/Durchblicke fehlen) |
| Räumliche Dichte | Vorlage deutlich dichter: ≈ 25 Bäume füllen alle Lücken (Hof hinter dem Eckhaus, Turmfuß, linke und rechte Ecke); im Blockout bewusst noch leer |
| Fehlt noch | Bäume, Hecke vorne, Autos, Laternen, Kamine/Dachtechnik, innere Fahrspur an der linken Ecke |

## 3. Nächster Schritt (nach Freigabe)
Architekturdetails exakt auf diese Massen setzen (Fenster je Fassade gezählt, Gaubenzahl/-form je Dach,
Turm-Fachwerk mit dem gemessenen Profil), danach Bäume/Autos/Möblierung an ihren Bildpositionen.
