# backend/app/websocket/price_ticker.py
"""Real-time price ticker – publishes ticks and signals to Redis channel 'prices.ticks'."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from decimal import Decimal

import pandas as pd
from redis.asyncio import Redis

from app.database.connection import async_session_factory
from app.services.market_data_service import MarketDataService
from app.services.paper_trading import PaperTradingService
from app.services.prediction_engine import get_full_prediction
import pandas_ta as ta

logger = logging.getLogger(__name__)

import time

from app.core.watchlist import WATCHLIST_SYMBOLS
from app.services.data_ingestion.scheduler import is_market_hours


class TokenBucket:
    def __init__(self, rate: float, capacity: float):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()

    async def consume(self, tokens: float = 1.0):
        while True:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return
            await asyncio.sleep(0.1)


async def run_price_ticker(redis: Redis) -> None:
    """Infinite loop fetching and broadcasting Watchlist prices and signals, rate limited and staggered."""
    logger.info("Starting run_price_ticker background loop")

    # 3 req/sec limit to avoid NSE bans
    bucket = TokenBucket(rate=3.0, capacity=3.0)

    from sqlalchemy import select
    from app.models.watchlist import UserWatchlist
    from app.models.instrument import Instrument
    from app.models.portfolio import PortfolioHolding
    from app.models.paper_trading import PaperPosition

    while True:
        try:
            market_open = is_market_hours()

            # 1. Gather all active symbols dynamically
            symbols_to_poll = set(MarketDataService.NSE_NIFTY50[:5]) # poll top 5 always just to keep it alive
            
            # Fetch from DB: Watchlists, Portfolios, Paper Positions
            try:
                async with async_session_factory() as session:
                    wl_res = await session.execute(select(UserWatchlist.symbol))
                    symbols_to_poll.update([s for s in wl_res.scalars().all()])
                    
                    pf_res = await session.execute(
                        select(Instrument.symbol)
                        .join(PortfolioHolding, PortfolioHolding.symbol_id == Instrument.id)
                    )
                    symbols_to_poll.update([s for s in pf_res.scalars().all()])
                    
                    pp_res = await session.execute(select(PaperPosition.symbol))
                    symbols_to_poll.update([s for s in pp_res.scalars().all()])
            except Exception as db_err:
                logger.debug(f"Failed to fetch symbols from DB: {db_err}")
                
            # Fetch from Redis active subscriptions
            try:
                active_from_redis = await redis.smembers("active_symbols")
                if active_from_redis:
                    symbols_to_poll.update([s.decode('utf-8') for s in active_from_redis])
            except Exception as redis_err:
                logger.debug(f"Failed to fetch active_symbols from Redis: {redis_err}")

            for sym in list(symbols_to_poll):
                try:
                    await bucket.consume(1)

                    quote = await MarketDataService.get_quote(sym)

                    if not quote or quote.get("price") is None:
                        continue

                    normalized_symbol = quote["symbol"]  # e.g. RELIANCE.NS
                    price = float(quote["price"])

                    # 1. Fetch cached daily history to compute latest indicators
                    ema9_val, ema21_val, rsi_val = None, None, None
                    macd_val, macd_sig, macd_h = None, None, None
                    try:
                        hist = await MarketDataService.get_history(
                            normalized_symbol, interval="1d", period="3mo"
                        )
                        if hist and len(hist) >= 10:
                            closes = [float(h["close"]) for h in hist] + [price]
                            closes_df = pd.DataFrame({"close": closes})

                            ema9 = closes_df.ta.ema(close="close", length=9)
                            ema21 = closes_df.ta.ema(close="close", length=21)
                            rsi = closes_df.ta.rsi(close="close", length=14)
                            macd_df = closes_df.ta.macd(close="close", fast=12, slow=26, signal=9)

                            if ema9 is not None and not pd.isna(ema9.iloc[-1]):
                                ema9_val = float(ema9.iloc[-1])
                            if ema21 is not None and not pd.isna(ema21.iloc[-1]):
                                ema21_val = float(ema21.iloc[-1])
                            if rsi is not None and not pd.isna(rsi.iloc[-1]):
                                rsi_val = float(rsi.iloc[-1])

                            if macd_df is not None:
                                if not pd.isna(macd_df.iloc[-1, 0]):
                                    macd_val = float(macd_df.iloc[-1, 0])
                                if not pd.isna(macd_df.iloc[-1, 1]):
                                    macd_h = float(macd_df.iloc[-1, 1])
                                if not pd.isna(macd_df.iloc[-1, 2]):
                                    macd_sig = float(macd_df.iloc[-1, 2])
                    except Exception as ind_err:
                        logger.warning(
                            f"Failed to calculate indicators for tick {normalized_symbol}: {ind_err}"
                        )

                    # Standard Envelope for tick
                    tick = {
                        "type": "tick",
                        "symbol": normalized_symbol,
                        "payload": {
                            "price": price,
                            "change": float(quote.get("change", 0.0)),
                            "change_pct": float(quote.get("change_pct", 0.0)),
                            "market_closed": not market_open,
                            "ema9": ema9_val,
                            "ema21": ema21_val,
                            "rsi": rsi_val,
                            "macd": macd_val,
                            "macd_signal": macd_sig,
                            "macd_hist": macd_h,
                        },
                        "ts": datetime.now(UTC).isoformat(),
                        "source": quote.get("source", "unknown"),
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
                                session, normalized_symbol, Decimal(str(price))
                            )
                    except Exception as order_err:
                        logger.error(
                            f"Error checking limit orders for {normalized_symbol}: {order_err}"
                        )

                    # 4. Generate live ML signals on tick
                    try:
                        pred = await get_full_prediction(normalized_symbol, bypass_cache=False)
                        if pred and pred.get("is_computed", False):
                            ens = pred.get("ensemble", {})

                            rsi_str = f"{rsi_val:.1f}" if rsi_val is not None else "N/A"
                            macd_str = f"{macd_val:.2f}" if macd_val is not None else "N/A"
                            ema9_str = f"{ema9_val:.2f}" if ema9_val is not None else "N/A"
                            rationale = f"RSI is {rsi_str}. MACD is {macd_str}. Price is ₹{price:,.2f} vs EMA9 ₹{ema9_str}. Ensemble suggests {ens.get('direction')} (Conf: {ens.get('confidence', 0.5) * 100:.1f}%)."

                            # Standard Envelope for signal
                            signal_msg = {
                                "type": "signal",
                                "symbol": normalized_symbol,
                                "payload": {
                                    "direction": ens.get("direction", "NEUTRAL"),
                                    "confidence": float(ens.get("confidence", 0.5)),
                                    "raw_ensemble": float(ens.get("raw_ensemble", 0.0)),
                                    "stop_loss": float(ens.get("stop_loss", price)),
                                    "take_profit": float(ens.get("take_profit", price)),
                                    "rationale": rationale,
                                },
                                "ts": datetime.now(UTC).isoformat(),
                                "source": "system",
                            }

                            await redis.publish("prices.ticks", json.dumps(signal_msg))
                    except Exception as sig_err:
                        logger.warning(
                            f"Failed to compute live signal for tick {normalized_symbol}: {sig_err}"
                        )
                except Exception as e:
                    logger.debug(f"Ticker processing failed for symbol={sym}: {e}")

        except Exception as e:
            logger.warning(f"Error in run_price_ticker loop: {e}", exc_info=True)

        # Market gating: if off-hours, significantly increase sleep after 1 loop (since we emit last close).
        sleep_time = 10 if market_open else 300
        await asyncio.sleep(sleep_time)
