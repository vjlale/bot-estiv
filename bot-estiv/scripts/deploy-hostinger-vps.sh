#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose --env-file "${ROOT_DIR}/.env" -f "${ROOT_DIR}/infra/docker-compose.vps.yml")

if [[ ! -f "${ROOT_DIR}/.env" ]]; then
  echo "Falta ${ROOT_DIR}/.env. Copia .env.vps.example a .env y completa secretos reales."
  exit 1
fi

env_get() {
  local key="$1"
  local value
  value="$(awk -v key="${key}" 'BEGIN { FS = "=" } $1 == key { sub(/^[^=]*=/, ""); print; exit }' "${ROOT_DIR}/.env")"
  value="${value%$'\r'}"
  value="${value%\"}"
  value="${value#\"}"
  printf '%s' "${value}"
}

BOT_ESTIV_DASHBOARD_DOMAIN="${BOT_ESTIV_DASHBOARD_DOMAIN:-$(env_get BOT_ESTIV_DASHBOARD_DOMAIN)}"
BOT_ESTIV_API_DOMAIN="${BOT_ESTIV_API_DOMAIN:-$(env_get BOT_ESTIV_API_DOMAIN)}"
BOT_ESTIV_LETSENCRYPT_EMAIL="${BOT_ESTIV_LETSENCRYPT_EMAIL:-$(env_get BOT_ESTIV_LETSENCRYPT_EMAIL)}"

: "${BOT_ESTIV_DASHBOARD_DOMAIN:?Falta BOT_ESTIV_DASHBOARD_DOMAIN en .env}"
: "${BOT_ESTIV_API_DOMAIN:?Falta BOT_ESTIV_API_DOMAIN en .env}"
: "${BOT_ESTIV_LETSENCRYPT_EMAIL:?Falta BOT_ESTIV_LETSENCRYPT_EMAIL en .env}"

install_nginx_http_only() {
  sudo tee /etc/nginx/sites-available/bot-estiv >/dev/null <<EOF
server {
    listen 80;
    server_name ${BOT_ESTIV_DASHBOARD_DOMAIN} ${BOT_ESTIV_API_DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 200 "Bot Estiv VPS listo para emitir certificados.\\n";
        add_header Content-Type text/plain;
    }
}
EOF
  sudo ln -sf /etc/nginx/sites-available/bot-estiv /etc/nginx/sites-enabled/bot-estiv
  sudo nginx -t
  sudo systemctl reload nginx
}

install_nginx_https() {
  sed \
    -e "s/bot-estiv.gardenswood.com.ar/${BOT_ESTIV_DASHBOARD_DOMAIN}/g" \
    -e "s/api.bot-estiv.gardenswood.com.ar/${BOT_ESTIV_API_DOMAIN}/g" \
    "${ROOT_DIR}/infra/nginx/bot-estiv.conf" | sudo tee /etc/nginx/sites-available/bot-estiv >/dev/null
  sudo ln -sf /etc/nginx/sites-available/bot-estiv /etc/nginx/sites-enabled/bot-estiv
  sudo nginx -t
  sudo systemctl reload nginx
}

echo "Construyendo imagenes..."
"${COMPOSE[@]}" build

echo "Levantando Postgres y Redis..."
"${COMPOSE[@]}" up -d postgres redis

echo "Ejecutando migraciones..."
"${COMPOSE[@]}" run --rm api alembic upgrade head

echo "Levantando API, worker y dashboard..."
"${COMPOSE[@]}" up -d api worker dashboard

if [[ "${SKIP_TLS:-0}" != "1" ]]; then
  install_nginx_http_only
  sudo certbot certonly \
    --webroot \
    --webroot-path /var/www/html \
    --email "${BOT_ESTIV_LETSENCRYPT_EMAIL}" \
    --agree-tos \
    --no-eff-email \
    -d "${BOT_ESTIV_DASHBOARD_DOMAIN}"
  sudo certbot certonly \
    --webroot \
    --webroot-path /var/www/html \
    --email "${BOT_ESTIV_LETSENCRYPT_EMAIL}" \
    --agree-tos \
    --no-eff-email \
    -d "${BOT_ESTIV_API_DOMAIN}"
  install_nginx_https
else
  echo "SKIP_TLS=1: se omitio Certbot/Nginx HTTPS."
fi

"${COMPOSE[@]}" ps
echo "Deploy VPS completado. Verifica https://${BOT_ESTIV_API_DOMAIN}/health y https://${BOT_ESTIV_DASHBOARD_DOMAIN}."
