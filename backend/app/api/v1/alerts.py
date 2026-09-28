import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_role
from app.core.entitlements import require_feature
from app.core.security import RequestContext
from app.database.connection import get_db
from app.models.alerts import Alert, AlertEvent

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

@router.get("/history")
async def alert_history(
    limit: int = 20,
    ctx: RequestContext = Depends(require_role("VIEWER")),
    db: AsyncSession = Depends(get_db)
):
    if not ctx.organization_id:
        raise HTTPException(status_code=403, detail="Organization required")

    result = await db.execute(
        select(AlertEvent, Alert)
        .join(Alert, AlertEvent.alert_id == Alert.id)
        .where(AlertEvent.organization_id == uuid.UUID(ctx.organization_id))
        .order_by(AlertEvent.created_at.desc())
        .limit(limit)
    )
    items = []
    for event, alert in result.all():
        data = event.event_data if isinstance(event.event_data, dict) else {}
        items.append({
            "id": str(event.id),
            "alert_id": str(event.alert_id),
            "alert_name": data.get("alert_name", f"{alert.symbol} {alert.alert_type}"),
            "symbol": alert.symbol,
            "alert_type": alert.alert_type.lower(),
            "severity": data.get("severity", 2),
            "message": data.get("message", "Alert triggered."),
            "payload": data,
            "triggered_at": event.created_at.isoformat(),
        })
    return items
