"""
Market data endpoints for real-time and historical data.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user_with_permissions
from app.core.database import get_db
from app.schemas.market_data import (
    HistoricalDataRequest,
    HistoricalDataResponse,
    MarketDataResponse,
    MarketOverviewResponse,
    OHLCVResponse,
    QuoteResponse,
)
from app.services.market_data_service import MarketDataService

router = APIRouter()
market_data_service = MarketDataService()


@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_quote(
    symbol: str,
    exchange: str = Query("NSE", description="Exchange code"),
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Get real-time quote for a symbol.
    """
    return await market_data_service.get_quote(symbol, db)


@router.get("/quotes", response_model=List[QuoteResponse])
async def get_multiple_quotes(
    symbols: str = Query(..., description="Comma-separated symbols"),
    exchange: str = Query("NSE", description="Exchange code"),
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Get real-time quotes for multiple symbols.
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",")]

    quotes = []
    for symbol in symbol_list:
        try:
            quote = await market_data_service.get_quote(symbol, db)
            quotes.append(quote)
        except Exception as e:
            # Continue with other symbols if one fails
            continue

    return quotes


@router.post("/historical", response_model=List[dict])
async def get_historical_data(
    request: HistoricalDataRequest,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Get historical OHLCV data for a symbol.
    """
    return await market_data_service.get_historical_data(request, db)


@router.get("/overview", response_model=MarketOverviewResponse)
async def get_market_overview(
    db: AsyncSession = Depends(get_db)
):
    """
    Get market overview with major indices and top movers.
    """
    return await market_data_service.get_market_overview(db)


@router.get("/indices", response_model=List[dict])
async def get_market_indices(
    db: AsyncSession = Depends(get_db)
):
    """
    Get current values for major market indices.
    """
    overview = await market_data_service.get_market_overview(db)
    return [
        {
            "symbol": symbol,
            "name": data["name"],
            "value": data["price"],
            "change": data["change"],
            "change_percent": data["change_percent"],
            "timestamp": overview.timestamp
        }
        for symbol, data in overview.indices.items()
    ]


@router.websocket("/ws/market/{symbol}")
async def market_data_websocket(
    symbol: str,
    websocket: WebSocket,
    current_user: dict = Depends(get_current_user_with_permissions)
):
    """
    WebSocket endpoint for real-time market data streaming.
    """
    await websocket.accept()

    try:
        await market_data_service.subscribe_to_realtime_data(symbol, websocket)
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()