"""Genera file_sd de Prometheus desde Postgres: /targets/servers.json"""
import json, os
from app.db.session import SessionLocal
from app.models.entities import Server

TARGETS_FILE = os.environ.get("TARGETS_FILE", "/targets/servers.json")

def regenerate_targets() -> int:
    db = SessionLocal()
    try:
        servers = db.query(Server).all()
        targets = []
        for sv in servers:
            host = (sv.primary_ip or sv.hostname).strip()
            if not host: continue
            targets.append({"targets": [f"{host}:9100"],
                            "labels": {"server_id": str(sv.id), "hostname": sv.hostname}})
        os.makedirs(os.path.dirname(TARGETS_FILE), exist_ok=True)
        with open(TARGETS_FILE + ".tmp", "w") as f:
            json.dump(targets, f, indent=2)
        os.replace(TARGETS_FILE + ".tmp", TARGETS_FILE)
        return len(targets)
    finally:
        db.close()
