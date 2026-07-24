import logging

import requests

logger = logging.getLogger(__name__)


class IndianStockAPI:
    """Simple client for the 0xramm Indian Stock Market API (free, no auth)."""

    BASE_URL = "https://api.0xramm.com/stock/list"

    @staticmethod
    def fetch_quote(symbol: str) -> dict | None:
        """Fetch a live quote for a given NSE symbol.
        Returns a dict compatible with MarketDataService.get_quote format or None on failure.
        """
        try:
            params = {"symbols": symbol.upper()}
            resp = requests.get(IndianStockAPI.BASE_URL, params=params, timeout=10)
            if resp.status_code != 200:
                logger.debug(f"IndianStockAPI non‑200 response {resp.status_code} for {symbol}")
                return None
            data = resp.json()
            # Expected format: {"stock": [{...}]} or list directly
            if isinstance(data, dict) and "stock" in data:
                entries = data["stock"]
            elif isinstance(data, list):
                entries = data
            else:
                entries = []
            if not entries:
                return None
            entry = entries[0]
            return {
                "symbol": symbol.upper(),
                "price": float(entry.get("price", 0.0)),
                "change": float(entry.get("change", 0.0)),
                "change_pct": float(entry.get("change_pct", 0.0)),
                "open": float(entry.get("open", 0.0)),
                "high": float(entry.get("high", 0.0)),
                "low": float(entry.get("low", 0.0)),
                "volume": int(entry.get("volume", 0)),
                "previous_close": float(entry.get("previous_close", 0.0)),
                "source": "0xramm",
            }
        except Exception as e:
            logger.debug(f"IndianStockAPI fetch failed for {symbol}: {e}")
            return None
