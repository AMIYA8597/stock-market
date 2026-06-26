# backend/app/services/upstox_service.py
"""Upstox Integration Service.

Coordinates Upstox OAuth, instrument search, WebSocket market tick streaming,
caching live prices, enriching ticks with indicators, and auditing logs.
"""

from __future__ import annotations

import os
import json
import logging
import asyncio
import httpx
from datetime import datetime, UTC
from pathlib import Path
from decimal import Decimal
from typing import Any, Optional, Dict, List
import pandas as pd
import pandas_ta as ta

import upstox_client

logger = logging.getLogger(__name__)

# Cache for ticks: symbol (e.g. "RELIANCE") -> tick dict
UPSTOX_TICK_CACHE: Dict[str, dict] = {}
# Symbol mappings
SYMBOL_TO_KEY: Dict[str, str] = {}
KEY_TO_SYMBOL: Dict[str, str] = {}

class UpstoxService:
    TRADING_MODE: str = "PAPER"  # ALWAYS defaults to PAPER, not persisted
    ACCESS_TOKEN: Optional[str] = None
    STREAMER: Optional[Any] = None
    CONNECTION_STATUS: str = "disconnected"  # disconnected, connecting, connected, reconnecting, error
    USER_PROFILE: Optional[dict] = None
    LOOP: Optional[asyncio.AbstractEventLoop] = None
    
    @classmethod
    def get_token_cache_path(cls) -> Path:
        """Returns path to cached token file in user's home Gemini config directory."""
        # For ease of local dev and to survive server restarts, cache token under app data / config
        cache_dir = Path("C:/Users/USER/.gemini/antigravity")
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "upstox_token.txt"

    @classmethod
    def log_audit(cls, message: str):
        """Logs trading actions to backend/logs/trading_audit.log with UTC timestamps."""
        try:
            backend_root = Path(__file__).resolve().parent.parent.parent
            logs_dir = backend_root / "logs"
            logs_dir.mkdir(exist_ok=True)
            audit_file = logs_dir / "trading_audit.log"
            
            timestamp = datetime.now(UTC).isoformat()
            log_line = f"[{timestamp}] {message}\n"
            
            with open(audit_file, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception as e:
            logger.error(f"Failed to write to audit log: {e}")

    @classmethod
    def get_cached_quote(cls, symbol: str) -> Optional[dict]:
        """Looks up a symbol (base or suffix) in our memory cache."""
        sym = symbol.upper().strip()
        base_sym = sym.split(".")[0]
        return UPSTOX_TICK_CACHE.get(base_sym) or UPSTOX_TICK_CACHE.get(sym)

    @classmethod
    def get_login_url(cls) -> str:
        """Generates Upstox login dialog URL."""
        from app.core.config import get_settings
        settings = get_settings()
        
        if not settings.UPSTOX_API_KEY:
            raise ValueError("UPSTOX_API_KEY is not configured in environment/.env file.")
            
        return (
            f"https://api.upstox.com/v2/login/authorization/dialog"
            f"?response_type=code"
            f"&client_id={settings.UPSTOX_API_KEY}"
            f"&redirect_uri={settings.UPSTOX_REDIRECT_URI}"
        )

    @classmethod
    async def exchange_code_for_token(cls, code: str) -> dict:
        """Exchanges authorization code for access token and caches it."""
        from app.core.config import get_settings
        settings = get_settings()
        
        url = "https://api.upstox.com/v2/login/authorization/token"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "code": code,
            "client_id": settings.UPSTOX_API_KEY,
            "client_secret": settings.UPSTOX_API_SECRET,
            "redirect_uri": settings.UPSTOX_REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        async with httpx.AsyncClient() as client:
            r = await client.post(url, headers=headers, data=data, timeout=15.0)
            if r.status_code != 200:
                err_msg = f"Token exchange failed: status={r.status_code} body={r.text}"
                logger.error(err_msg)
                raise ValueError(err_msg)
                
            res = r.json()
            token = res.get("access_token")
            if not token:
                raise ValueError("Access token missing in Upstox authorization response.")
                
            cls.ACCESS_TOKEN = token
            # Store in token cache file
            try:
                cls.get_token_cache_path().write_text(token, encoding="utf-8")
            except Exception as te:
                logger.warning(f"Could not persist access token to disk cache: {te}")
                
            # Fetch profile details
            profile = await cls.fetch_profile()
            cls.USER_PROFILE = profile
            cls.log_audit(f"Successfully authenticated Upstox user: {profile.get('user_name', 'Unknown')}")
            
            # Start streamer feed
            cls.LOOP = asyncio.get_running_loop()
            asyncio.create_task(cls.start_websocket_feed())
            
            return res

    @classmethod
    async def fetch_profile(cls) -> dict:
        """Fetches profile details of the authenticated user."""
        url = "https://api.upstox.com/v2/user/profile"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {cls.ACCESS_TOKEN}"
        }
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers, timeout=10.0)
            if r.status_code == 200:
                res = r.json()
                return res.get("data", {})
            return {}

    @classmethod
    async def init_service(cls):
        """Initializes service on boot: restores cached token, verifies it, and auto-starts connection."""
        cls.TRADING_MODE = "PAPER"  # Force default mode on boot
        cls.LOOP = asyncio.get_running_loop()
        
        token_file = cls.get_token_cache_path()
        if token_file.exists():
            try:
                token = token_file.read_text(encoding="utf-8").strip()
                if token:
                    cls.ACCESS_TOKEN = token
                    # Verify by calling profile
                    profile = await cls.fetch_profile()
                    if profile:
                        cls.USER_PROFILE = profile
                        cls.log_audit("Restored cached Upstox token successfully.")
                        # Auto connect WS
                        asyncio.create_task(cls.start_websocket_feed())
                    else:
                        cls.ACCESS_TOKEN = None
                        logger.info("Cached Upstox token has expired or is invalid.")
            except Exception as e:
                logger.warning(f"Error restoring cached token: {e}")

    @classmethod
    async def resolve_symbol(cls, symbol: str) -> Optional[str]:
        """Resolves NSE trading symbol to Upstox instrument_key."""
        sym = symbol.upper().strip()
        
        # Check cache
        if sym in SYMBOL_TO_KEY:
            return SYMBOL_TO_KEY[sym]
            
        # Hardcoded overrides for common index feeds
        if sym in ("NIFTY 50", "NIFTY_50", "NIFTY"):
            key = "NSE_INDEX|Nifty 50"
            SYMBOL_TO_KEY[sym] = key
            KEY_TO_SYMBOL[key] = sym
            return key
        if sym in ("NIFTY BANK", "BANKNIFTY", "NIFTY_BANK"):
            key = "NSE_INDEX|Nifty Bank"
            SYMBOL_TO_KEY[sym] = key
            KEY_TO_SYMBOL[key] = sym
            return key

        if not cls.ACCESS_TOKEN:
            return None

        # Search using instruments API
        url = f"https://api.upstox.com/v2/instruments/search?query={sym}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {cls.ACCESS_TOKEN}"
        }
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(url, headers=headers, timeout=10.0)
                if r.status_code == 200:
                    res = r.json()
                    data = res.get("data", [])
                    
                    # 1st pass: exact trading symbol match for NSE EQ or Index
                    for item in data:
                        t_sym = item.get("trading_symbol", "").upper()
                        seg = item.get("segment", "")
                        if t_sym == sym and seg in ("NSE_EQ", "NSE_INDEX"):
                            key = item.get("instrument_key")
                            SYMBOL_TO_KEY[sym] = key
                            KEY_TO_SYMBOL[key] = sym
                            return key
                            
                    # 2nd pass: prefix/partial match under NSE EQ
                    for item in data:
                        t_sym = item.get("trading_symbol", "").upper()
                        seg = item.get("segment", "")
                        if t_sym.startswith(sym) and seg == "NSE_EQ":
                            key = item.get("instrument_key")
                            SYMBOL_TO_KEY[sym] = key
                            KEY_TO_SYMBOL[key] = sym
                            return key
        except Exception as e:
            logger.error(f"Error resolving Upstox symbol {sym}: {e}")
            
        return None

    @classmethod
    async def start_websocket_feed(cls):
        """Starts background thread Upstox V3 Market Data Streamer."""
        if not cls.ACCESS_TOKEN:
            logger.warning("Attempted to start Upstox WebSocket feed without access token.")
            return
            
        # Close active streamer if any
        await cls.stop_websocket_feed()
        
        default_symbols = [
            "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN",
            "NIFTY 50", "NIFTY BANK"
        ]
        
        keys_to_subscribe = []
        for sym in default_symbols:
            key = await cls.resolve_symbol(sym)
            if key:
                keys_to_subscribe.append(key)
                
        if not keys_to_subscribe:
            logger.warning("No instruments resolved for Upstox subscription.")
            return

        cls.CONNECTION_STATUS = "connecting"
        cls.log_audit(f"Connecting Upstox WebSocket feed for keys: {keys_to_subscribe}")
        
        try:
            cfg = upstox_client.Configuration()
            cfg.access_token = cls.ACCESS_TOKEN
            api_client = upstox_client.ApiClient(cfg)
            
            # Instantiate MarketDataStreamerV3
            cls.STREAMER = upstox_client.MarketDataStreamerV3(api_client, keys_to_subscribe, mode="full")
            
            # Wire up callbacks
            cls.STREAMER.on("open", cls.on_open)
            cls.STREAMER.on("close", cls.on_close)
            cls.STREAMER.on("message", cls.on_message)
            cls.STREAMER.on("error", cls.on_error)
            cls.STREAMER.on("reconnecting", cls.on_reconnecting)
            
            # Non-blocking connect (SDK spawns standard background daemon thread)
            cls.STREAMER.connect()
            
        except Exception as e:
            cls.CONNECTION_STATUS = "error"
            cls.log_audit(f"Failed to start Upstox WebSocket feed: {e}")
            logger.error(f"Failed to start Upstox WebSocket feed: {e}", exc_info=True)

    @classmethod
    async def stop_websocket_feed(cls):
        """Disconnects the active Upstox WebSocket streamer."""
        if cls.STREAMER:
            try:
                cls.STREAMER.disconnect()
            except Exception as e:
                logger.debug(f"Disconnect error: {e}")
            cls.STREAMER = None
        cls.CONNECTION_STATUS = "disconnected"

    # ─── Streamer callbacks (Executed on SDK background daemon thread) ────
    
    @classmethod
    def on_open(cls):
        cls.CONNECTION_STATUS = "connected"
        cls.log_audit("Upstox WebSocket Feed connected successfully.")
        logger.info("Upstox WebSocket Feed connected successfully.")

    @classmethod
    def on_close(cls, close_status_code, close_msg):
        cls.CONNECTION_STATUS = "disconnected"
        cls.log_audit(f"Upstox WebSocket Feed closed: {close_status_code} - {close_msg}")
        logger.info(f"Upstox WebSocket Feed closed: {close_status_code} - {close_msg}")

    @classmethod
    def on_error(cls, error):
        cls.CONNECTION_STATUS = "error"
        cls.log_audit(f"Upstox WebSocket Feed error: {error}")
        logger.error(f"Upstox WebSocket Feed error: {error}")

    @classmethod
    def on_reconnecting(cls, message):
        cls.CONNECTION_STATUS = "reconnecting"
        cls.log_audit(f"Upstox WebSocket Feed reconnecting: {message}")
        logger.info(f"Upstox WebSocket Feed reconnecting: {message}")

    @classmethod
    def on_message(cls, message: dict):
        """Parses decoded Protobuf dict, updates cache, and publishes tick to Redis."""
        try:
            feeds = message.get("feeds", {})
            if not feeds:
                return

            for inst_key, feed in feeds.items():
                symbol = KEY_TO_SYMBOL.get(inst_key)
                if not symbol:
                    continue

                price = None
                prev_close = 0.0
                open_p, high, low, volume = 0.0, 0.0, 0.0, 0
                
                # Check union fields
                if "ltpc" in feed:
                    ltpc = feed["ltpc"]
                    price = ltpc.get("ltp")
                    prev_close = ltpc.get("cp", 0.0)
                elif "ff" in feed:
                    mff = feed["ff"].get("marketFF", {})
                    if "ltpc" in mff:
                        price = mff["ltpc"].get("ltp")
                        prev_close = mff["ltpc"].get("cp", 0.0)
                    if "marketOHLC" in mff:
                        ohlc_list = mff["marketOHLC"].get("ohlc", [])
                        for ohlc in ohlc_list:
                            if ohlc.get("interval") == "1d":
                                open_p = ohlc.get("open", 0.0)
                                high = ohlc.get("high", 0.0)
                                low = ohlc.get("low", 0.0)
                                prev_close = ohlc.get("close", prev_close)
                                volume = ohlc.get("volume", 0)

                if price is not None:
                    change = price - prev_close
                    change_pct = (change / prev_close * 100.0) if prev_close > 0 else 0.0
                    
                    tick = {
                        "symbol": symbol.upper(),
                        "price": float(price),
                        "change": float(change),
                        "change_pct": float(change_pct),
                        "open": float(open_p),
                        "high": float(high),
                        "low": float(low),
                        "volume": int(volume),
                        "previous_close": float(prev_close),
                        "source": "upstox",
                        "live": True,
                        "timestamp": datetime.now(UTC).isoformat()
                    }
                    
                    # Store both basic symbol and suffix versions
                    base_sym = symbol.split(".")[0].upper()
                    UPSTOX_TICK_CACHE[base_sym] = tick
                    UPSTOX_TICK_CACHE[f"{base_sym}.NS"] = tick

                    # Schedule Redis publish in main loop
                    if cls.LOOP and cls.LOOP.is_running():
                        asyncio.run_coroutine_threadsafe(
                            cls.publish_tick_to_redis(tick),
                            cls.LOOP
                        )
        except Exception as e:
            logger.error(f"Error in Upstox message handler: {e}")

    @classmethod
    async def publish_tick_to_redis(cls, tick: dict):
        """Calculates indicators, enriches tick, and publishes to Redis channel 'prices.ticks'."""
        try:
            from app.database.redis_client import get_redis_client
            redis_client = await get_redis_client()
            
            # Enrich tick with overlay indicators
            enriched_tick = await cls.enrich_tick_with_indicators(tick)
            
            # Publish to Redis channel
            await redis_client.publish("prices.ticks", json.dumps(enriched_tick))
            
            # Trigger limit order check in simulated paper wallet
            try:
                from app.database.connection import async_session_factory
                from app.services.paper_trading import PaperTradingService
                async with async_session_factory() as session:
                    await PaperTradingService.check_and_execute_limit_orders(
                        session,
                        tick["symbol"],
                        Decimal(str(tick["price"]))
                    )
            except Exception as err:
                logger.error(f"Limit order validation error for {tick['symbol']}: {err}")
                
        except Exception as e:
            logger.debug(f"Redis publish fail for {tick['symbol']}: {e}")

    @classmethod
    async def enrich_tick_with_indicators(cls, tick: dict) -> dict:
        """Helper to compute technical indicators on-the-fly via pandas_ta for streaming."""
        from app.services.market_data_service import MarketDataService
        symbol = tick["symbol"]
        price = tick["price"]
        
        # Set baseline keys
        keys = ["ema9", "ema21", "ema50", "ema200", "rsi", "macd", "macd_signal", "macd_hist", "vwap", "supertrend", "bb_basis", "bb_upper", "bb_lower"]
        for k in keys:
            tick[k] = None

        try:
            # yfinance NS suffix mapping check
            lookup_sym = symbol if "." in symbol else f"{symbol}.NS"
            hist = await MarketDataService.get_history(lookup_sym, interval="1d", period="3mo")
            
            if hist and len(hist) >= 10:
                closes = [float(h["close"]) for h in hist] + [float(price)]
                highs = [float(h["high"]) for h in hist] + [float(tick.get("high", price))]
                lows = [float(h["low"]) for h in hist] + [float(tick.get("low", price))]
                opens = [float(h["open"]) for h in hist] + [float(tick.get("open", price))]
                volumes = [int(h["volume"]) for h in hist] + [int(tick.get("volume", 0))]
                
                df = pd.DataFrame({
                    "open": opens,
                    "high": highs,
                    "low": lows,
                    "close": closes,
                    "volume": volumes
                })
                
                # Append indicators
                df.ta.ema(length=9, append=True)
                df.ta.ema(length=21, append=True)
                df.ta.ema(length=50, append=True)
                df.ta.ema(length=200, append=True)
                df.ta.rsi(length=14, append=True)
                df.ta.macd(fast=12, slow=26, signal=9, append=True)
                df.ta.bbands(length=20, std=2, append=True)
                df.ta.vwap(append=True)
                df.ta.supertrend(length=10, multiplier=3.0, append=True)
                
                last_row = df.iloc[-1]
                
                for col in df.columns:
                    col_lower = col.lower()
                    if col_lower.startswith("ema_9") or col_lower == "ema_9":
                        tick["ema9"] = float(last_row[col]) if not pd.isna(last_row[col]) else None
                    elif col_lower.startswith("ema_21") or col_lower == "ema_21":
                        tick["ema21"] = float(last_row[col]) if not pd.isna(last_row[col]) else None
                    elif col_lower.startswith("ema_50") or col_lower == "ema_50":
                        tick["ema50"] = float(last_row[col]) if not pd.isna(last_row[col]) else None
                    elif col_lower.startswith("ema_200") or col_lower == "ema_200":
                        tick["ema200"] = float(last_row[col]) if not pd.isna(last_row[col]) else None
                    elif "rsi_14" in col_lower:
                        tick["rsi"] = float(last_row[col]) if not pd.isna(last_row[col]) else None
                    elif col_lower.startswith("macd_12") and not col_lower.startswith("macdh") and not col_lower.startswith("macds"):
                        tick["macd"] = float(last_row[col]) if not pd.isna(last_row[col]) else None
                    elif col_lower.startswith("macdh_12"):
                        tick["macd_hist"] = float(last_row[col]) if not pd.isna(last_row[col]) else None
                    elif col_lower.startswith("macds_12"):
                        tick["macd_signal"] = float(last_row[col]) if not pd.isna(last_row[col]) else None
                    elif "vwap" in col_lower:
                        tick["vwap"] = float(last_row[col]) if not pd.isna(last_row[col]) else None
                    elif col_lower.startswith("supert_10_3.0"):
                        tick["supertrend"] = float(last_row[col]) if not pd.isna(last_row[col]) else None
                    elif "bbm_20_2" in col_lower:
                        tick["bb_basis"] = float(last_row[col]) if not pd.isna(last_row[col]) else None
                    elif "bbu_20_2" in col_lower:
                        tick["bb_upper"] = float(last_row[col]) if not pd.isna(last_row[col]) else None
                    elif "bbl_20_2" in col_lower:
                        tick["bb_lower"] = float(last_row[col]) if not pd.isna(last_row[col]) else None
        except Exception as e:
            logger.debug(f"Error enriching tick for {symbol}: {e}")
            
        return tick
