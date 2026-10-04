# Monitoreo SRV — Linux + VMware vCenter 7 (Ubuntu 24.04, React 100%)
Backend FastAPI + Postgres 16 + Prometheus 3 + Alertmanager + React TS (Recharts).

## URLs del proyecto

Sustituye `SERVIDOR` por la IP o dominio del host donde se despliegue el servicio.

- Aplicación: `https://SERVIDOR/`
- Servidores: `https://SERVIDOR/#/servers`
- Detalle servidor: `https://SERVIDOR/#/servers/{id}`
- VMware: `https://SERVIDOR/#/vmware`
- Mantenimiento: `https://SERVIDOR/#/maintenance`
- Login: `https://SERVIDOR/#/login`
- Swagger: `https://SERVIDOR/api/docs`
- Health: `https://SERVIDOR/api/health`
- Métricas backend: `https://SERVIDOR/metrics`
- Prometheus: `http://SERVIDOR:9090`
- Alertmanager: `http://SERVIDOR:9093`

## Credenciales iniciales

- Usuario: `admin@monitoreo.local`
- Password: `Admin123!`

## Despliegue en Ubuntu 24.04

Sigue la [guía paso a paso](docs/install.md) para instalar Docker, configurar secretos, levantar el stack y crear el administrador.

## Arranque rápido en Windows

```powershell
./start-monitoreo.ps1
```

## Arquitectura

- Compose: db, redis, prometheus, alertmanager, backend, frontend, **caddy (HTTPS :443)**; grafana opt-in `--profile observability`.
- API: `/api/docs`. Salud: `/api/health`. Métricas backend: `/metrics`.
- vCenter 7: REST + pyVmomi SOAP, matching VM↔Linux por instanceUuid/hostname/IP. Scheduler 5/15 min.
- DATABASE_URL con `?schema=public` (Prisma) se normaliza solo.
- Arranque: `cp .env.example .env` → editar secrets → `docker compose up -d --build` → admin (`scripts/bootstrap-admin.py` o `POST /api/auth/bootstrap` con DB vacía) → playbook node_exporter → `POST /api/servers` → `POST /api/vcenters` → `/test` → `/discover`.
- Migraciones prod: `docker compose exec backend alembic upgrade head`. Backup: `scripts/backup.sh`.
- Docs: `docs/install.md`, `docs/urls-proyecto.md`, `architecture.md`, `backup-restore.md`, `troubleshooting.md`, `vcenter-permissions.md`.
