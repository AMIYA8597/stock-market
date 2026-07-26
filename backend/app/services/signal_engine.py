# backend/app/services/signal_engine.py
"""Signal Engine — Evaluates prediction output against strict trading rules and stores signals."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instrument import Instrument
from app.models.signal import EnsembleSignal
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
            "position_size_pct": float
        }
        """
        df = df.copy()
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
                "position_size_pct": 0.0,
            }

        # 1. Trend
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)
        df.ta.ema(length=20, append=True)
        df.ta.macd(append=True)
        df.ta.adx(append=True)
        df.ta.supertrend(append=True)
        df.ta.psar(append=True)
        try:
            df.ta.ichimoku(append=True)
        except Exception as exc:
            logger.warning(f"Ichimoku computation failed, continuing without it: {exc}")

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

        last = df.iloc[-1]
        prev = df.iloc[-2]
        close = float(last["close"])
        high = float(last["high"])
        low = float(last["low"])
        open_ = float(last["open"])

        # Per-indicator list for the UI's "why"
        trend_score = 0.0

        # EMA/SMA Cross (Golden/Death)
        if last.get("SMA_20") and last.get("SMA_50") and not pd.isna(last["SMA_20"]) and not pd.isna(last["SMA_50"]):
            if last["SMA_20"] > last["SMA_50"] and prev["SMA_20"] <= prev["SMA_50"]:
                trend_score += 0.2
                breakdown["SMA Cross"] = 0.2
            elif last["SMA_20"] < last["SMA_50"] and prev["SMA_20"] >= prev["SMA_50"]:
                trend_score -= 0.2
                breakdown["SMA Cross"] = -0.2

        # MACD
        macdh_col = [c for c in df.columns if c.startswith("MACDh_")]
        if macdh_col:
            macdh = last[macdh_col[0]]
            prev_macdh = prev[macdh_col[0]]
            if macdh > 0 and macdh > prev_macdh:
                trend_score += 0.2
                breakdown["MACD Hist"] = 0.2
            elif macdh < 0 and macdh < prev_macdh:
                trend_score -= 0.2
                breakdown["MACD Hist"] = -0.2

        # ADX
        adx_col = [c for c in df.columns if c.startswith("ADX_")]
        dmp_col = [c for c in df.columns if c.startswith("DMP_")]
        dmn_col = [c for c in df.columns if c.startswith("DMN_")]
        if adx_col and dmp_col and dmn_col:
            if last[adx_col[0]] > 25:
                if last[dmp_col[0]] > last[dmn_col[0]]:
                    trend_score += 0.2
                    breakdown["ADX"] = 0.2
                else:
                    trend_score -= 0.2
                    breakdown["ADX"] = -0.2

        # Supertrend
        st_dir_col = [c for c in df.columns if c.startswith("SUPERTd_")]
        if st_dir_col:
            if last[st_dir_col[0]] > 0:
                trend_score += 0.2
                breakdown["Supertrend"] = 0.2
            else:
                trend_score -= 0.2
                breakdown["Supertrend"] = -0.2

        # PSAR
        [c for c in df.columns if c.startswith("PSARr_")] # reversal col
        psar_long_col = [c for c in df.columns if c.startswith("PSARl_")]
        if psar_long_col and not pd.isna(last[psar_long_col[0]]):
            trend_score += 0.2
            breakdown["PSAR"] = 0.2
        else:
            psar_short_col = [c for c in df.columns if c.startswith("PSARs_")]
            if psar_short_col and not pd.isna(last[psar_short_col[0]]):
                trend_score -= 0.2
                breakdown["PSAR"] = -0.2

        trend_score = max(-1.0, min(1.0, trend_score))

        mom_score = 0.0
        rsi_col = [c for c in df.columns if c.startswith("RSI_")]
        if rsi_col:
            rsi = last[rsi_col[0]]
            if rsi < 30:
                mom_score += 0.3
                breakdown["RSI"] = 0.3
            elif rsi > 70:
                mom_score -= 0.3
                breakdown["RSI"] = -0.3

        stochk_col = [c for c in df.columns if c.startswith("STOCHk_")]
        stochd_col = [c for c in df.columns if c.startswith("STOCHd_")]
        if stochk_col and stochd_col:
            if last[stochk_col[0]] < 20 and last[stochd_col[0]] < 20:
                mom_score += 0.2
                breakdown["Stochastic"] = 0.2
            elif last[stochk_col[0]] > 80 and last[stochd_col[0]] > 80:
                mom_score -= 0.2
                breakdown["Stochastic"] = -0.2

        roc_col = [c for c in df.columns if c.startswith("ROC_")]
        if roc_col:
            if last[roc_col[0]] > 0:
                mom_score += 0.2
                breakdown["ROC"] = 0.2
            else:
                mom_score -= 0.2
                breakdown["ROC"] = -0.2

        cci_col = [c for c in df.columns if c.startswith("CCI_")]
        if cci_col:
            if last[cci_col[0]] > 100:
                mom_score += 0.15
                breakdown["CCI"] = 0.15
            elif last[cci_col[0]] < -100:
                mom_score -= 0.15
                breakdown["CCI"] = -0.15

        willr_col = [c for c in df.columns if c.startswith("WILLR_")]
        if willr_col:
            if last[willr_col[0]] < -80:
                mom_score += 0.15
                breakdown["Williams %R"] = 0.15
            elif last[willr_col[0]] > -20:
                mom_score -= 0.15
                breakdown["Williams %R"] = -0.15

        mom_score = max(-1.0, min(1.0, mom_score))

        vol_score = 0.0
        bbp_col = [c for c in df.columns if c.startswith("BBP_")]
        bbb_col = [c for c in df.columns if c.startswith("BBB_")]
        if bbp_col and bbb_col:
            if last[bbp_col[0]] < 0.05:
                vol_score += 0.3
                breakdown["Bollinger Breakout"] = 0.3
            elif last[bbp_col[0]] > 0.95:
                vol_score -= 0.3
                breakdown["Bollinger Breakout"] = -0.3
            if last[bbb_col[0]] < 5:
                breakdown["Bollinger Squeeze"] = 0.1

        kcu_col = [c for c in df.columns if c.startswith("KCU_")]
        kcl_col = [c for c in df.columns if c.startswith("KCL_")]
        if kcu_col and kcl_col:
            if close > last[kcu_col[0]]:
                vol_score += 0.2
                breakdown["Keltner Breakout"] = 0.2
            elif close < last[kcl_col[0]]:
                vol_score -= 0.2
                breakdown["Keltner Breakout"] = -0.2

        dcu_col = [c for c in df.columns if c.startswith("DCU_")]
        dcl_col = [c for c in df.columns if c.startswith("DCL_")]
        if dcu_col and dcl_col:
            if close >= last[dcu_col[0]]:
                vol_score += 0.2
                breakdown["Donchian Breakout"] = 0.2
            elif close <= last[dcl_col[0]]:
                vol_score -= 0.2
                breakdown["Donchian Breakout"] = -0.2

        vol_score = max(-1.0, min(1.0, vol_score))

        volu_score = 0.0
        obv_col = [c for c in df.columns if c.startswith("OBV")]
        if obv_col:
            obv_series = df[obv_col[0]]
            obv_slope = (obv_series.iloc[-1] - obv_series.iloc[-5]) / (abs(obv_series.iloc[-5]) + 1)
            if obv_slope > 0:
                volu_score += 0.3
                breakdown["OBV"] = 0.3
            else:
                volu_score -= 0.3
                breakdown["OBV"] = -0.3

        vwap_col = [c for c in df.columns if c.startswith("VWAP")]
        if vwap_col:
            if close > last[vwap_col[0]]:
                volu_score += 0.2
                breakdown["VWAP"] = 0.2
            else:
                volu_score -= 0.2
                breakdown["VWAP"] = -0.2

        mfi_col = [c for c in df.columns if c.startswith("MFI_")]
        if mfi_col:
            if last[mfi_col[0]] < 20:
                volu_score += 0.2
                breakdown["MFI"] = 0.2
            elif last[mfi_col[0]] > 80:
                volu_score -= 0.2
                breakdown["MFI"] = -0.2

        # Volume Spike Z-score
        volume = df["volume"]
        vol_mean = volume.rolling(20).mean()
        vol_std = volume.rolling(20).std()
        z_score = (volume - vol_mean) / (vol_std + 1e-9)
        last_z = z_score.iloc[-1]

        if last_z > 2.0:
            if close > open_:
                volu_score += 0.3
                breakdown["Volume Spike"] = 0.3
            else:
                volu_score -= 0.3
                breakdown["Volume Spike"] = -0.3

        volu_score = max(-1.0, min(1.0, volu_score))

        struct_score = 0.0

        # Gap detection
        if low > prev["high"]:
            struct_score += 0.2
            breakdown["Gap Up"] = 0.2
        elif high < prev["low"]:
            struct_score -= 0.2
            breakdown["Gap Down"] = -0.2

        # 52-week High/Low proximity
        high_252 = df["high"].rolling(252).max().iloc[-1]
        low_252 = df["low"].rolling(252).min().iloc[-1]

        if not pd.isna(high_252) and high_252 > 0:
            if close >= high_252 * 0.98:
                struct_score += 0.3
                breakdown["52W High"] = 0.3
            elif close <= low_252 * 1.02:
                struct_score -= 0.3
                breakdown["52W Low"] = -0.3

        # Pivots Support/Resistance (Simple Rolling)
        roll_high = df["high"].rolling(20).max().iloc[-2]
        roll_low = df["low"].rolling(20).min().iloc[-2]
        if close > roll_high:
            struct_score += 0.2
            breakdown["Resistance Breakout"] = 0.2
        elif close < roll_low:
            struct_score -= 0.2
            breakdown["Support Breakdown"] = -0.2

        pat = get_pattern_score(df)
        if pat["pattern_score"] != 0:
            struct_score += pat["pattern_score"]
            breakdown["Candlestick Pattern"] = pat["pattern_score"]

        struct_score = max(-1.0, min(1.0, struct_score))

        # Composite (Trend: 30%, Mom: 20%, Vol: 15%, Volu: 15%, Struct: 20%)
        composite_score = (
            trend_score * 0.30
            + mom_score * 0.20
            + vol_score * 0.15
            + volu_score * 0.15
            + struct_score * 0.20
        )

        confidence = min(1.0, abs(composite_score) * 1.5)

        if composite_score >= 0.40:
            direction = "STRONG_BUY"
        elif composite_score >= 0.15:
            direction = "BUY"
        elif composite_score <= -0.40:
            direction = "STRONG_SELL"
        elif composite_score <= -0.15:
            direction = "SELL"
        else:
            direction = "NEUTRAL"

        # Risk Targets & Position Sizing
        atr_val = 0.0
        atr_col = [c for c in df.columns if c.startswith("ATRr_")]
        if atr_col:
            atr_val = last[atr_col[0]]

        if pd.isna(atr_val) or atr_val == 0:
            atr_val = close * 0.02

        if direction in ["BUY", "STRONG_BUY"]:
            stop_loss = close - (atr_val * 1.5)
            take_profit = close + (atr_val * 3.0)
        elif direction in ["SELL", "STRONG_SELL"]:
            stop_loss = close + (atr_val * 1.5)
            take_profit = close - (atr_val * 3.0)
        else:
            stop_loss = 0.0
            take_profit = 0.0

        # Position size from account risk %
        # Standard risk equation: position_size = account_risk / trade_risk
        # We output a position size percentage (0-100% of portfolio) assuming 1% portfolio risk.
        position_size_pct = 0.0
        if stop_loss > 0 and direction != "NEUTRAL":
            trade_risk_pct = abs(close - stop_loss) / close
            if trade_risk_pct > 0:
                # 1% max portfolio risk
                position_size_pct = min(100.0, (1.0 / trade_risk_pct))

        return {
            "direction": direction,
            "confidence": float(confidence),
            "score": float(composite_score),
            "breakdown": breakdown,
            "patterns": pat["patterns_detected"],
            "stop_loss": float(stop_loss),
            "take_profit": float(take_profit),
            "position_size_pct": float(position_size_pct),
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
        stmt = select(Instrument).where(Instrument.symbol == symbol_ticker.upper())
        res = await db.execute(stmt)
        symbol = res.scalar_one_or_none()
        if not symbol:
            logger.warning(
                f"Instrument {symbol_ticker} not found in database, skipping signal generation."
            )
            return None

        direction = prediction.get("direction", "NEUTRAL")
        confidence = float(prediction.get("confidence", 0.5))
        raw_ensemble = float(prediction.get("raw_ensemble", 0.0))
        regime = prediction.get("regime", {})
        regime_name = regime.get("regime", "SIDEWAYS")
        conditional_vol = regime.get("conditional_vol", 0.02)

        target_price_5d = float(prediction.get("target_price_5d", 0.0))
        stop_loss = float(prediction.get("stop_loss", 0.0))
        float(prediction.get("take_profit", 0.0))
        kelly = float(prediction.get("kelly", 0.0))

        technical = prediction.get("technical", {})
        current_price = float(
            technical.get("last_close") or prediction.get("current_price") or stop_loss
        )
        if current_price <= 0:
            current_price = stop_loss

        if confidence < 0.65:
            logger.info(
                f"Signal rejected for {symbol_ticker}: Confidence {confidence:.2%} is below 65% threshold."
            )
            return None

        if direction in ("BUY", "STRONG_BUY") and regime_name in ("BEAR", "CRISIS"):
            logger.info(
                f"Signal rejected for {symbol_ticker}: BUY direction is incompatible with HMM regime {regime_name}."
            )
            return None

        if direction in ("SELL", "STRONG_SELL") and regime_name == "BULL":
            logger.info(
                f"Signal rejected for {symbol_ticker}: SELL direction is incompatible with HMM regime {regime_name}."
            )
            return None

        trades_abs = np.array([[1.0]])
        prices = np.array([[current_price]])
        adv = np.array([[10000000.0]])
        realized_vol = np.array([[conditional_vol]])

        from research.backtesting.cost_model import compute_indian_costs
        cost_arr = compute_indian_costs(trades_abs, prices, adv, realized_vol)
        single_trip_cost = float(cost_arr[0][0])
        round_trip_cost = single_trip_cost * 2.0

        expected_gain = abs(target_price_5d - current_price)
        if expected_gain < (3.0 * round_trip_cost):
            logger.info(
                f"Signal rejected for {symbol_ticker}: Expected gain (₹{expected_gain:.2f}) "
                f"does not exceed 3x round-trip cost (₹{3.0 * round_trip_cost:.2f})."
            )
            return None

        regime_map = {
            "bull": 0,
            "bear": 1,
            "sideways": 2,
            "crisis": 3,
            "BULL": 0,
            "BEAR": 1,
            "SIDEWAYS": 2,
            "CRISIS": 3,
        }
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
        logger.info(
            f"Generated new EnsembleSignal for {symbol_ticker}: {direction} @ {confidence:.2%} confidence."
        )
        return ensemble_signal
