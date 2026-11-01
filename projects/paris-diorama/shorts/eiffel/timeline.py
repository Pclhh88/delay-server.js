"""Drehbuch des Pilot-Shorts „Gebaut für X – heute Y“: Der Eiffelturm sollte abgerissen werden.

Zeiten in Sekunden. Fakten:
* Bauzeit 28.01.1887 – 31.03.1889 (gut 2 Jahre), Anlass: Weltausstellung 1889.
* 14.02.1887: Protestbrief von Künstlern in „Le Temps“ gegen die „nutzlose und monströse“ Tour Eiffel.
* Eiffels Konzession lief 20 Jahre (bis 1909); danach sollte der Turm der Stadt zufallen / abgebaut werden.
* Eiffel förderte wissenschaftliche Nutzung, v. a. Funk (Funkversuche ab 1898, militärische Funkstation).
* 1910: Konzession um 70 Jahre verlängert – wegen der Bedeutung als Funkantenne.
"""
FPS = 24
DURATION = 34.0
TOWER_TOP = 15.45          # Objekt-z der Fahnenspitze (gemessenes Turmprofil)

# Sichtbarkeitsschwelle des Turms (Objekt-z): Turm sichtbar unterhalb der Schwelle
REVEAL = [  # (Sekunde, Schwelle)
    (0.0, TOWER_TOP + 0.5), (1.2, TOWER_TOP + 0.5), (2.9, -0.3),   # Hook: löst sich von oben auf
    (4.6, -0.3), (11.0, TOWER_TOP + 0.5),                           # Bau 1887–1889
    (15.4, TOWER_TOP + 0.5), (19.6, 8.5),                           # 1909: Abriss beginnt
    (21.2, 8.5), (24.8, TOWER_TOP + 0.5),                           # Funk rettet ihn
]
WAVES = [20.4, 21.4, 22.4, 23.4, 24.4]   # Startzeiten der Funkwellen (je 2,2 s)
ANTENNA_GLOW = (20.0, 26.5)

# Kamera: Umlaufwinkel (Grad) und Abstand
CAMERA = [  # (Sekunde, Azimut, Abstand, Zielhöhe)
    (0.0, -47, 52, 7.0), (3.0, -42, 44, 4.5), (11.0, -25, 46, 7.0), (15.0, -15, 42, 8.5),
    (20.0, -5, 36, 10.5), (25.0, 5, 44, 8.0), (34.0, 35, 58, 7.0),
]

# Texte (Sekunde von, bis, Text, Stil) – Stil: 'big' Jahreszahl, 'cap' Untertitel, 'hook'
CAPTIONS = [
    (0.0, 2.9, 'DIESER TURM\nSOLLTE ABGERISSEN\nWERDEN', 'hook'),
    (3.0, 4.6, 'PARIS 1887', 'big'),
    (4.6, 7.6, 'IN NUR 2 JAHREN\nGEBAUT', 'cap'),
    (7.6, 11.0, 'FÜR DIE\nWELTAUSSTELLUNG 1889', 'cap'),
    (11.0, 15.2, 'KÜNSTLER PROTESTIERTEN:\n„NUTZLOS UND MONSTRÖS“', 'cap'),
    (15.2, 17.4, 'GENEHMIGUNG:\nNUR 20 JAHRE', 'cap'),
    (17.4, 20.0, '1909 SOLLTE\nER WEG', 'hook'),
    (20.0, 24.8, 'EIFFELS RETTUNG:\nFUNK', 'cap'),
    (24.8, 28.6, '1910: GENEHMIGUNG\nUM 70 JAHRE VERLÄNGERT', 'cap'),
    (28.6, 34.0, 'HEUTE:\nWAHRZEICHEN VON PARIS', 'cap'),
]
RED_FLASH = [1.6, 17.4]       # Rot-Flash (Stilregel: 0 → 0,82 in 4 Frames, Ausklingen 11 Frames)
