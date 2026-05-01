#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose --env-file "${ROOT_DIR}/.env" -f "${ROOT_DIR}/infra/docker-compose.vps.yml")

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <backup-postgres.dump> [backup-media.tar.gz]"
  exit 1
fi

DB_BACKUP="$1"
MEDIA_BACKUP="${2:-}"

if [[ ! -f "${ROOT_DIR}/.env" ]]; then
  echo "Falta ${ROOT_DIR}/.env."
  exit 1
fi

if [[ ! -f "${DB_BACKUP}" ]]; then
  echo "No existe el backup Postgres: ${DB_BACKUP}"
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

read -r -p "Esto reemplazara la base ${POSTGRES_DB:-bot_estiv}. Escribi RESTORE para continuar: " CONFIRM
if [[ "${CONFIRM}" != "RESTORE" ]]; then
  echo "Restore cancelado."
  exit 1
fi

"${COMPOSE[@]}" up -d postgres redis

echo "Restaurando Postgres desde ${DB_BACKUP}..."
"${COMPOSE[@]}" exec -T postgres dropdb -U "${POSTGRES_USER:-postgres}" --if-exists "${POSTGRES_DB:-bot_estiv}"
"${COMPOSE[@]}" exec -T postgres createdb -U "${POSTGRES_USER:-postgres}" "${POSTGRES_DB:-bot_estiv}"
"${COMPOSE[@]}" exec -T postgres psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-bot_estiv}" -f /docker-entrypoint-initdb.d/init-db.sql
"${COMPOSE[@]}" exec -T postgres pg_restore -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-bot_estiv}" --clean --if-exists <"${DB_BACKUP}"

if [[ -n "${MEDIA_BACKUP}" ]]; then
  if [[ ! -f "${MEDIA_BACKUP}" ]]; then
    echo "No existe el backup media: ${MEDIA_BACKUP}"
    exit 1
  fi
  MEDIA_BACKUP_ABS="$(cd "$(dirname "${MEDIA_BACKUP}")" && pwd)/$(basename "${MEDIA_BACKUP}")"
  echo "Restaurando media desde ${MEDIA_BACKUP}..."
  docker run --rm -v bot_estiv_media_data:/media -v "${MEDIA_BACKUP_ABS}:/backup/media.tar.gz:ro" alpine \
    sh -c 'rm -rf /media/* && tar -xzf /backup/media.tar.gz -C /media'
fi

echo "Restore completado. Ejecuta scripts/deploy-hostinger-vps.sh para levantar servicios con migraciones."
