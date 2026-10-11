import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_role
from app.core.security import RequestContext
from app.database.connection import get_db
from app.models.alerts import Alert, AlertEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])

class AlertCreate(BaseModel):
    symbol: str
    alert_type: str
    threshold: float

@router.post("")
async def create_alert(
    payload: AlertCreate,
    ctx: RequestContext = Depends(require_role("VIEWER")),
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
    alerts_list = result.scalars().all()
    items = []
    for a in alerts_list:
        items.append({
            "id": str(a.id),
            "symbol": a.symbol,
            "alert_type": a.alert_type,
            "threshold": a.threshold,
            "is_active": a.is_active,
            "last_triggered_at": a.last_triggered_at.isoformat() if a.last_triggered_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return {"alerts": items, "total_count": len(items)}

class AlertUpdate(BaseModel):
    symbol: str | None = None
    alert_type: str | None = None
    threshold: float | None = None
    enabled: bool | None = None
    name: str | None = None

@router.patch("/{alert_id}")
async def update_alert(
    alert_id: str,
    payload: AlertUpdate,
    ctx: RequestContext = Depends(require_role("VIEWER")),
    db: AsyncSession = Depends(get_db)
):
    if not ctx.organization_id:
        raise HTTPException(status_code=403, detail="Organization required")
    try:
        aid = uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID")
    result = await db.execute(
        select(Alert).where(Alert.id == aid, Alert.organization_id == uuid.UUID(ctx.organization_id))
    )
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if payload.symbol is not None:
        alert.symbol = payload.symbol
    if payload.alert_type is not None:
        alert.alert_type = payload.alert_type
    if payload.threshold is not None:
        alert.threshold = payload.threshold
    if payload.enabled is not None:
        alert.is_active = payload.enabled
    await db.commit()
    await db.refresh(alert)
    return {"success": True, "data": {"id": str(alert.id)}}

@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: str,
    ctx: RequestContext = Depends(require_role("VIEWER")),
    db: AsyncSession = Depends(get_db)
):
    if not ctx.organization_id:
        raise HTTPException(status_code=403, detail="Organization required")
    try:
        aid = uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID")
    result = await db.execute(
        select(Alert).where(Alert.id == aid, Alert.organization_id == uuid.UUID(ctx.organization_id))
    )
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.delete(alert)
    await db.commit()
    return {"success": True}

@router.get("/history")
async def alert_history(
    limit: int = 20,
    ctx: RequestContext = Depends(require_role("VIEWER")),
    db: AsyncSession = Depends(get_db)
):
    if not ctx.organization_id:
        raise HTTPException(status_code=403, detail="Organization required")

    try:
        result = await db.execute(
            select(AlertEvent, Alert)
            .join(Alert, AlertEvent.alert_id == Alert.id)
            .where(AlertEvent.organization_id == uuid.UUID(ctx.organization_id))
            .order_by(AlertEvent.created_at.desc())
            .limit(limit)
        )
    except Exception as exc:
        logger.warning("Alert history DB query failed: %s", exc)
        return {"events": [], "total": 0}
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
