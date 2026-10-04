from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.models.entities import Vcenter, Datacenter, Cluster, Host, Vm, Datastore
from app.core.deps import get_current_user, require_role
from app.core.security import encrypt_secret
from app.integrations.vcenter.client import discover_vcenter, VcenterError
from datetime import datetime, timezone

router = APIRouter(prefix="/api/vcenters", tags=["vcenters"])

class VcenterIn(BaseModel):
    name: str
    hostname: str
    port: int = 443
    username: str
    password: str = ""
    verify_ssl: bool = True
    ca_bundle: str | None = None

@router.get("")
def lista(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return [{"id": str(v.id), "name": v.name, "hostname": v.hostname, "status": v.status,
             "version": v.version, "last_seen": v.last_seen} for v in db.query(Vcenter).all()]

@router.post("")
def crear(body: VcenterIn, db: Session = Depends(get_db), _=Depends(require_role("admin", "operator"))):
    if not body.password:
        raise HTTPException(400, "password requerido al registrar")
    v = Vcenter(name=body.name, hostname=body.hostname, port=body.port, username=body.username,
                password_encrypted=encrypt_secret(body.password), verify_ssl=body.verify_ssl, ca_bundle=body.ca_bundle)
    db.add(v); db.commit(); db.refresh(v)
    return {"id": str(v.id)}

@router.put("/{vid}")
def actualizar(vid: str, body: VcenterIn, db: Session = Depends(get_db), _=Depends(require_role("admin", "operator"))):
    v = db.query(Vcenter).filter(Vcenter.id == vid).first()
    if not v: raise HTTPException(404, "No encontrado")
    v.name, v.hostname, v.port, v.username = body.name, body.hostname, body.port, body.username
    if body.password:
        v.password_encrypted = encrypt_secret(body.password)
    v.verify_ssl, v.ca_bundle = body.verify_ssl, body.ca_bundle
    db.commit()
    return {"ok": True}

@router.delete("/{vid}")
def eliminar(vid: str, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    v = db.query(Vcenter).filter(Vcenter.id == vid).first()
    if not v: raise HTTPException(404, "No encontrado")
    db.delete(v); db.commit()
    return {"ok": True}

@router.post("/{vid}/rotate-password")
def rotar(vid: str, body: dict, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    """Rotación de credencial almacenada (requiere password nuevo en body)."""
    v = db.query(Vcenter).filter(Vcenter.id == vid).first()
    if not v: raise HTTPException(404, "No encontrado")
    if not body.get("password"): raise HTTPException(400, "password requerido")
    v.password_encrypted = encrypt_secret(body["password"])
    v.status = "unknown"; db.commit()
    return {"ok": True}

@router.post("/{vid}/test")
def test_conexion(vid: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    from app.integrations.vcenter.client import rest_login
    from app.core.security import decrypt_secret
    v = db.query(Vcenter).filter(Vcenter.id == vid).first()
    if not v: raise HTTPException(404, "No encontrado")
    try:
        rest_login(v.hostname, v.port, v.username, decrypt_secret(v.password_encrypted), v.verify_ssl)
        v.status = "ok"; v.last_seen = datetime.now(timezone.utc); db.commit()
        return {"ok": True}
    except VcenterError as e:
        v.status = "error"; db.commit()
        raise HTTPException(502, str(e))

@router.post("/{vid}/discover")
def discover(vid: str, db: Session = Depends(get_db), _=Depends(require_role("admin", "operator"))):
    from app.integrations.vcenter.sync import sync_vcenter
    v = db.query(Vcenter).filter(Vcenter.id == vid).first()
    if not v: raise HTTPException(404, "No encontrado")
    try:
        data = discover_vcenter(v)
    except VcenterError as e:
        v.status = "error"; db.commit()
        raise HTTPException(502, f"Discovery fallo: {e}")
    return sync_vcenter(db, v, data)

@router.get("/{vid}/datastores")
def datastores(vid: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    out = []
    for d in db.query(Datastore).filter(Datastore.vcenter_id == vid).all():
        pct = round(100.0 * (1 - (d.free_bytes or 0) / d.capacity_bytes), 1) if d.capacity_bytes else 0.0
        out.append({"id": str(d.id), "name": d.name, "type": d.type,
                    "capacity_bytes": d.capacity_bytes, "free_bytes": d.free_bytes, "used_pct": pct})
    return out

@router.get("/{vid}/vms")
def vms(vid: str, power: str | None = None, skip: int = 0, limit: int = 50, q: str | None = None,
        db: Session = Depends(get_db), _=Depends(get_current_user)):
    from app.core.pagination import paged
    query = db.query(Vm).filter(Vm.vcenter_id == vid)
    if power: query = query.filter(Vm.power_state == power.upper())
    if q: query = query.filter(Vm.name.ilike(f"%{q}%"))
    total = query.count()
    rows = query.offset(skip).limit(min(limit, 200)).all()
    return paged(total, [{"id": str(x.id), "name": x.name, "power_state": x.power_state, "cpu": x.cpu_count,
             "mem_mb": x.mem_mb, "snapshots": x.snapshot_count, "oldest_snapshot_days": x.oldest_snapshot_days,
             "ips": x.ips} for x in rows])

@router.get("/{vid}/hosts")
def hosts(vid: str, skip: int = 0, limit: int = 50, db: Session = Depends(get_db), _=Depends(get_current_user)):
    from app.core.pagination import paged
    query = db.query(Host).filter(Host.vcenter_id == vid)
    total = query.count()
    rows = query.offset(skip).limit(min(limit, 200)).all()
    return paged(total, [{"id": str(h.id), "name": h.name, "connection": h.connection_state, "power": h.power_state,
             "cpu_mhz": h.cpu_used_mhz, "mem_bytes": h.mem_used_bytes} for h in rows])

@router.get("/{vid}/datacenters")
def dcs(vid: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return [{"id": str(d.id), "name": d.name, "moref": d.moref} for d in db.query(Datacenter).filter(Datacenter.vcenter_id == vid)]

@router.get("/{vid}/clusters")
def clusters(vid: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    dcs_ = db.query(Datacenter).filter(Datacenter.vcenter_id == vid).all()
    ids = [d.id for d in dcs_]
    return [{"id": str(c.id), "name": c.name} for c in db.query(Cluster).filter(Cluster.datacenter_id.in_(ids))]
