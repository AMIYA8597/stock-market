"""Yahoo Finance market data adapter with async-safe execution."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pandas as pd
import yfinance as yf

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

        def _download() -> pd.DataFrame:
            return yf.download(
                tickers=symbol,
                start=start,
                end=end,
                interval=y_interval,
                auto_adjust=False,
                progress=False,
                threads=False,
            )

        frame = await asyncio.to_thread(_download)
        if frame.empty:
            return []

        frame = frame.reset_index()
        datetime_col = "Datetime" if "Datetime" in frame.columns else "Date"
        if datetime_col not in frame.columns:
            raise DataSourceError(f"{self.name}: missing datetime column for {symbol}")

        bars: list[OHLCVBar] = []
        for row in frame.to_dict(orient="records"):
            ts_raw = row[datetime_col]
            ts = ts_raw.to_pydatetime() if hasattr(ts_raw, "to_pydatetime") else ts_raw
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
