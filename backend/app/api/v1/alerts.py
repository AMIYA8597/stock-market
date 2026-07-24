"""Alert management endpoints router (GET/POST/PATCH/DELETE /alerts/*)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.alert import Alert
from app.models.instrument import Instrument
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


@router.get("/history")
async def get_alerts_history(
    limit: int = 5,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id_str = str(current_user.id)
    try:
        uid = uuid.UUID(user_id_str)
    except Exception:
        return []

    stmt = (
        select(Alert, Instrument.symbol)
        .outerjoin(Instrument, Alert.instrument_id == Instrument.id)
        .where(and_(Alert.user_id == uid, Alert.is_triggered))
        .order_by(Alert.triggered_at.desc())
        .limit(limit)
    )

    res = await db.execute(stmt)
    rows = res.all()

    items = []
    for row, ticker in rows:
        items.append(
            {
                "id": f"evt-{row.id}",
                "alert_id": str(row.id),
                "alert_name": row.name,
                "symbol": ticker if ticker else "MARKET",
                "alert_type": row.alert_type,
                "severity": 3,
                "message": f"Alert {row.name} triggered on {ticker if ticker else 'market'}",
                "payload": {"threshold": float(row.threshold) if row.threshold else None},
                "triggered_at": row.triggered_at.isoformat()
                if row.triggered_at
                else datetime.now(UTC).isoformat(),
            }
        )

    return items


@router.get("", response_model=AlertListResponse)
async def get_alerts(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertListResponse:
    user_id_str = str(current_user.id)
    try:
        uid = uuid.UUID(user_id_str)
    except Exception:
        return AlertListResponse(alerts=[], total_count=0)

    stmt = (
        select(Alert, Instrument.symbol)
        .outerjoin(Instrument, Alert.instrument_id == Instrument.id)
        .where(Alert.user_id == uid)
    )
    res = await db.execute(stmt)
    rows = res.all()

    items = []
    for row, ticker in rows:
        items.append(
            AlertData(
                id=str(row.id),
                symbol=ticker if ticker else None,
                alert_type=row.alert_type,
                threshold=row.threshold,
                name=row.name,
                enabled=row.enabled,
                is_triggered=row.is_triggered,
                triggered_at=row.triggered_at,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )
    return AlertListResponse(alerts=items, total_count=len(items))


@router.post("", response_model=AlertData, status_code=201)
async def post_alert(
    request: AlertCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertData:
    user_id_str = str(current_user.id)

    if request.alert_type not in {
        "PRICE_ABOVE",
        "PRICE_BELOW",
        "RSI_OB",
        "MACD_CROSS",
        "SIGNAL_CHANGE",
        "REGIME_CHANGE",
    }:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse.create(
                code=ErrorCode.VALIDATION_ERROR,
                message="Invalid alert type.",
            ).dict(),
        )

    try:
        uid = uuid.UUID(user_id_str)
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")

    symbol_id = None
    symbol_ticker = None
    if request.symbol:
        symbol_ticker = request.symbol.upper().strip()
        sym_res = await db.execute(select(Instrument).where(Instrument.symbol == symbol_ticker))
        sym = sym_res.scalar_one_or_none()
        if not sym:
            # Auto-create the instrument on the fly to support 10,000+ dynamic stocks
            new_sym = Instrument(
                symbol=symbol_ticker,
                name=f"{symbol_ticker} (Auto-added)",
                exchange="NSE" if symbol_ticker.endswith(".NS") else ("CRYPTO" if "-USD" in symbol_ticker else "NASDAQ"),
                asset_class="STOCK"
            )
            db.add(new_sym)
            await db.flush()
            sym = new_sym
        symbol_id = sym.id

    new_alert = Alert(
        user_id=uid,
        instrument_id=symbol_id,
        alert_type=request.alert_type,
        threshold=request.threshold,
        name=request.name,
        enabled=request.enabled,
    )
    db.add(new_alert)
    await db.commit()
    await db.refresh(new_alert)

    return AlertData(
        id=str(new_alert.id),
        symbol=symbol_ticker,
        alert_type=new_alert.alert_type,
        threshold=new_alert.threshold,
        name=new_alert.name,
        enabled=new_alert.enabled,
        is_triggered=new_alert.is_triggered,
        triggered_at=new_alert.triggered_at,
        created_at=new_alert.created_at,
        updated_at=new_alert.updated_at,
    )


@router.patch("/{alert_id}", response_model=AlertUpdateResponse)
async def patch_alert(
    alert_id: str,
    request: AlertUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertUpdateResponse:
    user_id_str = str(current_user.id)
    try:
        uid = uuid.UUID(user_id_str)
        a_id = uuid.UUID(alert_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    stmt = (
        select(Alert, Instrument.symbol)
        .outerjoin(Instrument, Alert.instrument_id == Instrument.id)
        .where(and_(Alert.id == a_id, Alert.user_id == uid))
    )
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found.")

    alert_obj, ticker = row

    if request.name is not None:
        alert_obj.name = request.name
    if request.threshold is not None:
        alert_obj.threshold = request.threshold
    if request.enabled is not None:
        alert_obj.enabled = request.enabled

    await db.commit()
    await db.refresh(alert_obj)

    alert_data = AlertData(
        id=str(alert_obj.id),
        symbol=ticker if ticker else None,
        alert_type=alert_obj.alert_type,
        threshold=alert_obj.threshold,
        name=alert_obj.name,
        enabled=alert_obj.enabled,
        is_triggered=alert_obj.is_triggered,
        triggered_at=alert_obj.triggered_at,
        created_at=alert_obj.created_at,
        updated_at=alert_obj.updated_at,
    )
    return AlertUpdateResponse(alert=alert_data)


@router.delete("/{alert_id}", response_model=AlertDeleteResponse)
async def delete_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertDeleteResponse:
    user_id_str = str(current_user.id)
    try:
        uid = uuid.UUID(user_id_str)
        a_id = uuid.UUID(alert_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    stmt = delete(Alert).where(and_(Alert.id == a_id, Alert.user_id == uid))
    res = await db.execute(stmt)
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="Alert not found.")

    await db.commit()
    return AlertDeleteResponse(id=alert_id, deleted_at=datetime.now(UTC))
