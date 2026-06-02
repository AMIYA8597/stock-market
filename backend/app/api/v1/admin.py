from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.blog import BlogPost
from app.models.user import User
from app.schemas.errors import ErrorCode, ErrorResponse

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(current_user: dict) -> None:
    if current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail=ErrorResponse.create(
                code=ErrorCode.INSUFFICIENT_PERMISSIONS,
                message="Admin access is required for this operation.",
            ).dict(),
        )


class AdminUserItem(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str
    is_active: bool


class UpdateRoleRequest(BaseModel):
    role: str = Field(..., pattern="^(ADMIN|USER)$")


@router.get("/users", response_model=list[AdminUserItem])
async def list_users(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[AdminUserItem]:
    _require_admin(current_user)
    
    from app.core.config import get_settings
    settings = get_settings()

    if settings.MONGODB_URL:
        from app.database.mongodb import get_mongo_db
        database = get_mongo_db()
        if database is not None:
            cursor = database.users.find().sort("created_at", -1).limit(200)
            rows = await cursor.to_list(length=200)
            return [
                AdminUserItem(
                    id=str(row["_id"]),
                    email=row["email"],
                    full_name=row.get("full_name"),
                    role=row["role"],
                    is_active=row["is_active"],
                )
                for row in rows
            ]
        return []

    result = await db.execute(select(User).order_by(User.created_at.desc()).limit(200))
    rows = result.scalars().all()
    return [
        AdminUserItem(
            id=str(row.id),
            email=row.email,
            full_name=row.full_name,
            role=row.role,
            is_active=row.is_active,
        )
        for row in rows
    ]


@router.patch("/users/{user_id}/role", response_model=AdminUserItem)
async def update_user_role(
    user_id: str,
    payload: UpdateRoleRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AdminUserItem:
    _require_admin(current_user)

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
                    message="User not found.",
                ).dict(),
            )
        await mongo_update_user(user_id, {"role": payload.role})
        return AdminUserItem(
            id=user_id,
            email=user["email"],
            full_name=user.get("full_name"),
            role=payload.role,
            is_active=user["is_active"],
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse.create(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="User not found.",
            ).dict(),
        )

    user.role = payload.role
    return AdminUserItem(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )


@router.get("/content")
async def content_control(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict[str, list[dict[str, str]]]:
    _require_admin(current_user)

    from app.core.config import get_settings
    settings = get_settings()

    if settings.MONGODB_URL:
        from app.database.mongodb import get_mongo_db
        database = get_mongo_db()
        if database is not None:
            cursor = database.blog_posts.find().sort("updated_at", -1).limit(100)
            posts = await cursor.to_list(length=100)
            return {
                "posts": [
                    {
                        "id": str(post["_id"]),
                        "slug": post["slug"],
                        "title": post["title"],
                        "status": post["status"],
                    }
                    for post in posts
                ]
            }
        return {"posts": []}

    post_result = await db.execute(select(BlogPost).order_by(BlogPost.updated_at.desc()).limit(100))
    posts = post_result.scalars().all()
    return {
        "posts": [
            {
                "id": str(post.id),
                "slug": post.slug,
                "title": post.title,
                "status": post.status,
            }
            for post in posts
        ]
    }

