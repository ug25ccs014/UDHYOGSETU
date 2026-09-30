#!/usr/bin/env bash
set -euo pipefail

# Generates a self-signed TLS certificate for the local/demo reverse proxy.
# These are development certificates (CN=udyogsetu.local) and are gitignored.
# Replace them with real certificates in front of a production deployment.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERT_DIR="$REPO_ROOT/infrastructure/nginx/certs"
mkdir -p "$CERT_DIR"

openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout "$CERT_DIR/key.pem" \
  -out "$CERT_DIR/cert.pem" \
  -days 3650 \
  -subj "/CN=udyogsetu.local" \
  -addext "subjectAltName=DNS:localhost,DNS:udyogsetu.local,IP:127.0.0.1" \
  >/dev/null 2>&1

echo "Self-signed certs written to $CERT_DIR (cert.pem, key.pem)"
echo "Add a .gitkeep to keep the directory tracked:" 
test -f "$CERT_DIR/.gitkeep" || touch "$CERT_DIR/.gitkeep"