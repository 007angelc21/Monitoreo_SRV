"""Scheduler periódico + evaluador VMware->alertas con deduplicación.
Jobs: discovery 5min, evaluación capacidad/snapshots 15min, targets 5min.
Sin Celery: APScheduler en-proceso (suficiente hasta ~500 nodos; pasar a workers distribuidos después)."""
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from app.db.session import SessionLocal
from app.models.entities import Vcenter, Vm, Datastore, Host, Alert
from app.collectors.targets import regenerate_targets

_scheduler: BackgroundScheduler | None = None

SNAP_MAX_DAYS = 7
DS_WARN = 85.0
DS_CRIT = 95.0


def upsert_alert(db, fingerprint: str, scope_type: str, scope_id: str, severity: str,
                 status: str, value: float | None, threshold: float | None, description: str):
    now = datetime.now(timezone.utc)
    row = db.query(Alert).filter(Alert.fingerprint == fingerprint).first()
    if row and row.status == "firing" and status == "firing":
        row.dedup_count += 1
        row.updated_at = now
        row.value = value
    elif row:
        row.status = status
        row.updated_at = now
        row.value = value
        row.threshold = threshold
        if status == "resolved":
            row.resolved_at = now
    else:
        db.add(Alert(fingerprint=fingerprint, scope_type=scope_type, scope_id=scope_id,
                     severity=severity, status=status, value=value, threshold=threshold,
                     description=description))
    db.commit()


def job_discover_all():
    from app.integrations.vcenter.client import discover_vcenter, VcenterError
    from app.integrations.vcenter.sync import sync_vcenter
    db = SessionLocal()
    try:
        for v in db.query(Vcenter).all():
            try:
                data = discover_vcenter(v)
                sync_vcenter(db, v, data)
            except VcenterError as e:
                v.status = "error"
                db.commit()
                upsert_alert(db, f"vcenter-down-{v.id}", "vcenter", str(v.id), "CRITICAL",
                             "firing", None, None, f"vCenter sin conexión {v.name}: {e}")
            else:
                upsert_alert(db, f"vcenter-down-{v.id}", "vcenter", str(v.id), "CRITICAL",
                             "resolved", None, None, f"vCenter recuperado {v.name}")
        try:
            regenerate_targets()
        except Exception:
            pass
    finally:
        db.close()


def job_evaluate_vmware():
    db = SessionLocal()
    try:
        for vm in db.query(Vm).all():
            if (vm.power_state or "").upper() == "POWERED_OFF":
                upsert_alert(db, f"vm-off-{vm.id}", "vm", str(vm.id), "WARNING", "firing",
                             None, None, f"VM apagada: {vm.name}")
            else:
                upsert_alert(db, f"vm-off-{vm.id}", "vm", str(vm.id), "WARNING", "resolved",
                             None, None, f"VM encendida: {vm.name}")
            if (vm.oldest_snapshot_days or 0) > SNAP_MAX_DAYS:
                upsert_alert(db, f"vm-snap-{vm.id}", "vm", str(vm.id), "WARNING", "firing",
                             vm.oldest_snapshot_days, SNAP_MAX_DAYS,
                             f"Snapshot antiguo en {vm.name}: {vm.oldest_snapshot_days}d > {SNAP_MAX_DAYS}d")
            else:
                upsert_alert(db, f"vm-snap-{vm.id}", "vm", str(vm.id), "WARNING", "resolved",
                             vm.oldest_snapshot_days, SNAP_MAX_DAYS, f"Snapshots OK {vm.name}")
        for ds in db.query(Datastore).all():
            pct = 0.0
            if ds.capacity_bytes:
                pct = 100.0 * (1 - (ds.free_bytes or 0) / ds.capacity_bytes)
            if pct >= DS_CRIT:
                upsert_alert(db, f"ds-crit-{ds.id}", "datastore", str(ds.id), "CRITICAL", "firing",
                             round(pct, 1), DS_CRIT, f"Datastore {ds.name} > 95%: {pct:.1f}%")
            elif pct >= DS_WARN:
                upsert_alert(db, f"ds-crit-{ds.id}", "datastore", str(ds.id), "WARNING", "firing",
                             round(pct, 1), DS_WARN, f"Datastore {ds.name} > 85%: {pct:.1f}%")
            else:
                upsert_alert(db, f"ds-crit-{ds.id}", "datastore", str(ds.id), "WARNING", "resolved",
                             round(pct, 1), DS_WARN, f"Datastore OK {ds.name}")
        for h in db.query(Host).all():
            bad = (h.connection_state or "").lower() not in ("connected", "unknown")
            upsert_alert(db, f"host-conn-{h.id}", "host", str(h.id),
                         "CRITICAL" if bad else "INFO",
                         "firing" if bad else "resolved",
                         None, None, f"Host ESXi {h.name}: {h.connection_state}")
    finally:
        db.close()


