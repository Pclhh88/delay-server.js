# Paris-Diorama – Analyse der Vorlage & Modellierungsplan

Vorlage: `reference/reference.png` (2048 × 2048, aus dem Original 2732 × 2048 ohne schwarze Ränder
zugeschnitten; enthält Freepik-Wasserzeichen → nur interne Referenz, **nicht veröffentlichen**).

## 1. Analyse

### Komposition & Kamera
* Diorama auf quadratischer, stark abgerundeter Sockelplatte (Ecken-Radius ≈ 13 % der Kante),
  Ecke zeigt zur Kamera („Rauten“-Ansicht), Eiffelturm hinten rechts der Mitte überragt alles.
* Quasi-isometrische 3/4-Ansicht: Blickhöhe ≈ 36° über Horizont, Azimut ≈ 45°,
  kaum stürzende Linien → Teleobjektiv (120 mm KB) aus großer Entfernung.
* Kalibrierung (`blender/fit_camera.py`): Ankerpunkte vorderste/linke/rechte Plattformrundung,
  Turmfuß, Turmspitze, Laterne → Restfehler **≈ 14 px RMS** (2048-px-Bild). Turmposition wird mitgefittet.

### Gebäude (Welt: Plattform 24 × 24, Vorderecke = (0,0), +x rechts hinten, +y links hinten)
Vermessen über *Fußpunkt der vorderen Gebäudekante + Traufpunkt senkrecht darüber* (→ Traufhöhe)
und Rückprojektion der Fassaden-Endpunkte auf Traufhöhe (→ Grundriss).

| Objekt | Charakter | Grundriss (x / y) | Traufe |
|---|---|---|---|
| House_White_Corner | hellcremefarben, gerundete Ecke, Mansarde blaugrau mit Rundbogengauben, grüne Tür | 4,3–8,3 / 4,2–6,8 | 4,6 |
| House_Red_Roof | beige, rotbraunes Mansarddach, große Gauben | 3,9–7,4 / 6,8–10,6 | 3,6 |
| House_Center_Mansard | sandfarben, blaugraue Mansarde, viele Terrakotta-Kaminaufsätze | 8,3–12,1 / 4,4–8,6 | 4,7 |
| House_Center_Tall | rosé-sand, braune Fensterläden, flaches helles Dach | 12,1–15,5 / 4,3–7,6 | 6,3 |
| House_Left_Large | creme, durchgehende Balkone, Mansarde mit Giebelgauben | 6,2–10,4 / 15,5–20,6 | 4,8 |
| House_Right_Dome | sand, stark gerundete Ecke, geschwungene Kuppel-Mansarde, Erker, Dachpavillon mit Kupferdach | 17,4–22,0 / 7,6–11,6 | 7,1 |
| House_Back_Left | ocker/tan, Attikageschoss, Dachterrasse, weißes Kuppeltürmchen | 11,2–16,6 / 18,8–22,4 | 7,1 (+Attika) |

### Eiffelturm
Achsparallel zur Plattform (Ecke zur Kamera), Höhe bis Fähnchen ≈ 17,8 Einheiten.
Profil: reale Proportionen am Fuß, oberhalb der 2. Etage etwas schlanker als das Original.
Erkennbar an: vier getrennte Pfeiler bis zur 2. Etage, große Bögen, kastenförmige 1. Etage, Laterne mit Kuppel.

### Straßen, Vegetation, Fahrzeuge
* Ringstraße mit Mittel-Strichlinie und Randlinien, Bordsteine, breiter Gehweg; Hecke außen an der Vorderecke.
* Bäume: runde Laubbäume (oliv-/gelbgrün), Herbstbäume (orange/ocker), ein weißer Blütenbaum links.
* Fahrzeuge: weißer Lieferwagen, dunkler Kleinwagen (vorne links); graues Auto, hellblauer Kastenwagen, rotes Auto (vorne rechts).
* Laternen, Poller.

### Licht & Material
* Warmes Studio-Licht, cremefarbener Hintergrund (≈ RGB 238/229/214), weiche Schatten nach links.
* Sonne von rechts/vorne-oben, große weiche Aufhellung; Materialien matt, Zinkdächer leicht metallisch.

## 2. Modellierungsplan (umgesetzt)
1. **Bausteine** (`blender/diorama/`): `meshkit` (Quader/Balken/Lofts → ein Mesh pro Objekt),
   `materials`, `haussmann` (parametrischer Gebäudegenerator), `eiffel` (Fachwerk aus Einzelstäben),
   `nature` (Bäume, Hecken, Büsche), `vehicles`, `street` (Plattform, Straße, Laternen), `extras` (Dachaufbauten).
2. **Layout** (`blender/layout.py`): alle Positionen/Maße zentral; Bäume, Laternen, Poller werden über
   ihre Bildkoordinate + Kamerastrahl platziert (`img2world`).
3. **Szene** (`blender/build_scene.py`): baut alles in Collections (Street, Buildings, Tower, Trees, Vehicles, Props, Light_Camera),
   speichert `paris_diorama.blend`, rendert mit Cycles.
4. **Abgleich**: `blender/compare.py` (Nebeneinander, Überblendung, Kanten), `blender/overlay_layout.py`
   (Drahtgitter der Grundrisse über der Vorlage, ohne Rendern).

## 3. Iterationen (Abgleich)
| Iteration | Änderung | Befund |
|---|---|---|
| 01 | erster Gesamtaufbau, lineare Bildvermessung | Plattform passt grob, Häuser zu hoch / falsch platziert |
| 02 | Kamera an Ankerpunkte gefittet, Grundrisse per Rückprojektion neu vermessen | Häuser decken sich in der Überblendung |
| 03 | größere Fensterachsen, Fensterläden, Fassadenfarben, Bäume über Kronenmitte platziert | Maßstab der Details näher an der Vorlage |
| 04 | Turmprofil (reale Ausstellung, getrennte Pfeiler), mehr Grün, Licht | Turm-Silhouette erkennbar wie Vorlage |
| 05 | wärmere Farben, Hintergrund, Laubfarben, offeneres Turmgitter | → `renders/render_v1.png` |

## 4. Bekannte Abweichungen (nächste Schritte)
* Fassaden noch zu regelmäßig/sauber; Vorlage hat mehr Ornamentik (Kartuschen, Rundbögen, Gesimsprofile) und Patina.
* Turm: Bogenfeld-Ornamente und Fries der 1. Etage nur angedeutet; Fachwerk ohne gebogene Zierstäbe.
* Bäume: Kronen noch „knubbelig“; Vorlage hat feinere Blattbüschel (→ Partikel-/Geometry-Nodes-Laub).
* Linke Ecke: in der Vorlage zweite, innere Fahrbahn – noch nicht modelliert.
* Viele kleine Requisiten der Vorlage fehlen (Bänke, Fahrräder, Kübelpflanzen, Markisen).
* Render-Artefakte v1: dunkler Keil auf dem Mansarddach von House_Left_Large (Gaube/Kamin schneidet die Dachfläche),
  feine schwarze Kanten an Gebäudeecken (dunkler Kern blitzt zwischen den Fassadenrastern durch).
* Gesamteindruck noch „sauberer“ und heller als die Vorlage: Höfe zu leer, Vegetation zu knubbelig, Turm zu rötlich und zu gleichmäßig.
