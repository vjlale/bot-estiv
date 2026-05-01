#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${BOT_ESTIV_ROOT:-/opt/bot-estiv}"
SSH_PORT="${SSH_PORT:-22}"
ENABLE_UFW="${BOT_ESTIV_ENABLE_UFW:-0}"
EXTRA_UFW_PORTS="${BOT_ESTIV_EXTRA_UFW_PORTS:-}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Ejecuta este script con sudo: sudo BOT_ESTIV_ROOT=${APP_ROOT} bash scripts/setup-hostinger-vps.sh"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates \
  certbot \
  curl \
  git \
  gnupg \
  lsb-release \
  nginx \
  ufw

install -m 0755 -d /etc/apt/keyrings
if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
fi

UBUNTU_CODENAME="$(. /etc/os-release && echo "${VERSION_CODENAME}")"
cat >/etc/apt/sources.list.d/docker.list <<EOF
deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME} stable
EOF

apt-get update
apt-get install -y --no-install-recommends docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

install -m 0755 -d \
  "${APP_ROOT}" \
  "${APP_ROOT}/app" \
  "${APP_ROOT}/backups" \
  "${APP_ROOT}/branding" \
  "${APP_ROOT}/media" \
  "${APP_ROOT}/secrets"

if [[ "${ENABLE_UFW}" == "1" ]]; then
  ufw allow "${SSH_PORT}/tcp"
  ufw allow 80/tcp
  ufw allow 443/tcp
  for port in ${EXTRA_UFW_PORTS}; do
    ufw allow "${port}/tcp"
  done
  ufw --force enable
else
  echo "UFW instalado pero no activado. Usa BOT_ESTIV_ENABLE_UFW=1 si ya validaste puertos del otro bot."
fi

systemctl enable --now docker
systemctl enable --now nginx

cat >/etc/logrotate.d/bot-estiv-docker <<'EOF'
/var/lib/docker/containers/*/*.log {
  rotate 7
  daily
  compress
  size=50M
  missingok
  delaycompress
  copytruncate
}
EOF

echo "VPS base listo. Siguiente paso: clonar el repo en ${APP_ROOT}/app y completar bot-estiv/.env."
