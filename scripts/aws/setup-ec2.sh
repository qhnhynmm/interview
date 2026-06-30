#!/usr/bin/env bash
# Bootstrap Ubuntu 22.04 EC2 for Aurelia (region khuyến nghị: ap-southeast-2 Sydney).
# Chạy TRÊN EC2 sau khi SSH vào:
#   curl -fsSL <raw-url>/scripts/aws/setup-ec2.sh | bash
# hoặc clone repo rồi:  ./scripts/aws/setup-ec2.sh
#
# Trước đó — AWS Console → EC2 → Security Group, mở:
#   TCP  22    SSH (chỉ IP của bạn)
#   TCP  80    HTTP
#   TCP  443   HTTPS (khi có SSL)
#   TCP  7880  LiveKit signaling (nếu không qua nginx)
#   TCP  7881  LiveKit RTC TCP
#   UDP  50000-50100  WebRTC media (LiveKit — BẮT BUỘC)

set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Chạy với sudo: sudo ./scripts/aws/setup-ec2.sh"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git nginx

# Docker Engine + Compose plugin
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "${VERSION_CODENAME:-jammy}") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

usermod -aG docker "${SUDO_USER:-ubuntu}" 2>/dev/null || true

# Nginx site (IP-only default — sửa domain sau)
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ -f "${REPO_ROOT}/configs/nginx/aurelia.aws.conf" ]]; then
  cp "${REPO_ROOT}/configs/nginx/aurelia.aws.conf" /etc/nginx/sites-available/aurelia
  ln -sf /etc/nginx/sites-available/aurelia /etc/nginx/sites-enabled/aurelia
  rm -f /etc/nginx/sites-enabled/default
  nginx -t
  systemctl enable nginx
  systemctl reload nginx
fi

PUBLIC_IP="$(curl -fsSL https://checkip.amazonaws.com 2>/dev/null | tr -d '[:space:]' || true)"
echo ""
echo "=== EC2 bootstrap xong ==="
echo "Public IP: ${PUBLIC_IP:-<unknown>}"
echo ""
echo "Tiếp theo (user ubuntu, không cần sudo):"
echo "  1. clone repo vào ~/interview (hoặc git pull)"
echo "  2. cp .env.aws.example .env && chỉnh GEMINI_API_KEY, JWT_SECRET, FRONTEND_URL=http://${PUBLIC_IP}"
echo "  3. ./scripts/aws/deploy.sh"
echo "  4. Mở http://${PUBLIC_IP:-YOUR_IP}"
echo ""
echo "Gợi ý instance: t3.large (2 vCPU / 8GB) trở lên cho voice + MediaPipe."