#!/usr/bin/env bash
# Backup Postgres + targets. Uso: ./scripts/backup.sh [dir]
set -euo pipefail
OUT="${1:-./backups}/backup-$(date +%F-%H%M).sql"
mkdir -p "$(dirname "$OUT")"
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-postgres}" "${POSTGRES_DB:-monitoreo_srv}" > "$OUT"
cp monitoring/prometheus/targets/servers.json "$(dirname "$OUT")/targets-$(date +%F-%H%M).json" || true
echo "Backup en $OUT"
