# URLs del proyecto Monitoreo SRV

Sustituye `SERVIDOR` por la IP o dominio del equipo que va a hacer de host de monitorización.

## Aplicación (vía Caddy HTTPS en producción)

- https://SERVIDOR/ — Panel general
- https://SERVIDOR/#/servers — Servidores y formulario de alta
- https://SERVIDOR/#/servers/{id} — Detalle por servidor
- https://SERVIDOR/#/vmware — Infraestructura VMware
- https://SERVIDOR/#/maintenance — Mantenimiento
- https://SERVIDOR/#/login — Inicio de sesión

## API backend

- https://SERVIDOR/api/docs — Swagger/OpenAPI
- https://SERVIDOR/api/health — Salud del backend, Prometheus, BD y scheduler
- https://SERVIDOR/metrics — Métricas propias del backend

## Servicios internos (solo red del servidor)

- http://SERVIDOR:9090 — Prometheus
- http://SERVIDOR:9090/api/v1/targets — Estado de targets de Node Exporter
- http://SERVIDOR:9093 — Alertmanager
- http://SERVIDOR:8000/api/docs — API directa del backend
- http://SERVIDOR:3000 — Frontend directo, si se publica el puerto

## Opcionales

- Grafana (perfil observability): http://SERVIDOR:3001 si se levanta con ese mapeo
- Desarrollo local: http://localhost:5173 (frontend), http://localhost:8000 (API)

> Nota: con la configuración actual, frontend y backend quedan publicados en la red del host para facilitar la operación; en producción se recomienda exponer sólo a través de Caddy y cerrar los puertos directos por firewall.
