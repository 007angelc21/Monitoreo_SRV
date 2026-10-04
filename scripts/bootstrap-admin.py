"""Crea admin inicial: python scripts/bootstrap-admin.py admin@local pass"""
import sys
sys.path.insert(0, "backend")
from app.db.session import SessionLocal
from app.models.entities import User, Role
from app.core.security import hash_password
email, pwd = sys.argv[1], sys.argv[2]
db = SessionLocal()
if db.query(User).count() == 0:
    for n in ["admin", "operator", "viewer"]:
        if not db.query(Role).filter(Role.name == n).first(): db.add(Role(name=n))
    db.flush()
    r = db.query(Role).filter(Role.name == "admin").first()
    db.add(User(email=email, password_hash=hash_password(pwd), role_id=r.id)); db.commit()
    print("admin creado", email)
else:
    print("ya existen usuarios")
