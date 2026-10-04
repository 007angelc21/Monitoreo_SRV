# Troubleshooting
- `docker compose ps` y `docker compose logs backend prometheus alertmanager db`.
- API: `curl localhost:8000/api/health` (db, prometheus, scheduler).
- Prometheus sin targets: `curl localhost:9090/api/v1/targets`; regenera con alta de servidor (POST /api/servers) o reinicia backend.
- vCenter 401: credenciales/permiso; cert: `verify_ssl=false` temporal o `ca_bundle`; timeout: red 443 + circuit breaker 60s tras 5 fallos.
- Sin matching VM-Linux: instala VMware Tools y registra `system_uuid` (`dmidecode -s system-uuid`).
- Login 401 en UI: token expirado (15min) → /login de nuevo.
