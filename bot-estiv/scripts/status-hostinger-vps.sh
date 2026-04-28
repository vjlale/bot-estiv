#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose --env-file "${ROOT_DIR}/.env" -f "${ROOT_DIR}/infra/docker-compose.vps.yml")

if [[ ! -f "${ROOT_DIR}/.env" ]]; then
  echo "Falta ${ROOT_DIR}/.env."
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

echo "== Docker Compose =="
"${COMPOSE[@]}" ps

echo
echo "== API health local =="
if command -v curl >/dev/null 2>&1; then
  curl -fsS http://127.0.0.1:8000/health || true
  echo
else
  echo "curl no esta instalado"
fi

echo
echo "== Nginx =="
systemctl is-active nginx || true

echo
echo "== Certificados =="
if command -v certbot >/dev/null 2>&1; then
  sudo certbot certificates | sed -n '/Certificate Name:/,/Expiry Date:/p' || true
else
  echo "certbot no esta instalado"
fi

echo
echo "== URLs esperadas =="
echo "Dashboard: https://${BOT_ESTIV_DASHBOARD_DOMAIN:-<sin-dominio>}"
echo "API health: https://${BOT_ESTIV_API_DOMAIN:-<sin-dominio>}/health"
echo "Twilio webhook: https://${BOT_ESTIV_API_DOMAIN:-<sin-dominio>}/webhook/twilio"
