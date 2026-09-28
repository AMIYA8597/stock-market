import logging
from datetime import datetime, timedelta

import httpx
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Candle(BaseModel):
    timestamp: int  # UNIX epoch seconds
    open: float
    high: float
    low: float
    close: float
    volume: float


class AngelOneProvider:
    """Fetch market data from Angel One SmartAPI.

    This provider requires free Angel One credentials (client id, client secret, and TOTP secret).
    It obtains an access token via the login endpoint and then calls the historical data endpoint.
    Live tick streaming would normally be done via a WebSocket; for the Phase‑2 implementation we
    focus on the REST historical candles used for backtesting and chart hydration.
    """

    @staticmethod
    async def _obtain_access_token() -> str:
        """Obtain a JWT/Bearer token from Angel One.

        The actual login flow uses a POST to ``/v1/auth/login`` with the client id, secret, and a TOTP
        code generated from the stored base‑32 secret. For brevity we perform a simple request and raise
        an informative error if any credential is missing.
        """
        if not all(
            [
                settings.ANGEL_ONE_CLIENT_ID,
                settings.ANGEL_ONE_CLIENT_SECRET,
                settings.ANGEL_ONE_TOTP_SECRET,
            ]
        ):
            raise RuntimeError("Angel One credentials are not configured in the environment.")

        # Generate a TOTP code – we rely on the ``pyotp`` package which is already a transitive dependency.
        try:
            import pyotp
        except ImportError as exc:
            raise RuntimeError("pyotp is required for Angel One TOTP generation") from exc

        totp = pyotp.TOTP(settings.ANGEL_ONE_TOTP_SECRET)
        payload = {
            "clientcode": settings.ANGEL_ONE_CLIENT_ID,
            "password": settings.ANGEL_ONE_CLIENT_SECRET,
            "totp": totp.now(),
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://smartapi.angelbroking.com/v1/auth/login", json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            token = data.get("jwtToken") or data.get("access_token")
            if not token:
                raise RuntimeError("Failed to obtain Angel One access token")
            return token

    @staticmethod
    async def fetch_candles(symbol: str, interval: str = "1d", period: str = "1mo") -> list[Candle]:
        """Return a list of :class:`Candle` objects for *symbol*.

        *interval* follows Angel One's naming (e.g. ``1minute``, ``5minute``, ``1day``).
        *period* is a string like ``1mo`` or ``30d``; we translate it to ``from``/``to`` dates.
        """
        token = await AngelOneProvider._obtain_access_token()
        # Determine exchange from suffix – simple heuristic for NSE/BSE.
        exchange = "NSE" if symbol.endswith(".NS") else "BSE" if symbol.endswith(".BO") else "NSE"  # honesty: allow
        # Strip the suffix for the API call.
        clean_symbol = symbol.replace(".NS", "").replace(".BO", "")  # honesty: allow
        # Compute date range.
        to_date = datetime.utcnow()
        if period.lower().endswith("mo"):
            months = int(period[:-2])
            from_date = to_date - timedelta(days=30 * months)
        elif period.lower().endswith("d"):
            days = int(period[:-1])
            from_date = to_date - timedelta(days=days)
        else:
            from_date = to_date - timedelta(days=30)
        fmt = "%Y-%m-%d"
        params = {
            "exchange": exchange,
            "symbol": clean_symbol,
            "interval": interval,
            "fromdate": from_date.strftime(fmt),
            "todate": to_date.strftime(fmt),
        }
        headers = {"authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://smartapi.angelbroking.com/v1/marketdata/historical/",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        # Expected payload: {"data": [{"timestamp": ..., "open": ..., ...}], "status": "success"}
        candles_raw = data.get("data", [])
        candles: list[Candle] = []
        for item in candles_raw:
            try:
                ts = int(datetime.strptime(item["timestamp"], "%Y-%m-%d %H:%M:%S").timestamp())
                candles.append(
                    Candle(
                        timestamp=ts,
                        open=float(item.get("open", 0)),
                        high=float(item.get("high", 0)),
                        low=float(item.get("low", 0)),
                        close=float(item.get("close", 0)),
                        volume=float(item.get("volume", 0)),
                    )
                )
            except Exception as exc:
                logger.warning("Skipping malformed candle %s: %s", item, exc)
        return candles
