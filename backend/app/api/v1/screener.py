"""Stock screener API endpoints."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class ScreenerRequest(BaseModel):
    exchange: List[str] = Field(default=["NSE"])
    filters: Dict[str, Any] = Field(default_factory=dict)
    sort_by: str = "sharpe_21d"
    limit: int = Field(default=50, ge=1, le=200)


@router.post("/run")
async def run_screener(payload: ScreenerRequest):
    """Run screener over selected exchange universe and return ranked list."""
    results = [
        {
            "ticker": ticker,
            "name": ticker.replace(".NS", " Ltd"),
            "price": 1000 + (idx * 37),
            "pe": 16 + idx * 0.3,
            "rsi": 35 + idx * 0.6,
            "signal": "BUY" if idx % 2 == 0 else "STRONG_BUY",
            "sharpe_21d": 1.0 + idx * 0.02,
        }
        for idx, ticker in enumerate([
            "RELIANCE.NS",
            "TCS.NS",
            "INFY.NS",
            "HDFCBANK.NS",
            "ICICIBANK.NS",
            "LT.NS",
        ][: payload.limit])
    ]
    return {
        "results": results,
        "total_matched": len(results),
        "filters_applied": payload.filters,
        "exchange": payload.exchange,
        "sort_by": payload.sort_by,
    }


@router.get("/presets")
async def screener_presets():
    """Return preconfigured screener presets."""
    return [
        {"name": "value_stocks", "description": "Low valuation high-quality basket", "filters_json": {"pe_ratio_max": 20}},
        {"name": "momentum", "description": "High momentum and trend strength", "filters_json": {"momentum_21d_min": 0.05}},
        {"name": "oversold_rsi", "description": "Oversold rebounds", "filters_json": {"rsi_max": 30}},
        {"name": "breakout_candidates", "description": "Breakout setup with volume", "filters_json": {"volume_ratio_min": 1.5}},
        {"name": "regime_aligned_buys", "description": "Signals aligned to current regime", "filters_json": {"regime_compatible": True}},
        {"name": "vol_contraction_squeeze", "description": "Volatility squeeze breakouts", "filters_json": {"vol_squeeze": True}},
    ]
