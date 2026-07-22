from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.market_data import fetch_ohlcv
from app.schemas.market import HistoryResponse
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/ohlcv/{symbol}", response_model=HistoryResponse)
async def get_ohlcv(
    symbol: str,
    interval: str = Query(default="1m", pattern="^(1m|5m|15m|30m|1h|1d)$"),
    period: str = Query(default="1d", pattern="^(1d|5d|1mo|3mo|6mo|1y)$"),
    db: AsyncSession = Depends(get_db),
) -> HistoryResponse:
    """Return OHLCV data for a symbol using the simple market_data service.

    This endpoint is a thin wrapper around the `fetch_ohlcv` helper which
    retrieves data from yfinance with a small in‑memory cache.
    """
    try:
        df = fetch_ohlcv(symbol, interval=interval, period=period)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch OHLCV: {e}")
    # Convert DataFrame to list of dicts expected by HistoryResponse
    bars = []
    for ts, row in df.iterrows():
        bars.append({
            "time": ts.isoformat(),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": float(row.get("Volume", 0.0)),
        })
    return HistoryResponse(bars=bars)
