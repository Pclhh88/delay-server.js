#!/usr/bin/env bash
# Side-by-side video: reference (left) | reconstruction (right), audio of the reconstruction.
# usage: tools/side_by_side.sh REF.mp4 RECON.mp4 OUT.mp4 [duration]
set -euo pipefail
DUR="${4:-20}"
ffmpeg -v error -y -t "$DUR" -i "$1" -t "$DUR" -i "$2" -filter_complex \
 "[0:v:0]scale=480:854,setsar=1,drawtext=text='ORIGINAL':x=10:y=820:fontsize=22:fontcolor=yellow:box=1:boxcolor=black@0.6[a];\
  [1:v:0]scale=480:854,setsar=1,drawtext=text='REKONSTRUKTION':x=10:y=820:fontsize=22:fontcolor=yellow:box=1:boxcolor=black@0.6[b];\
  [a][b]hstack=inputs=2[v]" -map "[v]" -map 1:a? -c:v libx264 -crf 20 -pix_fmt yuv420p -c:a aac -b:a 160k "$3"
echo "wrote $3"
