import logging
import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import RequestContext, get_current_context
from app.database.connection import get_db
from app.models.identity import User

logger = logging.getLogger(__name__)


def _as_user_id(raw: str) -> uuid.UUID | str:
    """RequestContext.user_id is always a plain str (set via str(user.id)).
    Comparing that directly against User.id - a UUID(as_uuid=True) column -
    works against real Postgres (which casts implicitly) but raises
    AttributeError: 'str' object has no attribute 'hex' when the same query
    runs against SQLite's stricter bind-parameter processing, since nothing
    ever exercised an authenticated request end-to-end against SQLite before
    now. Casting back to a real UUID keeps the query portable across both.
    """
    try:
        return uuid.UUID(raw)
    except (ValueError, AttributeError):
        return raw


async def get_current_user(
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Return the User model for the authenticated context.
    Raises if user doesn't exist (e.g. if auth was API_KEY not tied to user).
    """
    if not ctx.user_id:
        raise HTTPException(status_code=401, detail="User context required")
    result = await db.execute(select(User).where(User.id == _as_user_id(ctx.user_id)))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_current_user_or_none(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    try:
        from app.core.security import api_key_header, oauth2_scheme
        token = await oauth2_scheme(request)
        api_key = await api_key_header(request)
        if not token and not api_key:
            return None
        ctx = await get_current_context(request, token, api_key, db)
        if ctx.user_id:
            result = await db.execute(select(User).where(User.id == _as_user_id(ctx.user_id)))
            return result.scalars().first()
        return None
    except HTTPException:
        return None


def require_role(required_role: str):
    """Dependency factory for organization role-based access control.

    Roles: OWNER (5) > ADMIN (4) > RESEARCHER (3) > ANALYST (2) > TRADER (2) > VIEWER (1)
    """
    async def role_checker(ctx: RequestContext = Depends(get_current_context)) -> RequestContext:
        role_hierarchy = {
            "OWNER": 5,
            "ADMIN": 4,
            "BILLING_ADMIN": 4,
            "RESEARCHER": 3,
            "ANALYST": 2,
            "TRADER": 2,
            "VIEWER": 1,
            "API_USER": 1,
        }

        user_role = ctx.organization_role
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 99)

        if user_level < required_level:
            logger.warning(
                f"insufficient_permissions org_id={ctx.organization_id} "
                f"user_id={ctx.user_id} role={user_role} required={required_role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role} role or higher in the organization",
            )
        return ctx

    return role_checker


class PaginationParams:
    def __init__(self, skip: int = 0, limit: int = 100):
        self.skip = max(0, skip)
        self.limit = min(max(1, limit), 1000)


async def get_pagination(skip: int = 0, limit: int = 100) -> PaginationParams:
    return PaginationParams(skip=skip, limit=limit)


def get_rate_limiter(requests: int, window: int):
    async def _rate_limiter(request: Request):
        from app.core.rate_limit import check_rate_limit
        client_ip = request.client.host if request.client else "unknown"
        key = f"route:{request.url.path}:{client_ip}"
        await check_rate_limit(key, requests, window)
    return _rate_limiter

async def get_redis():
    from app.database.redis_client import get_redis_client
    return await get_redis_client()



