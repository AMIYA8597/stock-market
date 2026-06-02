from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.errors import ErrorCode, ErrorResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationCreate(BaseModel):
    user_id: str
    title: str = Field(..., min_length=3, max_length=180)
    message: str = Field(..., min_length=3)
    level: str = Field(default="info", pattern="^(info|success|warning|error)$")


@router.get("")
async def list_notifications(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    user_id = current_user.get("sub")
    result = await db.execute(
        select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc()).limit(100)
    )
    rows = result.scalars().all()
    return {
        "items": [
            {
                "id": str(row.id),
                "title": row.title,
                "message": row.message,
                "level": row.level,
                "is_read": row.is_read,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
    }


@router.post("")
async def create_notification(
    payload: NotificationCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    if current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail=ErrorResponse.create(
                code=ErrorCode.INSUFFICIENT_PERMISSIONS,
                message="Admin access is required for this operation.",
            ).dict(),
        )

    user_result = await db.execute(select(User).where(User.id == payload.user_id))
    if user_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse.create(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Target user not found.",
            ).dict(),
        )

    row = Notification(
        user_id=payload.user_id,
        title=payload.title,
        message=payload.message,
        level=payload.level,
        is_read=False,
    )
    db.add(row)
    await db.flush()
    return {"id": str(row.id)}


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    user_id = current_user.get("sub")
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse.create(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Notification not found.",
            ).dict(),
        )

    row.is_read = True
    row.read_at = datetime.now(UTC)
    return {"status": "ok"}
