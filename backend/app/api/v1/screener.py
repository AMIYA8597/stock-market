"""Stock screener endpoints router (POST/GET /screener/*)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.schemas.screener import (
    ScreenerPreset,
    ScreenerPresetsResponse,
    ScreenerResult,
    ScreenerRunRequest,
    ScreenerRunResponse,
)

router = APIRouter(prefix="/screener", tags=["screener"])


@router.post("/run", response_model=ScreenerRunResponse)
async def post_screener_run(request: ScreenerRunRequest, db: AsyncSession = Depends(get_db)) -> ScreenerRunResponse:
    _ = db
    max_items = min(request.limit, 20)
    data = [
        ScreenerResult(
            ticker="RELIANCE.NS",
            name="Reliance Industries",
            exchange=request.exchange[0] if request.exchange else "NSE",
            asset_type="EQUITY",
            price=Decimal("2521.30000000"),
            change_pct=Decimal("1.3600"),
            pe_ratio=Decimal("24.1200"),
            rsi=Decimal("58.1000"),
            signal_direction="BUY",
            signal_confidence=Decimal("0.7300"),
            regime_state="bull",
            momentum_21d=Decimal("0.0610"),
            volume_ratio=Decimal("1.4200"),
        ),
        ScreenerResult(
            ticker="TCS.NS",
            name="Tata Consultancy Services",
            exchange=request.exchange[0] if request.exchange else "NSE",
            asset_type="EQUITY",
            price=Decimal("4242.70000000"),
            change_pct=Decimal("0.9400"),
            pe_ratio=Decimal("27.9800"),
            rsi=Decimal("55.8000"),
            signal_direction="BUY",
            signal_confidence=Decimal("0.6900"),
            regime_state="bull",
            momentum_21d=Decimal("0.0480"),
            volume_ratio=Decimal("1.1900"),
        ),
    ][:max_items]

    return ScreenerRunResponse(
        results=data,
        total_matched=len(data),
        filters_applied=request.model_dump(),
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/presets", response_model=ScreenerPresetsResponse)
async def get_screener_presets(db: AsyncSession = Depends(get_db)) -> ScreenerPresetsResponse:
    _ = db
    now = datetime.now(timezone.utc)
    presets = [
        ScreenerPreset(name="value_stocks", description="Low PE and stable trend", filters_json={"pe_ratio_max": 20, "rsi_min": 35}, created_at=now),
        ScreenerPreset(name="momentum", description="Strong 21d momentum with volume support", filters_json={"momentum_21d_min": 0.05, "volume_ratio_min": 1.3}, created_at=now),
        ScreenerPreset(name="regime_aligned_buys", description="BUY signals aligned with bull regime", filters_json={"signal_direction": ["BUY", "STRONG_BUY"], "regime_compatible": True}, created_at=now),
    ]
    return ScreenerPresetsResponse(presets=presets)
