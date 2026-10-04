#!/usr/bin/env python3
"""Vincula VMs de vCenter con servidores Linux sin usar el nombre.

Cascada: 1) system_uuid == instanceUuid (100)
         2) hostname Tools == hostname (90)
         3) IP única compartida (70)
Respeta enlaces existentes y nunca sobrescribe un enlace manual
(salvo --force, que aun así conserva manual_override).

Uso:
  DATABASE_URL=... python3 scripts/link-vm-servers.py [--dry-run] [--force]
"""
import sys, os, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.db.session import SessionLocal
from app.models.entities import Vm, Server, VmServerLink


def short_host(h: str) -> str:
    return (h or "").lower().split(".")[0].strip()


def find_match(vm: Vm, servers: list):
    iu = (vm.instance_uuid or "").lower().strip()
    if iu:
        for s in servers:
            if (s.system_uuid or "").lower().strip() == iu:
                return s, "uuid", 100
    ghn = short_host(vm.guest_hostname or "")
    if ghn:
        for s in servers:
            if short_host(s.hostname) == ghn:
                return s, "hostname", 90
    vips = set(vm.ips or [])
    if vips:
        hits = [s for s in servers if (s.primary_ip or "") in vips]
        if len(hits) == 1:
            return hits[0], "ip", 70
    return None, "", 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="solo muestra, no guarda")
    ap.add_argument("--force", action="store_true", help="re-evalúa VMs ya enlazadas (respeta manuales)")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        servers = db.query(Server).all()
        vms = db.query(Vm).order_by(Vm.name).all()
        created, skipped, manual = 0, 0, 0
        for vm in vms:
            link = db.query(VmServerLink).filter(VmServerLink.vm_id == vm.id).first()
            if link and link.manual_override:
                manual += 1
                continue
            if link and not args.force:
                skipped += 1
                continue
            srv, method, conf = find_match(vm, servers)
            if not srv:
                print(f"  [sin match] {vm.name} uuid={vm.instance_uuid} ips={vm.ips}")
                continue
            print(f"  [link {conf}%:{method}] {vm.name} -> {srv.hostname}")
            if args.dry_run:
                continue
            if link:
                link.server_id = srv.id
                link.match_method = method
                link.confidence = conf
            else:
                db.add(VmServerLink(vm_id=vm.id, server_id=srv.id,
                                   match_method=method, confidence=conf,
                                   manual_override=False))
            created += 1
        if not args.dry_run:
            db.commit()
        print(f"Resumen: vinculados={created} existentes={skipped} manuales={manual}"
              + (" (dry-run)" if args.dry_run else ""))
    finally:
        db.close()


if __name__ == "__main__":
    main()
