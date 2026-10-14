"""Async SQLAlchemy engine and session factory.

Uses asyncpg as the async driver for PostgreSQL + TimescaleDB.
Implements connection pooling with health checks and automatic reconnection.

All database operations use the AsyncSession dependency from app.core.dependencies.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


# ─── Engine Configuration ────────────────────────────────────────────────
def _get_engine_kwargs() -> dict:
    kwargs = {
        "echo": settings.DEBUG,
        "echo_pool": settings.DEBUG,
    }

    # The asyncpg-specific connect_args below (server_settings, ssl,
    # statement_cache_size, ...) are meaningless — and rejected outright —
    # for the sqlite+aiosqlite driver used by the documented local-dev
    # fallback (README.md / LOCAL_SETUP.md). Only apply them for Postgres.
    is_postgres = settings.DATABASE_URL.startswith("postgresql")

    if is_postgres:
        connect_args = {
            "server_settings": {"application_name": "neuroquant-api"},
            "command_timeout": 15.0,  # roughly equivalent to statement_timeout for asyncpg
            # Bounds the initial TCP/SSL handshake itself (distinct from
            # command_timeout, which only bounds a query once connected).
            # Without this, a DB host that's unreachable at boot (down,
            # firewalled, wrong network route) hangs FastAPI's startup
            # lifespan forever instead of logging the warning already
            # written for this case below and letting the app continue.
            "timeout": 10.0,
        }
        if settings.DB_SSL_REQUIRED:
            # "require" (encrypt, don't verify the cert chain) rather than
            # True (full verification via ssl.create_default_context()):
            # Supabase's connection pooler (PgBouncer/Supavisor) presents a
            # certificate chain that terminates in a self-signed cert not
            # in the public CA trust store, so strict verification always
            # fails with CERTIFICATE_VERIFY_FAILED against it.
            connect_args["ssl"] = "require"

        is_supabase_pooler = (
            "pooler.supabase.com" in settings.DATABASE_URL or ":6543" in settings.DATABASE_URL
        )
        if settings.DB_POOL_MODE == "transaction" or is_supabase_pooler:
            connect_args["statement_cache_size"] = 0
            connect_args["prepared_statement_cache_size"] = 0

        if settings.DB_POOL_MODE == "transaction":
            kwargs["poolclass"] = NullPool
        else:
            kwargs["pool_size"] = getattr(settings, "DB_POOL_SIZE", 5)
            kwargs["max_overflow"] = getattr(settings, "DB_MAX_OVERFLOW", 5)
            kwargs["pool_pre_ping"] = True
            kwargs["pool_recycle"] = (
                min(getattr(settings, "DB_POOL_RECYCLE", 300), 300)
                if is_supabase_pooler
                else getattr(settings, "DB_POOL_RECYCLE", 1800)
            )

        kwargs["connect_args"] = connect_args

    return kwargs


engine = create_async_engine(
    # `create_async_engine` only builds the Engine object here; it does not
    # connect. If DATABASE_URL is unset (misconfigured deployment), fail
    # loudly the moment anything actually tries to use this engine, instead
    # of silently connecting to "postgres:postgres@localhost:5432" - the
    # single most common real local Postgres default, which risks silently
    # reading from/writing to an unrelated real database rather than
    # surfacing the missing configuration.
    settings.DATABASE_URL
    or "postgresql+asyncpg://DATABASE_URL_NOT_CONFIGURED:@localhost/DATABASE_URL_NOT_CONFIGURED",
    **_get_engine_kwargs(),
)

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


logger.debug(
    "database_engine_created",
    database_url=settings.DATABASE_URL.split("@")[1] if "@" in settings.DATABASE_URL else "***",
    pool_size=settings.DB_POOL_SIZE,
    mode="production" if settings.is_production else "development",
)


# ─── Session Factory ──────────────────────────────────────────────────────
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

logger.debug("database_session_factory_created")


# ─── ORM Base Class ───────────────────────────────────────────────────────
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    """Base class for all SQLAlchemy ORM models.

    All model classes should inherit from this to be tracked
    by the ORM and included in migrations.

    Example:
        class User(Base):
            __tablename__ = "users"
            id: Mapped[str] = mapped_column(primary_key=True)
            email: Mapped[str] = mapped_column(unique=True)
    """

    pass


# ─── Connection Pool Event Handlers ────────────────────────────────────
# Only register PostgreSQL-specific listeners if we're using PostgreSQL.
# SQLite does not support SET, CREATE EXTENSION, etc.
_is_postgres = True


# ─── Session Dependency ────────────────────────────────────────────────
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session for dependency injection.

    DEPRECATED: Use get_db() from app.core.dependencies instead.
    This function is kept for backwards compatibility.

    Yields:
        AsyncSession: SQLAlchemy async session.

    Raises:
        Exception: Propagates any database errors.
    """
    from contextlib import suppress

    async with async_session_factory() as session:
        try:
            yield session
            if session.in_transaction():
                if session.new or session.dirty or session.deleted:
                    await session.commit()
                else:
                    try:
                        await session.commit()
                    except Exception:
                        with suppress(Exception):
                            await session.rollback()
        except Exception:
            with suppress(Exception):
                await session.rollback()
            raise
        finally:
            with suppress(Exception):
                await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Compatibility alias for legacy imports expecting get_db."""
    async for session in get_session():
        yield session


# ─── Utility Functions ────────────────────────────────────────────────
async def create_all_for_tests() -> None:
    """Initialize database schema by creating all tables.

    Creates all tables defined in Base.metadata.
    Should be called during application startup for new databases.

    Args:
        None

    Returns:
        None

    Raises:
        Exception: If database operations fail.

    Example:
        # In main.py startup
        if settings.INIT_DB_ON_STARTUP:
            await init_db()
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_schema_initialized")


async def drop_db() -> None:
    """Drop all tables from the database.

    DANGEROUS: This deletes all data. Only use in development/testing.

    Args:
        None

    Returns:
        None

    Raises:
        Exception: If database operations fail.
    """
    if settings.is_production:
        raise RuntimeError("Cannot drop database in production")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("database_schema_dropped")


async def get_db_health() -> dict[str, bool]:
    """Check database connection health.

    Args:
        None

    Returns:
        dict: {"healthy": bool, "connection": bool, "tables": bool}

    Raises:
        None: Returns health status even if checks fail.
    """
    health = {"healthy": True, "connection": False, "tables": False}

    try:
        async with async_session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            health["connection"] = bool(result.scalar())

            # Check if any tables exist
            result = await session.execute(
                text(
                    """
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'public'
                    """
                )
            )
            table_count = result.scalar() or 0
            health["tables"] = table_count > 0
            health["healthy"] = all(health[k] for k in ["connection", "tables"])

    except Exception as e:
        logger.warning("database_health_check_error", error=str(e))
        health["healthy"] = False

    return health
