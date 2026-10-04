import hashlib
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.db.session import get_db
from app.models.entities import Alert, Notification, AlertRule
from app.alerts.notifiers import send_email, send_webhook, format_alert
from app.core.config import get_settings
from app.core.deps import get_current_user, require_role
from pydantic import BaseModel

router = APIRouter(prefix="/api/alerts", tags=["alerts"])
settings = get_settings()

def fp(labels: dict) -> str:
    if not labels:
        return hashlib.sha256(b"").hexdigest()[:32]
    normalized = {str(k): "" if v is None else str(v).strip() for k, v in labels.items()}
    payload = "|".join(f"{k}={normalized[k]}" for k in sorted(normalized))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]

@router.get("")
def lista(status: str | None = None, severity: str | None = None, skip: int = 0, limit: int = 50,
          db: Session = Depends(get_db), _=Depends(get_current_user)):
    from app.core.pagination import paged
    q = db.query(Alert).order_by(Alert.updated_at.desc())
    if status: q = q.filter(Alert.status == status)
    if severity: q = q.filter(Alert.severity == severity.upper())
    total = q.count()
    items = q.offset(skip).limit(min(limit, 200)).all()
    return paged(total, [{"id": str(a.id), "fingerprint": a.fingerprint, "severity": a.severity, "status": a.status,
             "scope": f"{a.scope_type}:{a.scope_id}", "value": a.value, "threshold": a.threshold,
             "dedup": a.dedup_count, "updated": a.updated_at} for a in items])

@router.post("/{aid}/ack")
def ack(aid: str, db: Session = Depends(get_db), _=Depends(require_role("admin", "operator"))):
    from fastapi import HTTPException
    from datetime import datetime, timezone
    a = db.query(Alert).filter(Alert.id == aid).first()
    if not a: raise HTTPException(404, "Alerta no encontrada")
    a.status = "acked"; a.updated_at = datetime.now(timezone.utc); db.commit()
    return {"ok": True}

@router.post("/{aid}/resolve")
def resolve(aid: str, db: Session = Depends(get_db), _=Depends(require_role("admin", "operator"))):
    from fastapi import HTTPException
    from datetime import datetime, timezone
    a = db.query(Alert).filter(Alert.id == aid).first()
    if not a: raise HTTPException(404, "Alerta no encontrada")
    now = datetime.now(timezone.utc)
    a.status = "resolved"; a.resolved_at = now; a.updated_at = now; db.commit()
    return {"ok": True}

class RuleIn(BaseModel):
    name: str
    metric: str
    warn_threshold: float | None = None
    crit_threshold: float | None = None
    duration: str = "5m"
    enabled: bool = True

@router.get("/rules")
def rules_list(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return [{"id": str(r.id), "name": r.name, "metric": r.metric, "warn": r.warn_threshold,
             "crit": r.crit_threshold, "duration": r.duration, "enabled": r.enabled}
            for r in db.query(AlertRule).order_by(AlertRule.name).all()]

@router.post("/rules")
def rules_create(body: RuleIn, db: Session = Depends(get_db), _=Depends(require_role("admin", "operator"))):
    from fastapi import HTTPException
    if db.query(AlertRule).filter(AlertRule.name == body.name).first():
        raise HTTPException(409, "Regla ya existe")
    r = AlertRule(**body.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return {"id": str(r.id), "name": r.name}

@router.put("/rules/{rid}")
def rules_update(rid: str, body: RuleIn, db: Session = Depends(get_db), _=Depends(require_role("admin", "operator"))):
    from fastapi import HTTPException
    r = db.query(AlertRule).filter(AlertRule.id == rid).first()
    if not r: raise HTTPException(404, "Regla no encontrada")
    for k, v in body.model_dump().items():
        setattr(r, k, v)
    db.commit()
    return {"ok": True}

@router.delete("/rules/{rid}")
def rules_delete(rid: str, db: Session = Depends(get_db), _=Depends(require_role("admin", "operator"))):
    from fastapi import HTTPException
    r = db.query(AlertRule).filter(AlertRule.id == rid).first()
    if not r: raise HTTPException(404, "Regla no encontrada")
    db.delete(r); db.commit()
    return {"ok": True}

@router.post("/webhook")
async def webhook(req: Request, db: Session = Depends(get_db)):
    """Recibe Alertmanager. Deduplica por fingerprint: si existe firing -> dedup_count++."""
    body = await req.json()
    now = datetime.now(timezone.utc)
    for al in body.get("alerts", []):
        labels = al.get("labels", {})
        sev = (labels.get("severity") or "warning").upper()
        f = fp({"alertname": labels.get("alertname"), "instance": labels.get("instance"),
                "mountpoint": labels.get("mountpoint"), "name": labels.get("name")})
        row = db.query(Alert).filter(Alert.fingerprint == f).first()
        status = "resolved" if al.get("status") == "resolved" else "firing"
        if row and row.status == "firing" and status == "firing":
            row.dedup_count += 1; row.updated_at = now
        elif row:
            row.status = status; row.updated_at = now
            if status == "resolved": row.resolved_at = now
        else:
            row = Alert(fingerprint=f, scope_type="server", scope_id=labels.get("instance", "?"),
                        severity=sev, status=status, value=None, threshold=None,
                        description=al.get("annotations", {}).get("summary", labels.get("alertname")))
            db.add(row); db.flush()
            if status == "firing":
                db.add(Notification(alert_id=row.id, channel="email", status="queued",
                                    payload={"text": format_alert(row)}))
        db.commit()
    return {"ok": True}
