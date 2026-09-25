import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_role
from app.core.security import RequestContext, get_current_context
from app.database.connection import get_db
from app.models.identity import ApiKey, Invitation, Organization, OrgMember, User

router = APIRouter(prefix="/organizations", tags=["organizations"])

class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    role: str

@router.get("", response_model=list[OrganizationResponse])
async def list_user_organizations(
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db)
):
    # Returns all organizations the user is a member of
    user_id = uuid.UUID(ctx.user_id)
    result = await db.execute(
        select(Organization, OrgMember)
        .join(OrgMember, OrgMember.organization_id == Organization.id)
        .where(OrgMember.user_id == user_id, OrgMember.status == "active")
    )
    rows = result.all()
    return [
        OrganizationResponse(
            id=str(org.id),
            name=org.name,
            slug=org.slug,
            role=member.role
        )
        for org, member in rows
    ]

# Members
class MemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    full_name: str | None
    role: str
    status: str

@router.get("/{org_id}/members", response_model=list[MemberResponse])
async def list_members(
    org_id: str,
    ctx: RequestContext = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db)
):
    if ctx.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-organization access denied")

    result = await db.execute(
        select(OrgMember, User)
        .join(User, User.id == OrgMember.user_id)
        .where(OrgMember.organization_id == uuid.UUID(org_id))
    )
    rows = result.all()
    return [
        MemberResponse(
            id=str(member.id),
            user_id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=member.role,
            status=member.status
        )
        for member, user in rows
    ]

class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "VIEWER"

@router.post("/{org_id}/invitations")
async def invite_member(
    org_id: str,
    payload: InviteRequest,
    ctx: RequestContext = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db)
):
    if ctx.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-organization access denied")

    # Check seat limits here
    # A complete implementation would check OrgMember count vs Plan limit

    # Check if already invited
    org_uuid = uuid.UUID(org_id)
    existing_invite = await db.execute(
        select(Invitation).where(Invitation.organization_id == org_uuid, Invitation.email == payload.email, Invitation.status == "pending")
    )
    if existing_invite.first():
        raise HTTPException(status_code=409, detail="Invitation already pending")

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    invitation = Invitation(
        organization_id=org_uuid,
        inviter_id=uuid.UUID(ctx.user_id),
        email=payload.email,
        role=payload.role.upper(),
        token_hash=token_hash,
        status="pending",
        expires_at=datetime.now(UTC) + timedelta(days=7)
    )
    db.add(invitation)
    await db.commit()

    # In real world, send email with `token` here
    return {"success": True, "message": "Invitation created", "token": token}

# API Keys
class ApiKeyCreate(BaseModel):
    name: str
    scopes: str

@router.post("/{org_id}/api-keys")
async def create_api_key(
    org_id: str,
    payload: ApiKeyCreate,
    ctx: RequestContext = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db)
):
    if ctx.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-organization access denied")

    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    prefix = raw_key[:8]

    api_key = ApiKey(
        organization_id=uuid.UUID(org_id),
        created_by_id=uuid.UUID(ctx.user_id),
        prefix=prefix,
        key_hash=key_hash,
        name=payload.name,
        scopes=payload.scopes,
        status="active"
    )
    db.add(api_key)
    await db.commit()

    return {
        "success": True,
        "data": {
            "id": str(api_key.id),
            "key": raw_key, # Show only once!
            "prefix": prefix,
            "scopes": api_key.scopes
        }
    }

@router.get("/{org_id}/api-keys")
async def list_api_keys(
    org_id: str,
    ctx: RequestContext = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db)
):
    if ctx.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-organization access denied")

    result = await db.execute(
        select(ApiKey).where(ApiKey.organization_id == uuid.UUID(org_id), ApiKey.status == "active")
    )
    keys = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": str(k.id),
                "name": k.name,
                "prefix": k.prefix,
                "scopes": k.scopes,
                "created_at": k.created_at.isoformat()
            } for k in keys
        ]
    }

class OrganizationCreate(BaseModel):
    name: str
    slug: str

@router.post("", response_model=OrganizationResponse)
async def create_organization(
    payload: OrganizationCreate,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db)
):
    user_id = uuid.UUID(ctx.user_id)
    org = Organization(name=payload.name, slug=payload.slug)
    db.add(org)
    await db.flush()
    member = OrgMember(organization_id=org.id, user_id=user_id, role="OWNER", status="active")
    db.add(member)
    await db.commit()
    return OrganizationResponse(id=str(org.id), name=org.name, slug=org.slug, role="OWNER")
