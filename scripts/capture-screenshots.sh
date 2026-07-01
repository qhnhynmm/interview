#!/usr/bin/env bash
# Capture README screenshots end-to-end (requires stack running on localhost).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

BASE="${SCREENSHOT_BASE:-http://localhost:8080}"
API="${SCREENSHOT_API:-http://localhost:8000}"

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1"; exit 1; }
}
need curl
need python3
need node

if [[ ! -d node_modules/puppeteer-core ]]; then
  echo "Installing puppeteer-core (one-time)…"
  npm install --no-save puppeteer-core
fi

EMAIL="screenshot-$(date +%s)@demo.com"
PASS="demo12345"
USER="screenshot_$(date +%s)"

echo "==> Register HR user ${EMAIL}"
TOKEN=$(curl -sf -X POST "${API}/api/v1/auth/register" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"${USER}\",\"email\":\"${EMAIL}\",\"password\":\"${PASS}\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

create_interview() {
  local name="$1"
  local cv_file
  cv_file="$(mktemp)"
  echo "Python, FastAPI, PostgreSQL, 5 years backend experience" >"$cv_file"
  curl -sf -X POST "${API}/api/v1/interviews/generate-link" \
    -H "Authorization: Bearer ${TOKEN}" \
    -F "candidate_name=${name}" \
    -F "candidate_email=${name// /_}@demo.com" \
    -F "position=Backend Engineer" \
    -F "jd_text=Build scalable REST APIs with Python, FastAPI, and PostgreSQL. DSA required." \
    -F "interview_language=vi" \
    -F "seniority=Mid" \
    -F "cv_file=@${cv_file};filename=cv.txt" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])"
  rm -f "$cv_file"
}

echo "==> Create interviews for screenshots"
ID_RULES=$(create_interview "Nguyen Van A")
ID_CODE=$(create_interview "Tran Minh Code")
ID_DONE=$(create_interview "Le Thi Report")

echo "   rules=${ID_RULES}  code=${ID_CODE}  done=${ID_DONE}"

echo "==> Seed code + completed demo data"
(cd backend && PYTHONPATH=. .venv/bin/python ../scripts/seed-screenshot-data.py --interview-id "$ID_CODE" --mode code)
(cd backend && PYTHONPATH=. .venv/bin/python ../scripts/seed-screenshot-data.py --interview-id "$ID_DONE" --mode completed)

echo "==> Capture screenshots"
node scripts/capture-screenshots.mjs \
  --base "$BASE" \
  --api "$API" \
  --token "$TOKEN" \
  --interview-rules "$ID_RULES" \
  --interview-code "$ID_CODE" \
  --interview-done "$ID_DONE"

echo ""
echo "Screenshots saved to docs/screenshots/"
ls -1 docs/screenshots/*.png