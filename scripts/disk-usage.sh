#!/usr/bin/env bash
# Snapshot de uso de disco por carpeta para node_exporter textfile collector.
# du limitado a 1 filesystem y profundidad 2 para no saturar I/O.
# Cron diario nocturno (ver playbook). Requiere lectura; se ejecuta como root.
set -euo pipefail
DIR="${TEXTFILE_DIR:-/var/lib/node_exporter/textfile_collector}"
OUT="$DIR/disk_usage.prom"
TMP="$DIR/disk_usage.prom.$$"
DEPTH="${DU_DEPTH:-2}"
mkdir -p "$DIR"
{
  echo "# HELP diskusage_bytes Uso de disco por carpeta (du)"
  echo "# TYPE diskusage_bytes gauge"
  timeout 600 nice -n 10 ionice -c3 du -x -d "$DEPTH" -B1 / 2>/dev/null | sort -rn | head -n 60 | while read -r bytes path; do
    case "$path" in /proc*|/sys*|/dev*) continue;; esac
    esc=$(printf '%s' "$path" | sed 's/\\/\\\\/g; s/"/\\"/g')
    echo "diskusage_bytes{path=\"$esc\"} $bytes"
  done
} > "$TMP"
mv "$TMP" "$OUT"
