"""Alembic env: usa DATABASE_URL normalizada (tolera ?schema=public estilo Prisma)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine
from app.db.base import Base
import app.models.entities  # noqa - registra metadatos
from app.core.config import get_settings

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
settings = get_settings()

def run_migrations_online():
    engine = create_engine(settings.sqlalchemy_url(), future=True)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=Base.metadata,
                          compare_type=True, compare_server_default=True)
        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
