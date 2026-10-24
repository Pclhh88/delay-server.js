# Stilregeln (gemessen am Referenzvideo, 0–20 s)

Alle Zahlen stammen aus Messungen (`projects/bundeswehr-kennzeichen/analysis/`).
Pixelangaben beziehen sich auf die Referenz (480×854); ×2,25 = Design-Einheiten (1080×1920).

## Format
* 9:16, 30 fps, ~50 s. Stimme durchgehend, sehr schnelles Sprechtempo (~3,7 Wörter/s).

## Untertitel
* **Ein Wort pro Einblendung**, harte Wechsel exakt zum Wortbeginn, keine Animation.
* Versalien, geometrische Grotesk (Nachbau: League Spartan 700), weiß, dunkle Kontur (~1 px),
  weicher Schatten nach rechts unten.
* Position: horizontal zentriert, vertikal **genau Bildmitte** (Zeilenmitte y = 50 %).
* Größe: Versalhöhe ≈ 20,5 px (= 64 Design-px Schriftgröße). **Betonungswörter 1,5×**
  (UNSICHTBAR, KEINE, NATO), ENTGEGENFLASHT. 1,25×.
* Komposita bleiben ein Wort (JOHN-CENA-LACKIERUNG, HANDYTASCHENLAMPE).
* Sprechpausen = Untertitel-Lücke (z. B. 0,3 s Stille nach der Blendung).

## Hintergrund
* Standard: vertikaler Pastellverlauf (oben Pfirsich RGB≈253,231,202 → unten Hellblau ≈190,202,213)
  mit schrägen dunkleren Streifen (Periode 284 px, Dunkelanteil 55 %, Neigung dx/dy = −0,175),
  die **konstant 1,3 px/Frame nach rechts scrollen** – auch unter anderen Szenen.
* Szenen mit eigener Welt (Studio, Busch, Minecraft-Welt, Weißblende) ersetzen den Verlauf.

## Bildsprache
* Freigestellte Fotos (Fahrzeug, Kennzeichen) zentral, groß, oft angeschnitten.
* Pro Satzteil genau ein neues visuelles Ereignis; Ereignisse sitzen auf dem Schlüsselwort
  (±3 Frames).
* **Punch-Zooms**: 2–3 Frames, linear, ohne Ease (Skalierungssprünge 1,3–1,5×), dann Standbild.
* **Pop-ins** von Objekten mit Überschwinger: 0,15 → 0,45 → 1,24 → 1,37 → 1,28 → 1,15 → 1,0 (je 1 Frame).
* **Meme-Auftritte** von unten (2 Frames hoch, 1–2 Frames raus) oder von der Seite.
* **Push-Übergänge** zwischen gleichartigen Objekten (Kennzeichen): altes raus ~195 px/Frame,
  neues rein mit Ease-out.
* **Roter Blockpfeil** (Länge 194 px, Schaft 71 px, Kopf 137×98 px, Reinrot) zeigt auf das Detail,
  fliegt entlang seiner Achse in 2 Frames ein und wieder aus.
* **Roter Flash** auf negative Aussagen (KEINE, NICHT SEHEN): Farbe RGB(168,40,45),
  Deckkraft 0 → 0,82 in 4 Frames, Ausklingen über 11 Frames, + Buzzer.
* **Weißblende** für „blenden/flashen": Glint am Objekt, wachsende weiße Scheibe in 6 Frames.
* Quellen: `[Qn]` oben links (fällt in 10 Frames 48 px ein), vertikale Quellenzeile rechts.

## Comedy-Timing
* Wortwitz → wörtliche Bebilderung (John-Cena-Lackierung → Maler-Meme malt Fahrzeug an;
  unsichtbar → Fahrzeug verschwindet im Busch; Feind → Videospiel-Gegner).
* Zustimmung/Ablehnung über Drake-Meme mit thematisch umgefärbtem Shirt.
* Reaktions-Meme nach der Pointe (geblendete Katze) mit kurzer Sprechpause.

## Sounddesign
* Stimme trocken und laut (Mittel −16 dB), Effekte darunter (−4 … −16 dB relativ).
* Impact auf Punch-Zoom der Kernaussage, Pop für erscheinende Objekte, Swoosh/Whoosh auf
  Szenen- und Push-Übergänge, Glissando + Glocken für „Magie/Malen", Blitz + Fiepton für
  Blendung, Buzzer auf roten Flash.

## Abgleich mit Referenz 2 („Burj Khalifa", 63,8 s)

Ausgewertet (nicht nachgebaut): `projects/burj-khalifa/analysis/`. Ergebnis, was **fest** zum Stil
gehört (in beiden Videos gleich) und was **pro Thema wechselt**:

| Merkmal | Bundeswehr | Burj Khalifa | Regel |
|---|---|---|---|
| Format | 9:16, 30 fps, 50,5 s | 9:16, 30 fps, 63,8 s | fest; Länge 50–65 s |
| Sprechtempo | 3,5 Wörter/s | 3,8 Wörter/s | fest: 3,5–3,8 Wörter/s |
| Untertitel | 1 Wort, Versalien, Bildmitte | identisch (Mitte y≈430 px) | fest |
| Streifen-Hintergrund | ja | ja, **identisch** (gleiche Farben, Neigung, Scroll; Median-Abweichung 1/255) | fest |
| Quellen | [Q1]–[Q9] + vertikale Zeile rechts | [Q1]–[Q11] + Zeile rechts | fest |
| Einstieg | Behauptung „… reflektieren nicht." | Behauptung „… hat keinen Haupteingang." | fest: verblüffende Negativ-Behauptung, ≤ 2,7 s |
| Zweiter Satz | „Wäre ja auch dumm, wenn …" | „Klingt erst mal dumm, aber wenn du …" | fest: „dumm"-Brücke + du-Szenario |
| Ende | „…, denn …" (Abbruch) | „Überlegt euch mal …" (Abbruch) | fest: offenes Ende mitten im Satz |
| Roter Blockpfeil | ja | ja (auf Spitze/Fuß) | fest |
| Roter Flash bei Verneinung | KEINE / NICHT SEHEN | NICHT MAL … ÖFFNEN KANNST | fest |
| Voxel-Figur (Minecraft-Stil) | Gegner + Prüfer | Bewohner mit Kopftuch | wiederkehrend, Rolle wechselt |
| Memes | Bob Ross, Drake, Katze, Schwitzmann, Wasted | Meme-Gesicht auf Auto, SpongeBob | wechselt pro Thema |
| Erklär-Grafiken | Karte, StVO-Seite, Kreuzung | Turm-Querschnitt mit Farbetagen + Beschriftung | wechselt; flache, bunte Info-Grafik |
| Vergleich aus dem Alltag | Panzer braucht TÜV | Aufzug = „vom ICE in den Regio umsteigen" | fest: deutscher Alltagsvergleich |
| Schnitte (harte) | 32 in 50,5 s | 30 in 63,8 s | fest: neues Bild-Ereignis alle 1–2 s, oft ohne harten Schnitt (Zoom/Push) |
| Soundeffekte | ~7 pro 10 s | ~8 pro 10 s | fest: 7–8 Effekte pro 10 s |
| Lautheit | −16,2 dB | −14,4 dB | Stimme dominant, Effekte ~15 dB leiser |
| Zahlen im Untertitel | Ziffern | kurze Zahlen als Wort (ZEHN), große als Ziffern | Regel: ≤ 12 als Wort, sonst Ziffern |
