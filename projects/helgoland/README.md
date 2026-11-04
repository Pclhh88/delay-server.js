# Helgoland – „Die Insel, die nicht kaputtging"

Cartoon-3D-Short (Stil aus dem Skill-Paket „claude-animated-shorts"), 1080x1920, 30 fps, 96 s, Deutsch.

* Skript + Quellen: `SCRIPT.md`
* Stimme (ElevenLabs, vom Nutzer): `voice/voice.mp3`; Wortzeiten `voice/words.json` (`make_words.py` aus `segments.json`)
* Bild: Remotion-Projekt `animated/`, Komposition `Helgoland` (`animated/src/videos/helgoland/`)
* Ton: `python3 animated/audio/helgo_audio.py projects/helgoland/voice/voice.mp3 animated/out/audio` (eigene Musik + SFX, -14 LUFS)
* Render (CPU/SwiftShader, ~3-7 s pro Frame): `cd animated && node scripts/render.mjs Helgoland out/x.mp4 <von> <bis> 1 4`
  in Teilen, dann mit ffmpeg zusammensetzen und `out/audio/mix.wav` muxen.
* QA: `python3 animated/scripts/short_qa.py <video> <outdir> animated/out/shots.json`
* Ergebnis (nicht im Git, 130 MB): `projects/helgoland/output/helgoland_final.mp4`
