"""Quantile LightGBM Forecaster — CPU-cheap sequence model replacement for TFT/LSTM-Attn.
Produces real P10, P50, and P90 return forecasts.
"""

from __future__ import annotations

import os
import pickle
import logging
import numpy as np
import pandas as pd
import pandas_ta as ta
from typing import Dict, List, Tuple, Any
from pathlib import Path
import lightgbm as lgb

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent.parent.parent.parent / "data" / "models"

class QuantileLGBForecaster:
    """Multi-quantile LightGBM regressor for predicting multi-horizon returns."""

    def __init__(self):
        self.quantiles = [0.1, 0.5, 0.9]
        self.models: Dict[float, lgb.LGBMRegressor] = {}
        self.features = [
            "ret_1d", "ret_5d", "ret_21d", "momentum_63d",
            "RSI_14", "MACDh_12_26_9", "BBP_20_2.0", "ATRr_14",
            "ADX_14", "realized_vol_21d", "yang_zhang_vol_21d",
            "dist_52w_high", "dist_52w_low", "drawdown",
            "range_pct", "close_to_open"
        ]

    def save(self) -> None:
        """Save models to disk."""
        os.makedirs(MODEL_DIR, exist_ok=True)
        for q, model in self.models.items():
            path = MODEL_DIR / f"quantile_lgb_q{int(q*100)}.pkl"
            with open(path, "wb") as f:
                pickle.dump(model, f)
        logger.info(f"QuantileLGBForecaster models saved to {MODEL_DIR}")

    @classmethod
    def load(cls) -> QuantileLGBForecaster:
        """Load models from disk."""
        forecaster = cls()
        loaded = 0
        for q in forecaster.quantiles:
            path = MODEL_DIR / f"quantile_lgb_q{int(q*100)}.pkl"
            if os.path.exists(path):
                with open(path, "rb") as f:
                    forecaster.models[q] = pickle.load(f)
                loaded += 1
        if loaded == len(forecaster.quantiles):
            logger.info("QuantileLGBForecaster models loaded successfully.")
        else:
            logger.warning("Some or all quantile models were missing. Need training.")
        return forecaster

    def prepare_training_data(self, symbols: List[str]) -> Tuple[pd.DataFrame, pd.Series]:
        """Collect historical stacked features and 5d forward return targets across symbols."""
        import yfinance as yf
        from research.feature_engineering.price_factors import PriceFactorsBuilder
        from research.feature_engineering.volatility_factors import VolatilityFactorsBuilder

        X_list = []
        y_list = []

        for symbol in symbols:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="2y", interval="1d")
            if df.empty or len(df) < 100:
                continue

            df.columns = [c.lower() for c in df.columns]
            df = df.rename(columns={"stock splits": "stock_splits", "capital gains": "capital_gains"})
            df = df[["open", "high", "low", "close", "volume"]].dropna()
            df = df.reset_index().rename(columns={"Date": "time", "Datetime": "time"})
            df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)
            df.index = pd.DatetimeIndex(df["time"])
            df.index.name = None

            # Add features
            df = PriceFactorsBuilder().transform(df)
            df = VolatilityFactorsBuilder().transform(df)

            df.ta.rsi(length=14, append=True)
            df.ta.macd(fast=12, slow=26, signal=9, append=True)
            df.ta.ema(length=9, append=True)
            df.ta.ema(length=21, append=True)
            df.ta.ema(length=50, append=True)
            df.ta.ema(length=200, append=True)
            df.ta.bbands(length=20, std=2, append=True)
            df.ta.atr(length=14, append=True)
            df.ta.vwap(append=True)
            df.ta.adx(length=14, append=True)
            df.ta.stoch(k=14, d=3, append=True)
            df.ta.obv(append=True)
            df.ta.supertrend(length=10, multiplier=3.0, append=True)
            df.ta.cdl_pattern(name="all", append=True)

            cols_to_drop = [c for c in df.columns if "SUPERTl" in c or "SUPERTs" in c]
            df = df.drop(columns=cols_to_drop, errors="ignore")
            df = df.replace([np.inf, -np.inf], np.nan).dropna()

            # Target: 5-day forward return
            df["target_5d"] = (df["close"].shift(-5) / df["close"]) - 1.0
            
            # Standardize columns to match self.features
            rename_map = {}
            RSI_col = "RSI_14" if "RSI_14" in df.columns else [c for c in df.columns if "RSI" in c][0]
            MACDh_col = "MACDh_12_26_9" if "MACDh_12_26_9" in df.columns else [c for c in df.columns if "MACDh" in c][0]
            BBP_col = "BBP_20_2.0_2.0" if "BBP_20_2.0_2.0" in df.columns else ("BBP_20_2.0" if "BBP_20_2.0" in df.columns else [c for c in df.columns if "BBP" in c][0])
            ATR_col = "ATRr_14" if "ATRr_14" in df.columns else [c for c in df.columns if "ATR" in c][0]
            ADX_col = "ADX_14" if "ADX_14" in df.columns else [c for c in df.columns if "ADX" in c][0]
            
            if RSI_col != "RSI_14": rename_map[RSI_col] = "RSI_14"
            if MACDh_col != "MACDh_12_26_9": rename_map[MACDh_col] = "MACDh_12_26_9"
            if BBP_col != "BBP_20_2.0": rename_map[BBP_col] = "BBP_20_2.0"
            if ATR_col != "ATRr_14": rename_map[ATR_col] = "ATRr_14"
            if ADX_col != "ADX_14": rename_map[ADX_col] = "ADX_14"
            
            if rename_map:
                df = df.rename(columns=rename_map)

            # Drop final NaN rows where target_5d is not defined (last 5 rows)
            df_subset = df[self.features + ["target_5d"]].dropna()

            X_list.append(df_subset[self.features])
            y_list.append(df_subset["target_5d"])

        if not X_list:
            return pd.DataFrame(columns=self.features), pd.Series(dtype=float)

        return pd.concat(X_list, ignore_index=True), pd.concat(y_list, ignore_index=True)

    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        """Fit LightGBM models for quantiles 0.1, 0.5, and 0.9."""
        if X.empty:
            logger.warning("Empty features. Skipping training.")
            return

        for q in self.quantiles:
            logger.info(f"Training LightGBM regressor for quantile={q}...")
            model = lgb.LGBMRegressor(
                objective="quantile",
                alpha=q,
                n_estimators=100,
                max_depth=4,
                learning_rate=0.05,
                random_state=42,
                verbose=-1
            )
            model.fit(X, y)
            self.models[q] = model

    def predict(self, features: Dict[str, float]) -> Tuple[float, float, float]:
        """Predict P10, P50, and P90 returns for a single feature vector.
        
        Args:
            features: Dict containing the standard indicators for the stock.
            
        Returns:
            Tuple of (p10_return, p50_return, p90_return)
        """
        # Build single row dataframe
        row = pd.DataFrame([features], columns=self.features)
        
        preds = {}
        for q in self.quantiles:
            model = self.models.get(q)
            if model is not None:
                preds[q] = float(model.predict(row)[0])
            else:
                # Fallbacks if model not fitted
                if q == 0.1:
                    preds[q] = -0.015
                elif q == 0.5:
                    preds[q] = 0.002
                else:
                    preds[q] = 0.015

        # Enforce monotonic constraint (p10 <= p50 <= p90)
        p10 = preds[0.1]
        p50 = max(p10, preds[0.5])
        p90 = max(p50, preds[0.9])
        
        return p10, p50, p90
