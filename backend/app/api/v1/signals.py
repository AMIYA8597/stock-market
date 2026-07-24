# backend/app/api/v1/signals.py
"""Signal prediction endpoints — all values computed from real yfinance OHLCV data."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.database.redis_client import get_redis
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.signal import BulkSignalResponse, SignalResponse
from app.services.market_data_service import MarketDataService
from app.services.signal_engine import TechnicalSignalEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/signals", tags=["signals"])

CACHE_TTL = 300  # seconds (5 minutes)


async def _get_technical_signal(symbol: str) -> dict:
    hist = await MarketDataService.get_history(symbol, interval="1d", period="1y")
    if not hist:
        raise ValueError(f"No history available for {symbol}")

    df = pd.DataFrame(hist)
    # convert cols to numeric
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col])

    return TechnicalSignalEngine.generate_signal(df)


@router.get("/bulk", response_model=BulkSignalResponse)
async def get_signals_bulk(
    symbols: str = Query(..., min_length=1, max_length=500),
) -> BulkSignalResponse:
    parsed = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not parsed:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse.create(
                code=ErrorCode.VALIDATION_ERROR, message="At least one symbol required."
            ).dict(),
        )
    if len(parsed) > 50:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse.create(
                code=ErrorCode.UNPROCESSABLE, message="Maximum 50 symbols."
            ).dict(),
        )

    signals = []

    # We fetch serially or gather to avoid overloading providers
    tasks = [_get_technical_signal(sym) for sym in parsed]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for symbol, result in zip(parsed, results, strict=False):
        if isinstance(result, Exception):
            logger.warning(f"Failed to get signal for symbol={symbol} in bulk check: {result}")
            continue

        signals.append(
            SignalResponse(
                symbol=symbol,
                timestamp=datetime.now(UTC),
                direction=result["direction"],
                confidence=result["confidence"],
                score=result["score"],
                breakdown=result["breakdown"],
                patterns=result.get("patterns", []),
                stop_loss=result["stop_loss"],
                take_profit=result["take_profit"],
                position_size_pct=result.get("position_size_pct", 0.0)
            )
        )

    return BulkSignalResponse(
        symbols=parsed,
        signals=signals,
        generated_at=datetime.now(UTC),
        total_symbols=len(parsed),
        processed_symbols=len(signals),
    )


@router.get("/{symbol}", response_model=SignalResponse)
async def get_signal(symbol: str) -> SignalResponse:
    if not symbol.strip():
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse.create(
                code=ErrorCode.VALIDATION_ERROR, message="symbol is required."
            ).dict(),
        )

    symbol_upper = symbol.strip().upper()

    redis = None
    try:
        redis = await get_redis()
        cached = await redis.get(f"signal:{symbol_upper}")
        if cached:
            return SignalResponse(**json.loads(cached))
    except Exception as e:
        logger.warning(f'Redis cache read failed for signal f"signal:{symbol_upper}": {e}')

    try:
        result = await _get_technical_signal(symbol_upper)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Signal engine error: {e}")

    response = SignalResponse(
        symbol=symbol_upper,
        timestamp=datetime.now(UTC),
        direction=result["direction"],
        confidence=result["confidence"],
        score=result["score"],
        breakdown=result["breakdown"],
        patterns=result.get("patterns", []),
        stop_loss=result["stop_loss"],
        take_profit=result["take_profit"],
        position_size_pct=result.get("position_size_pct", 0.0)
    )

    if redis is not None:
        try:
            await redis.setex(f"signal:{symbol_upper}", CACHE_TTL, response.model_dump_json())
        except Exception as e:
            logger.warning(f'Redis cache write failed for signal f"signal:{symbol_upper}": {e}')

    return response


@router.get("/history/{symbol}")
async def get_signal_history(symbol: str) -> dict:
    """Historical signals endpoint stubbed for B6."""
    raise HTTPException(status_code=501, detail="Historical signals not implemented for classical engine")
