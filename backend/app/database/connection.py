"""Async SQLAlchemy engine and session factory.

Uses asyncpg as the async driver for PostgreSQL + TimescaleDB.
Implements connection pooling with health checks and automatic reconnection.

All database operations use the AsyncSession dependency from app.core.dependencies.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ─── Engine Configuration ────────────────────────────────────────────────
def _get_engine_kwargs() -> dict:
    """Build engine kwargs based on environment configuration.
    
    Args:
        None
        
    Returns:
        dict: SQLAlchemy AsyncEngine initialization arguments.
        
    Raises:
        None
    """
    kwargs = {
        "echo": settings.DEBUG,
        "echo_pool": settings.DEBUG,
        "pool_pre_ping": True,  # Execute SELECT 1 before using connection
        "pool_recycle": settings.DATABASE_POOL_RECYCLE,
    }

    # Use QueuePool for production (persistent pooling)
    # Use NullPool for testing/development (no pooling)
    if settings.is_production:
        kwargs["poolclass"] = QueuePool
        kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
        kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
    else:
        kwargs["poolclass"] = NullPool

    return kwargs


# ─── Create Async Engine ──────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    **_get_engine_kwargs(),
)

logger.debug(
    "database_engine_created",
    database_url=settings.DATABASE_URL.split("@")[1] if "@" in settings.DATABASE_URL else "***",
    pool_size=settings.DATABASE_POOL_SIZE,
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
class Base(DeclarativeBase):
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
@event.listens_for(engine.sync_engine, "connect")
def receive_connect(dbapi_conn: any, connection_record: any) -> None:
    """Configure PostgreSQL connection on creation.
    
    Called when a new database connection is created.
    Sets up TimescaleDB-specific settings for hypertables.
    
    Args:
        dbapi_conn: Raw database connection (psycopg2).
        connection_record: SQLAlchemy connection record.
        
    Returns:
        None
        
    Raises:
        None: Exceptions are logged but don't interrupt connection.
    """
    try:
        # Enable TimescaleDB continuous aggregates for hypertables
        cursor = dbapi_conn.cursor()
        cursor.execute("SET jit = on;")  # Enable JIT compilation for complex queries
        cursor.execute("SET random_page_cost = 1.1;")  # Optimize for SSD
        cursor.close()
        logger.debug("database_connection_configured")
    except Exception as e:
        logger.warning("database_connection_configure_error", error=str(e))


@event.listens_for(engine.sync_engine, "first_connect")
def receive_first_connect(dbapi_conn: any, connection_record: any) -> None:
    """Initialize database on first connection.
    
    Called exactly once when the first connection is created.
    Initializes TimescaleDB extension if not already present.
    
    Args:
        dbapi_conn: Raw database connection.
        connection_record: SQLAlchemy connection record.
        
    Returns:
        None
        
    Raises:
        None: Exceptions are logged but don't interrupt startup.
    """
    try:
        cursor = dbapi_conn.cursor()
        cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
        cursor.close()
        logger.info("database_timescaledb_initialized")
    except Exception as e:
        logger.warning("database_timescaledb_init_error", error=str(e))


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
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Compatibility alias for legacy imports expecting get_db."""
    async for session in get_session():
        yield session


# ─── Utility Functions ────────────────────────────────────────────────
async def init_db() -> None:
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
