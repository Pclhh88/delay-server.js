# Rekonstruktion „Bundeswehr-Kennzeichen" – Stand: Auftrag 1 (0–20 s)

## Ergebnis

| Datei | Inhalt |
|---|---|
| `output/recon_20s_1080.mp4` | Rekonstruktion 0–20 s, 1080×1920, mit Ton |
| `output/vergleich_original_vs_rekonstruktion_20s.mp4` | links Original, rechts Rekonstruktion |
| `output/compare_frames/full/` | Vergleichsbilder + `metrics.json` (lokal erzeugt, nicht im Git) |
| `analysis/timeline_analysis.json` | Phase 1: Szenen, Elemente, Bewegungen, Gags, SFX (maschinenlesbar) |
| `analysis/captions.json` | 75 Untertitel-Wörter, framegenau |
| `reconstruction/timeline.json` | die Rekonstruktion als steuerbare Layer/Keyframes/Audio |

## Abgleich mit dem Original (480×854, 600 Frames)

* **Szenengrenzen:** alle 10 Schnitte des Originals werden auf denselben Frame getroffen
  (85, 215, 283, 317, 355, 467, 500, 523, 543), plus ein Zwischenframe bei 214.
* **Untertitel:** alle 75 Wörter mit identischem Start-/Endframe.
* **Pointen:** Meme-Auftritte, Pfeile, Rot-Flashes, Weißblende und Zooms auf denselben Frames
  (gemessen, nicht geschätzt).
* **Mittlere Abweichung:** 7,0 Graustufen pro Pixel (PSNR 21,8 dB); Hauptursachen siehe unten.

## Bekannte Abweichungen

1. **Senderlogo** bewusst durch neutrale 2×2-Kacheln ersetzt (Markenrecht), gleiches Timing.
2. Studio-Szene (0–2,8 s): Bodenfläche leicht abweichend, weil sie im Original nicht
   konsistent mit dem Fahrzeug skaliert.
3. Jeep im Busch (6,3–7,1 s): Grüntönung etwas heller als im Original.
4. Deutschlandkarte: rechter Rand beim Einflug abgeschnitten (Quellframes zeigen die Karte
   nur angeschnitten).
5. Untertitel-Schrift: League Spartan statt der (unbekannten) Originalschrift – sehr ähnlich.
6. **Ton:** Sprecherstimme ist die per KI getrennte Originalspur (Platzhalter). Alle Effekte
   sind selbst synthetisiert und nur klanglich angenähert (Pegel an Original angepasst).
   Ein leises Musikbett im Original konnte nicht sicher nachgewiesen werden.

## Rechte

17 der 19 Bild-Assets sind **Referenz-Platzhalter** (aus dem Originalvideo geschnitten) und
nur für den 1:1-Vergleich gedacht – siehe `assets/manifest.json` (`replace_with` nennt den
jeweiligen Ersatz). Für ein veröffentlichbares Video müssen sie ersetzt werden;
`--publish` beim Rendern verweigert sie.

## Neu bauen

```bash
ffmpeg -i ../../references/Bundeswehr-Kennzeichen.mp4 -map 0:v:0 analysis/frames/f%04d.png
python3 reconstruction/build_proxies.py          # Assets + measurements.json (dauert ~30 min)
python3 reconstruction/build_timeline.py         # timeline.json
cd ../.. && P=projects/bundeswehr-kennzeichen
python3 -m shortsfactory.audio.mix $P/reconstruction/timeline.json $P/output/mix_20s.wav --end 20
python3 -m shortsfactory.render $P/reconstruction/timeline.json $P/output/recon_20s_1080.mp4 \
        --end 20 --audio $P/output/mix_20s.wav
python3 -m shortsfactory.analysis.compare references/Bundeswehr-Kennzeichen.mp4 \
        $P/output/recon_20s_1080.mp4 $P/output/compare_frames/full --end 20
```
