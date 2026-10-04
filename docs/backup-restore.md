# Backup & Restore
- Backup: `./scripts/backup.sh ./backups` (pg_dump + copia targets).
- Restore: `./scripts/restore.sh backups/backup-FECHA.sql`.
- Actualización: `git pull && docker compose up -d --build && docker compose exec backend alembic upgrade head`.
- Volúmenes persistentes: pgdata, promdata, amdata, redisdata, caddy_data.
