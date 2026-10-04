#!/usr/bin/env bash
# Snapshot de top aplicaciones para node_exporter textfile collector.
# Cron cada 2 min (ver playbook). No requiere privilegios salvo ps.
set -euo pipefail
DIR="${TEXTFILE_DIR:-/var/lib/node_exporter/textfile_collector}"
OUT="$DIR/top_apps.prom"
TMP="$DIR/top_apps.prom.$$"
mkdir -p "$DIR"
ps -eo comm=,pcpu=,pmem= --sort=-pcpu 2>/dev/null | head -n 100 | awk '
  { cpu[$1]+=$2; if ($3+0>mem[$1]+0) mem[$1]=$3; n[$1]++ }
  END {
    print "# HELP topapp_cpu_percent CPU total por aplicacion";
    print "# TYPE topapp_cpu_percent gauge";
    for (a in cpu) { gsub(/["\\]/, "", a); if (a!="") printf "topapp_cpu_percent{app=\"%s\"} %.2f\n", a, cpu[a] }
    print "# HELP topapp_mem_percent MEM max por proceso de la aplicacion";
    print "# TYPE topapp_mem_percent gauge";
    for (a in mem) { gsub(/["\\]/, "", a); if (a!="") printf "topapp_mem_percent{app=\"%s\"} %.2f\n", a, mem[a] }
    print "# HELP topapp_processes Numero de procesos por aplicacion";
    print "# TYPE topapp_processes gauge";
    for (a in n) { gsub(/["\\]/, "", a); if (a!="") printf "topapp_processes{app=\"%s\"} %d\n", a, n[a] }
  }' > "$TMP"
mv "$TMP" "$OUT"
