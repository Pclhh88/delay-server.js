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
