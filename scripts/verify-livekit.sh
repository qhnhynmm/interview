#!/usr/bin/env bash
# Quick health check for local LiveKit (Phase 0).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

HOST="${LIVEKIT_HOST:-127.0.0.1}"
PORT="${LIVEKIT_PORT:-7880}"
API_KEY="${LIVEKIT_API_KEY:?Set LIVEKIT_API_KEY in .env}"
API_SECRET="${LIVEKIT_API_SECRET:?Set LIVEKIT_API_SECRET in .env}"

if [[ ! -f configs/livekit.yaml ]]; then
  ./scripts/generate-livekit-config.sh
fi

echo "==> LiveKit TCP ${HOST}:${PORT}"
python3 - <<PY
import socket
s = socket.socket()
s.settimeout(3)
try:
    s.connect(("${HOST}", ${PORT}))
except OSError as exc:
    raise SystemExit(f"LiveKit not reachable: {exc}") from exc
finally:
    s.close()
print("port open")
PY

echo "==> ListRooms API (optional — pip install livekit-api)"
python3 - <<PY || echo "(skipped — livekit-api not installed)"
import asyncio
import importlib.util
import sys

if importlib.util.find_spec("livekit") is None:
    sys.exit(1)

from livekit.api import LiveKitAPI, ListRoomsRequest

async def main():
    async with LiveKitAPI("http://${HOST}:${PORT}", "${API_KEY}", "${API_SECRET}") as client:
        resp = await client.room.list_rooms(ListRoomsRequest())
        print(f"rooms: {len(resp.rooms)}")
        for room in resp.rooms:
            print(f"  - {room.name} ({room.num_participants} participants)")

asyncio.run(main())
PY

echo "OK — LiveKit is reachable at ws://${HOST}:${PORT}"