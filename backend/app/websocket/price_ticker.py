# backend/app/websocket/price_ticker.py
"""Real-time price ticker – publishes ticks and signals to Redis channel 'prices.ticks'."""

from __future__ import annotations

import asyncio
from decimal import Decimal
import json
from datetime import UTC, datetime
import logging

import pandas as pd
import pandas_ta as ta
from redis.asyncio import Redis

from app.services.market_data_service import MarketDataService
from app.services.paper_trading import PaperTradingService
from app.services.prediction_engine import get_full_prediction
from app.database.connection import async_session_factory

logger = logging.getLogger(__name__)

WATCHLIST_SYMBOLS = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
    "SBIN", "BHARTIARTL", "LT", "ITC", "HINDUNILVR",
    "AXISBANK", "KOTAKBANK", "BAJFINANCE", "SUNPHARMA", "MARUTI",
    "NTPC", "TATASTEEL", "POWERGRID", "ADANIPORTS", "TITAN"
]


async def run_price_ticker(redis: Redis) -> None:
    """Infinite loop fetching and broadcasting Watchlist prices and signals every 10 seconds."""
    logger.info("Starting run_price_ticker background loop")
    
    while True:
        try:
            tasks = [MarketDataService.get_quote(sym) for sym in WATCHLIST_SYMBOLS]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for sym, quote in zip(WATCHLIST_SYMBOLS, results):
                if isinstance(quote, Exception):
                    logger.debug(f"Ticker quote failed for symbol={sym}: {quote}")
                    continue
                if not quote or quote.get("price") is None:
                    continue
                
                normalized_symbol = quote["symbol"] # e.g. RELIANCE.NS
                price = quote["price"]

                # 1. Fetch cached daily history to compute latest indicators
                ema9_val, ema21_val, rsi_val = None, None, None
                macd_val, macd_sig, macd_h = None, None, None
                try:
                    hist = await MarketDataService.get_history(normalized_symbol, interval="1d", period="3mo")
                    if hist and len(hist) >= 10:
                        closes = [float(h["close"]) for h in hist] + [float(price)]
                        closes_df = pd.DataFrame({"close": closes})
                        
                        ema9 = closes_df.ta.ema(close="close", length=9)
                        ema21 = closes_df.ta.ema(close="close", length=21)
                        rsi = closes_df.ta.rsi(close="close", length=14)
                        macd_df = closes_df.ta.macd(close="close", fast=12, slow=26, signal=9)

                        ema9_val = float(ema9.iloc[-1]) if ema9 is not None and not pd.isna(ema9.iloc[-1]) else None
                        ema21_val = float(ema21.iloc[-1]) if ema21 is not None and not pd.isna(ema21.iloc[-1]) else None
                        rsi_val = float(rsi.iloc[-1]) if rsi is not None and not pd.isna(rsi.iloc[-1]) else None
                        
                        if macd_df is not None:
                            macd_val = float(macd_df.iloc[-1, 0]) if not pd.isna(macd_df.iloc[-1, 0]) else None
                            macd_h = float(macd_df.iloc[-1, 1]) if not pd.isna(macd_df.iloc[-1, 1]) else None
                            macd_sig = float(macd_df.iloc[-1, 2]) if not pd.isna(macd_df.iloc[-1, 2]) else None
                except Exception as ind_err:
                    logger.warning(f"Failed to calculate indicators for tick {normalized_symbol}: {ind_err}")

                tick = {
                    "type": "tick",
                    "symbol": normalized_symbol,
                    "price": float(price),
                    "change": float(quote.get("change", 0.0)),
                    "change_pct": float(quote.get("change_pct", 0.0)),
                    "timestamp": datetime.now(UTC).isoformat(),
                    "ema9": ema9_val,
                    "ema21": ema21_val,
                    "rsi": rsi_val,
                    "macd": macd_val,
                    "macd_signal": macd_sig,
                    "macd_hist": macd_h,
                }
                
                # 2. Publish tick to Redis
                try:
                    await redis.publish("prices.ticks", json.dumps(tick))
                except Exception as pe:
                    logger.warning(f"Failed to publish tick to Redis for {sym}: {pe}")

                # 3. Check and execute limit orders against the new tick price
                try:
                    async with async_session_factory() as session:
                        await PaperTradingService.check_and_execute_limit_orders(
                            session,
                            normalized_symbol,
                            Decimal(str(price))
                        )
                except Exception as order_err:
                    logger.error(f"Error checking limit orders for {normalized_symbol}: {order_err}")

                # 4. Generate live ML signals on tick
                try:
                    pred = await get_full_prediction(normalized_symbol, bypass_cache=False)
                    if pred and pred.get("is_computed", False):
                        ens = pred.get("ensemble", {})
                        
                        rsi_str = f"{rsi_val:.1f}" if rsi_val is not None else "N/A"
                        macd_str = f"{macd_val:.2f}" if macd_val is not None else "N/A"
                        ema9_str = f"{ema9_val:.2f}" if ema9_val is not None else "N/A"
                        
                        signal_msg = {
                            "type": "signal",
                            "symbol": normalized_symbol,
                            "direction": ens.get("direction", "NEUTRAL"),
                            "confidence": float(ens.get("confidence", 0.5)),
                            "raw_ensemble": float(ens.get("raw_ensemble", 0.0)),
                            "stop_loss": float(ens.get("stop_loss", price)),
                            "take_profit": float(ens.get("take_profit", price)),
                            "rationale": f"RSI is {rsi_str}. MACD is {macd_str}. Price is ₹{price:,.2f} vs EMA9 ₹{ema9_str}. Ensemble suggests {ens.get('direction')} (Conf: {ens.get('confidence', 0.5)*100:.1f}%).",
                            "timestamp": datetime.now(UTC).isoformat(),
                        }
                        
                        # Publish signal to Redis channel prices.ticks (so it goes to the same price_broadcaster -> prices:global WS connection!)
                        await redis.publish("prices.ticks", json.dumps(signal_msg))
                except Exception as sig_err:
                    logger.warning(f"Failed to compute live signal for tick {normalized_symbol}: {sig_err}")
                    
        except Exception as e:
            logger.warning(f"Error in run_price_ticker loop: {e}", exc_info=True)
            
        try:
            from app.services.data_ingestion.scheduler import is_market_hours
            sleep_time = 3 if is_market_hours() else 10
        except Exception:
            sleep_time = 10
            
        await asyncio.sleep(sleep_time)
