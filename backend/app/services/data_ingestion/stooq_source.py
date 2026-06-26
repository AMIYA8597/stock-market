"""Stooq market data adapter."""

from __future__ import annotations

import csv
import io
import logging
from datetime import UTC, datetime

import httpx
from app.services.data_ingestion.base import DataSourceError, Interval, MarketDataSource, OHLCVBar

logger = logging.getLogger(__name__)

class StooqSource(MarketDataSource):
    """Fetch OHLCV from Stooq."""

    name = "stooq"

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: Interval,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVBar]:
        if interval != "1d":
            # Stooq free CSV endpoint only supports daily data
            return []

        # Map symbol if needed
        # Stooq uses .US for US equities, .IN for Indian equities, etc.
        stooq_symbol = symbol.upper()
        if stooq_symbol.endswith(".NS"):
            stooq_symbol = stooq_symbol.replace(".NS", ".IN")
        elif "." not in stooq_symbol and stooq_symbol not in ("^NSEI", "^BSESN"):
            stooq_symbol = f"{stooq_symbol}.US"

        url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&f=sd2t2ohlcv&a=dn"
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    raise DataSourceError(f"Stooq returned status {response.status_code}")
                csv_data = response.text
            except Exception as e:
                raise DataSourceError(f"Failed to fetch from Stooq: {e}")

        # Parse CSV
        f = io.StringIO(csv_data)
        reader = csv.DictReader(f)
        
        # Check if we got an empty response or error page
        if not reader.fieldnames or "Date" not in reader.fieldnames:
            logger.warning(f"Invalid Stooq response for {stooq_symbol}")
            return []

        bars: list[OHLCVBar] = []
        for row in reader:
            try:
                # Format of Date: YYYY-MM-DD
                dt = datetime.strptime(row["Date"], "%Y-%m-%d")
                # Normalize dt timezone
                dt = dt.replace(tzinfo=UTC)
                # Normalize start/end timezone
                start_tz = start.replace(tzinfo=UTC) if start.tzinfo is None else start.astimezone(UTC)
                end_tz = end.replace(tzinfo=UTC) if end.tzinfo is None else end.astimezone(UTC)
                
                if not (start_tz <= dt <= end_tz):
                    continue
                    
                bars.append(
                    OHLCVBar(
                        time=dt,
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=float(row.get("Volume", 0.0) or 0.0),
                        adjusted_close=None,
                        interval=interval,
                    )
                )
            except Exception:
                continue

        # Stooq returns newest first, so reverse to chronological order
        bars.reverse()
        return bars
