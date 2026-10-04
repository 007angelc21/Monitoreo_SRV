from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@db:5432/monitoreo_srv"
    SECRET_KEY: str = "change-me"
    FERNET_KEY: str = ""  # base64 urlsafe 32 bytes; generar con scripts/gen-fernet.py
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 7
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    PROMETHEUS_URL: str = "http://prometheus:9090"
    ALERTMANAGER_URL: str = "http://alertmanager:9093"
    REDIS_URL: str = "redis://redis:6379/0"
    LOG_LEVEL: str = "INFO"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "monitoreo@tu-empresa.com"
    SMTP_TLS: bool = True
    METRICS_RETENTION_DAYS: int = 400

    class Config:
        env_file = ".env"
        extra = "ignore"

    def sqlalchemy_url(self) -> str:
        # Tu dato trae ?schema=public (sintaxis Prisma). SQLAlchemy/psycopg no lo usa:
        # se elimina el query param para evitar "invalid connection option".
        url = self.DATABASE_URL.strip().strip('"').strip("'")
        if "?" in url:
            url = url.split("?", 1)[0]
        # Normaliza driver: postgresql:// -> postgresql+psycopg://
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

@lru_cache
def get_settings() -> Settings:
    return Settings()
