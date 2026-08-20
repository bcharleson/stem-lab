#!/usr/bin/env bash
# Create a local venv and install stem-lab + Demucs.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-python3}"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required. macOS: brew install ffmpeg" >&2
  exit 1
fi

"$PYTHON" -m venv "$ROOT/.venv"
# shellcheck source=/dev/null
source "$ROOT/.venv/bin/activate"
python -m pip install -U pip
python -m pip install -e "$ROOT"
echo
echo "Installed. Try: $ROOT/bin/stem-lab doctor"
