#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BOT_ESTIV_BACKUP_DIR:-/opt/bot-estiv/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
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

POSTGRES_USER="${POSTGRES_USER:-$(env_get POSTGRES_USER)}"
POSTGRES_DB="${POSTGRES_DB:-$(env_get POSTGRES_DB)}"
BACKUP_DIR="${BOT_ESTIV_BACKUP_DIR:-$(env_get BOT_ESTIV_BACKUP_DIR)}"
BACKUP_DIR="${BACKUP_DIR:-/opt/bot-estiv/backups}"

mkdir -p "${BACKUP_DIR}"

DB_FILE="${BACKUP_DIR}/bot-estiv-postgres-${STAMP}.dump"
MEDIA_FILE="${BACKUP_DIR}/bot-estiv-media-${STAMP}.tar.gz"

echo "Creando backup Postgres: ${DB_FILE}"
"${COMPOSE[@]}" exec -T postgres pg_dump -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-bot_estiv}" -Fc >"${DB_FILE}"

echo "Creando backup media: ${MEDIA_FILE}"
docker run --rm -v bot_estiv_media_data:/media:ro -v "${BACKUP_DIR}:/backup" alpine \
  tar -czf "/backup/$(basename "${MEDIA_FILE}")" -C /media .

find "${BACKUP_DIR}" -type f -name 'bot-estiv-*' -mtime +"${BACKUP_RETENTION_DAYS:-14}" -delete

echo "Backup completado:"
echo "  ${DB_FILE}"
echo "  ${MEDIA_FILE}"
