#!/usr/bin/env bash
# Deploy / update Aurelia stack trên AWS EC2 (Linux + Docker host network).
# Usage: ./scripts/aws/deploy.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.aws.yml"

if [[ ! -f .env ]]; then
  if [[ -f .env.aws.example ]]; then
    echo "Chưa có .env — copy từ .env.aws.example và chỉnh secret/API key."
    cp .env.aws.example .env
    echo "Đã tạo .env — sửa file rồi chạy lại deploy."
    exit 1
  fi
  echo "Missing .env"
  exit 1
fi

# Gợi ý set FRONTEND_URL theo IP nếu vẫn là placeholder
PUBLIC_IP="$(curl -fsSL https://checkip.amazonaws.com 2>/dev/null | tr -d '[:space:]' || true)"
if [[ -n "$PUBLIC_IP" ]] && grep -q 'YOUR_EC2_PUBLIC_IP' .env 2>/dev/null; then
  sed -i "s|YOUR_EC2_PUBLIC_IP|${PUBLIC_IP}|g" .env
  echo "Đã thay YOUR_EC2_PUBLIC_IP → ${PUBLIC_IP} trong .env"
fi

echo "Generating LiveKit config from .env..."
./scripts/generate-livekit-config.sh configs/livekit.aws.yaml.template configs/livekit.aws.yaml

echo "Building and starting Aurelia on AWS..."
$COMPOSE up -d --build

echo ""
echo "=== Deploy xong ==="
$COMPOSE ps
echo ""
echo "Frontend (qua nginx): http://${PUBLIC_IP:-localhost}"
echo "Backend docs (nội bộ): http://127.0.0.1:8000/docs"
echo "Health: curl -s http://127.0.0.1:8000/health"