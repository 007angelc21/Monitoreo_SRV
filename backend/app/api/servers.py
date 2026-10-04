from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import Server
from app.core.deps import get_current_user, require_role
from app.collectors.targets import regenerate_targets
from pydantic import BaseModel

router = APIRouter(prefix="/api/servers", tags=["servers"])

class ServerIn(BaseModel):
    hostname: str
    system_uuid: str | None = None
    primary_ip: str | None = None
    os: str | None = None

@router.get("")
def lista(skip: int = 0, limit: int = Query(50, le=200), q: str | None = None,
          db: Session = Depends(get_db), _=Depends(get_current_user)):
    qry = db.query(Server)
    if q: qry = qry.filter(Server.hostname.ilike(f"%{q}%"))
    total = qry.count()
    return {"total": total, "items": [{"id": str(s.id), "hostname": s.hostname, "primary_ip": s.primary_ip,
            "os": s.os, "agent_status": s.agent_status, "system_uuid": s.system_uuid} for s in qry.offset(skip).limit(limit)]}

@router.post("")
def crear(body: ServerIn, db: Session = Depends(get_db), _=Depends(get_current_user)):
    s = Server(hostname=body.hostname, system_uuid=body.system_uuid, primary_ip=body.primary_ip, os=body.os)
    db.add(s); db.commit(); db.refresh(s)
    regenerate_targets()
    return {"id": str(s.id), "hostname": s.hostname}

