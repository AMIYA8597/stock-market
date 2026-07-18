# backend/app/services/data_ingestion/provider_manager.py
"""Provider manager for live market data with automatic fallback.

The manager knows about all built‑in data source classes (YFinanceSource,
AlphaVantageSource, CoinGeckoSource, FREDSource, NSESource, StooqSource)
and provides a unified ``fetch`` method that attempts each source in order
until data is successfully retrieved.

Configuration:
    - API keys are read from environment variables (e.g. ``ALPHA_VANTAGE_KEY``).
    - Sources that require a key are only instantiated when the key is present.
    - The manager logs each attempt and raises ``DataSourceError`` if all
      providers fail.
"""

from __future__ import annotations

import os
import logging
from typing import List

from app.services.data_ingestion.base import MarketDataSource, IngestionTask, OHLCVBar, DataSourceError
from app.services.data_ingestion.yfinance_source import YFinanceSource
from app.services.data_ingestion.alpha_vantage_source import AlphaVantageSource
from app.services.data_ingestion.coingecko_source import CoinGeckoSource
from app.services.data_ingestion.fred_source import FREDSource
from app.services.data_ingestion.nse_source import NSESource
from app.services.data_ingestion.stooq_source import StooqSource

logger = logging.getLogger(__name__)


class ProviderManager:
    """Centralised manager that holds all available market data providers.

    It builds the provider list lazily based on environment configuration and
    provides ``fetch`` which returns a list of ``OHLCVBar`` for the requested
    ``IngestionTask``.
    """

    def __init__(self) -> None:
        self._sources: List[MarketDataSource] = self._init_sources()

    def _init_sources(self) -> List[MarketDataSource]:
        sources: List[MarketDataSource] = []
        # Always available free sources
        sources.append(YFinanceSource())
        sources.append(StooqSource())
        sources.append(CoinGeckoSource())
        sources.append(FREDSource())
        sources.append(NSESource())
        # Conditional source requiring API key
        av_key = os.getenv("ALPHA_VANTAGE_KEY")
        if av_key:
            # AlphaVantageSource reads the key from env internally, we just add it
            sources.append(AlphaVantageSource())
        else:
            logger.info("Alpha Vantage key not set – skipping provider.")
        return sources

    def _select_candidates(self, task: IngestionTask) -> List[MarketDataSource]:
        """Return an ordered list of candidate providers for a given task.

        The ordering prefers the most reliable free sources first and falls back
        to alternatives. Crypto assets use CoinGecko first, equities use YFinance
        first, etc.
        """
        if task.asset_type == "CRYPTO":
            # Prefer CoinGecko, then YFinance (if it supports crypto), then any fallback
            return [src for src in self._sources if isinstance(src, (CoinGeckoSource, YFinanceSource))]
        if task.asset_type == "MACRO":
            return [src for src in self._sources if isinstance(src, FREDSource)]
        # Default to equity handling – prioritize YFinance then Stooq then others
        return [src for src in self._sources if isinstance(src, (YFinanceSource, StooqSource, NSESource))]

    async def fetch(self, task: IngestionTask) -> List[OHLCVBar]:
        """Attempt to fetch OHLCV data using the ordered provider list.

        Raises
        ------
        DataSourceError
            If none of the providers return data.
        """
        candidates = self._select_candidates(task)
        errors: List[str] = []
        for source in candidates:
            try:
                logger.debug(f"Attempting fetch from {source.name} for {task.symbol}")
                bars = await source.fetch_ohlcv(
                    symbol=task.symbol,
                    interval=task.interval,
                    start=task.start,
                    end=task.end,
                )
                if bars:
                    return bars
                errors.append(f"{source.name}: empty result")
            except Exception as exc:
                errors.append(f"{source.name}: {exc}")
                logger.warning(f"Provider {source.name} failed for {task.symbol}: {exc}")
        raise DataSourceError(f"All providers failed for {task.symbol}. Details: {' | '.join(errors)}")


# Export a singleton for easy import
provider_manager = ProviderManager()
