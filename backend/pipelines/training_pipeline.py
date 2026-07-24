"""End-to-end model training pipeline orchestration."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

import pandas as pd
import yfinance as yf

from research.feature_engineering.pipeline import FeaturePipeline
from research.models.hmm_garch.trainer import HMMGarchTrainer
from research.models.lstm_attention.classifier import LSTMAttentionClassifier
from research.models.tft.quantile_forecaster import QuantileLGBForecaster
from research.models.xgboost_model.classifier import XGBoostDirectionalClassifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent.parent / "data" / "models"


def fetch_data_for_training(symbol: str) -> pd.DataFrame:
    """Fetch 2-3 years of data and run the feature engineering pipeline."""
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="3y", interval="1d")
    if df.empty or len(df) < 100:
        logger.warning(f"Insufficient data for {symbol}")
        return pd.DataFrame()

    df.columns = [c.lower() for c in df.columns]
    df = df.rename(columns={"stock splits": "stock_splits", "capital gains": "capital_gains"})
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    df = df.reset_index().rename(columns={"Date": "time", "Datetime": "time"})
    df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)
    df.index = pd.DatetimeIndex(df["time"])
    df.index.name = None

    # Run the core FeaturePipeline (Price, Volatility)
    df = FeaturePipeline().run(df)

    # Add Technical Indicators
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

    # Deduplicate
    df = df.loc[:, ~df.columns.duplicated()]

    # Standardize names for classifiers
    rename_map = {}
    RSI_col = "RSI_14" if "RSI_14" in df.columns else [c for c in df.columns if "RSI" in c][0]
    MACDh_col = (
        "MACDh_12_26_9"
        if "MACDh_12_26_9" in df.columns
        else [c for c in df.columns if "MACDh" in c][0]
    )
    BBP_col = (
        "BBP_20_2.0_2.0"
        if "BBP_20_2.0_2.0" in df.columns
        else (
            "BBP_20_2.0" if "BBP_20_2.0" in df.columns else [c for c in df.columns if "BBP" in c][0]
        )
    )
    ATR_col = "ATRr_14" if "ATRr_14" in df.columns else [c for c in df.columns if "ATR" in c][0]
    ADX_col = "ADX_14" if "ADX_14" in df.columns else [c for c in df.columns if "ADX" in c][0]

    if RSI_col != "RSI_14":
        rename_map[RSI_col] = "RSI_14"
    if MACDh_col != "MACDh_12_26_9":
        rename_map[MACDh_col] = "MACDh_12_26_9"
    if BBP_col != "BBP_20_2.0":
        rename_map[BBP_col] = "BBP_20_2.0"
    if ATR_col != "ATRr_14":
        rename_map[ATR_col] = "ATRr_14"
    if ADX_col != "ADX_14":
        rename_map[ADX_col] = "ADX_14"

    if rename_map:
        df = df.rename(columns=rename_map)

    return df


def train_models_for_symbol(symbol: str) -> None:
    logger.info(f"--- Training models for {symbol} ---")
    df = fetch_data_for_training(symbol)
    if df.empty:
        return

    # Generate labels: 1 if 5-day return > 0, else 0
    df["target_5d_ret"] = (df["close"].shift(-5) / df["close"]) - 1.0
    y = (df["target_5d_ret"] > 0).astype(int)

    # 1. XGBoost
    logger.info(f"[{symbol}] Training XGBoost...")
    xgb_clf = XGBoostDirectionalClassifier()
    try:
        xgb_clf.fit(df, y)
        xgb_clf.save(MODEL_DIR / f"xgboost_{symbol}.pkl")
        logger.info(f"[{symbol}] XGBoost saved.")
    except Exception as e:
        logger.error(f"[{symbol}] XGBoost training failed: {e}")

    # 2. LSTM Attention
    logger.info(f"[{symbol}] Training LSTM Attention...")
    lstm_clf = LSTMAttentionClassifier()
    try:
        lstm_clf.fit(df, y)
        lstm_clf.save(MODEL_DIR / f"lstm_attention_{symbol}.pkl")
        logger.info(f"[{symbol}] LSTM Attention saved.")
    except Exception as e:
        logger.error(f"[{symbol}] LSTM training failed: {e}")

    # 3. HMM-GARCH
    logger.info(f"[{symbol}] Training HMM-GARCH...")
    returns = df["close"].pct_change().dropna().values
    hmm_trainer = HMMGarchTrainer(checkpoint_dir=MODEL_DIR / "hmm_garch")
    try:
        hmm_trainer.train(returns, symbol)
        logger.info(f"[{symbol}] HMM-GARCH saved.")
    except Exception as e:
        logger.error(f"[{symbol}] HMM-GARCH training failed: {e}")


def train_global_models(symbols: list[str]) -> None:
    logger.info("--- Training Global TFT/QuantileLGB Model ---")
    tft_clf = QuantileLGBForecaster()
    X, y = tft_clf.prepare_training_data(symbols)
    if X.empty:
        logger.warning("No data for TFT training.")
        return
    tft_clf.train(X, y)
    tft_clf.save()


def run_training_pipeline(symbols: list[str]) -> None:
    os.makedirs(MODEL_DIR, exist_ok=True)

    # Train per-symbol models
    for sym in symbols:
        train_models_for_symbol(sym)

    # Train cross-sectional models
    train_global_models(symbols)

    logger.info("Training pipeline complete!")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["AAPL", "MSFT", "RELIANCE.NS"],
        help="List of symbols to train on",
    )
    args = parser.parse_args()

    symbols = [s.upper() for s in args.symbols]
    run_training_pipeline(symbols)


if __name__ == "__main__":
    main()
