"""Model retraining Celery tasks."""

from __future__ import annotations

import logging
import os
import pickle
from pathlib import Path
import numpy as np
import pandas as pd
import pandas_ta as ta
from celery import shared_task
import xgboost as xgb
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent.parent / "data" / "models"
SYMBOLS = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"]

def train_single_xgboost(symbol: str) -> None:
    """Train XGBoost classifier for a single stock and save to disk."""
    import yfinance as yf
    from research.feature_engineering.price_factors import PriceFactorsBuilder
    from research.feature_engineering.volatility_factors import VolatilityFactorsBuilder

    logger.info(f"Training scheduled XGBoost model for {symbol}...")
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="2y", interval="1d")
    if df.empty or len(df) < 100:
        logger.warning(f"Insufficient history to train XGBoost for {symbol}")
        return

    df.columns = [c.lower() for c in df.columns]
    df = df.rename(columns={"stock splits": "stock_splits", "capital gains": "capital_gains"})
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    df = df.reset_index().rename(columns={"Date": "time", "Datetime": "time"})
    df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)
    df.index = pd.DatetimeIndex(df["time"])
    df.index.name = None

    # Compute features
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

    # Standardize column names
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

    features = [
        "ret_1d", "ret_5d", "ret_21d", "momentum_63d",
        "RSI_14", "MACDh_12_26_9", "BBP_20_2.0", "ATRr_14",
        "ADX_14", "realized_vol_21d", "yang_zhang_vol_21d",
        "dist_52w_high", "dist_52w_low", "drawdown",
        "range_pct", "close_to_open"
    ]

    df["target_5d"] = (df["close"].shift(-5) / df["close"] - 1.0)
    df["label"] = (df["target_5d"] > 0).astype(int)

    X_train = df[features].iloc[:-6].dropna()
    y_train = df["label"].loc[X_train.index]

    if len(X_train) < 30:
        return

    from research.models.xgboost_model import XGBoostDirectionalClassifier
    
    classifier = XGBoostDirectionalClassifier()
    classifier.fit(X_train, y_train)

    # Save scaler and classifier
    os.makedirs(MODEL_DIR, exist_ok=True)
    checkpoint_path = MODEL_DIR / f"xgboost_{symbol.upper()}.pkl"
    with open(checkpoint_path, "wb") as f:
        pickle.dump({"scaler": classifier.scaler, "model": classifier.model}, f)
    logger.info(f"XGBoost model saved for {symbol} to {checkpoint_path}")

@shared_task(name="tasks.training_tasks.retrain_model")
def retrain_model(model_name: str) -> dict[str, str]:
    """Retrain one model family."""
    if model_name.lower() == "xgboost":
        for symbol in SYMBOLS:
            try:
                train_single_xgboost(symbol)
            except Exception as e:
                logger.error(f"Failed to retrain XGBoost for {symbol}: {e}")
        return {"status": "ok", "model": "xgboost"}
    
    elif model_name.lower() == "meta_learner":
        from research.models.ensemble.meta_learner import EnsembleMetaLearner
        try:
            learner = EnsembleMetaLearner()
            X, y = learner.prepare_training_data(SYMBOLS)
            if not X.empty:
                learner.train(X, y)
                learner.save()
                return {"status": "ok", "model": "meta_learner"}
        except Exception as e:
            logger.error(f"Failed to retrain meta-learner: {e}")
            return {"status": "error", "message": str(e)}

    elif model_name.lower() == "lstm_attention":
        from research.models.lstm_attention import LSTMAttentionClassifier
        import yfinance as yf
        for symbol in SYMBOLS:
            try:
                logger.info(f"Retraining LSTM with Attention for {symbol}...")
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
                
                from research.feature_engineering.price_factors import PriceFactorsBuilder
                from research.feature_engineering.volatility_factors import VolatilityFactorsBuilder
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
                
                # Standardize column names
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
                    
                df = df.replace([np.inf, -np.inf], np.nan).dropna()
                
                df["target_5d"] = (df["close"].shift(-5) / df["close"] - 1.0)
                df["label"] = (df["target_5d"] > 0).astype(int)
                
                clf = LSTMAttentionClassifier()
                clf.fit(df, df["label"])
                checkpoint_path = MODEL_DIR / f"lstm_attention_{symbol.upper()}.pkl"
                clf.save(checkpoint_path)
                logger.info(f"LSTM with Attention model saved for {symbol} to {checkpoint_path}")
            except Exception as e:
                logger.error(f"Failed to retrain LSTM for {symbol}: {e}")
        return {"status": "ok", "model": "lstm_attention"}
        
    elif model_name.lower() == "quantile_forecaster":
        from research.models.tft.quantile_forecaster import QuantileLGBForecaster
        try:
            forecaster = QuantileLGBForecaster()
            X, y = forecaster.prepare_training_data(SYMBOLS)
            if not X.empty:
                forecaster.train(X, y)
                forecaster.save()
                return {"status": "ok", "model": "quantile_forecaster"}
        except Exception as e:
            logger.error(f"Failed to retrain quantile forecaster: {e}")
            return {"status": "error", "message": str(e)}

    elif model_name.lower() == "online_learner":
        from research.models.online_learner import OnlineAdaptiveLearner
        import yfinance as yf
        for symbol in SYMBOLS:
            try:
                logger.info(f"Retraining Online Adaptive Learner for {symbol}...")
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
                
                from research.feature_engineering.price_factors import PriceFactorsBuilder
                from research.feature_engineering.volatility_factors import VolatilityFactorsBuilder
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
                
                # Standardize column names
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
                    
                df = df.replace([np.inf, -np.inf], np.nan).dropna()
                
                df["target_5d"] = (df["close"].shift(-5) / df["close"] - 1.0)
                df["label"] = (df["target_5d"] > 0).astype(int)
                
                # Fit online learner incrementally row-by-row
                learner = OnlineAdaptiveLearner()
                df_clean = df.iloc[:-5].dropna()
                for idx in range(len(df_clean)):
                    row = df_clean.iloc[idx]
                    x_dict = {feat: float(row[feat]) for feat in learner.features if feat in df_clean.columns}
                    y = int(row["label"])
                    learner.update(x_dict, y)
                
                checkpoint_path = MODEL_DIR / f"online_learner_{symbol.upper()}.pkl"
                learner.save(checkpoint_path)
                logger.info(f"Online learner saved for {symbol} to {checkpoint_path}")
            except Exception as e:
                logger.error(f"Failed to retrain Online Learner for {symbol}: {e}")
        return {"status": "ok", "model": "online_learner"}

    return {"status": "unknown_model", "model": model_name}
