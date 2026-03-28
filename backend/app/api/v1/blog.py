from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, get_redis
from app.models.blog import BlogPost

router = APIRouter(prefix="/blog", tags=["blog"])


class BlogPostCreate(BaseModel):
    slug: str = Field(..., min_length=3, max_length=180)
    title: str = Field(..., min_length=3, max_length=220)
    excerpt: str = Field(..., min_length=8, max_length=400)
    content: str = Field(..., min_length=20)
    status: Literal["draft", "published"] = "draft"


class BlogPostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=220)
    excerpt: str | None = Field(default=None, min_length=8, max_length=400)
    content: str | None = Field(default=None, min_length=20)
    status: Literal["draft", "published"] | None = None


def _admin_only(current_user: dict) -> None:
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/posts")
async def list_posts(
    limit: int = 20,
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    cache_key = f"blog:list:{limit}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    result = await db.execute(
        select(BlogPost)
        .where(BlogPost.status == "published")
        .order_by(BlogPost.published_at.desc().nullslast(), BlogPost.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()

    payload = {
        "items": [
            {
                "slug": row.slug,
                "title": row.title,
                "excerpt": row.excerpt,
                "published_at": row.published_at.isoformat() if row.published_at else None,
            }
            for row in rows
        ]
    }
    await redis.setex(cache_key, 60, json.dumps(payload))
    return payload


@router.get("/posts/{slug}")
async def get_post(slug: str, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    result = await db.execute(select(BlogPost).where(BlogPost.slug == slug))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Post not found")

    return {
        "slug": row.slug,
        "title": row.title,
        "excerpt": row.excerpt,
        "content": row.content,
        "status": row.status,
        "published_at": row.published_at.isoformat() if row.published_at else None,
    }


@router.post("/posts")
async def create_post(
    payload: BlogPostCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    _admin_only(current_user)

    exists = await db.execute(select(BlogPost).where(BlogPost.slug == payload.slug))
    if exists.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Slug already exists")

    published_at = datetime.now(timezone.utc) if payload.status == "published" else None
    post = BlogPost(
        slug=payload.slug,
        title=payload.title,
        excerpt=payload.excerpt,
        content=payload.content,
        status=payload.status,
        author_id=current_user.get("sub"),
        published_at=published_at,
    )
    db.add(post)
    await db.flush()
    return {"id": str(post.id), "slug": post.slug}


@router.patch("/posts/{slug}")
async def update_post(
    slug: str,
    payload: BlogPostUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    _admin_only(current_user)

    result = await db.execute(select(BlogPost).where(BlogPost.slug == slug))
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    if payload.title is not None:
        post.title = payload.title
    if payload.excerpt is not None:
        post.excerpt = payload.excerpt
    if payload.content is not None:
        post.content = payload.content
    if payload.status is not None:
        post.status = payload.status
        if payload.status == "published" and post.published_at is None:
            post.published_at = datetime.now(timezone.utc)

    return {"id": str(post.id), "slug": post.slug}
