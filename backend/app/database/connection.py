"""Compatibility wrappers for database connection objects."""

from app.core.database import Base, async_session_factory, engine, get_db

__all__ = ["Base", "engine", "async_session_factory", "get_db"]
