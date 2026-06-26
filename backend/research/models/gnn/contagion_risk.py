"""Contagion Risk Analyzer — CPU-cheap substitute for Graph Neural Network spillover model.
Computes rolling index correlation, rolling beta, idiosyncratic alpha, and contagion exposure.
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any
import yfinance as yf

logger = logging.getLogger(__name__)

class ContagionRiskAnalyzer:
    """Computes cross-sectional risk factors and market beta."""

    def __init__(self, index_symbol: str = "^NSEI"):
        self.index_symbol = index_symbol

    def compute_risk_factors(self, stock_df: pd.DataFrame, index_df: pd.DataFrame | None = None) -> Dict[str, float]:
        """Compute index correlation, beta, spread, alpha, and contagion score.
        
        Args:
            stock_df: DataFrame with close prices of the target stock.
            index_df: Optional index DataFrame. If None, index is downloaded.
            
        Returns:
            Dict containing correlation, beta, alpha, and contagion score.
        """
        # Ensure we have index data
        if index_df is None or index_df.empty:
            try:
                # Fetch index history matching the stock dataframe date range
                start_date = stock_df.index.min().strftime('%Y-%m-%d')
                end_date = (stock_df.index.max() + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                index_ticker = yf.Ticker(self.index_symbol)
                index_df = index_ticker.history(start=start_date, end=end_date, interval="1d")
            except Exception as e:
                logger.error(f"Failed to fetch index data for contagion risk: {e}")
                # Fallback to defaults
                return {
                    "corr_to_index": 0.5,
                    "sector_beta": 1.0,
                    "idiosyncratic_alpha": 0.0,
                    "contagion_score": 0.5,
                    "raw_signal": 0.0
                }

        if index_df.empty or len(stock_df) < 22:
            return {
                "corr_to_index": 0.5,
                "sector_beta": 1.0,
                "idiosyncratic_alpha": 0.0,
                "contagion_score": 0.5,
                "raw_signal": 0.0
            }

        # Align close prices
        stock_close = stock_df["close"].astype(float)
        index_close = index_df["Close"].astype(float)
        
        # Localize timezones if mismatch
        if stock_close.index.tz is not None:
            stock_close.index = stock_close.index.tz_localize(None)
        if index_close.index.tz is not None:
            index_close.index = index_close.index.tz_localize(None)

        combined = pd.DataFrame({"stock": stock_close, "index": index_close}).ffill().dropna()
        if len(combined) < 22:
            return {
                "corr_to_index": 0.5,
                "sector_beta": 1.0,
                "idiosyncratic_alpha": 0.0,
                "contagion_score": 0.5,
                "raw_signal": 0.0
            }

        # Compute log returns
        combined["stock_ret"] = np.log(combined["stock"] / combined["stock"].shift(1))
        combined["index_ret"] = np.log(combined["index"] / combined["index"].shift(1))
        combined = combined.dropna()

        if len(combined) < 21:
            return {
                "corr_to_index": 0.5,
                "sector_beta": 1.0,
                "idiosyncratic_alpha": 0.0,
                "contagion_score": 0.5,
                "raw_signal": 0.0
            }

        # Use last 63 trading days (approx 3 months) for beta and correlation
        subset = combined.iloc[-63:]
        stock_rets = subset["stock_ret"].values
        index_rets = subset["index_ret"].values

        # Rolling Correlation
        corr = float(np.corrcoef(stock_rets, index_rets)[0, 1])
        if np.isnan(corr):
            corr = 0.5

        # Rolling Beta (Covariance / Variance of index)
        cov = np.cov(stock_rets, index_rets)[0, 1]
        index_var = np.var(index_rets, ddof=1)
        beta = float(cov / index_var) if index_var > 0 else 1.0
        if np.isnan(beta):
            beta = 1.0

        # Idiosyncratic Alpha (Residual Return on the last day)
        # alpha_t = return_t - beta * index_return_t
        last_stock_ret = combined["stock_ret"].iloc[-1]
        last_index_ret = combined["index_ret"].iloc[-1]
        alpha = float(last_stock_ret - beta * last_index_ret)

        # Spread proxy
        spread = 0.0015  # Default free tier proxy
        if "high" in stock_df.columns and "low" in stock_df.columns:
            # Corwin-Schultz spread estimator proxy
            high_low_ratio = float((stock_df["high"].iloc[-1] - stock_df["low"].iloc[-1]) / stock_df["close"].iloc[-1])
            spread = max(0.0001, min(high_low_ratio * 0.1, 0.02))

        # Contagion score calculation
        corr_risk = abs(corr)
        contagion_score = 0.6 * corr_risk + 0.3 * min(abs(beta - 1.0), 1.0) + 0.1 * min(spread * 500, 1.0)
        
        # Raw signal combining alpha and contagion dampening
        raw_signal = float(np.tanh(alpha * 20.0) * (1.0 - 0.65 * contagion_score))

        return {
            "corr_to_index": corr,
            "sector_beta": beta,
            "idiosyncratic_alpha": alpha,
            "contagion_score": contagion_score,
            "raw_signal": raw_signal
        }
