# Rekonstruktion „Bundeswehr-Kennzeichen" – komplett (0–50,5 s)

## Ergebnis

| Datei | Inhalt |
|---|---|
| `output/recon_full_1080.mp4` | Rekonstruktion komplett (50,5 s), 1080×1920, mit Ton |
| `output/vergleich_original_vs_rekonstruktion_komplett.mp4` | links Original, rechts Rekonstruktion |
| `output/compare_frames/full/` | Vergleichsbilder + `metrics.json` (lokal erzeugt, nicht im Git) |
| `analysis/SPRECHERTEXT.md` | kompletter Sprechertext mit Zeitmarken + Tonfall-Analyse |
| `analysis/timeline_analysis.json` | Phase 1: Szenen, Elemente, Bewegungen, Gags, SFX (maschinenlesbar) |
| `analysis/captions.json` + WORDS2 / WORDS3 in `timeline_part2.py` / `timeline_part3.py` | 75 + 63 + 37 Untertitel-Wörter, framegenau |
| `reconstruction/timeline.json` | die Rekonstruktion als steuerbare Layer/Keyframes/Audio |

## Abgleich mit dem Original (480×854, 1515 Frames)

* **Szenengrenzen:** alle 32 Schnitte des Originals werden auf denselben Frame getroffen.
* **Untertitel:** alle Wörter mit identischem Start-/Endframe.
* **Pointen und Bewegungen** gemessen (nicht geschätzt): Zooms, Pop-ins, Pfeile, Rot-Flashes,
  Weißblende, Siegel-Flüge, vorbeifahrende Fahrzeuge (konstante Geschwindigkeit je Fahrzeug),
  Rottönung beim „Herzinfarkt", Breiten-Gag beim Leopard („BREITER": 75 % → 100 % Breite),
  Kamerafahrt aufs Kanonenrohr, GTA-„Wasted" (Entsättigung + Abdunkeln + Zoom/Drehung),
  StVO-Seite mit aufgezogener Markierung.
* **Mittlere Abweichung:** 0–20 s 7,0 / 20–40 s 6,1 / 40–50,5 s 4,5 Graustufen pro Pixel; Lautheit −16,6 dB (Original −16,2 dB).

## Szenen 20–40 s

| Frames | Inhalt |
|---|---|
| 598–642 | Kennzeichen-Nahaufnahme, TÜV-Plakette blendet in Bundeswehr-Siegel über, Wackel-Zoom |
| 641–914 | Haus der Zulassungsstelle: Push von unten, Prüfer (Voxel-Figur) taucht im Fenster auf, Zoom-out auf die Straße, 3 Fahrzeuge + Panzer fahren durch, Siegel fliegen, Stempel klebt auf dem Panzer, Zoom-in, Schwenk raus |
| 916–973 | animiertes Meme „schwitzender Mann", wächst, Bild wird rot (RGB 200/88/88, bis 75 %) |
| 981–1141 | Leopard 2: Pop-in gestaucht, „BREITER"-Dehnung, Hügelwelt blendet ein, Pfeil auf Fahrspur, Zoom aufs Rohr mit CE-Zeichen, „Wasted" |
| 1141–1191 | StVO § 35 als Webseite, Markierung wird aufgezogen |

## Szenen 40–50,5 s

| Frames | Inhalt |
|---|---|
| 1196–1351 | Panzer fährt ein, Strasse schiebt sich rein, Ampel ploppt auf, STOP-Schild blendet aus, Panzer fährt weg und schiebt die Ampel um |
| 1352–1392 | Kreuzung von oben: Panzer fährt hoch, Radfahrer von rechts („rechts vor links") |
| 1393–1461 | Blitzer: Nahaufnahme, Zoom-out, Jeep rast vorbei mit Blitz, Schwenk auf unscharfe Strasse |
| 1462–1515 | Foto-Karte ploppt auf, Zoom ins Vollbild-Foto des Jeeps |

## Bekannte Abweichungen

1. **Senderlogo** bewusst durch neutrale 2×2-Kacheln ersetzt (Markenrecht), gleiches Timing.
2. Studio-Szene (0–2,8 s): Bodenfläche leicht abweichend.
3. Jeep im Busch (6,3–7,1 s): Grüntönung etwas heller als im Original.
4. Deutschlandkarte: rechter Rand beim Einflug abgeschnitten.
5. Schwitz-Meme: kleine Hintergrund-Reste zwischen Arm und Körper, in einem Frame Untertitelreste.
6. Untertitel-Schrift: League Spartan statt der (unbekannten) Originalschrift.
7. **Ton:** Stimme = per KI getrennte Originalspur (Platzhalter). Effekte selbst synthetisiert und
   nur klanglich angenähert (Pegel ans Original angepasst).

## Rechte

17 der 19 Bild-Assets sind **Referenz-Platzhalter** (aus dem Originalvideo geschnitten) und
nur für den 1:1-Vergleich gedacht – siehe `assets/manifest.json` (`replace_with` nennt den
jeweiligen Ersatz). Für ein veröffentlichbares Video müssen sie ersetzt werden;
`--publish` beim Rendern verweigert sie.

## Neu bauen

```bash
ffmpeg -i ../../references/Bundeswehr-Kennzeichen.mp4 -map 0:v:0 analysis/frames/f%04d.png
python3 reconstruction/build_proxies.py          # Assets + Messungen 0-20 s (dauert ~30 min)
python3 reconstruction/build_part2.py            # Assets + Messungen 20-40 s
python3 reconstruction/build_part3.py            # Assets + Messungen 40-50,5 s
python3 reconstruction/build_timeline.py         # timeline.json
cd ../.. && P=projects/bundeswehr-kennzeichen
python3 -m shortsfactory.audio.mix $P/reconstruction/timeline.json $P/output/mix_full.wav
python3 -m shortsfactory.render $P/reconstruction/timeline.json $P/output/recon_full_1080.mp4 \
        --audio $P/output/mix_full.wav
python3 -m shortsfactory.analysis.compare references/Bundeswehr-Kennzeichen.mp4 \
        $P/output/recon_full_1080.mp4 $P/output/compare_frames/full --end 50.5
```
