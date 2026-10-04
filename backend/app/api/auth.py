from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import User, Role
from app.core.security import verify_password, create_token, hash_password
from app.core.config import get_settings
from app.core.audit import auth_log
from app.core.deps import get_current_user
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)
settings = get_settings()

def _ip(req: Request) -> str | None:
    return req.client.host if req.client else None

@router.post("/login")
@limiter.limit("5/minute")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == form.username).first()
    ok = bool(u and u.is_active and verify_password(form.password, u.password_hash))
    auth_log(db, form.username, ok, _ip(request), request.headers.get("user-agent"))
    if not ok:
        raise HTTPException(401, "Credenciales invalidas")
    access = create_token(u.email, settings.ACCESS_TOKEN_MINUTES)
    refresh = create_token("refresh:" + u.email, settings.REFRESH_TOKEN_DAYS * 1440)
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}

@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(Role).filter(Role.id == user.role_id).first()
    return {"id": str(user.id), "email": user.email, "role": r.name if r else "?"}

@router.post("/bootstrap")
def bootstrap(email: str, password: str, db: Session = Depends(get_db)):
    """Crea admin inicial solo si no hay usuarios. Usar scripts/bootstrap-admin.py en prod."""
    if db.query(User).count() > 0:
        raise HTTPException(403, "Ya existen usuarios")
    r = db.query(Role).filter(Role.name == "admin").first()
    if not r:
        r = Role(name="admin"); db.add(r); db.flush()
        db.add_all([Role(name="operator"), Role(name="viewer")]); db.flush()
    u = User(email=email, password_hash=hash_password(password), role_id=r.id)
    db.add(u); db.commit()
    return {"ok": True, "email": email}
