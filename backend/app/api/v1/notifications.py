"""Notification management endpoints router."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.identity import User
from app.models.notification import Notification
from app.schemas.errors import ErrorCode, ErrorResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationCreate(BaseModel):
    user_id: str
    title: str = Field(..., min_length=3, max_length=180)
    message: str = Field(..., min_length=3)
    level: str = Field(default="info", pattern="^(info|success|warning|error)$")


@router.get("")
async def list_notifications(
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict[str, object]:
    user_id_str = str(current_user.id)
    try:
        uid = uuid.UUID(user_id_str)
    except Exception:
        return {"items": []}

    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == uid)
        .order_by(Notification.created_at.desc())
        .limit(100)
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
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail=ErrorResponse.create(
                code=ErrorCode.INSUFFICIENT_PERMISSIONS,
                message="Admin access is required for this operation.",
            ).dict(),
        )

    try:
        uid = uuid.UUID(payload.user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID format.")

    user_result = await db.execute(select(User).where(User.id == uid))
    if user_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse.create(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Target user not found.",
            ).dict(),
        )

    row = Notification(
        user_id=uid,
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
    user_id_str = str(current_user.id)
    try:
        uid = uuid.UUID(user_id_str)
        nid = uuid.UUID(notification_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    result = await db.execute(
        select(Notification).where(Notification.id == nid, Notification.user_id == uid)
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
    await db.commit()
    return {"status": "ok"}
