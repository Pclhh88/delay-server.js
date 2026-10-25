# Qualitätsabgleich mit Referenzbild B2

B2 = das isometrische Paris-Diorama (Eiffelturm, Häuserblock, Ringstraße).
Ziel: diesen Look mit **echten, wiederverwendbaren Blender-Modellen** erreichen.

## 1. Analyse: Was B2 ausmacht – und was unserem ersten Output fehlte

| Bereich | B2 | erster Output (Hausstudie) | Maßnahme |
|---|---|---|---|
| **Komposition** | eine abgerundete Kachel, Wahrzeichen in der Mitte, Häuserblock darum, Ringstraße, Rand mit Hecke | Ausschnitt einer Straße | `kit/diorama.py`: Kachel mit Ringstraße, Bordsteinen, Block, freier Ecke als Sichtachse |
| **Kamera** | erhöhte 3/4-Ansicht (~33° Neigung, ~45° Drehung), lange Brennweite → fast isometrisch | 70 mm, nah dran | 85 mm aus ~150 Einheiten Abstand → nahezu orthografisch, geringe Tiefenunschärfe |
| **Gebäude-Vielfalt** | jedes Haus anders: Höhe, Dachform, Farbe, Ecke rund/abgeschrägt, Fensterformen | zwei sehr ähnliche Häuser | `house_detail.random_spec()`: würfelt pro Haus Geschosse, Achsmaß, Fensterköpfe (gerade, Verdachung, Dreiecksgiebel, Rundbogen), Balkonetagen, Läden, Erdgeschoss (Läden/Arkaden/Rustika+Portal), Eckquader, Konsolgesims, Dachform |
| **Fassadentiefe** | tiefe Laibungen, Gesimse, Sohlbänke, Faschen | zum Teil vorhanden | Rundbögen mit echter Bogengeometrie (`Facade.arch_fill`) und Archivolten, Gesimse pro Geschoss |
| **Dachlandschaft** | Gauben, Kaminzüge, Tonaufsätze, Aufbauten, Dachterrassen | große leere Dachflächen, Gauben als „Trommeln" | Gauben (Giebel/Segment/flach), kleinere Kamine, Lüfter, Klimageräte, Antennen, Wassertanks, Treppenhaus-Aufbauten, Kübelpflanzen, Pergolen, Balustraden |
| **Materialien** | gealterter Stein, Patina, Schmutz in Ecken, Farbschwankung | saubere Einheitsfarben („Plastik") | prozeduraler PBR-Shader: Farbvariation pro Objekt + großflächig, Schmutz über Ambient Occlusion, senkrechte Regenschlieren, Rauheitsvariation, Mikrorelief, Zinkfalze, Ziegelreihen, Pflaster |
| **Licht** | warmes, tief stehendes Licht von vorne links, weiche aber klare Schatten, viel Umgebungslicht | flach, eher kühl | Sonne 38° Höhe, 3,5° Winkel (weiche Schatten), warme Farbe; warme Umgebung; Cycles mit 8 Bounces (Global Illumination) |
| **Farbgebung** | warm, leicht entsättigt, sanfte Lichter | neutral | AgX-Farbmanagement + Nachbearbeitung `cityshorts/grade.py` (warme Tönung, Glow, Vignette, angehobene Schwärzen) |
| **Bäume** | buschig, unregelmäßig, verschiedene Arten/Farben | wenige glatte Kugeln | Kronen aus verformten Kugeln (2× Displace) + Blattrelief (Voronoi); Laub, Herbst, Blüte, Schirmpinie |
| **Kleinteile** | Laternen, Poller, Hecken, Autos, Bänke | einfache Laterne | Pariser/Römische Laternen, Poller, Hecken, Bänke, Zebrastreifen, Randmarkierungen, abgerundete Autos/Lieferwagen, Passanten |

## 2. Was prozedural geht – und wo echte Assets besser wären

**Prozedural (umgesetzt, beliebig wiederverwendbar):**
Häuser (Fassaden-Grammatik), Dächer, Dachlandschaft, Straßen, Kachel, Laternen,
Hecken, einfache Bäume, Wahrzeichen aus Grundformen (Kolosseum mit echten Bögen),
alle Materialien (Shader-Nodes, keine Bilddateien nötig).

**Mit hochwertigen 3D-Assets deutlich besser (nächster Qualitätssprung):**

| Asset | warum | kostenlose Quelle (CC0) |
|---|---|---|
| Bäume / Büsche | echte Blattgeometrie, wichtigster Unterschied zu B2 | Poly Haven, Blender-Add-on „Sapling" (mitgeliefert), Geometry-Nodes-Baumgeneratoren |
| Autos, Busse, Vespas | Silhouette bleibt bei Nahaufnahmen glaubwürdig | Poly Haven, Kenney (CC0, stilisiert) |
| PBR-Texturen (Putz, Travertin, Zink, Ziegel, Asphalt) | echte Fotostruktur statt Rauschen | Poly Haven, ambientCG |
| HDRI-Umgebung | natürlicheres Licht und Reflexionen | Poly Haven |
| Menschen | erkennbare Figuren statt Stäbchen | Kenney, Sketchfab (CC0-Filter) |
| Ikonische Wahrzeichen (Eiffelturm-Fachwerk, Statuen) | Detail, das prozedural sehr aufwendig ist | Sketchfab (Lizenz prüfen) oder einmalig modellieren lassen |

Hinweis: In dieser Cloud-Umgebung sind Poly Haven und ambientCG gesperrt; auf
deinem Rechner (oder mit freigegebener Domain) können die Assets in einen Ordner
`assets/` gelegt und vom Baukasten statt der prozeduralen Varianten geladen werden.
Alle genannten Quellen sind kostenlos.

## 3. Rendern

```bash
python cityshorts/blender/diorama_still.py build/diorama/rom.png --samples 256   # 1080x1920
# schneller Test:
python cityshorts/blender/diorama_still.py build/diorama/test.png --percent 40 --samples 48
```

CPU-Rendering hier: ~25–30 min für ein Vollbild. Mit einer Grafikkarte
(Cycles nutzt sie automatisch) 1–2 min; für 60-s-Videos ist eine GPU
praktisch Pflicht (oder Cloud-Rendering, kostenpflichtig).

## 4. Version 2: gewachsener Stadtteil statt Rahmen

| Wunsch | Umsetzung (alles im wiederverwendbaren Baukasten) |
|---|---|
| **Vielfalt der Gebäude** | `house_detail.random_spec()` würfelt zusätzlich: Fassadentyp (plastisch / glatt / aufgemalte Rahmen), Achsrhythmus (gleichmäßig, betonte Mitte, Fensterpaare), andersfarbiges Erdgeschoss, Satteldach (neben Walm, Mansarde, Flachdach), zurückgesetztes Dachgeschoss mit Terrasse, Bogen-Loggia im obersten Stock, römische Dachterrasse (Altana). **Pro Fenster** zufällig: Läden offen/halb/geschlossen, Blumenkasten mit Blüten, Einzelbalkon, Klimagerät, Vorhang. Dazu Efeu und Wäscheleinen. |
| **Akzentbauten** | `kit/specials.py`: Barockkirche mit Tambourkuppel, Laterne und Voluten-Fassade; romanischer Campanile; Piazza-Brunnen. |
| **organische Stadt** | `kit/diorama.py`: Randbebauung entlang der Straße mit wechselnden Breiten/Tiefen, Rücksprüngen, ±2,5° Verdrehung und Durchgängen; danach zufällig gepackte Innenbebauung (Kollisionstest) mit Höfen; Freiflächen für Wahrzeichen (frei positionierbar), Piazza, gewundene Gasse, Park. Brandwände werden automatisch erkannt. |
| **Höhenstaffelung** | Höhenzonen relativ zur Kamera: vorne 2–3, Mitte 3–5, hinten 4–6 Geschosse → Wahrzeichen bleibt sichtbar, Tiefe entsteht. |
| **9:16-Komposition** | Hochformat-Kachel (26 × 37 statt quadratisch), Kamera −102° / 40°, 85 mm: Kachel füllt die Bildbreite, oben bleibt Platz für Titel, unten für Untertitel, rundum Luft für Kamerafahrten. |
| **animierbar** | Jedes Haus, jeder Baum, jede Laterne, jeder Poller, jede Bank, jede Person, jedes Auto ist ein eigenes Objekt (gleiche Requisiten teilen sich die Mesh-Daten). |
| **Konfiguration** | Kachel-Layout + Kamera in `cities/rome/city.json` → `"tiles"`. Neue Stadt/Kachel = neuer Eintrag, kein Code. |

```bash
python cityshorts/blender/diorama_still.py build/diorama/rom.png --city rome --tile colosseum
python3 -m cityshorts.compare_stills vergleich.png alt.png "v1" neu.png "v2"
```
