"""
Market data service implementation.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import yfinance as yf
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis_client
from app.models.market_data import OHLCV, EconomicIndicator, IndexData, TickData
from app.schemas.market_data import (
    HistoricalDataRequest,
    MarketOverviewResponse,
    QuoteResponse,
    RealTimeQuote,
)


class MarketDataService:
    """Service for handling market data operations."""

    def __init__(self):
        self.redis = get_redis_client()
        self.cache_ttl = 300  # 5 minutes

    async def get_quote(self, symbol: str, db: AsyncSession) -> QuoteResponse:
        """
        Get current quote for a symbol.
        """
        # Check cache first
        cache_key = f"quote:{symbol}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return QuoteResponse(**json.loads(cached_data))

        # Fetch from yfinance
        try:
            ticker = yf.Ticker(symbol + ".NS")  # NSE suffix
            info = ticker.info

            quote = QuoteResponse(
                symbol=symbol,
                name=info.get("longName", symbol),
                price=info.get("currentPrice", 0.0),
                change=info.get("currentPrice", 0.0) - info.get("previousClose", 0.0),
                change_percent=((info.get("currentPrice", 0.0) - info.get("previousClose", 0.0)) /
                              info.get("previousClose", 1.0)) * 100,
                volume=info.get("volume", 0),
                market_cap=info.get("marketCap"),
                pe_ratio=info.get("trailingPE"),
                pb_ratio=info.get("priceToBook"),
                dividend_yield=info.get("dividendYield"),
                fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
                fifty_two_week_low=info.get("fiftyTwoWeekLow"),
                timestamp=datetime.utcnow().isoformat(),
                exchange="NSE"
            )

            # Cache the result
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(quote.dict()))

            return quote

        except Exception as e:
            # Return cached data if available, otherwise raise error
            raise Exception(f"Failed to fetch quote for {symbol}: {str(e)}")

    async def get_historical_data(
        self,
        request: HistoricalDataRequest,
        db: AsyncSession
    ) -> List[Dict]:
        """
        Get historical OHLCV data.
        """
        cache_key = f"historical:{request.symbol}:{request.interval}:{request.start_date}:{request.end_date}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return json.loads(cached_data)

        try:
            ticker = yf.Ticker(request.symbol + ".NS")
            data = ticker.history(
                start=request.start_date,
                end=request.end_date,
                interval=request.interval
            )

            # Convert to list of dicts
            historical_data = []
            for index, row in data.iterrows():
                historical_data.append({
                    "timestamp": index.isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"])
                })

            # Cache the result
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(historical_data))

            return historical_data

        except Exception as e:
            raise Exception(f"Failed to fetch historical data for {request.symbol}: {str(e)}")

    async def get_market_overview(self, db: AsyncSession) -> MarketOverviewResponse:
        """
        Get market overview with major indices.
        """
        cache_key = "market_overview"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return MarketOverviewResponse(**json.loads(cached_data))

        try:
            indices = ["^NSEI", "^NSEBANK", "^CNXIT"]  # NIFTY 50, NIFTY Bank, NIFTY IT
            index_data = {}

            for index_symbol in indices:
                ticker = yf.Ticker(index_symbol)
                info = ticker.info
                hist = ticker.history(period="1d")

                if not hist.empty:
                    current_price = hist["Close"].iloc[-1]
                    previous_close = hist["Open"].iloc[0]

                    index_data[index_symbol.replace("^", "")] = {
                        "name": info.get("shortName", index_symbol),
                        "price": float(current_price),
                        "change": float(current_price - previous_close),
                        "change_percent": float(((current_price - previous_close) / previous_close) * 100),
                        "volume": int(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 0
                    }

            overview = MarketOverviewResponse(
                indices=index_data,
                market_status="OPEN",  # TODO: Check actual market hours
                timestamp=datetime.utcnow().isoformat(),
                total_volume=sum(idx["volume"] for idx in index_data.values()),
                advancers=1250,  # TODO: Calculate from actual data
                decliners=980
            )

            # Cache for 1 minute
            await self.redis.setex(cache_key, 60, json.dumps(overview.dict()))

            return overview

        except Exception as e:
            raise Exception(f"Failed to fetch market overview: {str(e)}")

    async def get_realtime_quote(self, symbol: str) -> RealTimeQuote:
        """
        Get real-time quote (simulated for now).
        """
        # In production, this would connect to live data feeds
        # For now, return current quote
        quote = await self.get_quote(symbol, None)  # db not needed for this

        return RealTimeQuote(
            symbol=symbol,
            price=quote.price,
            change=quote.change,
            change_percent=quote.change_percent,
            volume=quote.volume,
            timestamp=datetime.utcnow().isoformat(),
            bid=quote.price - 0.01,  # Simulated
            ask=quote.price + 0.01,
            bid_size=100,
            ask_size=150
        )

    async def subscribe_to_realtime_data(self, symbol: str, websocket):
        """
        Subscribe to real-time data stream.
        """
        # In production, this would use WebSocket connections to live feeds
        # For now, simulate real-time updates
        while True:
            try:
                quote = await self.get_realtime_quote(symbol)
                await websocket.send_json(quote.dict())
                await asyncio.sleep(1)  # Update every second
            except Exception as e:
                await websocket.send_json({"error": str(e)})
                break

    async def get_economic_indicators(self, db: AsyncSession) -> List[Dict]:
        """
        Get economic indicators.
        """
        # TODO: Implement economic data fetching
        return [
            {
                "indicator": "GDP_Growth",
                "value": 6.8,
                "unit": "percent",
                "date": "2023-Q4",
                "source": "MOSPI"
            },
            {
                "indicator": "Inflation",
                "value": 5.1,
                "unit": "percent",
                "date": "2023-12",
                "source": "RBI"
            }
        ]

    async def get_sector_performance(self, db: AsyncSession) -> Dict[str, Dict]:
        """
        Get sector-wise performance.
        """
        # TODO: Implement sector performance calculation
        return {
            "Technology": {
                "change_percent": 2.5,
                "volume": 15000000,
                "top_gainer": "TCS",
                "top_loser": "INFY"
            },
            "Finance": {
                "change_percent": -0.8,
                "volume": 12000000,
                "top_gainer": "HDFC",
                "top_loser": "ICICI"
            }
        }