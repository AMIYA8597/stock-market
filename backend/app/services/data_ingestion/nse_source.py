"""NSE India adapter with fallback behavior for unsupported intervals."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import logging
import httpx

from app.services.data_ingestion.base import DataSourceError, Interval, MarketDataSource, OHLCVBar

logger = logging.getLogger(__name__)


class NSESource(MarketDataSource):
    """Fetch NSE historical data and normalize to OHLCV.

    Endpoint coverage is used for daily bars. Intraday is intentionally rejected
    in this adapter to avoid silently wrong sampling.
    """

    name = "nse"
    _base_url = "https://www.nseindia.com/api/historical/cm/equity"

    async def _bootstrap_session(self, client: httpx.AsyncClient) -> dict[str, str]:
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "referer": "https://www.nseindia.com/",
        }
        for attempt in range(3):
            try:
                response = await client.get("https://www.nseindia.com", headers=headers, timeout=10)
                if response.status_code == 200:
                    return dict(response.cookies)
            except Exception as e:
                logger.warning(f"NSE session bootstrap attempt {attempt+1} failed: {e}")
                await asyncio.sleep(1 * (attempt + 1))
        raise DataSourceError("Failed to bootstrap NSE session cookies")

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: Interval,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVBar]:
        if interval != "1d":
            raise DataSourceError("NSE adapter currently supports daily interval only")

        params = {
            "symbol": symbol.replace(".NS", ""),
            "from": start.strftime("%d-%m-%Y"),
            "to": end.strftime("%d-%m-%Y"),
            "series": '["EQ"]',
        }
        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "referer": "https://www.nseindia.com/report-detail/historical-corporate-action",
        }

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            try:
                cookies = await self._bootstrap_session(client)
            except Exception as e:
                raise DataSourceError(f"NSE bootstrap failed: {e}")

            response = None
            backoff_delays = [1.0, 3.0, 8.0]
            for attempt in range(4):
                try:
                    response = await client.get(self._base_url, params=params, headers=headers, cookies=cookies)
                    if response.status_code == 200:
                        break
                    elif response.status_code in (401, 403):
                        logger.info(f"NSE session expired or forbidden (status {response.status_code}), re-bootstrapping...")
                        try:
                            cookies = await self._bootstrap_session(client)
                        except Exception as e:
                            logger.warning(f"Failed to bootstrap session on attempt {attempt+1}: {e}")
                    else:
                        logger.warning(f"NSE request returned status {response.status_code}, retrying...")
                except Exception as ex:
                    logger.warning(f"NSE fetch attempt {attempt+1} failed: {ex}")
                
                if attempt < 3:
                    await asyncio.sleep(backoff_delays[attempt])

            if response is None or response.status_code != 200:
                status_code = response.status_code if response else "No Response"
                raise DataSourceError(f"NSE request failed for {symbol} after retries: {status_code}")

            try:
                payload = response.json()
            except Exception as json_err:
                raise DataSourceError(f"NSE response json parse error: {json_err}")

        rows = payload.get("data", [])
        bars: list[OHLCVBar] = []
        for row in rows:
            date_str = row.get("CH_TIMESTAMP")
            if not date_str:
                continue
            ts = datetime.strptime(date_str, "%d-%b-%Y").replace(tzinfo=UTC)
            bars.append(
                OHLCVBar(
                    time=ts,
                    open=float(row["CH_OPENING_PRICE"]),
                    high=float(row["CH_TRADE_HIGH_PRICE"]),
                    low=float(row["CH_TRADE_LOW_PRICE"]),
                    close=float(row["CH_CLOSING_PRICE"]),
                    volume=float(row.get("CH_TOT_TRADED_QTY", 0.0) or 0.0),
                    adjusted_close=None,
                    interval="1d",
                )
            )

        bars.sort(key=lambda x: x.time)
        return bars
