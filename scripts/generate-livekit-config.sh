#!/usr/bin/env bash
# Render LiveKit server config from template + .env secrets (never commit output).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

TEMPLATE="${1:-configs/livekit.yaml.template}"
OUTPUT="${2:-configs/livekit.yaml}"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${LIVEKIT_API_KEY:?Set LIVEKIT_API_KEY in .env}"
: "${LIVEKIT_API_SECRET:?Set LIVEKIT_API_SECRET in .env}"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "Missing template: $TEMPLATE" >&2
  exit 1
fi

python3 - <<PY
from pathlib import Path
import os

template = Path("${TEMPLATE}").read_text(encoding="utf-8")
key = os.environ["LIVEKIT_API_KEY"]
secret = os.environ["LIVEKIT_API_SECRET"]
out = (
    template.replace("__LIVEKIT_API_KEY__", key)
    .replace("__LIVEKIT_API_SECRET__", secret)
)
Path("${OUTPUT}").write_text(out, encoding="utf-8")
print(f"Wrote ${OUTPUT}")
PY