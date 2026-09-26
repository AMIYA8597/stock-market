import logging
from typing import List
import pandas as pd
from app.data_platform.providers.base import BaseProvider, ProviderError

logger = logging.getLogger(__name__)

class ProviderChain:
    """Manages fallback logic across multiple providers."""
    
    def __init__(self, providers: List[BaseProvider]):
        self.providers = providers
        
    async def fetch_eod_with_fallback(self, canonical_symbol: str, exchange: str, start_date: str, end_date: str) -> pd.DataFrame:
        last_error = None
        for i, provider in enumerate(self.providers):
            if 'eod' not in provider.capabilities():
                continue
                
            try:
                df = await provider.fetch_eod(canonical_symbol, exchange, start_date, end_date)
                if not df.empty:
                    df['provider'] = provider.name
                    df['substituted'] = (i > 0)  # True if fallback was used
                    return df
            except ProviderError as e:
                logger.warning(f"{provider.name} failed to fetch EOD for {canonical_symbol}: {e}")
                last_error = e
                continue
                
        raise ProviderError(f"All providers failed for {canonical_symbol}. Last error: {last_error}")
