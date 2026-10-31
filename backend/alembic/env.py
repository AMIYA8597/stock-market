"""
Alembic migration environment.

Configured for async SQLAlchemy with auto-detection of model changes.
"""

from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection

# Configure logging (stderr, not stdout) before importing anything that
# logs at import time -- app.database.connection logs
# "database_engine_created" the moment it's imported (via app.models
# below), and without this, structlog falls back to its own un-configured
# default logger, which writes to stdout. That corrupts any invocation
# that captures stdout, e.g. `alembic upgrade head --sql > migration.sql`.
from app.core.logging import setup_logging

setup_logging()

# Import all models so Alembic detects them
import app.models  # noqa: F401
from alembic import context
from app.core.config import get_settings
from app.core.database import Base

config = context.config
settings = get_settings()

def _normalize_sync_url(url: str) -> str:
    """Ensure the URL uses a sync driver (psycopg2 for PostgreSQL) for Alembic."""
    if not url:
        return url
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    return url


# Override sqlalchemy.url with the env variable. configparser's default
# interpolation treats bare "%" as special syntax — a percent-encoded
# password (e.g. "%40" for "@") would otherwise raise
# "invalid interpolation syntax". Escape it as "%%" before handing it to
# set_main_option, which configparser un-escapes back to a single "%".
config.set_main_option(
    "sqlalchemy.url",
    _normalize_sync_url(settings.MIGRATIONS_DATABASE_URL).replace("%", "%%"),
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and object.schema in ("auth", "storage", "realtime", "extensions", "graphql", "vault", "cron", "net", "supabase_migrations"):
        return False
    return True



def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generates SQL without connecting."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _normalize_sync_url(settings.MIGRATIONS_DATABASE_URL)
    from sqlalchemy import engine_from_config

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # psycopg2 has no connect timeout by default (unlike the app's main
        # asyncpg engine, which sets one - see app/database/connection.py).
        # Without this, `alembic upgrade head` against an unreachable host
        # hangs on the OS-level TCP timeout (60s+) with zero feedback
        # instead of failing fast with a clear connection error.
        connect_args={"connect_timeout": 10},
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
