#!/usr/bin/env bash
# Gắn domain aurelia.io.vn lên EC2: Nginx + Let's Encrypt + cập nhật .env + redeploy.
#
# Trước khi chạy — Mat Bao DNS (A record → Elastic IP):
#   @       → 54.79.17.205
#   www     → 54.79.17.205
#   livekit → 54.79.17.205
#
# Usage (trên EC2, sau khi DNS propagate):
#   ./scripts/aws/setup-domain.sh
#   ./scripts/aws/setup-domain.sh --email you@example.com

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

DOMAIN="aurelia.io.vn"
WWW="www.${DOMAIN}"
LIVEKIT_HOST="livekit.${DOMAIN}"
CERT_EMAIL="${CERT_EMAIL:-admin@${DOMAIN}}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --email) CERT_EMAIL="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

PUBLIC_IP="$(curl -fsSL https://checkip.amazonaws.com 2>/dev/null | tr -d '[:space:]' || true)"
RESOLVED="$(dig +short "${DOMAIN}" A @8.8.8.8 2>/dev/null | head -1 || true)"

echo "=== Aurelia domain setup ==="
echo "EC2 public IP: ${PUBLIC_IP:-unknown}"
echo "DNS ${DOMAIN} → ${RESOLVED:-<no A record>}"

NGINX_CONF="${REPO_ROOT}/configs/nginx/${DOMAIN}.conf"
if [[ ! -f "$NGINX_CONF" ]]; then
  echo "Missing ${NGINX_CONF}"
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  SUDO=sudo
else
  SUDO=""
fi

$SUDO apt-get update -qq
$SUDO apt-get install -y -qq nginx certbot python3-certbot-nginx dnsutils >/dev/null

$SUDO cp "$NGINX_CONF" "/etc/nginx/sites-available/${DOMAIN}"
$SUDO ln -sf "/etc/nginx/sites-available/${DOMAIN}" "/etc/nginx/sites-enabled/${DOMAIN}"
# Giữ IP-only fallback (aurelia.aws.conf) nếu đã cài
$SUDO nginx -t
$SUDO systemctl reload nginx
echo "Nginx: HTTP proxy cho ${DOMAIN}, ${WWW}, ${LIVEKIT_HOST}"

if [[ -z "$RESOLVED" || "$RESOLVED" != "$PUBLIC_IP" ]]; then
  echo ""
  echo "DNS chưa trỏ đúng IP. Thêm tại Mat Bao (ns1.matbao.vn):"
  echo "  Loại A | Tên @       | Giá trị ${PUBLIC_IP}"
  echo "  Loại A | Tên www     | Giá trị ${PUBLIC_IP}"
  echo "  Loại A | Tên livekit | Giá trị ${PUBLIC_IP}"
  echo ""
  echo "Đợi 5–30 phút rồi chạy lại: ./scripts/aws/setup-domain.sh"
  exit 0
fi

echo "DNS OK — xin chứng chỉ SSL..."
if $SUDO certbot --nginx \
  -d "${DOMAIN}" -d "${WWW}" -d "${LIVEKIT_HOST}" \
  --non-interactive --agree-tos -m "${CERT_EMAIL}" \
  --redirect; then
  echo "SSL OK"
else
  echo "Certbot thất bại — thử lại sau khi DNS ổn định:"
  echo "  sudo certbot --nginx -d ${DOMAIN} -d ${WWW} -d ${LIVEKIT_HOST}"
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "Missing .env — chạy deploy trước."
  exit 1
fi

# Cập nhật URL production
sed -i "s|^FRONTEND_URL=.*|FRONTEND_URL=https://${DOMAIN}|" .env
sed -i "s|^LIVEKIT_PUBLIC_URL=.*|LIVEKIT_PUBLIC_URL=wss://${LIVEKIT_HOST}|" .env

echo "Đã cập nhật .env — rebuild stack..."
if groups | grep -q docker || id -nG | grep -q docker; then
  ./scripts/aws/deploy.sh
else
  sg docker -c "./scripts/aws/deploy.sh"
fi

echo ""
echo "=== Domain sẵn sàng ==="
echo "  Web:     https://${DOMAIN}"
echo "  LiveKit: wss://${LIVEKIT_HOST}"