# backend/app/services/nse_service.py
# NSE India unofficial REST API — completely free, no API key needed

from __future__ import annotations

import httpx
import asyncio

NSE_BASE = "https://www.nseindia.com/api"
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com"
}

class NSEService:
    _session: httpx.AsyncClient | None = None

    @classmethod
    async def get_session(cls) -> httpx.AsyncClient:
        if cls._session is None or cls._session.is_closed:
            cls._session = httpx.AsyncClient(headers=NSE_HEADERS, timeout=10.0, follow_redirects=True)
            # Warm up session with homepage visit (required by NSE to get cookies)
            try:
                await cls._session.get("https://www.nseindia.com")
            except Exception:
                # Silently ignore warm-up failures, will retry on request
                pass
        return cls._session

    @classmethod
    async def get_nifty50_data(cls) -> dict:
        """Live Nifty 50 index data — all 50 stocks with price, change, volume."""
        session = await cls.get_session()
        resp = await session.get(f"{NSE_BASE}/equity-stockIndices?index=NIFTY%2050")
        return resp.json()

    @classmethod
    async def get_banknifty_data(cls) -> dict:
        """Live Bank Nifty data."""
        session = await cls.get_session()
        resp = await session.get(f"{NSE_BASE}/equity-stockIndices?index=NIFTY%20BANK")
        return resp.json()

    @classmethod
    async def get_option_chain(cls, symbol: str) -> dict:
        """
        Live F&O Option Chain — completely free from NSE.
        symbol: "NIFTY" or "BANKNIFTY" or stock name like "RELIANCE"
        """
        session = await cls.get_session()
        if symbol in ("NIFTY", "BANKNIFTY"):
            resp = await session.get(f"{NSE_BASE}/option-chain-indices?symbol={symbol}")
        else:
            resp = await session.get(f"{NSE_BASE}/option-chain-equities?symbol={symbol}")
        return resp.json()

    @classmethod
    async def get_market_status(cls) -> dict:
        """Check if NSE market is open right now."""
        session = await cls.get_session()
        resp = await session.get(f"{NSE_BASE}/marketStatus")
        return resp.json()

    @classmethod
    async def get_gainers_losers(cls) -> dict:
        """Top gainers and losers from NSE — live data."""
        session = await cls.get_session()
        gainers = await session.get(f"{NSE_BASE}/live-analysis-gainers-losers?index=gainers")
        losers = await session.get(f"{NSE_BASE}/live-analysis-gainers-losers?index=loosers")
        return {"gainers": gainers.json(), "losers": losers.json()}

    @classmethod
    async def get_52week_hl(cls) -> dict:
        """52-week high/low data from NSE."""
        session = await cls.get_session()
        highs = await session.get(f"{NSE_BASE}/live-analysis-52Week?index=high")
        lows = await session.get(f"{NSE_BASE}/live-analysis-52Week?index=low")
        return {"highs": highs.json(), "lows": lows.json()}
