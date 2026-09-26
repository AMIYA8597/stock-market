import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_role
from app.core.entitlements import require_feature
from app.core.security import RequestContext
from app.database.connection import get_db
from app.models.alerts import Alert

router = APIRouter(prefix="/alerts", tags=["alerts"])

class AlertCreate(BaseModel):
    symbol: str
    alert_type: str
    threshold: float

@router.post("")
async def create_alert(
    payload: AlertCreate,
    ctx: RequestContext = Depends(require_role("VIEWER")),
    _ = Depends(require_feature("ALERTS")),
    db: AsyncSession = Depends(get_db)
):
    if not ctx.organization_id:
        raise HTTPException(status_code=403, detail="Organization required")

    alert = Alert(
        organization_id=uuid.UUID(ctx.organization_id),
        user_id=uuid.UUID(ctx.user_id),
        symbol=payload.symbol,
        alert_type=payload.alert_type,
        threshold=payload.threshold
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return {"success": True, "data": {"id": str(alert.id)}}

@router.get("")
async def list_alerts(
    ctx: RequestContext = Depends(require_role("VIEWER")),
    db: AsyncSession = Depends(get_db)
):
    if not ctx.organization_id:
        raise HTTPException(status_code=403, detail="Organization required")

    result = await db.execute(select(Alert).where(Alert.organization_id == uuid.UUID(ctx.organization_id)))
    alerts = result.scalars().all()
    return {"success": True, "data": alerts}
