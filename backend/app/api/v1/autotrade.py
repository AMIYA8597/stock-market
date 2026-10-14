"""FastAPI router for the automatic paper-trading opt-in (AutoTradeSetting).

Enabling this makes app.tasks.autotrade_tasks.run_autotrade_scan (runs every
5 minutes via Celery beat) place paper orders on the user's behalf when a
symbol in their chosen watchlist crosses the configured confidence
threshold. It never places real broker orders -- BrokerAdapter.place_order
is hardcoded to paper trading.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.autotrade import AutoTradeSetting
from app.models.identity import User

router = APIRouter(prefix="/autotrade", tags=["autotrade"])


class AutoTradeSettingRequest(BaseModel):
    enabled: bool = False
    watchlist_id: int = 0
    max_open_positions: int = Field(default=5, ge=1, le=50)
    risk_per_trade_pct: float = Field(default=0.02, gt=0, le=0.5)
    min_confidence: float = Field(default=65.0, ge=0, le=100)


class AutoTradeSettingResponse(BaseModel):
    execution_mode: str = "paper"
    enabled: bool
    watchlist_id: int
    max_open_positions: int
    risk_per_trade_pct: float
    min_confidence: float
    last_scan_at: str | None = None
    last_scan_result: dict | None = None


def _to_response(setting: AutoTradeSetting) -> AutoTradeSettingResponse:
    return AutoTradeSettingResponse(
        execution_mode="paper",
        enabled=setting.enabled,
        watchlist_id=setting.watchlist_id,
        max_open_positions=setting.max_open_positions,
        risk_per_trade_pct=float(setting.risk_per_trade_pct),
        min_confidence=float(setting.min_confidence),
        last_scan_at=setting.last_scan_at.isoformat() if setting.last_scan_at else None,
        last_scan_result=setting.last_scan_result,
    )


@router.get("/settings", response_model=AutoTradeSettingResponse)
async def get_autotrade_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    res = await db.execute(
        select(AutoTradeSetting).where(AutoTradeSetting.user_id == current_user.id)
    )
    setting = res.scalar_one_or_none()
    if not setting:
        setting = AutoTradeSetting(user_id=current_user.id)
    return _to_response(setting)


@router.put("/settings", response_model=AutoTradeSettingResponse)
async def update_autotrade_settings(
    request: AutoTradeSettingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    res = await db.execute(
        select(AutoTradeSetting).where(AutoTradeSetting.user_id == current_user.id)
    )
    setting = res.scalar_one_or_none()
    if not setting:
        setting = AutoTradeSetting(user_id=current_user.id)
        db.add(setting)

    setting.enabled = request.enabled
    setting.watchlist_id = request.watchlist_id
    setting.max_open_positions = request.max_open_positions
    setting.risk_per_trade_pct = request.risk_per_trade_pct
    setting.min_confidence = request.min_confidence

    await db.commit()
    await db.refresh(setting)
    return _to_response(setting)
