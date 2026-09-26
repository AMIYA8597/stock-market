import asyncio
import logging
from datetime import UTC, datetime
import yfinance as yf

from app.models.instrument import Instrument
from app.services.ingestion.base import (
    DataUnavailableError,
    Interval,
    MarketDataProvider,
    OHLCVBar,
    Quote,
)

logger = logging.getLogger(__name__)

_YF_INTERVAL_MAP: dict[Interval, str] = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "60m",
    "1d": "1d",
}


class YFinanceProvider(MarketDataProvider):
    """Yahoo Finance provider implementation."""

    name = "yfinance"

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    async def get_quote(self, symbol: str) -> Quote:
        yf_symbol = (
            Instrument.normalize_symbol(symbol) + ""
            if not symbol.endswith("") and "^" not in symbol and "=" not in symbol
            else symbol
        )
        try:
            def _fetch():
                ticker = yf.Ticker(yf_symbol)
                return ticker.info
                
            info = await asyncio.to_thread(_fetch)
            if not info or 'regularMarketPrice' not in info and 'currentPrice' not in info:
                # Try getting last day data
                def _fetch_hist():
                    return yf.download(yf_symbol, period="1d", progress=False)
                df = await asyncio.to_thread(_fetch_hist)
                if df.empty:
                    raise DataUnavailableError(f"No quote data for {symbol}")
                price = float(df['Close'].iloc[-1].item() if hasattr(df['Close'].iloc[-1], 'item') else df['Close'].iloc[-1])
                prev_price = float(df['Open'].iloc[-1].item() if hasattr(df['Open'].iloc[-1], 'item') else df['Open'].iloc[-1])
                return Quote(
                    symbol=symbol,
                    price=price,
                    change=price - prev_price,
                    change_pct=((price / prev_price) - 1) * 100 if prev_price else 0.0,
                    volume=float(df['Volume'].iloc[-1].item() if hasattr(df['Volume'].iloc[-1], 'item') else df['Volume'].iloc[-1]),
                    timestamp=datetime.now(UTC),
                )
            
            price = float(info.get('currentPrice') or info.get('regularMarketPrice') or 0.0)
            prev_price = float(info.get('previousClose') or price)
            
            return Quote(
                symbol=symbol,
                price=price,
                change=price - prev_price,
                change_pct=((price / prev_price) - 1) * 100 if prev_price else 0.0,
                volume=float(info.get('regularMarketVolume') or info.get('volume') or 0.0),
                timestamp=datetime.now(UTC),
            )
        except Exception as e:
            raise DataUnavailableError(f"{self.name} quote failed: {e}") from e

    async def get_ohlcv(
        self, symbol: str, interval: Interval, start: datetime, end: datetime
    ) -> list[OHLCVBar]:
        yf_symbol = (
            Instrument.normalize_symbol(symbol) + ""
            if not symbol.endswith("") and "^" not in symbol and "=" not in symbol
            else symbol
        )
        y_interval = _YF_INTERVAL_MAP[interval]
        
        try:
            def _fetch():
                # yfinance expects naive strings or specific date formats
                s_str = start.strftime("%Y-%m-%d")
                e_str = end.strftime("%Y-%m-%d")
                return yf.download(yf_symbol, start=s_str, end=e_str, interval=y_interval, progress=False)
                
            df = await asyncio.to_thread(_fetch)
            if df.empty:
                return []

            bars = []
            # yfinance returns multi-index columns if downloading multiple, but we only request one.
            # However, in newer yfinance versions, it sometimes still returns multi-index columns.
            for idx, row in df.iterrows():
                # Extract scalar values
                def _get_val(col):
                    if col in row:
                        val = row[col]
                        if hasattr(val, 'item'): val = val.item() # Handle numpy types or Series
                        # If it's a pandas Series (because of MultiIndex), take the first value
                        if hasattr(val, 'iloc'): val = val.iloc[0]
                        return float(val) if not pd.isna(val) else 0.0
                    return 0.0

                import pandas as pd
                dt = idx.to_pydatetime()
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                
                open_p = _get_val('Open')
                close_p = _get_val('Close')
                if open_p == 0.0 or close_p == 0.0:
                    continue
                    
                bars.append(
                    OHLCVBar(
                        time=dt,
                        open=open_p,
                        high=_get_val('High'),
                        low=_get_val('Low'),
                        close=close_p,
                        volume=_get_val('Volume'),
                        adjusted_close=_get_val('Adj Close') if 'Adj Close' in row else close_p,
                        interval=interval,
                    )
                )
            return bars
        except Exception as e:
            raise DataUnavailableError(f"{self.name} ohlcv failed for {symbol}: {e}") from e

    async def get_universe(self) -> list[dict]:
        return []

    async def health(self) -> dict:
        try:
            await self.get_quote("^NSEI")
            return {"status": "ok", "provider": self.name}
        except Exception as e:
            return {"status": "down", "provider": self.name, "error": str(e)}
