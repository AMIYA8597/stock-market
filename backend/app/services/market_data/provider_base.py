import abc
from typing import Any


class MarketDataProvider(abc.ABC):
    """Abstract base class for market data providers.

    Implementations must provide async methods for the core market data
    operations required by the platform. All methods should raise ``ValueError``
    when the requested symbol cannot be resolved.
    """

    @staticmethod
    @abc.abstractmethod
    async def get_quote(symbol: str) -> dict[str, Any]:
        """Return a live quote dictionary for *symbol*.

        The dictionary must contain at least ``symbol`` and ``price`` keys and
        may include additional fields such as ``change``, ``volume`` etc.
        """
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    async def get_history(symbol: str, interval: str, period: str) -> list[dict[str, Any]]:
        """Return historical OHLCV bars for *symbol*.

        ``interval`` follows the frontend timeframe identifiers (e.g. ``1m``),
        ``period`` is a yfinance‑compatible period string (e.g. ``5d``).
        """
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    async def get_intraday_candles(symbol: str, interval: str) -> list[dict[str, Any]]:
        """Return intraday candles for *symbol*.

        Implementations may delegate to ``get_history`` with a short period.
        """
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    async def get_movers(n: int = 10, mover_type: str = "gainers") -> list[dict[str, Any]]:
        """Return a list of mover quotes (gainers/losers/volume/momentum)."""
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    async def get_indices() -> list[dict[str, Any]]:
        """Return market index quotes (e.g., NIFTY, Sensex, Bank Nifty)."""
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    async def get_ticker_info(symbol: str) -> dict[str, Any]:
        """Fetch general ticker metadata (PE, market cap, name, etc.)."""
        raise NotImplementedError
