#!/usr/bin/env bash
# UDYOGSETU - idempotent VM setup for the free single-VM deploy.
# Runs on Ubuntu 22.04 (e.g. Oracle Cloud Always Free Ampere A1).
#
# Usage:
#   chmod +x deploy/setup-vm.sh
#   sudo ./deploy/setup-vm.sh
#
# First run installs Docker + firewall and clones the repo. It then stops and
# asks you to fill in deploy/.env; re-run the script after editing to start
# the stack.

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/amulya-ajay/Udyogsetu-SIH-Project-.git}"
APP_DIR="${APP_DIR:-/opt/udyogsetu}"
SSH_PORT="${SSH_PORT:-22}"
API_PORT="${API_PORT:-8000}"

# --- 1. Base packages -----------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  echo "==> Installing Docker + compose plugin"
  apt-get update
  apt-get install -y ca-certificates curl git docker.io docker-compose-plugin
fi
systemctl enable --now docker

# --- 2. Firewall: SSH + API only (Postgres/Redis stay internal) ----------
install -d /etc/ufw/applications.d
cat >/etc/ufw/applications.d/udyogsetu-api <<EOF
[UdyogsetuAPI]
title=UDYOGSETU API
description=UDYOGSETU FastAPI backend (Vercel frontend -> :${API_PORT})
ports=${API_PORT}/tcp
EOF
ufw allow "${SSH_PORT}/tcp"
ufw allow UdyogsetuAPI
ufw --force enable

# --- 3. Repository ---------------------------------------------------------
echo "==> Repository at ${APP_DIR}"
if [ ! -d "${APP_DIR}/.git" ]; then
  git clone "${REPO_URL}" "${APP_DIR}"
else
  git -C "${APP_DIR}" fetch --quiet origin
  git -C "${APP_DIR}" reset --hard origin/main
fi

# --- 4. Configuration -------------------------------------------------------
if [ ! -f "${APP_DIR}/deploy/.env" ]; then
  echo "==> Creating deploy/.env from the template (no .env found)"
  cp "${APP_DIR}/deploy/.env.example" "${APP_DIR}/deploy/.env"
  echo
  echo "PLEASE EDIT ${APP_DIR}/deploy/.env and set:"
  echo "  - POSTGRES_PASSWORD / JWT_SECRET_KEY"
  echo "  - CORS_ORIGINS = your Vercel URL"
  echo "  - ALLOWED_HOSTS = this VM's public IP / hostname"
  echo "Then re-run: sudo ./${APP_DIR##*/}/deploy/setup-vm.sh"
  exit 1
fi

# --- 5. Start the stack (alembic runs automatically inside the container) --
echo "==> Starting postgres + redis + backend"
docker compose \
  --env-file "${APP_DIR}/deploy/.env" \
  -f "${APP_DIR}/deploy/docker-compose.yml" \
  up -d --build

# --- 6. Wait for health -----------------------------------------------------
echo "==> Waiting for /health"
for _ in $(seq 1 30); do
  if curl -sf "http://localhost:${API_PORT}/health" | grep -q '"healthy"'; then
    echo
    echo "==> OK: backend is healthy"
    curl -s "http://localhost:${API_PORT}/health"; echo
    echo
    echo "NEXT STEPS:"
    echo "  1) Vercel: set NEXT_PUBLIC_API_URL=http://<PUBLIC_IP>:${API_PORT}/api"
    echo "  2) Vercel: redeploy the frontend"
    echo "  3) Open https://<your-app>.vercel.app and log in"
    exit 0
  fi
  sleep 5
done

echo "ERROR: backend did not become healthy within 150s."
echo "Check logs: docker compose -f ${APP_DIR}/deploy/docker-compose.yml logs backend"
exit 1