#!/usr/bin/env bash
# Deploy Aurelia lên EC2 từ máy local (SSH + git pull + rebuild).
# Usage:
#   ./scripts/aws/remote-deploy.sh
#   SSH_KEY=~/Downloads/aurelia_key.pem EC2_HOST=54.79.17.205 ./scripts/aws/remote-deploy.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

EC2_HOST="${EC2_HOST:-54.79.17.205}"
EC2_USER="${EC2_USER:-ubuntu}"
SSH_KEY="${SSH_KEY:-$HOME/Downloads/aurelia_key.pem}"
GIT_BRANCH="${GIT_BRANCH:-main}"

if [[ ! -f "$SSH_KEY" ]]; then
  echo "Không tìm thấy SSH key: $SSH_KEY"
  echo "Đặt SSH_KEY=/path/to/aurelia_key.pem rồi chạy lại."
  exit 1
fi

chmod 600 "$SSH_KEY" 2>/dev/null || true

echo "=== Aurelia remote deploy ==="
echo "Host: ${EC2_USER}@${EC2_HOST}"
echo "Branch: ${GIT_BRANCH}"
echo ""

ssh -i "$SSH_KEY" \
  -o BatchMode=yes \
  -o ConnectTimeout=15 \
  -o StrictHostKeyChecking=accept-new \
  "${EC2_USER}@${EC2_HOST}" bash -s <<REMOTE
set -euo pipefail
cd ~/interview
echo "Git pull..."
git fetch origin ${GIT_BRANCH}
git checkout ${GIT_BRANCH}
git pull --ff-only origin ${GIT_BRANCH}
echo "Generate LiveKit config..."
./scripts/generate-livekit-config.sh configs/livekit.aws.yaml.template configs/livekit.aws.yaml
echo "Docker rebuild..."
if groups | grep -q docker || id -nG | grep -q docker; then
  ./scripts/aws/deploy.sh
else
  sg docker -c "./scripts/aws/deploy.sh"
fi
echo ""
echo "=== Remote deploy xong ==="
docker compose -f docker-compose.yml -f docker-compose.aws.yml ps
REMOTE

echo ""
echo "Kiểm tra production:"
echo "  curl -sI https://aurelia.io.vn | head -3"
echo "  curl -s https://aurelia.io.vn/api/v1/auth/login -X POST -H 'Content-Type: application/json' -d '{}'"