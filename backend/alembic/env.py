from sqlalchemy import engine_from_config, pool

from alembic import context
import app.core.logger  # noqa: F401 — configure loguru before alembic loggers register
from app.core.config import settings
from app.db.base import Base
import app.db.models  # noqa: F401 — ensure all models are registered on Base.metadata

config = context.config
# fileConfig intentionally omitted — logging is managed by app.core.logger

target_metadata = Base.metadata

# Convert async URL (sqlite+aiosqlite://...) to sync (sqlite://...) for Alembic
_sync_url = settings.DATABASE_URL.replace("+aiosqlite", "")
config.set_main_option("sqlalchemy.url", _sync_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
