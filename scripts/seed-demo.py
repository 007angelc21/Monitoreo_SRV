#!/usr/bin/env python3
"""Datos temporales para validar gráficas y reportes (SOLO laboratorio).

Crea: 3 servidores demo, 1 vCenter demo con inventario, 24h de muestras
(cpu/ram/disk/load), servicios, enlaces VM-Servidor y 2 alertas firing.
Nada apunta a equipos reales (hostnames demo-*).

Uso:
  DATABASE_URL=... python3 scripts/seed-demo.py [--days 1] [--clean]
  --clean elimina todo lo creado por este script.
"""
import sys, os, argparse, math, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from datetime import datetime, timedelta, timezone
from app.db.session import SessionLocal
from app.models.entities import (Server, Vcenter, Datacenter, Cluster, Host, Vm,
                                 Datastore, MetricSample, ServiceStatus,
                                 VmServerLink, Alert, AlertRule)

PREFIX = "demo-"
random.seed(42)

def clean(db):
    for m in (MetricSample, VmServerLink, ServiceStatus, Alert, Vm, Host, Datastore,
              Cluster, Datacenter, Server, Vcenter):
        q = db.query(m)
        try:
            if m in (Server,):
                q = q.filter(Server.hostname.like(f"{PREFIX}%"))
            elif m is Vcenter:
                q = q.filter(Vcenter.name.like(f"{PREFIX}%"))
            elif m is Alert:
                q = q.filter(Alert.description.like(f"%{PREFIX}%"))
            elif m is Vm:
                q = q.filter(Vm.name.like(f"{PREFIX}%"))
            q.delete(synchronize_session=False)
        except Exception:
            db.rollback()
    rules = db.query(AlertRule).filter(AlertRule.name.like(f"{PREFIX}%")).all()
    for r in rules:
        db.delete(r)
    db.commit()
    print("Datos demo eliminados.")

def seed(db, days: int):
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    # Servidores
    srvs = []
    for i, (hn, ip, uu) in enumerate([
            (f"{PREFIX}web01", "10.99.0.11", "11111111-1111-1111-1111-111111111111"),
            (f"{PREFIX}db01", "10.99.0.12", "22222222-2222-2222-2222-222222222222"),
            (f"{PREFIX}app01", "10.99.0.13", "33333333-3333-3333-3333-333333333333")]):
        s = Server(hostname=hn, primary_ip=ip, system_uuid=uu, os="Ubuntu 24.04",
                   agent_status="ok", last_scrape_at=now)
        db.add(s); srvs.append(s)
    db.flush()
    # vCenter demo + inventario
    vc = Vcenter(name=f"{PREFIX}vc", hostname="vc-demo.local", username="demo",
                 password_encrypted="demo", status="ok", last_seen=now, version="7.0.3")
    db.add(vc); db.flush()
    dc = Datacenter(vcenter_id=vc.id, moref="dc-1", name=f"{PREFIX}dc"); db.add(dc); db.flush()
    cl = Cluster(datacenter_id=dc.id, moref="cl-1", name=f"{PREFIX}cluster"); db.add(cl); db.flush()
    h = Host(vcenter_id=vc.id, cluster_id=cl.id, moref="h-1", name=f"{PREFIX}esxi01",
             connection_state="connected", power_state="poweredOn",
             cpu_mhz_total=96000, mem_bytes_total=512 * 1024**3,
             cpu_used_mhz=32000, mem_used_bytes=300 * 1024**3)
    db.add(h); db.flush()
    ds = Datastore(vcenter_id=vc.id, moref="ds-1", name=f"{PREFIX}ds01", type="VMFS",
                   capacity_bytes=10 * 1024**4, free_bytes=int(10 * 1024**4 * 0.12))
    db.add(ds)
    vms = []
    for i, s in enumerate(srvs):
        vm = Vm(vcenter_id=vc.id, host_id=h.id, datacenter_id=dc.id, moref=f"vm-{i}",
                instance_uuid=s.system_uuid, name=f"{PREFIX}vm{i:02d}",
                guest_hostname=s.hostname, guest_os="Ubuntu Linux (64-bit)",
                power_state="POWERED_ON", cpu_count=4, mem_mb=8192,
                ips=[s.primary_ip], tools_status="toolsOk",
                snapshot_count=1 if i == 0 else 0, oldest_snapshot_days=9 if i == 0 else 0)
        db.add(vm); vms.append(vm)
    db.flush()
    for vm, s in zip(vms, srvs):
        db.add(VmServerLink(vm_id=vm.id, server_id=s.id, match_method="uuid", confidence=100))
    # Servicios
    units = [("ssh.service", True), ("docker.service", True), ("nginx.service", False)]
    for s in srvs:
        for unit, active in units:
            db.add(ServiceStatus(server_id=s.id, name=unit, systemd_unit=unit,
                                 status="active" if active else "inactive",
                                 enabled=True, last_check=now))
    # Muestras 5-min con curva diaria realista
    steps = int(days * 24 * 12)
    rows = 0
    for s in srvs:
        base = 25 + 10 * (hash(s.hostname) % 3)
        for k in range(steps):
            ts = now - timedelta(minutes=5 * (steps - k))
            hday = ts.hour + ts.minute / 60.0
            wave = math.sin((hday - 9) / 24 * 2 * math.pi)  # pico diurno
            vals = {
                "cpu": max(2, base + 30 * wave + random.uniform(-4, 4)),
                "ram": 55 + 10 * wave + random.uniform(-2, 2),
                "disk": 60 + (steps - k) * 0.002,
                "load1": max(0.1, 1.5 + 1.2 * wave + random.uniform(-0.3, 0.3)),
                "net_rx": max(0, 2000000 + 1500000 * wave + random.uniform(-100000, 100000)),
                "net_tx": max(0, 1200000 + 900000 * wave + random.uniform(-75000, 75000)),
            }
            for m, v in vals.items():
                db.add(MetricSample(server_id=s.id, metric=m, ts=ts, value=round(v, 2)))
                rows += 1
    # Regla + alertas demo firing
    rule = AlertRule(name=f"{PREFIX}cpu-alta", metric="cpu",
                     warn_threshold=75, crit_threshold=90, duration="5m")
    db.add(rule); db.flush()
    db.add(Alert(fingerprint=f"{PREFIX}1", rule_id=rule.id, scope_type="server",
                 scope_id=str(srvs[0].id), severity="WARNING", status="firing",
                 value=82.5, threshold=75, dedup_count=3,
                 description=f"{PREFIX} CPU alta sostenida en demo-web01"))
    db.add(Alert(fingerprint=f"{PREFIX}2", scope_type="datastore",
                 scope_id=str(ds.id), severity="CRITICAL", status="firing",
                 value=88.0, threshold=85, dedup_count=1,
                 description=f"{PREFIX} Datastore demo-ds01 sobre 85%"))
    db.commit()
    print(f"Seed OK: {len(srvs)} servidores, {len(vms)} VMs, {rows} muestras ({days}d), 2 alertas firing.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=1)
    ap.add_argument("--clean", action="store_true")
    args = ap.parse_args()
    db = SessionLocal()
    try:
        if args.clean:
            clean(db)
        else:
            seed(db, args.days)
    finally:
        db.close()

if __name__ == "__main__":
    main()
