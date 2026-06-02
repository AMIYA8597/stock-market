from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.test_state import TEST_USERS_BY_ID, is_test_mode
from app.models.user import User
from app.schemas.errors import ErrorCode, ErrorResponse

router = APIRouter(prefix="/users", tags=["users"])


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=120)


class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str
    is_active: bool


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> UserProfileResponse:
    user_id = current_user.get("sub")
    if is_test_mode():
        user = TEST_USERS_BY_ID.get(str(user_id))
        if user is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse.create(
                    code=ErrorCode.RESOURCE_NOT_FOUND,
                    message="User profile not found.",
                ).dict(),
            )

        return UserProfileResponse(
            id=str(user["id"]),
            email=str(user["email"]),
            full_name=user.get("full_name"),
            role=str(user.get("role", "USER")),
            is_active=bool(user.get("is_active", True)),
        )

    from app.core.config import get_settings
    settings = get_settings()

    if settings.MONGODB_URL:
        from app.database.mongodb import mongo_get_user_by_id
        user = await mongo_get_user_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse.create(
                    code=ErrorCode.RESOURCE_NOT_FOUND,
                    message="User profile not found.",
                ).dict(),
            )
        return UserProfileResponse(
            id=str(user["_id"]),
            email=user["email"],
            full_name=user.get("full_name"),
            role=user["role"],
            is_active=user["is_active"],
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse.create(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="User profile not found.",
            ).dict(),
        )

    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )


@router.patch("/profile", response_model=UserProfileResponse)
async def update_profile(
    payload: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    user_id = current_user.get("sub")
    
    from app.core.config import get_settings
    settings = get_settings()

    if settings.MONGODB_URL:
        from app.database.mongodb import mongo_get_user_by_id, mongo_update_user
        user = await mongo_get_user_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse.create(
                    code=ErrorCode.RESOURCE_NOT_FOUND,
                    message="User profile not found.",
                ).dict(),
            )
        await mongo_update_user(user_id, {"full_name": payload.full_name})
        return UserProfileResponse(
            id=user_id,
            email=user["email"],
            full_name=payload.full_name,
            role=user["role"],
            is_active=user["is_active"],
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse.create(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="User profile not found.",
            ).dict(),
        )

    user.full_name = payload.full_name

    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )
