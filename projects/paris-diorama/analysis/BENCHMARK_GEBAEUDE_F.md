# Qualitäts-Benchmark: Gebäude F (Kuppel-Mansardhaus rechts neben dem Eiffelturm)

Ziel: ein einzelnes Gebäude der Vorlage in der Detailqualität, die später für die ganze Stadt gelten soll.
Modell: `blender/diorama/landmark.py`, Build/Render: `blender/build_landmark.py` → `landmark_f.blend`.

## Was die Vorlage zeigt (Detailausschnitte 3× vergrößert)
| Bereich | Merkmal in der Vorlage | Umsetzung im Modell |
|---|---|---|
| Grundriss | fast quadratisch, große Rundung an der Kamera-Ecke, kleine Rundungen hinten | gerundetes Rechteck 4,4 × 5,21, Radien 1,3 / 0,35 / 0,25 / 0,35 (aus der Blockout-Messung) |
| Dach | glockenförmig geschwungene Zink-Mansarde, stark gerundete Ecken, feine waagerechte Falze | Profil-Sweep (16 Stützpunkte, Ausbauchung im unteren Drittel), 4 Falz-Sweeps, Traufblech |
| Gauben | kleine dunkle Ochsenaugen mit Haube, 3 je Seite + eine auf der Ecke | Gaubenkörper, ovaler Rahmen (Röhre), Glas, auskragende Halbzylinder-Haube, seitliche Voluten |
| Terrasse | dicke zweilagige Platte mit Brüstung, runder Pavillon mit grünem Lamellendach, Schornsteinpaare, Figur | Brüstungs-Sweep, gedrechselte Trommel mit 12 Fenstern, gewölbte Haube + 27 Lamellen, gedrechselte Schornsteinköpfe, Figur |
| Hauptgesims | schwerer, gerundeter Kranz | 15-Punkt-Profil-Sweep + Konsolen (Modillons) im 0,26er-Raster rundum |
| Fries | breites vorspringendes Band auf ~3,6 | 10-Punkt-Profil-Sweep |
| rechte Fassade | ionische Doppelvolute am Eckpfeiler, großer halbrunder Erker mit Kuppelhaube, kleiner Erker, massiver Balkon | Pilaster mit Kanneluren, Volutenkapitell (Spiralbänder, Augen, Eierstab, Abakus), gedrechselte Erker mit Kragkonsole, Gesimsringen, Rippenhaube und Knauf, Steinbalkon mit Konsolen und Brüstungsspiegeln |
| linke Fassade | Attikafenster direkt unter dem Gesims mit Steindraperie darunter, hohe Fenster mit Draperien | Lambrequin (7 Faltenröhren), Festons (3 gestaffelte Stoffbahnen, Endstücke mit Quasten, Rosette) |
| Fenster | tiefe Laibungen, helle Faschen | Boolean-Öffnungen (16 cm Wand), Zarge, zwei Flügel, Kämpfer, Sprossen, Glas, Vorhang, Faschen-Profil auf Gehrung, Schlussstein, Bank mit Konsolen, Verdachungen (Gesims, Segment), Brüstungsgitter |
| Material | warmer Kalkstein mit Patina, bläuliches Zink | Kalkstein: Farbrauschen, Schmutz in Kanten (AO), Regenspuren, Körnung (Bump); Zink metallisch mit Rauheitsvariation |

Nicht sichtbare Teile (Erdgeschoss, Rückseiten) sind im selben Stil vollständig modelliert, damit das
Modell aus jeder Richtung funktioniert (zweite Ansicht).

## Aufbau (Objekte unter dem Elternobjekt `Landmark_F`)
`LM_Walls`, `LM_Oriels`, `LM_Interior`, `LM_Cornices`, `LM_Modillions`, `LM_Windows`, `LM_Ornament`,
`LM_Roof`, `LM_Dormers`, `LM_Terrace`, `LM_Kiosk`, `LM_RoofProps` – ein Elternobjekt verschiebt/animiert alles.

## Abgleich
* Kamera: exakt die kalibrierte Referenzkamera, nur Ausschnitt (Brennweite × 2048/660, Shift angepasst).
* Silhouette (`renders/compare_landmark_outline.png`, lokal): Wandkanten links/rechts, Traufe und Terrassenecken
  liegen auf der Vorlage.
* Farbe: Fassaden-Mittelwert im Render 143/119/92 gegen 138/118/95 in der Vorlage.

## Bekannte Abweichungen
* Die Vorlage ist KI-generiert und „weich“: Ornamente gehen fließend ineinander über; das Modell ist
  architektonisch sauberer und regelmäßiger.
* Fensterzahl/-rhythmus der linken Fassade unter den Draperien ist in der Vorlage teils verdeckt → ergänzt.
* Bäume, Nachbarhaus und Turm fehlen in diesem Einzel-Benchmark bewusst.
