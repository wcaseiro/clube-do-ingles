#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/var/www/clube-do-ingles"
DOMAIN="clube-do-ingles.4cloud.tech"

if [[ $EUID -ne 0 ]]; then
  echo "Execute como root: sudo bash deploy/install-ubuntu.sh"
  exit 1
fi

apt update
apt install -y python3 python3-venv python3-pip nginx

mkdir -p "$APP_DIR"
rsync -a --exclude 'backend/venv' --exclude 'backend/clube_do_ingles.db' ./ "$APP_DIR/"
chown -R www-data:www-data "$APP_DIR"

cd "$APP_DIR/backend"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp -n .env.example .env || true
python -m app.seed

cp "$APP_DIR/deploy/clube-do-ingles.service" /etc/systemd/system/clube-do-ingles.service
systemctl daemon-reload
systemctl enable clube-do-ingles
systemctl restart clube-do-ingles

cp "$APP_DIR/deploy/nginx.conf" "/etc/nginx/sites-available/$DOMAIN"
ln -sf "/etc/nginx/sites-available/$DOMAIN" "/etc/nginx/sites-enabled/$DOMAIN"
nginx -t
systemctl reload nginx

echo "Instalado. Acesse http://$DOMAIN depois de apontar o DNS."
echo "Para SSL: apt install -y certbot python3-certbot-nginx && certbot --nginx -d $DOMAIN"