INSTANT_QUERIES = {
    "cpu": '100*(1-avg(rate(node_cpu_seconds_total{{instance="{inst}:9100",mode="idle"}}[5m])))',
    "ram": '100*(1-(node_memory_MemAvailable_bytes{{instance="{inst}:9100"}}/node_memory_MemTotal_bytes{{instance="{inst}:9100"}}))',
    "disk": '100*(1-(avg(node_filesystem_avail_bytes{{instance="{inst}:9100",fstype!~"tmpfs|overlay"}})/avg(node_filesystem_size_bytes{{instance="{inst}:9100",fstype!~"tmpfs|overlay"}})))',
    "load1": 'node_load1{{instance="{inst}:9100"}}',
    "net_rx": 'sum(rate(node_network_receive_bytes_total{{instance="{inst}:9100"}}[5m]))',
    "net_tx": 'sum(rate(node_network_transmit_bytes_total{{instance="{inst}:9100"}}[5m]))',
}


def job_persist_metrics():
    """Guarda en PG una muestra por servidor/métrica (downsample 5 min)
    y actualiza el estado de servicios systemd."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from app.collectors.prom import prom_instant
    from app.models.entities import Server, MetricSample, ServiceStatus
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        for s in db.query(Server).all():
            inst = (s.primary_ip or s.hostname)
            if not inst:
                continue
            for metric, tpl in INSTANT_QUERIES.items():
                try:
                    rows = prom_instant(tpl.format(inst=inst))
                    if not rows:
                        continue
                    val = float(rows[0]["value"][1])
                    stmt = pg_insert(MetricSample).values(
                        server_id=s.id, metric=metric, ts=now, value=round(val, 2))
                    stmt = stmt.on_conflict_do_nothing(index_elements=["server_id", "metric", "ts"])
                    db.execute(stmt)
                except Exception:
                    continue
            try:  # snapshot de servicios en la tabla services
                rows = prom_instant(f'node_systemd_unit_state{{instance="{inst}:9100"}}')
                for r in rows:
                    unit = r["metric"].get("name", "")
                    if not any(w in unit for w in ("ssh", "nginx", "apache", "docker", "postgres", "mysql", "mariadb")):
                        continue
                    active = r["value"][1] == "1"
                    row = db.query(ServiceStatus).filter(
                        ServiceStatus.server_id == s.id, ServiceStatus.name == unit).first()
                    if row:
                        row.status = r["metric"].get("state", "unknown")
                        row.last_check = now
                    else:
                        db.add(ServiceStatus(server_id=s.id, name=unit,
                                             systemd_unit=unit, status=r["metric"].get("state", "unknown"),
                                             enabled=active, last_check=now))
            except Exception:
                pass
        db.commit()
    finally:
        db.close()


def job_cleanup_metrics():
    """Retención del histórico PG (METRICS_RETENTION_DAYS, defecto 400)."""
    from datetime import timedelta
    from app.core.config import get_settings
    from app.models.entities import MetricSample
    days = get_settings().METRICS_RETENTION_DAYS
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    db = SessionLocal()
    try:
        db.query(MetricSample).filter(MetricSample.ts < cutoff).delete()
        db.commit()
    finally:
        db.close()


def start():
    global _scheduler
    if _scheduler:
        return
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(job_discover_all, "interval", minutes=5, max_instances=1, coalesce=True)
    _scheduler.add_job(job_evaluate_vmware, "interval", minutes=15, max_instances=1, coalesce=True)
    _scheduler.add_job(job_persist_metrics, "interval", minutes=5, max_instances=1, coalesce=True)
    _scheduler.add_job(job_cleanup_metrics, "interval", hours=24, max_instances=1, coalesce=True)
    _scheduler.start()


def stop():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
