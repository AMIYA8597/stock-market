import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.security import RequestContext, get_current_context
from app.models.identity import OrgMember, User
from app.schemas.errors import ErrorCode, ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

VALID_ORG_ROLES = {"OWNER", "ADMIN", "BILLING_ADMIN", "RESEARCHER", "ANALYST", "TRADER", "VIEWER", "API_USER"}
# The admin dashboard only exposes a simple USER/ADMIN toggle; "USER" is
# accepted as an alias for the org role "VIEWER" (base non-admin access).
FRONTEND_ROLE_ALIASES = {"USER": "VIEWER"}


def _require_superadmin(ctx: RequestContext) -> None:
    if ctx.organization_role != "SUPERADMIN" and ctx.platform_role != "SUPERADMIN":
        raise HTTPException(status_code=403, detail="Superadmin access is required.")


def _require_org_context(ctx: RequestContext) -> uuid.UUID:
    if not ctx.organization_id:
        raise HTTPException(status_code=400, detail="No organization context on this session.")
    try:
        return uuid.UUID(str(ctx.organization_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid organization id.") from exc


class UpdateRoleRequest(BaseModel):
    role: str = Field(..., description="New organization role for this member")


@router.get("/users")
async def list_users(
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    _require_superadmin(ctx)
    org_id = _require_org_context(ctx)

    stmt = (
        select(User.id, User.email, User.full_name, User.status, OrgMember.role)
        .join(OrgMember, OrgMember.user_id == User.id)
        .where(OrgMember.organization_id == org_id)
        .order_by(User.email)
    )
    res = await db.execute(stmt)
    rows = res.all()
    return [
        {
            "id": str(row.id),
            "email": row.email,
            "full_name": row.full_name,
            "is_active": row.status == "active",
            "role": "ADMIN" if row.role == "ADMIN" else "USER",
        }
        for row in rows
    ]


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    request: UpdateRoleRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    _require_superadmin(ctx)
    org_id = _require_org_context(ctx)

    requested_role = request.role.upper().strip()
    new_role = FRONTEND_ROLE_ALIASES.get(requested_role, requested_role)
    if new_role not in VALID_ORG_ROLES:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse.create(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"role must be one of {sorted(VALID_ORG_ROLES | set(FRONTEND_ROLE_ALIASES))}",
            ).dict(),
        )

    try:
        target_user_id = uuid.UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user_id.") from exc

    member_res = await db.execute(
        select(OrgMember, User).join(User, User.id == OrgMember.user_id).where(
            OrgMember.organization_id == org_id, OrgMember.user_id == target_user_id
        )
    )
    row = member_res.first()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse.create(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="This user is not a member of your organization.",
            ).dict(),
        )

    membership, target_user = row
    membership.role = new_role
    await db.commit()
    return {
        "id": str(target_user.id),
        "email": target_user.email,
        "full_name": target_user.full_name,
        "is_active": target_user.status == "active",
        "role": "ADMIN" if new_role == "ADMIN" else "USER",
    }


@router.get("/content")
async def content_control(
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    _require_superadmin(ctx)
    from app.models.blog import BlogPost

    stmt = select(BlogPost).order_by(BlogPost.created_at.desc()).limit(100)
    res = await db.execute(stmt)
    posts = res.scalars().all()
    return {
        "posts": [
            {
                "id": str(p.id),
                "slug": p.slug,
                "title": p.title,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in posts
        ]
    }


@router.post("/ingest")
async def trigger_ingestion(ctx: RequestContext = Depends(get_current_context)):
    _require_superadmin(ctx)
    import asyncio

    from app.jobs.ingestion import IngestionPipeline

    pipeline = IngestionPipeline()
    asyncio.create_task(pipeline.run_full_ingestion())
    return {"message": "Ingestion triggered"}
