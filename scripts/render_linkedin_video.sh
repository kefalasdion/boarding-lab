#!/usr/bin/env bash
# Render the LinkedIn video from the tracked default comparison.
# Rerun this whenever the model or the comparison artifact changes.
set -euo pipefail

PORT="${PORT:-8791}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT="${ROOT}/output"

cd "${ROOT}"
rm -rf "${OUTPUT}"
mkdir -p "${OUTPUT}" docs/media

python3 -m boarding_sim --port "${PORT}" >/dev/null 2>&1 &
SERVER_PID=$!
trap 'kill "${SERVER_PID}" 2>/dev/null || true' EXIT

for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:${PORT}/api/config" >/dev/null 2>&1; then break; fi
  sleep 0.5
done

node scripts/record_linkedin_video.mjs "http://127.0.0.1:${PORT}" "${OUTPUT}"

ffmpeg -v error -y -i "${OUTPUT}/race.webm" \
  -c:v libx264 -profile:v high -pix_fmt yuv420p -r 30 \
  -vf "scale=1080:1350:force_original_aspect_ratio=decrease,pad=1080:1350:(ow-iw)/2:(oh-ih)/2" \
  -movflags +faststart -an \
  "${OUTPUT}/boarding-frustration-linkedin.mp4"

cp "${OUTPUT}/poster.png" docs/media/boarding-frustration-poster.png

ffprobe -v error -show_entries format=duration \
  -show_entries stream=width,height,codec_name,r_frame_rate \
  -of default=noprint_wrappers=1 "${OUTPUT}/boarding-frustration-linkedin.mp4"
