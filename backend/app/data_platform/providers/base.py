import abc
from typing import Dict, List, Optional
import pandas as pd

class BaseProvider(abc.ABC):
    """Abstract base class for all data providers."""
    
    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass
        
    @abc.abstractmethod
    def capabilities(self) -> List[str]:
        """Returns a list of supported capabilities e.g. ['eod', 'intraday', 'quotes']"""
        pass
        
    @abc.abstractmethod
    async def fetch_eod(self, canonical_symbol: str, exchange: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch End-of-Day OHLCV data."""
        raise NotImplementedError
        
    @abc.abstractmethod
    async def fetch_intraday(self, canonical_symbol: str, exchange: str, interval: str) -> pd.DataFrame:
        """Fetch Intraday OHLCV data."""
        raise NotImplementedError
        
    @abc.abstractmethod
    async def fetch_quotes(self, symbols: List[str]) -> Dict[str, dict]:
        """Fetch real-time or delayed quotes."""
        raise NotImplementedError

class ProviderError(Exception):
    pass

class RateLimitError(ProviderError):
    pass

class SymbolNotFoundError(ProviderError):
    pass
