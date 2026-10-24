# Skript „Elektroautos dürfen nicht leise sein" (Entwurf 1)

Bauplan: `projects/bundeswehr-kennzeichen/analysis/SPRECHERTEXT.md`, Stilregeln: `docs/STYLE_GUIDE.md`.
Umfang: ~213 Wörter ≈ 57 s bei 3,7 Wörtern/s. Zahlen: ≤ 12 als Wort, sonst Ziffern.

## Text mit Bildideen

| # | Text | Bild (Pointe) | Quelle |
|---|---|---|---|
| 1 | **Elektroautos dürfen nicht leise sein.** | E-Auto-Foto, Punch-Zooms, roter Pfeil auf den (nicht vorhandenen) Auspuff, roter Flash auf NICHT | Q1 |
| 2 | Wäre ja auch dumm, wenn du dir für 50.000 € 'n Auto fürs Klima kaufst und dann auf dem Aldi-Parkplatz lautlos an 'ne Oma ranrollst, die dich erst bemerkt, wenn sie auf deiner Motorhaube sitzt. | Preisschild „50.000 €" in Rot, Weltkugel mit Herz, Parkplatz von oben, Auto als Ninja, Voxel-Oma landet auf der Haube; Reaktions-Grafik + 0,3 s Pause | – |
| 3 | Deshalb muss seit Juli 2021 jedes neue E-Auto in der EU künstlich Lärm machen, und zwar vom Anfahren bis Tempo 20 und beim Rückwärtsfahren. | EU-Flagge ploppt auf, Kalender „07/2021", Tacho mit Bereich 0–20 grün markiert, Auto fährt rückwärts | Q1, Q2 |
| 4 | Darüber nicht mehr, weil dann sowieso die **Reifen** lauter sind als der Motor. | Zoom auf Reifen, Schallwellen kommen aus dem Reifen | Q2 |
| 5 | Bei Tempo 20 müssen es mindestens 56 Dezibel sein, aber nicht mehr als 75, sonst wär's ja wieder Lärm. | Lautstärke-Balken füllt sich bis 56, schießt über 75 → roter Flash + Buzzer | Q2, Q3 |
| 6 | Und der Ton muss mit der Geschwindigkeit höher werden, damit du hörst, ob das Auto bremst oder Gas gibt, also quasi wie du früher auf dem **Bobbycar** immer höher „Brrrmmm" gemacht hast, je schneller du warst. | Tonhöhen-Kurve steigt mit Tacho; Kind auf Bobbycar, Sprechblase „BRRRMMM" wird größer | Q3 |
| 7 | Wie das klingt, dürfen sich die Hersteller selbst ausdenken, es soll aber nach 'nem Auto klingen und nicht nach Vogelgezwitscher oder Musik. | Mischpult; Vogel und Notenschlüssel ploppen auf und werden rot durchgestrichen | ⚠️ Q1 prüfen |
| 8 | BMW hat sich dafür trotzdem einfach **Hans Zimmer** geholt, also den Typen, der die Musik für „Interstellar" und „König der Löwen" gemacht hat. | Orchester auf der Rückbank, Dirigent am Lenkrad (eigene Grafik, kein Foto der Person ohne Rechte) | Q4 |
| 9 | Bei Hybriden wird's dann absurd, denn wenn da der Benziner schon läuft, darf das System keinen Extra-Ton machen, sonst würde das Auto ja doppelt brummen. | Auto mit zwei Mündern, einer wird zugeklebt | ⚠️ Q1 prüfen |
| 10 | Und ältere E-Autos von vor 2021 dürfen übrigens weiterhin komplett lautlos fahren, also wenn du auf dem Parkplatz gar nichts hörst, heißt das nicht, dass da nichts kommt, denn … | Parkplatz, Stille (Untertitel-Lücke), Scheinwerfer gehen im Dunkeln an – Video endet offen | Q2 |

**Fett** = Betonungswort (Untertitel 1,5×).

## Faktencheck

| Fakt | Stand | Quelle |
|---|---|---|
| Pflicht für neue Typen ab 1.7.2019, alle Neuzulassungen ab 1.7.2021 | ✅ mehrere Quellen | Q1, Q2 |
| Aktiv vom Anfahren bis 20 km/h und beim Rückwärtsfahren; darüber übertönt das Reifengeräusch | ✅ | Q2 |
| Mindestens 56 dB(A) bei 20 km/h (50 dB(A) bei 10 km/h), höchstens 75 dB(A) | ✅ Messtechnik-Quellen übereinstimmend | Q3 |
| Tonhöhe ändert sich mit der Geschwindigkeit (mind. 0,8 % pro km/h) | ✅ | Q3 |
| Klang soll einem Fahrzeug derselben Klasse mit Verbrennungsmotor ähneln; Musik/Naturgeräusche unzulässig | ⚠️ nur aus Fachpresse, im Verordnungstext (Anhang VIII) prüfen | Q1 |
| Hybrid: läuft der Verbrenner, darf AVAS keinen Ton erzeugen | ⚠️ nur ÖAMTC (laut Suchergebnis), im Verordnungstext prüfen | Q1 |
| Bestandsfahrzeuge ohne AVAS müssen nicht nachgerüstet werden | ✅ | Q2 |
| BMW IconicSounds Electric mit Hans Zimmer (angekündigt 2019, Serie ab i4/iX 2022) | ✅ BMW-Pressemitteilung; betrifft v. a. den Innenraum-Fahrsound | Q4 |

Bewusst weggelassen: „Abschalten verboten" – Quellen widersprechen sich (früher Pause-Schalter in der EU-Regel,
später Verbot über UN R138).

## Quellen

* Q1: Verordnung (EU) Nr. 540/2014, Anhang VIII (EUR-Lex) – Primärquelle, noch gegenlesen
* Q2: elektroauto-news.net, „Warngeräusch AVAS ab 2021 verpflichtend"; ÖAMTC, „Lärmpflicht für E-Autos"
* Q3: UN-ECE-Regelung Nr. 138; Zusammenfassungen: Siemens Simcenter Blog „AVAS electric vehicle warning sounds", Brüel & Kjær „Quiet Vehicle – Pass-by Noise"
* Q4: BMW Group PressClub, „New soundscapes for pure electric driving pleasure: BMW IconicSounds Electric"
