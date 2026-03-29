"""Alert management endpoints router (GET/POST/PATCH/DELETE /alerts/*)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.screener import (
    AlertCreateRequest,
    AlertData,
    AlertDeleteResponse,
    AlertListResponse,
    AlertUpdateRequest,
    AlertUpdateResponse,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse)
async def get_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> AlertListResponse:
    _ = db
    _ = current_user
    now = datetime.now(timezone.utc)
    items = [
        AlertData(
            id=str(uuid4()),
            symbol="RELIANCE.NS",
            alert_type="PRICE_ABOVE",
            threshold=Decimal("2500.00"),
            name="Reliance breakout",
            enabled=True,
            is_triggered=False,
            triggered_at=None,
            created_at=now,
            updated_at=now,
        )
    ]
    return AlertListResponse(alerts=items, total_count=len(items))


@router.post("", response_model=AlertData, status_code=201)
async def post_alert(
    request: AlertCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> AlertData:
    _ = db
    _ = current_user
    now = datetime.now(timezone.utc)
    if request.alert_type not in {"PRICE_ABOVE", "PRICE_BELOW", "RSI_OB", "MACD_CROSS", "SIGNAL_CHANGE", "REGIME_CHANGE"}:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse.create(
                code=ErrorCode.VALIDATION_ERROR,
                message="Invalid alert type.",
            ).dict(),
        )

    return AlertData(
        id=str(uuid4()),
        symbol=request.symbol,
        alert_type=request.alert_type,
        threshold=request.threshold,
        name=request.name,
        enabled=request.enabled,
        is_triggered=False,
        triggered_at=None,
        created_at=now,
        updated_at=now,
    )


@router.patch("/{alert_id}", response_model=AlertUpdateResponse)
async def patch_alert(
    alert_id: str,
    request: AlertUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> AlertUpdateResponse:
    _ = db
    _ = current_user
    now = datetime.now(timezone.utc)
    alert = AlertData(
        id=alert_id,
        symbol="RELIANCE.NS",
        alert_type="PRICE_ABOVE",
        threshold=request.threshold or Decimal("2500.00"),
        name=request.name or "Reliance breakout",
        enabled=True if request.enabled is None else request.enabled,
        is_triggered=False,
        triggered_at=None,
        created_at=now,
        updated_at=now,
    )
    return AlertUpdateResponse(alert=alert)


@router.delete("/{alert_id}", response_model=AlertDeleteResponse)
async def delete_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> AlertDeleteResponse:
    _ = db
    _ = current_user
    return AlertDeleteResponse(id=alert_id, deleted_at=datetime.now(timezone.utc))
