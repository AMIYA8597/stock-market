"""SQLAlchemy database configuration and session management.

This module re-exports the core database components:
- Base: ORM declarative base
- engine: AsyncEngine for async operations
- async_session_factory: Session factory
- get_session: Deprecated function (use get_db from dependencies)

For new code, import directly from app.database.connection or
use app.core.dependencies.get_db() for FastAPI dependency injection.
"""

from app.database.connection import (
    Base,
    async_session_factory,
    drop_db,
    engine,
    get_db_health,
    get_db,
    get_session,
    init_db,
)

__all__ = [
    "Base",
    "engine",
    "async_session_factory",
    "get_db",
    "get_session",
    "init_db",
    "drop_db",
    "get_db_health",
]

