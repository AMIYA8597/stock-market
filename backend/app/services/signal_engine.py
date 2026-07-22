# backend/app/services/signal_engine.py
"""Signal Engine — Evaluates prediction output against strict trading rules and stores signals."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
import pandas_ta as ta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Symbol
from app.models.signal import EnsembleSignal
from research.backtesting.cost_model import compute_costs
from app.services.pattern_service import get_pattern_score

logger = logging.getLogger(__name__)

class TechnicalSignalEngine:
    """Computes rule-based algorithmic trading signals computed from stored OHLCV data."""
    
    @staticmethod
    def generate_signal(df: pd.DataFrame) -> dict[str, Any]:
        """
        Generate composite signal by computing technical indicators on OHLCV data.
        Features: Trend, Momentum, Volatility, Volume, Structure.
        Returns: {
            "direction": "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL",
            "confidence": float (0-1),
            "score": float (-1 to 1),
            "breakdown": dict,
            "stop_loss": float,
            "take_profit": float,
        }
        """
        df = df.copy()
        score = 0.0
        breakdown = {}
        
        if len(df) < 50:
            return {
                "direction": "NEUTRAL",
                "confidence": 0.0,
                "score": 0.0,
                "breakdown": breakdown,
                "patterns": [],
                "stop_loss": 0.0,
                "take_profit": 0.0,
            }
            
        # Compute all indicators first
        # 1. Trend
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)
        df.ta.ema(length=20, append=True)
        df.ta.wma(length=20, append=True)
        df.ta.macd(append=True)
        df.ta.adx(append=True)
        df.ta.supertrend(append=True)
        df.ta.psar(append=True)
        
        # 2. Momentum
        df.ta.rsi(append=True)
        df.ta.stoch(append=True)
        df.ta.roc(append=True)
        df.ta.cci(append=True)
        df.ta.willr(append=True)
        
        # 3. Volatility
        df.ta.bbands(append=True)
        df.ta.atr(append=True)
        df.ta.kc(append=True)
        df.ta.donchian(append=True)
        
        # 4. Volume
        df.ta.obv(append=True)
        df.ta.vwap(append=True)
        df.ta.mfi(append=True)
        df.ta.ad(append=True)

        last = df.iloc[-1]
        prev = df.iloc[-2]
        close = float(last["close"])
        high = float(last["high"])
        low = float(last["low"])
        
        # Trend rules
        trend_score = 0.0
        
        # EMA/SMA Cross (Golden/Death)
        if last.get("SMA_20") and last.get("SMA_50"):
            if last["SMA_20"] > last["SMA_50"] and prev["SMA_20"] <= prev["SMA_50"]:
                trend_score += 0.3 # Golden cross
            elif last["SMA_20"] < last["SMA_50"] and prev["SMA_20"] >= prev["SMA_50"]:
                trend_score -= 0.3 # Death cross
        
        # MACD
        macd_col = [c for c in df.columns if c.startswith("MACD_") and not "h" in c and not "s" in c]
        macds_col = [c for c in df.columns if c.startswith("MACDs_")]
        macdh_col = [c for c in df.columns if c.startswith("MACDh_")]
        if macd_col and macds_col:
            macd = last[macd_col[0]]
            macds = last[macds_col[0]]
            macdh = last[macdh_col[0]]
            prev_macdh = prev[macdh_col[0]]
            
            if macd > macds: trend_score += 0.1
            else: trend_score -= 0.1
                
            if macdh > 0 and macdh > prev_macdh: trend_score += 0.1
            elif macdh < 0 and macdh < prev_macdh: trend_score -= 0.1
                
        # ADX
        adx_col = [c for c in df.columns if c.startswith("ADX_")]
        dmp_col = [c for c in df.columns if c.startswith("DMP_")]
        dmn_col = [c for c in df.columns if c.startswith("DMN_")]
        if adx_col:
            if last[adx_col[0]] > 25:
                if last[dmp_col[0]] > last[dmn_col[0]]: trend_score += 0.2
                else: trend_score -= 0.2
                
        # Supertrend
        st_dir_col = [c for c in df.columns if c.startswith("SUPERTd_")]
        if st_dir_col:
            if last[st_dir_col[0]] > 0: trend_score += 0.15
            else: trend_score -= 0.15
            
        breakdown["trend"] = max(-1.0, min(1.0, trend_score))
        
        mom_score = 0.0
        rsi_col = [c for c in df.columns if c.startswith("RSI_")]
        if rsi_col:
            rsi = last[rsi_col[0]]
            if rsi < 30: mom_score += 0.25 # Oversold
            elif rsi > 70: mom_score -= 0.25 # Overbought
            elif 45 < rsi < 55: mom_score += 0.05 # Mild momentum
                
        stochk_col = [c for c in df.columns if c.startswith("STOCHk_")]
        stochd_col = [c for c in df.columns if c.startswith("STOCHd_")]
        if stochk_col and stochd_col:
            if last[stochk_col[0]] < 20 and last[stochd_col[0]] < 20: mom_score += 0.15
            elif last[stochk_col[0]] > 80 and last[stochd_col[0]] > 80: mom_score -= 0.15
            
        roc_col = [c for c in df.columns if c.startswith("ROC_")]
        if roc_col:
            if last[roc_col[0]] > 0: mom_score += 0.1
            else: mom_score -= 0.1
            
        cci_col = [c for c in df.columns if c.startswith("CCI_")]
        if cci_col:
            if last[cci_col[0]] > 100: mom_score += 0.1
            elif last[cci_col[0]] < -100: mom_score -= 0.1
            
        willr_col = [c for c in df.columns if c.startswith("WILLR_")]
        if willr_col:
            if last[willr_col[0]] < -80: mom_score += 0.1
            elif last[willr_col[0]] > -20: mom_score -= 0.1
            
        breakdown["momentum"] = max(-1.0, min(1.0, mom_score))
        
        vol_score = 0.0
        bbp_col = [c for c in df.columns if c.startswith("BBP_")]
        bbb_col = [c for c in df.columns if c.startswith("BBB_")]
        if bbp_col and bbb_col:
            if last[bbp_col[0]] < 0.05: vol_score += 0.15
            elif last[bbp_col[0]] > 0.95: vol_score -= 0.15
            
            if last[bbb_col[0]] < 10: vol_score += 0.05 # Squeeze
            
        # Keltner breakout
        kcu_col = [c for c in df.columns if c.startswith("KCU_")]
        kcl_col = [c for c in df.columns if c.startswith("KCL_")]
        if kcu_col and kcl_col:
            if close > last[kcu_col[0]]: vol_score += 0.1
            elif close < last[kcl_col[0]]: vol_score -= 0.1
            
        # Donchian breakout
        dcu_col = [c for c in df.columns if c.startswith("DCU_")]
        dcl_col = [c for c in df.columns if c.startswith("DCL_")]
        if dcu_col and dcl_col:
            if close >= last[dcu_col[0]]: vol_score += 0.15
            elif close <= last[dcl_col[0]]: vol_score -= 0.15
            
        breakdown["volatility"] = max(-1.0, min(1.0, vol_score))
        
        volu_score = 0.0
        obv_col = [c for c in df.columns if c.startswith("OBV")]
        if obv_col:
            obv_series = df[obv_col[0]]
            obv_slope = (obv_series.iloc[-1] - obv_series.iloc[-5]) / (abs(obv_series.iloc[-5]) + 1)
            if obv_slope > 0: volu_score += 0.1
            else: volu_score -= 0.1
            
        vwap_col = [c for c in df.columns if c.startswith("VWAP")]
        if vwap_col:
            if close > last[vwap_col[0]]: volu_score += 0.1
            else: volu_score -= 0.1
            
        mfi_col = [c for c in df.columns if c.startswith("MFI_")]
        if mfi_col:
            if last[mfi_col[0]] < 20: volu_score += 0.1
            elif last[mfi_col[0]] > 80: volu_score -= 0.1
            
        # Volume Spike Z-score
        volume = df["volume"]
        vol_mean = volume.rolling(20).mean()
        vol_std = volume.rolling(20).std()
        z_score = (volume - vol_mean) / (vol_std + 1e-9)
        last_z = z_score.iloc[-1]
        
        if last_z > 2.0:
            if is_bullish := close > df["open"].iloc[-1]:
                volu_score += 0.2
            else:
                volu_score -= 0.2
                
        breakdown["volume"] = max(-1.0, min(1.0, volu_score))
        
        # 5. Structure (Patterns, Gap, 52-week proximity)
        struct_score = 0.0
        
        # Gap detection
        if low > prev["high"]: struct_score += 0.15
        elif high < prev["low"]: struct_score -= 0.15
        
        # 52-week High/Low proximity
        high_252 = df["high"].rolling(252).max().iloc[-1]
        low_252 = df["low"].rolling(252).min().iloc[-1]
        
        if not pd.isna(high_252) and high_252 > 0:
            if close >= high_252 * 0.98: struct_score += 0.1 # Breaking out
            elif close <= low_252 * 1.02: struct_score -= 0.1 # Breaking down
            
        pat = get_pattern_score(df)
        struct_score += pat["pattern_score"]
        
        breakdown["structure"] = max(-1.0, min(1.0, struct_score))
        
        # 6. Composite
        # Weights: Trend(30%), Momentum(20%), Volatility(15%), Volume(15%), Structure(20%)
        composite_score = (
            breakdown["trend"] * 0.30 +
            breakdown["momentum"] * 0.20 +
            breakdown["volatility"] * 0.15 +
            breakdown["volume"] * 0.15 +
            breakdown["structure"] * 0.20
        )
        
        # Scale to confidence 0-100%
        confidence = min(1.0, abs(composite_score) * 1.5)
        
        if composite_score >= 0.40: direction = "STRONG_BUY"
        elif composite_score >= 0.15: direction = "BUY"
        elif composite_score <= -0.40: direction = "STRONG_SELL"
        elif composite_score <= -0.15: direction = "SELL"
        else: direction = "NEUTRAL"
        
        # 7. Risk Targets (ATR-based)
        atr_val = 0.0
        atr_col = [c for c in df.columns if c.startswith("ATRr_")]
        if atr_col:
            atr_val = last[atr_col[0]]
            
        if pd.isna(atr_val) or atr_val == 0:
            atr_val = close * 0.02
            
        if direction in ["BUY", "STRONG_BUY"]:
            stop_loss = close - (atr_val * 1.5)
            take_profit = close + (atr_val * 3.0) # 1:2 R:R
        elif direction in ["SELL", "STRONG_SELL"]:
            stop_loss = close + (atr_val * 1.5)
            take_profit = close - (atr_val * 3.0)
        else:
            stop_loss = 0.0
            take_profit = 0.0
            
        return {
            "direction": direction,
            "confidence": float(confidence),
            "score": float(composite_score),
            "breakdown": {k: float(v) for k, v in breakdown.items()},
            "patterns": pat["patterns_detected"],
            "stop_loss": float(stop_loss),
            "take_profit": float(take_profit),
        }

class SignalEngine:
    """Evaluates prediction data against risk thresholds, regimes, and cost models."""

    @staticmethod
    async def process_new_prediction(
        db: AsyncSession,
        symbol_ticker: str,
        prediction: dict,
    ) -> EnsembleSignal | None:
        """Process predictions and generate a trade signal if filters are passed."""
        stmt = select(Symbol).where(Symbol.ticker == symbol_ticker.upper())
        res = await db.execute(stmt)
        symbol = res.scalar_one_or_none()
        if not symbol:
            logger.warning(f"Symbol {symbol_ticker} not found in database, skipping signal generation.")
            return None

        direction = prediction.get("direction", "NEUTRAL")
        confidence = float(prediction.get("confidence", 0.5))
        raw_ensemble = float(prediction.get("raw_ensemble", 0.0))
        regime = prediction.get("regime", {})
        regime_name = regime.get("regime", "SIDEWAYS")
        conditional_vol = regime.get("conditional_vol", 0.02)

        target_price_5d = float(prediction.get("target_price_5d", 0.0))
        stop_loss = float(prediction.get("stop_loss", 0.0))
        take_profit = float(prediction.get("take_profit", 0.0))
        kelly = float(prediction.get("kelly", 0.0))

        technical = prediction.get("technical", {})
        current_price = float(technical.get("last_close") or prediction.get("current_price") or stop_loss)
        if current_price <= 0:
            current_price = stop_loss

        if confidence < 0.65:
            logger.info(f"Signal rejected for {symbol_ticker}: Confidence {confidence:.2%} is below 65% threshold.")
            return None

        if direction in ("BUY", "STRONG_BUY") and regime_name in ("BEAR", "CRISIS"):
            logger.info(f"Signal rejected for {symbol_ticker}: BUY direction is incompatible with HMM regime {regime_name}.")
            return None

        if direction in ("SELL", "STRONG_SELL") and regime_name == "BULL":
            logger.info(f"Signal rejected for {symbol_ticker}: SELL direction is incompatible with HMM regime {regime_name}.")
            return None

        trades_abs = np.array([[1.0]])
        prices = np.array([[current_price]])
        adv = np.array([[10000000.0]])
        realized_vol = np.array([[conditional_vol]])

        cost_arr = compute_costs(trades_abs, prices, adv, realized_vol)
        single_trip_cost = float(cost_arr[0][0])
        round_trip_cost = single_trip_cost * 2.0

        expected_gain = abs(target_price_5d - current_price)
        if expected_gain < (3.0 * round_trip_cost):
            logger.info(
                f"Signal rejected for {symbol_ticker}: Expected gain (₹{expected_gain:.2f}) "
                f"does not exceed 3x round-trip cost (₹{3.0 * round_trip_cost:.2f})."
            )
            return None

        regime_map = {"bull": 0, "bear": 1, "sideways": 2, "crisis": 3, "BULL": 0, "BEAR": 1, "SIDEWAYS": 2, "CRISIS": 3}
        regime_state = regime_map.get(regime_name, 2)

        inputs_dict = {
            "technical_score": float(technical.get("score", 0.0)),
            "pattern_score": float(prediction.get("pattern", {}).get("pattern_score", 0.0)),
            "momentum_score": float(prediction.get("momentum", {}).get("momentum_score", 0.0)),
            "xgboost_score": float(prediction.get("xgboost", {}).get("xgb_score", 0.0)),
            "sentiment_score": float(prediction.get("online_learner", {}).get("raw_signal", 0.0)),
        }

        signal_time = datetime.now(UTC)

        ensemble_signal = EnsembleSignal(
            time=signal_time,
            symbol_id=symbol.id,
            signal=Decimal(str(round(raw_ensemble, 4))),
            confidence=Decimal(str(round(confidence, 4))),
            direction=direction,
            model_weights=prediction.get("model_weights") or {},
            regime_state=regime_state,
            kelly_fraction=Decimal(str(round(kelly, 4))) if kelly > 0 else Decimal("0.0"),
            inputs_used=inputs_dict,
            outcome="PENDING",
        )

        db.add(ensemble_signal)
        await db.flush()
        logger.info(f"Generated new EnsembleSignal for {symbol_ticker}: {direction} @ {confidence:.2%} confidence.")
        return ensemble_signal
