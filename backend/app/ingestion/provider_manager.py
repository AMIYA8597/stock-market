import abc
from typing import List, Dict, Any
from datetime import datetime
import yfinance as yf
from pandas import DataFrame

class IngestionProvider(abc.ABC):
    """Base class for data ingestion providers."""
    
    @abc.abstractmethod
    async def fetch_historical_ohlcv(self, provider_symbol: str, start: datetime, end: datetime) -> DataFrame:
        pass

    @abc.abstractmethod
    async def fetch_quote(self, provider_symbol: str) -> Dict[str, Any]:
        pass


class YFinanceProvider(IngestionProvider):
    """Yahoo Finance provider using yfinance."""
    
    async def fetch_historical_ohlcv(self, provider_symbol: str, start: datetime, end: datetime) -> DataFrame:
        ticker = yf.Ticker(provider_symbol)
        df = ticker.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
        return df

    async def fetch_quote(self, provider_symbol: str) -> Dict[str, Any]:
        ticker = yf.Ticker(provider_symbol)
        info = ticker.fast_info
        return {
            "bid": info.get("lastPrice"), # fast_info doesn't have bid, use lastPrice for mock
            "ask": info.get("lastPrice"),
            "price": info.get("lastPrice"),
            "volume": info.get("lastVolume")
        }


class ProviderManager:
    """Routes ingest requests to the correct provider."""
    
    def __init__(self):
        self.providers: Dict[str, IngestionProvider] = {
            "yfinance": YFinanceProvider()
        }

    def get_provider(self, name: str) -> IngestionProvider:
        if name not in self.providers:
            raise ValueError(f"Provider {name} not found")
        return self.providers[name]
