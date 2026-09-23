from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.database.connection import get_db
from app.models.identity import User, OrgMember, Organization, ApiKey

logger = logging.getLogger(__name__)
settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

class RequestContext:
    def __init__(
        self,
        user_id: str | None = None,
        organization_id: str | None = None,
        membership_id: str | None = None,
        organization_role: str | None = None,
        platform_role: str | None = None,
        plan_id: str | None = None,
        plan_name: str | None = None,
        entitlements: dict | None = None,
        auth_method: str = "anonymous",
        request_id: str | None = None,
    ):
        self.user_id = user_id
        self.organization_id = organization_id
        self.membership_id = membership_id
        self.organization_role = organization_role
        self.platform_role = platform_role
        self.plan_id = plan_id
        self.plan_name = plan_name
        self.entitlements = entitlements or {}
        self.auth_method = auth_method
        self.request_id = request_id


def verify_supabase_token(token: str) -> dict[str, Any]:
    """Verify Supabase JWT token signature and return payload."""
    try:
        # If we have a JWT secret configured, use HS256 to verify (Supabase default)
        from app.core.test_state import is_test_mode
        secret = settings.SUPABASE_JWT_SECRET
        if is_test_mode() and not secret:
            secret = "your-super-secret-jwt-token-with-at-least-32-characters-long"
        if not secret:
            raise HTTPException(status_code=500, detail="SUPABASE_JWT_SECRET not configured")
        
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_aud": False} # Usually aud is 'authenticated'
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_context(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    api_key: Annotated[str | None, Depends(api_key_header)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> RequestContext:
    """Resolve current context from token or API key."""
    req_id = getattr(request.state, "request_id", None)
    
    # 1. API Key Auth
    if api_key:
        result = await db.execute(
            select(ApiKey).where(ApiKey.key_hash == api_key, ApiKey.status == "active")
        )
        api_key_record = result.scalars().first()
        if not api_key_record:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        
        return RequestContext(
            user_id=str(api_key_record.created_by_id) if api_key_record.created_by_id else None,
            organization_id=str(api_key_record.organization_id),
            auth_method="API_KEY",
            request_id=req_id
        )

    # 2. Supabase JWT Auth
    if token:
        payload = verify_supabase_token(token)
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        # In a real flow, we map `sub` (auth_id) to our internal User
        result = await db.execute(select(User).where(User.auth_id == sub))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=401, detail="User profile not found")
        
        if user.status != "active":
            raise HTTPException(status_code=403, detail="User account suspended")

        # Resolve organization
        org_id = request.headers.get("X-Organization-ID")
        
        membership = None
        if org_id:
            res = await db.execute(select(OrgMember).where(
                OrgMember.user_id == user.id, 
                OrgMember.organization_id == org_id,
                OrgMember.status == "active"
            ))
            membership = res.scalars().first()
            if not membership:
                raise HTTPException(status_code=403, detail="Not a member of this organization")
        else:
            # Get default organization
            res = await db.execute(select(OrgMember).where(
                OrgMember.user_id == user.id,
                OrgMember.status == "active"
            ).limit(1))
            membership = res.scalars().first()
            if membership:
                org_id = str(membership.organization_id)

        return RequestContext(
            user_id=str(user.id),
            organization_id=org_id,
            membership_id=str(membership.id) if membership else None,
            organization_role=membership.role if membership else None,
            auth_method="SUPABASE_JWT",
            request_id=req_id
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
