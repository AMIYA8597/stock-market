"""CSRF token generation and validation.

Implements synchronizer token pattern for CSRF protection:
1. Server generates unique CSRF tokens
2. Tokens are tied to user sessions
3. Forms must include token in POST/PUT/DELETE requests
4. Server validates token before processing state-changing requests
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.csrf_token import CSRFToken
from app.core.config import get_settings

settings = get_settings()


async def generate_csrf_token(db: AsyncSession, user_id: str) -> str:
    """Generate a new CSRF token for the user.
    
    Args:
        db: Database session
        user_id: User ID to associate token with
        
    Returns:
        str: Base64-encoded CSRF token
    """
    token_value = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    
    csrf=CSRFToken(
        token=token_value,
        user_id=user_id,
        expires_at=expires_at,
    )
    db.add(csrf)
    await db.commit()
    
    return token_value


async def validate_csrf_token(db: AsyncSession, user_id: str, token: str) -> bool:
    """Validate a CSRF token.
    
    Args:
        db: Database session
        user_id: User ID that should own the token
        token: Token value to validate
        
    Returns:
        bool: True if token is valid, False otherwise
    """
    result = await db.execute(
        select(CSRFToken).where(
            and_(
                CSRFToken.user_id == user_id,
                CSRFToken.token == token,
                CSRFToken.expires_at > datetime.now(timezone.utc),
                CSRFToken.used_at.is_(None),
            )
        )
    )
    csrf_row = result.scalar_one_or_none()
    
    if csrf_row is None:
        return False
    
    # Mark token as used (one-time use)
    csrf_row.used_at = datetime.now(timezone.utc)
    await db.commit()
    
    return True


async def cleanup_expired_tokens(db: AsyncSession) -> int:
    """Delete expired CSRF tokens.
    
    Returns:
        int: Number of tokens deleted
    """
    from sqlalchemy import delete
    
    result = await db.execute(
        delete(CSRFToken).where(
            CSRFToken.expires_at < datetime.now(timezone.utc)
        )
    )
    await db.commit()
    return result.rowcount
