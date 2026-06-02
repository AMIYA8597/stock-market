"""
FastAPI dependency injection functions.

Provides reusable dependency functions for:
- Database session management
- Redis client pooling
- Current user authentication
- Rate limiting
- Request context

These functions are used as FastAPI `Depends()` parameters in route handlers.
"""

from __future__ import annotations

import logging
from typing import Annotated, AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.database.connection import async_session_factory
from app.core.security import decode_token, oauth2_scheme
from app.database.redis_client import _redis_pool_singleton

logger = get_logger(__name__)
settings = get_settings()
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)


# ─── Database Session ─────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async SQLAlchemy session for database operations.
    
    This dependency injects a database session into route handlers.
    The session is automatically committed on success or rolled back on error.
    
    Yields:
        AsyncSession: SQLAlchemy async session for ORM operations.
        
    Raises:
        Exception: Any database errors are propagated to the route handler.
        
    Example:
        @app.get("/users")
        async def get_users(db: Annotated[AsyncSession, Depends(get_db)]):
            result = await db.execute(select(User))
            users = result.scalars().all()
            return users
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("database_error: %s", str(e), exc_info=True)
            raise
        finally:
            await session.close()


# ─── Redis Client ────────────────────────────────────────────────────────
async def get_redis() -> Redis:
    """Get Redis async client from singleton pool.
    
    Returns the same connection pool instance across all requests.
    Handles automatic connection initialization and error recovery.
    
    Returns:
        Redis: Async Redis client connected to configured server.
        
    Raises:
        ConnectionError: If Redis server is unreachable.
        
    Example:
        @app.get("/cache/key")
        async def get_cached(
            redis: Annotated[Redis, Depends(get_redis)]
        ):
            value = await redis.get("key")
            return {"value": value}
    """
    try:
        redis_client = await _redis_pool_singleton()
        # Test connection with PING
        await redis_client.ping()
        return redis_client
    except Exception as e:
        logger.error("redis_connection_error: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache service unavailable",
        ) from e


# ─── Current User ────────────────────────────────────────────────────────
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> dict:
    """Get the current authenticated user from JWT token.
    
    Validates JWT signature and expiration. Returns decoded token payload
    containing user_id and role.
    
    Args:
        token: Bearer token from Authorization header (injected by oauth2_scheme).
        
    Returns:
        dict: Token payload with keys: user_id, role, type, iat, exp, jti.

    Raises:
        HTTPException: 401 if token is invalid, expired, or malformed.

    Example:
        @app.get("/me")
        async def current_user(
            current_user: Annotated[dict, Depends(get_current_user)]
        ):
            return {"user_id": current_user["user_id"]}
    """
    try:
        payload = decode_token(token)

        # Verify token type is ACCESS (not REFRESH or other)
        if payload.get("type") != "access":
            logger.warning("invalid_token_type: %s", payload.get("type"))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify subject (user_id) exists
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("missing_token_subject")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_current_user_error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user_or_none(
    token: Annotated[str | None, Depends(oauth2_scheme_optional)] = None,
) -> Optional[dict]:
    """Get current user if authenticated, otherwise None.
    
    Use this dependency for endpoints where authentication is optional.
    If no token is provided, returns None instead of raising an error.
    
    Args:
        token: Bearer token from Authorization header (optional).
        
    Returns:
        dict or None: Token payload if authenticated, None otherwise.
        
    Raises:
        None: Always succeeds, even without token.
        
    Example:
        @app.get("/public/data")
        async def public_data(
            current_user: Annotated[dict, Depends(get_current_user_or_none)]
        ):
            if current_user:
                return {"data": "personalized", "user_id": current_user["user_id"]}
            else:
                return {"data": "public"}
    """
    if not token:
        return None

    try:
        return await get_current_user(token)
    except HTTPException:
        return None
    except Exception as e:
        logger.debug("get_current_user_or_none_error: %s", str(e))
        return None


# ─── Role-Based Access Control ───────────────────────────────────────────
def require_role(required_role: str):
    """Dependency factory for role-based access control.
    
    Creates a dependency that verifies the current user has at least
    the required role level according to the role hierarchy:
    
        ADMIN (5) > RESEARCHER (4) > ANALYST (3) > VIEWER (2) > API_USER (1)
    
    Args:
        required_role: Minimum required role (ADMIN, RESEARCHER, ANALYST, VIEWER, API_USER).
        
    Returns:
        Callable: Dependency function for use in route handlers.
        
    Raises:
        HTTPException: 403 if user lacks required role.

    Example:
        @app.post("/admin/users")
        async def create_user(
            current_user: Annotated[dict, Depends(require_role("ADMIN"))],
            db: Annotated[AsyncSession, Depends(get_db)]
        ):
            # Only ADMIN role can access this endpoint
            ...
    """
    async def role_checker(
        current_user: Annotated[dict, Depends(get_current_user)],
    ) -> dict:
        """Check if user has required role."""
        role_hierarchy = {
            "ADMIN": 5,
            "RESEARCHER": 4,
            "ANALYST": 3,
            "VIEWER": 2,
            "API_USER": 1,
        }

        user_role = current_user.get("role")
        user_id = current_user.get("sub")
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 99)

        if user_level < required_level:
            logger.warning(
                "insufficient_permissions",
                user_id=user_id,
                user_role=user_role,
                required_role=required_role,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role} role or higher",
            )

        return current_user

    return role_checker


# ─── Request Context ────────────────────────────────────────────────────
class RequestContext:
    """Context container for current request.
    
    Holds request-scoped data like correlation ID, user info, etc.
    """

    def __init__(
        self,
        user_id: Optional[str] = None,
        role: Optional[str] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        self.user_id = user_id
        self.role = role
        self.correlation_id = correlation_id
        self.request_id = request_id


async def get_request_context(
    current_user: Annotated[Optional[dict], Depends(get_current_user_or_none)] = None,
) -> RequestContext:
    """Create request context from current user.
    
    Args:
        current_user: Current authenticated user (optional).
        
    Returns:
        RequestContext: Context object with user and request info.
        
    Example:
        @app.get("/data")
        async def get_data(
            ctx: Annotated[RequestContext, Depends(get_request_context)]
        ):
            logger.info("access", user_id=ctx.user_id, role=ctx.role)
            return {"user_id": ctx.user_id}
    """
    return RequestContext(
        user_id=current_user.get("sub") if current_user else None,
        role=current_user.get("role") if current_user else None,
    )


# ─── Pagination ──────────────────────────────────────────────────────────
class PaginationParams:
    """Query parameters for paginated list endpoints."""

    def __init__(self, skip: int = 0, limit: int = 100):
        """Initialize pagination parameters.
        
        Args:
            skip: Number of records to skip (offset).
            limit: Maximum records to return.
        """
        self.skip = max(0, skip)
        self.limit = min(max(1, limit), 1000)  # Cap at 1000


async def get_pagination(
    skip: int = 0,
    limit: int = 100,
) -> PaginationParams:
    """Get pagination parameters from query string.
    
    Args:
        skip: Offset (default 0).
        limit: Limit per page (default 100, capped at 1000).
        
    Returns:
        PaginationParams: Validated pagination parameters.
        
    Example:
        @app.get("/items")
        async def list_items(
            pagination: Annotated[PaginationParams, Depends(get_pagination)]
        ):
            items = await db.query(Item).offset(pagination.skip).limit(pagination.limit)
            return items
    """
    return PaginationParams(skip=skip, limit=limit)
