"""Alert management endpoints router (GET/POST/PATCH/DELETE /alerts/*)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_user
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
    current_user: dict = Depends(get_current_user),
) -> AlertListResponse:
    user_id = current_user.get("sub")

    from app.core.config import get_settings
    settings = get_settings()

    if settings.MONGODB_URL:
        from app.database.mongodb import mongo_get_alerts
        rows = await mongo_get_alerts(user_id)
        items = [
            AlertData(
                id=str(row["_id"]),
                symbol=row["symbol"],
                alert_type=row["alert_type"],
                threshold=Decimal(str(row["threshold"])),
                name=row["name"],
                enabled=row["enabled"],
                is_triggered=row["is_triggered"],
                triggered_at=row["triggered_at"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]
        return AlertListResponse(alerts=items, total_count=len(items))

    now = datetime.now(UTC)
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
    current_user: dict = Depends(get_current_user),
) -> AlertData:
    user_id = current_user.get("sub")

    if request.alert_type not in {"PRICE_ABOVE", "PRICE_BELOW", "RSI_OB", "MACD_CROSS", "SIGNAL_CHANGE", "REGIME_CHANGE"}:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse.create(
                code=ErrorCode.VALIDATION_ERROR,
                message="Invalid alert type.",
            ).dict(),
        )

    from app.core.config import get_settings
    settings = get_settings()

    if settings.MONGODB_URL:
        from app.database.mongodb import mongo_create_alert
        row = await mongo_create_alert(user_id, {
            "symbol": request.symbol,
            "alert_type": request.alert_type,
            "threshold": float(request.threshold),
            "name": request.name,
            "enabled": request.enabled,
        })
        return AlertData(
            id=str(row["_id"]),
            symbol=row["symbol"],
            alert_type=row["alert_type"],
            threshold=Decimal(str(row["threshold"])),
            name=row["name"],
            enabled=row["enabled"],
            is_triggered=row["is_triggered"],
            triggered_at=row["triggered_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    now = datetime.now(UTC)
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
    current_user: dict = Depends(get_current_user),
) -> AlertUpdateResponse:
    user_id = current_user.get("sub")

    from app.core.config import get_settings
    settings = get_settings()

    if settings.MONGODB_URL:
        from app.database.mongodb import mongo_update_alert
        update_dict = {}
        if request.threshold is not None:
            update_dict["threshold"] = float(request.threshold)
        if request.name is not None:
            update_dict["name"] = request.name
        if request.enabled is not None:
            update_dict["enabled"] = request.enabled

        row = await mongo_update_alert(user_id, alert_id, update_dict)
        if row is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse.create(
                    code=ErrorCode.RESOURCE_NOT_FOUND,
                    message="Alert not found.",
                ).dict(),
            )
        alert = AlertData(
            id=str(row["_id"]),
            symbol=row["symbol"],
            alert_type=row["alert_type"],
            threshold=Decimal(str(row["threshold"])),
            name=row["name"],
            enabled=row["enabled"],
            is_triggered=row["is_triggered"],
            triggered_at=row["triggered_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        return AlertUpdateResponse(alert=alert)

    now = datetime.now(UTC)
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
    current_user: dict = Depends(get_current_user),
) -> AlertDeleteResponse:
    user_id = current_user.get("sub")

    from app.core.config import get_settings
    settings = get_settings()

    if settings.MONGODB_URL:
        from app.database.mongodb import mongo_delete_alert
        ok = await mongo_delete_alert(user_id, alert_id)
        if not ok:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse.create(
                    code=ErrorCode.RESOURCE_NOT_FOUND,
                    message="Alert not found or already deleted.",
                ).dict(),
            )
        return AlertDeleteResponse(id=alert_id, deleted_at=datetime.now(UTC))

    return AlertDeleteResponse(id=alert_id, deleted_at=datetime.now(UTC))



