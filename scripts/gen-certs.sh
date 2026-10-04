#!/usr/bin/env bash
# Cert autofirmado para Caddy/backend en red interna. Prod: use CA interna o Let's Encrypt.
set -euo pipefail
mkdir -p docker/certs
openssl req -x509 -newkey rsa:4096 -sha256 -days 825 -nodes \
  -keyout docker/certs/privkey.pem -out docker/certs/fullchain.pem \
  -subj "/CN=${DOMAIN:-monitoreo.local}" \
  -addext "subjectAltName=DNS:${DOMAIN:-monitoreo.local},IP:127.0.0.1"
echo "Cert en docker/certs/. Monte en Caddyfile (linea tls comentada) si no usa 'tls internal'."
