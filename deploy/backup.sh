#!/usr/bin/env bash
# UDYOGSETU - nightly PostgreSQL backup to the VM disk.
# Install via cron (as root): sudo crontab deploy/crontab.example

set -euo pipefail

BACKUP_DIR="/var/backups/udyogsetu"
TS="$(date +%F_%H%M%S)"

if ! docker ps --format '{{.Names}}' | grep -q '^udyogsetu-postgres$'; then
  echo "ERROR: udyogsetu-postgres container is not running"
  exit 1
fi

install -d -m 0700 "${BACKUP_DIR}"  # note: install -o root tightens perms below

docker exec udyogsetu-postgres pg_dump -U udyogsetu -d udyogsetu -F custom -f /tmp/udyogsetu.dump
docker cp "udyogsetu-postgres:/tmp/udyogsetu.dump" "${BACKUP_DIR}/udyogsetu_${TS}.dump"
docker exec udyogsetu-postgres rm -f /tmp/udyogsetu.dump

chown root:root "${BACKUP_DIR}/udyogsetu_${TS}.dump"
chmod 0600 "${BACKUP_DIR}/udyogsetu_${TS}.dump"

# Keep 7 days of dumps.
find "${BACKUP_DIR}" -name 'udyogsetu_*.dump' -mtime +7 -delete

echo "Backup ok: ${BACKUP_DIR}/udyogsetu_${TS}.dump"