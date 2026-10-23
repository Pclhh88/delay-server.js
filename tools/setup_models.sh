#!/usr/bin/env bash
# Downloads the analysis models (only needed for transcription / voice separation).
set -euo pipefail
DIR="${1:-models}"
mkdir -p "$DIR"
cd "$DIR"
BASE=https://github.com/k2-fsa/sherpa-onnx/releases/download
[ -d sherpa-onnx-whisper-small ] || { curl -sSL -o w.tar.bz2 "$BASE/asr-models/sherpa-onnx-whisper-small.tar.bz2"; tar xjf w.tar.bz2; rm w.tar.bz2; }
[ -f silero_vad.onnx ] || curl -sSL -o silero_vad.onnx "$BASE/asr-models/silero_vad.onnx"
[ -f UVR-MDX-NET-Voc_FT.onnx ] || curl -sSL -o UVR-MDX-NET-Voc_FT.onnx "$BASE/source-separation-models/UVR-MDX-NET-Voc_FT.onnx"
echo "models in $(pwd)"
