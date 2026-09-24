from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.security import get_current_context, RequestContext
from app.database.connection import get_db
from app.models.identity import User
from app.schemas.errors import ErrorCode, ErrorResponse

router = APIRouter(prefix="/users", tags=["users"])

class UpdateProfileRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=120)

class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    status: str

@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    ctx: RequestContext = Depends(get_current_context), db: AsyncSession = Depends(get_db)
) -> UserProfileResponse:
    uid = uuid.UUID(ctx.user_id)
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User profile not found.")

    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        status=user.status,
    )

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

    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        status=user.status,
    )
