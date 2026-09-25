from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from app.core.security import get_current_context, RequestContext
from app.database.connection import get_db
from app.models.identity import User

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

class OnboardingRequest(BaseModel):
    profile: dict
    organization: dict
    marketPrefs: dict
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
        user.preferences = {
            "profile": payload.profile,
            "marketPrefs": payload.marketPrefs,
            "workspace": payload.workspace
        }
        await db.commit()
    return {"success": True, "message": "Onboarding completed"}
