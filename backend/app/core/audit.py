"""Auditoría de acciones administrativas + logs de autenticación."""
from sqlalchemy.orm import Session
from app.models.entities import AuditLog, AuthLog


def audit(db: Session, user_id, action: str, resource: str, resource_id: str | None, ip: str | None):
    try:
        db.add(AuditLog(user_id=user_id, action=action, resource=resource,
                        resource_id=str(resource_id) if resource_id else None, ip=ip))
        db.commit()
    except Exception:
        db.rollback()


def auth_log(db: Session, email: str, success: bool, ip: str | None, ua: str | None):
    try:
        db.add(AuthLog(email=email, success=success, ip=ip, user_agent=(ua or "")[:255]))
        db.commit()
    except Exception:
        db.rollback()
