# Despliegue en Ubuntu Server 24.04

Esta instalación usa Docker Compose: PostgreSQL, Redis, Prometheus, Alertmanager, backend, frontend y Caddy. PostgreSQL se mantiene en el volumen Docker `pgdata`; no hace falta instalar una base de datos en Ubuntu. Ejecuta los comandos desde una cuenta con `sudo`.

## 1. Preparar Ubuntu y Docker

```bash
sudo apt update
sudo apt install -y ca-certificates curl git openssl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker run --rm hello-world
sudo docker compose version
```

## 2. Obtener el proyecto

Clona el repositorio (sustituye el marcador por su URL real) y entra en la carpeta:

```bash
git clone <URL_DEL_REPOSITORIO> Monitoreo_SRV
cd Monitoreo_SRV
```

Si copiaste el código por otro medio, simplemente cambia a su directorio raíz.

## 3. Configurar secretos y dominio

```bash
cp .env.example .env
sudo nano .env
```

Configura como mínimo `POSTGRES_PASSWORD`, `SECRET_KEY`, `FERNET_KEY` y `DOMAIN`. Para generar valores seguros en Ubuntu:

```bash
openssl rand -hex 32
python3 -c 'import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())'
```

Usa el primer valor para `SECRET_KEY` y el segundo para `FERNET_KEY`. Define una contraseña de PostgreSQL aleatoria, por ejemplo con `openssl rand -hex 24`, y copia exactamente el mismo valor en `POSTGRES_PASSWORD`. El `.env.example` configura la base de datos en el servicio Docker `db`; no pongas `localhost` como host de base de datos dentro del contenedor. No publiques ni subas `.env` al repositorio.

En `DOMAIN`, pon el nombre DNS que apunta a este servidor o, para una red privada, su IP. El Caddyfile actual usa una CA interna (`tls internal`): la conexión HTTPS funciona, pero los navegadores de otros equipos no confiarán en el certificado hasta que instales esa CA. Para un certificado público de Let's Encrypt, usa un nombre DNS público, permite entrada TCP 80/443 y quita `tls internal` de `docker/Caddyfile` antes de iniciar el stack.

## 4. Abrir el firewall y levantar el stack

Si UFW está habilitado, permite SSH antes de activarlo y expón solo la aplicación web. No abras PostgreSQL, Prometheus ni Alertmanager a Internet:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Construye y arranca los servicios, y aplica las migraciones:

```bash
sudo docker compose up -d --build
sudo docker compose exec backend alembic upgrade head
sudo docker compose ps
```

## 5. Crear la cuenta administradora

El bootstrap solo funciona cuando todavía no hay usuarios. Sustituye el correo y la contraseña por valores propios; el comando muestra la respuesta de creación:

```bash
read -r -p "Correo del administrador: " ADMIN_EMAIL
read -r -s -p "Contraseña del administrador: " ADMIN_PASSWORD; echo
curl --fail-with-body --request POST --get \
  --data-urlencode "email=${ADMIN_EMAIL}" \
  --data-urlencode "password=${ADMIN_PASSWORD}" \
  http://127.0.0.1:8000/api/auth/bootstrap
unset ADMIN_PASSWORD
```

## 6. Validar y acceder

```bash
sudo docker compose ps
curl --fail http://127.0.0.1:8000/api/health
curl -k --fail "https://127.0.0.1/api/health"
sudo docker compose logs --tail=100 backend
```

Desde un equipo cliente, abre `https://<IP-o-dominio>/` y entra en `https://<IP-o-dominio>/api/docs` para la API. Con la CA interna, el navegador mostrará una advertencia hasta confiar en ella. Los puertos de Prometheus (9090) y Alertmanager (9093) no están publicados al host en esta configuración; consúltalos desde la red Docker o crea acceso privado explícito si lo necesitas.

## 7. Incorporar servidores monitorizados

Instala Node Exporter en cada servidor Linux y permite TCP 9100 desde el host de monitoreo. El playbook incluido requiere Ansible y un inventario propio:

```bash
ansible-playbook -i inventario.ini scripts/install-node-exporter.yml -e prom_ip=<IP_DEL_MONITOR>
```

Registra los servidores desde la interfaz. Para integrar vCenter, crea una cuenta de solo lectura y configura la conexión desde la vista VMware.

## Operación

- Estado y salud: `sudo docker compose ps` y `curl -k https://127.0.0.1/api/health`.
- Logs: `sudo docker compose logs -f backend prometheus`.
- Actualizar: `git pull` y `sudo docker compose up -d --build`.
- Backup: `sudo docker compose exec -T db pg_dump -U postgres monitoreo_srv > backup.sql`; conserva también una copia segura de los volúmenes Docker.
- URLs del proyecto: [urls-proyecto.md](urls-proyecto.md).
