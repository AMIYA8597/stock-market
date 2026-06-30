"""Yahoo Finance market data adapter with async-safe execution."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pandas as pd
from app.services.market_data_service import MarketDataService

from app.services.data_ingestion.base import DataSourceError, Interval, MarketDataSource, OHLCVBar

_YF_INTERVAL_MAP: dict[Interval, str] = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "60m",
    "1d": "1d",
}


class YFinanceSource(MarketDataSource):
    """Fetch OHLCV from Yahoo Finance using yfinance in a worker thread."""

    name = "yfinance"

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: Interval,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVBar]:
        y_interval = _YF_INTERVAL_MAP[interval]

        try:
            frame = await MarketDataService.download_raw(
                tickers=symbol,
                start=start,
                end=end,
                interval=y_interval,
                auto_adjust=False,
                progress=False,
                threads=False,
            )
        except Exception as e:
            logger.warning(f"yfinance download failed for {symbol}: {e}. Trying direct HTTP fallback...")
            frame = pd.DataFrame()

        if frame.empty:
            # Try direct HTTP v8 API fallback
            try:
                import urllib.request
                import json
                
                # Convert datetime to Unix timestamps
                start_ts = int(start.timestamp())
                end_ts = int(end.timestamp())
                
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}?period1={start_ts}&period2={end_ts}&interval={y_interval}"
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                
                def _fetch_direct():
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=15) as response:
                        return json.loads(response.read().decode())
                
                payload = await asyncio.to_thread(_fetch_direct)
                res = payload["chart"]["result"][0]
                indicators = res["indicators"]["quote"][0]
                timestamps = res["timestamp"]
                
                frame = pd.DataFrame({
                    "Date": pd.to_datetime(timestamps, unit="s"),
                    "Open": indicators["open"],
                    "High": indicators["high"],
                    "Low": indicators["low"],
                    "Close": indicators["close"],
                    "Volume": indicators["volume"],
                    "Adj Close": indicators["close"]  # Fallback adjusted close
                }).dropna(subset=["Close"])
                
                logger.info(f"Direct HTTP v8 API fallback succeeded for {symbol}")
            except Exception as e:
                logger.error(f"Direct HTTP v8 fallback failed for {symbol}: {e}")
                return []

        frame = frame.reset_index()
        datetime_col = "Datetime" if "Datetime" in frame.columns else ("Date" if "Date" in frame.columns else "time")
        if datetime_col not in frame.columns:
            raise DataSourceError(f"{self.name}: missing datetime column for {symbol}")

        bars: list[OHLCVBar] = []
        for row in frame.to_dict(orient="records"):
            ts_raw = row[datetime_col]
            ts = ts_raw.to_pydatetime() if hasattr(ts_raw, "to_pydatetime") else ts_raw
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            else:
                ts = ts.astimezone(UTC)

            bars.append(
                OHLCVBar(
                    time=ts,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row.get("Volume", 0.0) or 0.0),
                    adjusted_close=float(row["Adj Close"]) if "Adj Close" in row and row["Adj Close"] is not None else None,
                    interval=interval,
                )
            )

        return bars

