from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import decode_token
from app.models.entities import User, Role

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2)) -> User:
    try:
        sub = decode_token(token)
    except Exception:
        raise HTTPException(401, "Token invalido o expirado")
    u = db.query(User).filter(User.email == sub, User.is_active == True).first()
    if not u:
        raise HTTPException(401, "Usuario no encontrado")
    return u

def require_role(*roles: str):
    def check(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        r = db.query(Role).filter(Role.id == user.role_id).first()
        if not r or r.name not in roles:
            raise HTTPException(403, "Permiso insuficiente")
        return user
    return check