@router.get("/{sid}")
def detalle(sid: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    from app.models.entities import VmServerLink, Vm
    s = db.query(Server).filter(Server.id == sid).first()
    if not s: from fastapi import HTTPException; raise HTTPException(404, "No encontrado")
    link = db.query(VmServerLink).filter(VmServerLink.server_id == sid).first()
    vm = db.query(Vm).filter(Vm.id == link.vm_id).first() if link else None
    return {"id": str(s.id), "hostname": s.hostname, "primary_ip": s.primary_ip, "os": s.os,
            "system_uuid": s.system_uuid, "agent_status": s.agent_status,
            "vm": {"id": str(vm.id), "name": vm.name, "method": link.match_method,
                   "confidence": link.confidence} if vm else None}

@router.put("/{sid}")
def actualizar(sid: str, body: ServerIn, db: Session = Depends(get_db), _=Depends(require_role("admin", "operator"))):
    from fastapi import HTTPException
    s = db.query(Server).filter(Server.id == sid).first()
    if not s: raise HTTPException(404, "No encontrado")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    db.commit()
    regenerate_targets()
    return {"ok": True}

@router.delete("/{sid}")
def eliminar(sid: str, db: Session = Depends(get_db), _=Depends(require_role("admin", "operator"))):
    from fastapi import HTTPException
    s = db.query(Server).filter(Server.id == sid).first()
    if not s: raise HTTPException(404, "No encontrado")
    db.delete(s); db.commit()
    regenerate_targets()
    return {"ok": True}

@router.get("/{sid}/services")
def servicios(sid: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Estado systemd en vivo desde Prometheus (node_systemd_unit_state).
    Watch configurable: ssh, nginx, apache2, docker, postgresql, mysql/mariadb."""
    from fastapi import HTTPException
    from app.collectors.prom import prom_instant
    s = db.query(Server).filter(Server.id == sid).first()
    if not s:
        raise HTTPException(404, "Servidor no encontrado")
    inst = (s.primary_ip or s.hostname)
    watch = ["ssh", "nginx", "apache2", "docker", "postgresql", "mysql", "mariadb"]
    try:
        rows = prom_instant(f'node_systemd_unit_state{{instance="{inst}:9100"}}')
    except Exception as e:
        raise HTTPException(502, f"Prometheus no disponible: {e}")
    out = []
    for r in rows:
        name = r["metric"].get("name", "")
        if any(w in name for w in watch):
            out.append({"unit": name, "state": r["metric"].get("state"),
                        "active": r["value"][1] == "1"})
    return {"server_id": sid, "instance": inst, "services": out, "watch": watch}

@router.get("/{sid}/diskusage")
def disk_usage(sid: str, limit: int = 15, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Top carpetas por espacio (requiere disk-usage.sh + textfile en el servidor).
    Solo tiempo real desde Prometheus; sin histórico."""
    from fastapi import HTTPException
    from app.collectors.prom import prom_instant
    s = db.query(Server).filter(Server.id == sid).first()
    if not s:
        raise HTTPException(404, "Servidor no encontrado")
    inst = (s.primary_ip or s.hostname)
    try:
        rows = prom_instant(f'topk({min(limit, 30)}, diskusage_bytes{{instance="{inst}:9100"}})')
    except Exception as e:
        raise HTTPException(502, f"Prometheus no disponible: {e}")
    top = [{"path": r["metric"].get("path", "?"), "bytes": int(float(r["value"][1]))} for r in rows]
    if top:
        return {"server_id": sid, "instance": inst, "top": top, "synthetic": False, "note": None}
    if (s.hostname or "").startswith("demo-"):
        demo = [
            {"path": "/var/lib/docker", "bytes": 18 * 1024**3},
            {"path": "/var/log", "bytes": 6 * 1024**3},
            {"path": "/opt/app", "bytes": 4 * 1024**3},
            {"path": "/home", "bytes": 2 * 1024**3},
            {"path": "/tmp", "bytes": 512 * 1024**2},
            {"path": "/etc", "bytes": 96 * 1024**2},
        ]
        return {"server_id": sid, "instance": inst, "top": demo[:limit], "synthetic": True,
                "note": "Datos de prueba (demo). En producción viene de disk-usage.sh."}
    return {"server_id": sid, "instance": inst, "top": [], "synthetic": False,
            "note": "Sin datos: despliegue disk-usage.sh (playbook install-node-exporter.yml)."}

@router.get("/{sid}/top")
def top_apps(sid: str, limit: int = 10, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Top aplicaciones por CPU/memoria (requiere top-apps.sh + textfile en el servidor).
    Solo tiempo real desde Prometheus; sin histórico."""
    from fastapi import HTTPException
    from app.collectors.prom import prom_instant
    s = db.query(Server).filter(Server.id == sid).first()
    if not s:
        raise HTTPException(404, "Servidor no encontrado")
    inst = (s.primary_ip or s.hostname)
    try:
        cpu = prom_instant(f'topk({min(limit, 20)}, topapp_cpu_percent{{instance="{inst}:9100"}})')
        mem = prom_instant(f'topk({min(limit, 20)}, topapp_mem_percent{{instance="{inst}:9100"}})')
        procs = prom_instant(f'topapp_processes{{instance="{inst}:9100"}}')
    except Exception as e:
        raise HTTPException(502, f"Prometheus no disponible: {e}")
    by_app: dict[str, dict] = {}
    for r in cpu:
        by_app.setdefault(r["metric"]["app"], {}).update(cpu=float(r["value"][1]))
    for r in mem:
        by_app.setdefault(r["metric"]["app"], {}).update(mem=float(r["value"][1]))
    for r in procs:
        by_app.setdefault(r["metric"]["app"], {}).update(processes=int(float(r["value"][1])))
    top = sorted(
        ({"app": a, "cpu": v.get("cpu", 0), "mem": v.get("mem", 0), "processes": v.get("processes", 0)}
         for a, v in by_app.items()),
        key=lambda x: x["cpu"], reverse=True)[:limit]
    if top:
        return {"server_id": sid, "instance": inst, "top": top, "synthetic": False, "note": None}
    if (s.hostname or "").startswith("demo-"):
        # Datos de prueba deterministas SOLO para demo (validar UI sin agentes)
        demo = [
            {"app": "java", "cpu": 34.2, "mem": 28.5, "processes": 3},
            {"app": "postgres", "cpu": 18.7, "mem": 22.1, "processes": 8},
            {"app": "nginx", "cpu": 9.4, "mem": 3.2, "processes": 5},
            {"app": "python", "cpu": 6.1, "mem": 5.8, "processes": 2},
            {"app": "redis-server", "cpu": 2.3, "mem": 4.4, "processes": 1},
            {"app": "node_exporter", "cpu": 0.4, "mem": 0.6, "processes": 1},
        ]
        return {"server_id": sid, "instance": inst, "top": demo[:limit], "synthetic": True,
                "note": "Datos de prueba (demo). En producción viene de top-apps.sh."}
    return {"server_id": sid, "instance": inst, "top": [], "synthetic": False,
            "note": "Sin datos: despliegue top-apps.sh (playbook install-node-exporter.yml)."}
