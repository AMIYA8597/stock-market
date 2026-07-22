"""NSE India intraday adapter with cookie-priming session."""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import UTC, datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.services.data_ingestion.base import DataSourceError, Interval, MarketDataSource, OHLCVBar

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
]

class NSEIntradaySource(MarketDataSource):
    """Fetch NSE intraday chart data and normalize to OHLCV."""

    name = "nse_intraday"
    _base_url = "https://www.nseindia.com/api/chart-databyindex"

    async def _bootstrap_session(self, client: httpx.AsyncClient) -> tuple[dict[str, str], dict[str, str]]:
        ua = random.choice(USER_AGENTS)
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": ua,
            "referer": "https://www.nseindia.com/",
        }
        for attempt in range(3):
            try:
                response = await client.get("https://www.nseindia.com", headers=headers, timeout=10)
                if response.status_code == 200:
                    return headers, dict(response.cookies)
            except Exception as e:
                logger.warning(f"NSE intraday session bootstrap attempt {attempt+1} failed: {e}")
                await asyncio.sleep(2)
        raise DataSourceError("Failed to bootstrap NSE intraday session cookies")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: Interval,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVBar]:
        if interval == "1d":
            raise DataSourceError("NSE intraday adapter does not support 1d interval")

        clean_symbol = symbol.replace(".NS", "")
        params = {
            "index": f"{clean_symbol}EQN",
        }

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            try:
                headers, cookies = await self._bootstrap_session(client)
            except Exception as e:
                raise DataSourceError(f"NSE intraday bootstrap failed: {e}")

            headers["accept"] = "application/json, text/plain, */*"
            headers["referer"] = f"https://www.nseindia.com/get-quotes/equity?symbol={clean_symbol}"

            response = None
            for attempt in range(3):
                try:
                    response = await client.get(self._base_url, params=params, headers=headers, cookies=cookies)
                    if response.status_code == 200:
                        break
                    elif response.status_code in (401, 403):
                        logger.info(f"NSE intraday session forbidden ({response.status_code}), re-bootstrapping...")
                        headers, cookies = await self._bootstrap_session(client)
                except Exception as ex:
                    logger.warning(f"NSE intraday fetch attempt {attempt+1} failed: {ex}")
                
                await asyncio.sleep(2)

            if response is None or response.status_code != 200:
                status_code = response.status_code if response else "No Response"
                raise DataSourceError(f"NSE intraday request failed for {symbol} after retries: {status_code}")

            try:
                payload = response.json()
            except Exception as json_err:
                raise DataSourceError(f"NSE intraday response json parse error: {json_err}")

        # format is {"grapthData": [[timestamp, price], ...]}
        points = payload.get("grapthData", [])
        bars: list[OHLCVBar] = []
        for pt in points:
            if len(pt) < 2:
                continue
            ts_ms, price = pt[0], pt[1]
            # Convert milliseconds to datetime
            ts = datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC)
            
            # Since NSE only gives us price for intraday chart in this endpoint,
            # we simulate OHLC as the same price.
            bars.append(
                OHLCVBar(
                    time=ts,
                    open=float(price),
                    high=float(price),
                    low=float(price),
                    close=float(price),
                    volume=0.0,
                    adjusted_close=None,
                    interval=interval,
                )
            )

        # Filter by start/end
        bars = [b for b in bars if start <= b.time <= end]
        bars.sort(key=lambda x: x.time)
        return bars
