# Arquitectura (resumen operativo)
Backend FastAPI + Postgres (inventario/estado) + Prometheus (series) + Alertmanager + React.
Flujo: Node Exporter→Prometheus; vCenter→scheduler→Postgres; Prometheus→Alertmanager→/api/alerts/webhook (dedup)→Email/Webhook.
Escalado: 10 todo-en-uno; 100 backend x2 + Redis; 500 sharding Prometheus por vCenter + PG réplica; 1000+ Mimir/Thanos + collectors por sede + K8s.
Seguridad: JWT corto + refresh httpOnly, Argon2, RBAC admin/operator/viewer, Fernet para vCenter, rate-limit, auditoría, TLS vía Caddy.
