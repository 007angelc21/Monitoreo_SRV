"""Upsert de inventario vCenter reutilizable por API y scheduler.
Extrae la lógica del endpoint POST /discover para no duplicarla."""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.entities import Vcenter, Datacenter, Cluster, Host, Vm, Datastore, Server, VmServerLink


def sync_vcenter(db: Session, v: Vcenter, data: dict) -> dict:
    for d in data.get("datacenters", []):
        moref = d.get("datacenter", d.get("name"))
        if not db.query(Datacenter).filter(Datacenter.vcenter_id == v.id, Datacenter.moref == moref).first():
            db.add(Datacenter(vcenter_id=v.id, moref=moref, name=d.get("name")))
    for c in data.get("clusters", []):
        dc = db.query(Datacenter).filter(Datacenter.vcenter_id == v.id).first()
        moref = c.get("cluster", c.get("name"))
        if dc and not db.query(Cluster).filter(Cluster.moref == moref).first():
            db.add(Cluster(datacenter_id=dc.id, moref=moref, name=c.get("name")))
    for h in data.get("hosts", []):
        moref = h.get("host", h.get("name"))
        if not db.query(Host).filter(Host.vcenter_id == v.id, Host.moref == moref).first():
            cl = db.query(Cluster).first()
            db.add(Host(vcenter_id=v.id, cluster_id=cl.id if cl else None, moref=moref,
                        name=h.get("name"), connection_state=h.get("connection_state", "unknown"),
                        power_state=h.get("power_state", "unknown")))
    for vm in data.get("vms", []):
        ex = data.get("extra", {}).get(vm.get("vm", ""), {})
        moref = vm.get("vm", vm.get("name"))
        row = db.query(Vm).filter(Vm.vcenter_id == v.id, Vm.moref == moref).first()
        snaps = ex.get("snapshots", [])
        oldest = 0
        if snaps:
            try:
                dates = [datetime.fromisoformat(s["create"].replace("Z", "+00:00")) for s in snaps if s.get("create")]
                if dates:
                    oldest = (datetime.now(timezone.utc) - min(dates)).days
            except Exception:
                pass
        vals = dict(name=vm.get("name"), guest_hostname=ex.get("hostname"),
                    power_state=vm.get("power_state", ex.get("power", "unknown")),
                    cpu_count=vm.get("cpu_count", ex.get("cpu", 0)) or 0,
                    mem_mb=vm.get("memory_size_MiB", ex.get("mem", 0)) or 0,
                    instance_uuid=ex.get("instance_uuid"), guest_os=ex.get("guest_os"),
                    ips=ex.get("ips"), macs=ex.get("macs"), tools_status=ex.get("tools"),
                    snapshot_count=len(snaps), oldest_snapshot_days=oldest)
        if row:
            for k, val in vals.items():
                setattr(row, k, val)
        else:
            row = Vm(vcenter_id=v.id, moref=moref, **vals)
            db.add(row)
            db.flush()
        auto_link(db, row)
    for d in data.get("datastores", []):
        moref = d.get("datastore", d.get("name"))
        if not db.query(Datastore).filter(Datastore.vcenter_id == v.id, Datastore.moref == moref).first():
            db.add(Datastore(vcenter_id=v.id, moref=moref, name=d.get("name"),
                             type=d.get("type"), capacity_bytes=d.get("capacity", 0) or 0,
                             free_bytes=d.get("free_space", 0) or 0))
    v.status = "ok"
    v.last_seen = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "vms": len(data.get("vms", [])), "hosts": len(data.get("hosts", [])),
            "datastores": len(data.get("datastores", []))}


def auto_link(db: Session, vm: Vm):
    """Asocia VM->Server sin depender del nombre: UUID, hostname, MAC e IP única.
    Nunca sobrescribe un link manual."""
    if db.query(VmServerLink).filter(VmServerLink.vm_id == vm.id).first():
        return
    from app.integrations.vcenter.client import match_vm_to_server

    servers = db.query(Server).all()
    match = match_vm_to_server({
        "instance_uuid": vm.instance_uuid,
        "hostname": vm.guest_hostname or "",
        "ips": vm.ips or [],
        "macs": vm.macs or [],
    }, servers)
    if not match:
        return

    server_id, confidence = match
    method = "uuid" if confidence == 100 else "hostname" if confidence == 90 else "mac" if confidence == 80 else "ip"
    db.add(VmServerLink(vm_id=vm.id, server_id=server_id, match_method=method, confidence=confidence))
