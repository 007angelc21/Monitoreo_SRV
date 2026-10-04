# Addendum v2 — Especificación de la plataforma de monitoreo

Complementa al prompt original (19 secciones). 12 puntos nuevos integrados
en sus secciones correspondientes. Estado: pendiente de implementación salvo
lo indicado.

## 4-bis. Compatibilidad y ciclo de vida VMware
- **A4.1** vCenter/ESXi 7.0 alcanzó EOL (oct-2025). La plataforma debe incluir
  plan de migración a 8.x: matriz de compatibilidad (pyVmomi/REST por versión),
  modo compatibilidad dual y validación en laboratorio antes del corte.
- **A4.2** Detección de versiones EOL en inventario con alerta `WARNING`
  (versión sin soporte) y reporte de obsolescencia por cluster.

## 5-bis. Modelo de etiquetas y ciclo de vida del inventario
- **A5.1** Etiquetas obligatorias desde el día 1: `site`, `env` (prod/stg/dev),
  `owner`, propagadas como labels Prometheus y filtros del dashboard.
- **A5.2** Política de nodos obsoletos: marcar `stale` tras N días sin scrape,
  excluir de `targets.json` y requerir confirmación para baja definitiva.
  Prohíbe crecimiento del inventario con equipos dados de baja.

## 7-bis. Ventanas de mantenimiento y silenciamiento
- **A7.1** Mantenimiento programado por servidor/grupo con inicio-fin:
  durante la ventana las alertas se suprimen (no se evalúan ni notifican)
  y queda registro en auditoría.
- **A7.2** Silenciamiento manual con motivo obligatorio y expiración máxima
  (p. ej. 24 h), visible en el dashboard.

## 7-ter. Predicción de capacidad
- **A7.3** Alertas predictivas: disco local y datastore con
  `predict_linear` ("lleno estimado en N días"), severidad `WARNING`
  con 14 días y `CRITICAL` con 7 días.

## 8-bis. Payload de alerta extendido e ITSM
- **A8.1** Cada alerta incluye además: `runbook_url`, `labels` (site/env/owner),
  `maintenance` (si aplica) y `dashboard_url` profunda (servidor + rango).
- **A8.2** Integración ITSM (Jira/ServiceNow) como canal más sobre el webhook
  existente: crear/actualizar/cerrar ticket con el fingerprint, sin lógica
  propietaria nueva.

## 9-bis. Identidad empresarial
- **A9.1** SSO OIDC/SAML y/o LDAP como fuente primaria; usuarios locales solo
  para emergencia (break-glass) con custodia documentada.
- **A9.2** MFA obligatorio para rol administrador; sesiones con expiración
  absoluta además de inactividad.

## 9-ter. Gestión de secretos
- **A9.3** Soporte Vault (o equivalente) como backend de secretos con fallback
  a variables de entorno; rotación automática de credenciales vCenter con
  validación post-rotación (`/test`) y rollback.

## 10-bis. Versionado de API
- **A10.1** Prefijo `/api/v1` en todos los endpoints; nuevos contratos solo en
  versiones nuevas, con ventana de deprecación documentada.

## 11-bis. Continuidad del dato
- **A11.1** Postgres con PITR (WAL archiving/Barman): RPO ≤ 15 min, RTO ≤ 1 h
  documentados y probados con simulacro semestral. `pg_dump` queda como
  respaldo secundario, no primario.

## 13-bis. Sonda sintética
- **A13.1** `blackbox_exporter` en el compose (ping ICMP, TCP 22/443, HTTP):
  es la única fuente válida para las métricas de latencia/pérdida que pide
  la sección 3. Reglas y dashboard propios.

## 18-bis. Reportes y SLO
- **A18.1** Reportes ejecutivos: disponibilidad % por servidor/grupo, MTTR/MTTD,
  top-N incidentes, exportación PDF/CSV programada (diaria/semanal por email).
- **A18.2** SLO configurables (p. ej. 99.5 % mensual) con burn-rate y vista
  de cumplimiento en el dashboard general.

## Criterios de aceptación
1. Ningún endpoint nuevo sin versión, test y entrada en OpenAPI.
2. Ninguna alerta sin `runbook_url` o motivo documentado de exención.
3. Simulacro de restore PITR superado antes del pase a producción.
4. Inventario con 100 % de servidores etiquetados (site/env/owner).
