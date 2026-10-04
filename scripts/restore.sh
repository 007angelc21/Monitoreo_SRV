#!/usr/bin/env bash
# Restore Postgres. Uso: ./scripts/restore.sh backups/backup-XXXX.sql
set -euo pipefail
[ $# -eq 1 ] || { echo "Uso: $0 <backup.sql>"; exit 1; }
docker compose exec -T db psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-monitoreo_srv}" < "$1"
echo "Restore OK desde $1"
