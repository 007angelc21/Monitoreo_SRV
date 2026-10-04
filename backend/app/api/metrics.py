from fastapi import APIRouter, Depends, Query, HTTPException
from app.core.deps import get_current_user
from app.db.session import SessionLocal
from app.models.entities import Server
from app.collectors.prom import prom_range
router = APIRouter(prefix="/api", tags=["metrics"])
RANGES = {"15m": 900, "1h": 3600, "6h": 21600, "24h": 86400, "7d": 604800, "30d": 2592000}

def _inst(sid: str) -> str:
    db = SessionLocal()
    try:
        s = db.query(Server).filter(Server.id == sid).first()
        if not s:
            raise HTTPException(404, "Servidor no encontrado")
        return (s.primary_ip or s.hostname)
    finally:
        db.close()

@router.get("/servers/{sid}/metrics")
def server_metrics(sid: str, range: str = Query("1h"), source: str = Query("auto", pattern="^(auto|prom|db)$"),
                   _=Depends(get_current_user)):
    """source=auto: Prometheus en vivo; si falla, histórico de PG.
    source=db: fuerza PG. source=prom: fuerza Prometheus."""
    from datetime import timedelta, timezone
    from app.models.entities import MetricSample
    secs = RANGES.get(range, 3600)
    inst = _inst(sid)
    q = {
        "cpu": f'100*(1-avg(rate(node_cpu_seconds_total{{instance="{inst}:9100",mode="idle"}}[5m])))',
        "ram": f'100*(1-(node_memory_MemAvailable_bytes{{instance="{inst}:9100"}}/node_memory_MemTotal_bytes{{instance="{inst}:9100"}}))',
        "disk": f'100*(1-(node_filesystem_avail_bytes{{instance="{inst}:9100",fstype!~"tmpfs|overlay"}}/node_filesystem_size_bytes{{instance="{inst}:9100",fstype!~"tmpfs|overlay"}}))',
        "load1": f'node_load1{{instance="{inst}:9100"}}',
        "net_rx": f'rate(node_network_receive_bytes_total{{instance="{inst}:9100"}}[5m])',
        "net_tx": f'rate(node_network_transmit_bytes_total{{instance="{inst}:9100"}}[5m])',
    }
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=secs)
        stored = {}
        for m in ("cpu", "ram", "disk", "load1"):
            rows = db.query(MetricSample).filter(
                MetricSample.server_id == sid, MetricSample.metric == m,
                MetricSample.ts >= cutoff).order_by(MetricSample.ts).all()
            if rows:
                stored[m] = [{"metric": {"__name__": m},
                              "values": [[r.ts.timestamp(), str(r.value)] for r in rows]}]
    finally:
        db.close()
    out, used = {}, {}
    for k, query in q.items():
        if source == "db":
            out[k] = stored.get(k, [])
            used[k] = "db"
        elif source == "prom":
            try:
                out[k] = prom_range(query, secs)
            except Exception as e:
                out[k] = {"error": str(e)}
            used[k] = "prom"
        else:  # auto
            try:
                out[k] = prom_range(query, secs)
                used[k] = "prom"
            except Exception:
                out[k] = stored.get(k, [])
                used[k] = "db"
    return {"server_id": sid, "instance": inst, "range": range, "source": used, "series": out}

@router.get("/health")
def health():
    import urllib.request
    from app.core.config import get_settings
    settings = get_settings()
    checks = {"backend": "ok"}
    try:
        urllib.request.urlopen(settings.PROMETHEUS_URL + "/-/healthy", timeout=5).read()
        checks["prometheus"] = "ok"
    except Exception as e:
        checks["prometheus"] = f"error: {e}"
    try:
        db = SessionLocal(); db.execute(__import__("sqlalchemy").text("SELECT 1")); db.close()
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"
    try:
        from app.collectors.scheduler import _scheduler
        checks["scheduler"] = "running" if (_scheduler and _scheduler.running) else "stopped"
    except Exception:
        checks["scheduler"] = "unknown"
    return checks
