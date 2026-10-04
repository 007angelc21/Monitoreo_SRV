from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import get_settings

pwd_ctx = CryptContext(schemes=["argon2"], deprecated="auto")
settings = get_settings()

def hash_password(p: str) -> str:
    return pwd_ctx.hash(p)

def verify_password(p: str, h: str) -> bool:
    return pwd_ctx.verify(p, h)

def create_token(sub: str, minutes: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return jwt.encode({"sub": sub, "exp": exp}, settings.SECRET_KEY, algorithm="HS256")

def decode_token(t: str) -> str:
    return jwt.decode(t, settings.SECRET_KEY, algorithms=["HS256"])["sub"]

def get_fernet() -> Fernet:
    if not settings.FERNET_KEY:
        raise RuntimeError("FERNET_KEY no configurada. Genera con: python scripts/gen-fernet.py")
    return Fernet(settings.FERNET_KEY.encode())

def encrypt_secret(v: str) -> str:
    return get_fernet().encrypt(v.encode()).decode()

def decrypt_secret(v: str) -> str:
    try:
        return get_fernet().decrypt(v.encode()).decode()
    except InvalidToken as e:
        raise ValueError("No se pudo descifrar (FERNET_KEY incorrecta o dato corrupto)") from e
