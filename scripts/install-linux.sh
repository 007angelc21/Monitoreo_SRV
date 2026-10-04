#!/usr/bin/env bash
# Instalador desatendido — Monitoreo SRV en Ubuntu Server 24.04 (VM o físico)
# Uso: sudo ./scripts/install-linux.sh [--dir /opt/monitoreo_srv] [--repo URL]
#      [--domain monitoreo.midominio.local] [--admin-email admin@x] [--admin-pass '...']
#      [--db-pass '...']  (passwords se generan si se omiten y se muestran al final)
set -euo pipefail

DIR="/opt/monitoreo_srv"; REPO=""; DOMAIN="localhost"
ADMIN_EMAIL="admin@monitoreo.local"; ADMIN_PASS=""; DB_PASS=""
while [ $# -gt 0 ]; do case "$1" in
  --dir) DIR="$2"; shift 2;; --repo) REPO="$2"; shift 2;;
  --domain) DOMAIN="$2"; shift 2;; --admin-email) ADMIN_EMAIL="$2"; shift 2;;
  --admin-pass) ADMIN_PASS="$2"; shift 2;; --db-pass) DB_PASS="$2"; shift 2;;
  *) echo "Opción desconocida: $1"; exit 1;; esac; done

[ "$(id -u)" -eq 0 ] || { echo "Ejecutar como root (sudo)"; exit 1; }
command -v openssl >/dev/null || { apt-get update -qq; apt-get install -y -qq openssl; }
[ -z "$ADMIN_PASS" ] && ADMIN_PASS="$(openssl rand -base64 16 | tr -d '/+=' | head -c 16)"
[ -z "$DB_PASS" ] && DB_PASS="$(openssl rand -base64 18 | tr -d '/+=' | head -c 20)"
SECRET_KEY="$(openssl rand -hex 32)"
FERNET_KEY="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' 2>/dev/null || echo '')"
if [ -z "$FERNET_KEY" ]; then apt-get install -y -qq python3-cryptography 2>/dev/null || pip install -q cryptography 2>/dev/null || true
  FERNET_KEY="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"; fi

echo "[1/8] Paquetes base..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq docker.io docker-compose-plugin postgresql-16 ufw curl git
systemctl enable --now docker postgresql

echo "[2/8] PostgreSQL nativo (BD única)..."
su postgres -c "psql -c \"ALTER USER postgres PASSWORD '$DB_PASS';\""
su postgres -c "psql -tAc 'SELECT 1 FROM pg_database WHERE datname='"'"'monitoreo_srv'"'"''" | grep -q 1 \
  || su postgres -c "createdb -O postgres monitoreo_srv"
PGVER=$(psql --version | grep -oP '\d+' | head -1); PGVER=${PGVER:-16}
CONF="/etc/postgresql/$PGVER/main/postgresql.conf"; HBA="/etc/postgresql/$PGVER/main/pg_hba.conf"
grep -q "^listen_addresses" "$CONF" && sed -i "s/^listen_addresses.*/listen_addresses = '*'" "$CONF" \
  || echo "listen_addresses = '*'" >> "$CONF"
grep -q "172.16.0.0/12" "$HBA" || echo "host monitoreo_srv postgres 172.16.0.0/12 scram-sha-256" >> "$HBA"
systemctl reload postgresql

echo "[3/8] Proyecto en $DIR..."
if [ ! -d "$DIR/.git" ]; then
  [ -n "$REPO" ] && git clone "$REPO" "$DIR" || { echo "Sin repo: copie el proyecto en $DIR y reintente (--repo URL)"; exit 1; }
fi

echo "[4/8] Archivo .env..."
[ -f "$DIR/.env" ] || cp "$DIR/.env.example" "$DIR/.env"
set_kv() { grep -q "^$1=" "$DIR/.env" && sed -i "s|^$1=.*|$1=$2|" "$DIR/.env" || echo "$1=$2" >> "$DIR/.env"; }
set_kv POSTGRES_PASSWORD "$DB_PASS"
set_kv DATABASE_URL "postgresql://postgres:${DB_PASS}@localhost:5432/monitoreo_srv"
set_kv SECRET_KEY "$SECRET_KEY"
set_kv FERNET_KEY "$FERNET_KEY"
set_kv DOMAIN "$DOMAIN"

echo "[5/8] Build y arranque..."
cd "$DIR"
docker compose build backend frontend
docker compose up -d
echo "Esperando backend..."
for i in $(seq 1 40); do
  docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" 2>/dev/null && break
  sleep 5
done

echo "[6/8] Migraciones..."
docker compose exec -T backend alembic upgrade head || echo "(alembic omitido: verifique manualmente)"

echo "[7/8] Administrador ($ADMIN_EMAIL)..."
curl -sk -X POST "https://localhost/api/auth/bootstrap?email=$(printf %s "$ADMIN_EMAIL" | jq -sRr @uri 2>/dev/null || printf %s "$ADMIN_EMAIL")&password=$ADMIN_PASS" || true

echo "[8/8] Firewall..."
ufw --force enable >/dev/null 2>&1 || true
ufw allow OpenSSH >/dev/null 2>&1 || true
ufw allow 80,443/tcp >/dev/null 2>&1 || true

echo ""
echo "=============================================="
echo " Monitoreo SRV instalado"
echo " App:      https://$DOMAIN/  (acepte cert autofirmado)"
echo " API docs: https://$DOMAIN/api/docs"
echo " Grafana:  http://$DOMAIN:3001  (docker compose --profile observability up -d grafana)"
echo " Login:    $ADMIN_EMAIL / $ADMIN_PASS"
echo " DB local: postgres / $DB_PASS  (GUARDE ESTOS DATOS)"
echo " Siguiente: playbooks node-exporter/promtail en sus servidores"
echo "=============================================="
