import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import RequestContext, get_current_context
from app.database.connection import get_db
from app.models.identity import OrgMember, User

router = APIRouter(prefix="/users", tags=["users"])

class UpdateProfileRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=120)

class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str
    is_active: bool
    is_2fa_enabled: bool
    created_at: str | None
    last_login_at: str | None

async def _get_user_role(db: AsyncSession, user_id: uuid.UUID) -> str:
    result = await db.execute(
        select(OrgMember.role).where(OrgMember.user_id == user_id).limit(1)
    )
    role = result.scalar_one_or_none()
    return role or "viewer"

def _build_profile(user: User, role: str) -> UserProfileResponse:
    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=role,
        is_active=user.status == "active",
        is_2fa_enabled=False,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )

@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    ctx: RequestContext = Depends(get_current_context), db: AsyncSession = Depends(get_db)
) -> UserProfileResponse:
    uid = uuid.UUID(ctx.user_id)
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User profile not found.")

    role = await _get_user_role(db, uid)
    return _build_profile(user, role)

@router.patch("/profile", response_model=UserProfileResponse)
async def update_profile(
    payload: UpdateProfileRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    uid = uuid.UUID(ctx.user_id)
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User profile not found.")

    user.full_name = payload.full_name
    await db.commit()

    role = await _get_user_role(db, uid)
    return _build_profile(user, role)
