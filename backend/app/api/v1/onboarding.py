import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import RequestContext, get_current_context
from app.database.connection import get_db
from app.models.identity import User

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

class OnboardingRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    profile: dict
    organization: dict
    # The frontend sends this key as camelCase JSON (matches its own JS/TS
    # naming convention); alias it on the wire while keeping the Python
    # attribute name snake_case.
    market_prefs: dict = Field(alias="marketPrefs")
    workspace: dict

@router.post("")
async def complete_onboarding(
    payload: OnboardingRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db)
):
    uid = uuid.UUID(ctx.user_id)
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if user:
        profile_name = payload.profile.get("full_name") or payload.profile.get("name")
        if profile_name and isinstance(profile_name, str):
            user.full_name = profile_name
        await db.commit()
    return {"success": True, "message": "Onboarding completed"}
