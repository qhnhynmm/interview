#!/usr/bin/env bash
# Install Nginx site + Let's Encrypt SSL for aurelia.io.vn
# Run on the VPS (sudo): ./scripts/setup-nginx-aurelia.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SITE_NAME="aurelia.io.vn"
CONF_SRC="${REPO_ROOT}/configs/nginx/${SITE_NAME}.conf"
CONF_DST="/etc/nginx/sites-available/${SITE_NAME}"

if [[ ! -f "$CONF_SRC" ]]; then
  echo "Missing ${CONF_SRC}"
  exit 1
fi

if ! command -v nginx >/dev/null 2>&1; then
  echo "Installing nginx + certbot..."
  sudo apt-get update
  sudo apt-get install -y nginx certbot python3-certbot-nginx
fi

sudo cp "$CONF_SRC" "$CONF_DST"
sudo ln -sf "$CONF_DST" "/etc/nginx/sites-enabled/${SITE_NAME}"
sudo nginx -t
sudo systemctl reload nginx

echo "Requesting SSL certificates..."
sudo certbot --nginx \
  -d aurelia.io.vn \
  -d www.aurelia.io.vn \
  -d livekit.aurelia.io.vn \
  --non-interactive --agree-tos -m admin@aurelia.io.vn || {
  echo "Certbot failed — run manually: sudo certbot --nginx -d aurelia.io.vn -d www.aurelia.io.vn -d livekit.aurelia.io.vn"
  exit 1
}

echo "Done. Open https://aurelia.io.vn"