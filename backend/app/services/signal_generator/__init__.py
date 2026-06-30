"""Trading signal generator service.

Implements all 5 quantitative strategies:
1. Mean Reversion (Pairs Trading & Z-Score)
2. Momentum + Trend Following (EMA Crossover + ADX)
3. Volatility Breakout (Bollinger Bands + ATR)
4. ML Signal-Based Alpha (Ensemble Model)
5. Statistical Arbitrage (Pairs Spread Cointegration)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import pandas_ta as ta
import statsmodels.tsa.stattools as ts

from research.backtesting.engine import run_vectorized_backtest

logger = logging.getLogger(__name__)


class MeanReversionStrategy:
    """Mean Reversion Strategy based on rolling close price z-score."""

    def __init__(self, window: int = 20, entry_z: float = 2.0):
        self.window = window
        self.entry_z = entry_z

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        if len(df) < self.window:
            return pd.Series(0.0, index=df.index)
        
        close = df["close"].astype(float)
        rolling_mean = close.rolling(self.window).mean()
        rolling_std = close.rolling(self.window).std().replace(0, 1e-6)
        
        z_score = (close - rolling_mean) / rolling_std
        
        signals = pd.Series(0.0, index=df.index)
        signals[z_score < -self.entry_z] = 1.0  # Buy oversold
        signals[z_score > self.entry_z] = -1.0  # Short overbought
        return signals


class MomentumTrendStrategy:
    """Momentum + Trend Following Strategy using EMA stack and ADX filter."""

    def __init__(self, fast: int = 9, medium: int = 21, slow: int = 50, trend_strength: float = 25.0):
        self.fast = fast
        self.medium = medium
        self.slow = slow
        self.trend_strength = trend_strength

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        if len(df) < self.slow:
            return pd.Series(0.0, index=df.index)
            
        close = df["close"].astype(float)
        
        ema_fast = ta.ema(close, length=self.fast)
        ema_med = ta.ema(close, length=self.medium)
        ema_slow = ta.ema(close, length=self.slow)
        
        # Safely compute ADX
        adx_df = ta.adx(df["high"], df["low"], df["close"], length=14)
        if adx_df is not None and not adx_df.empty:
            adx = adx_df.iloc[:, 0]
        else:
            adx = pd.Series(30.0, index=df.index)  # Default to trending if failed

        signals = pd.Series(0.0, index=df.index)
        
        # Bullish condition
        bullish = (ema_fast > ema_med) & (ema_med > ema_slow) & (adx > self.trend_strength)
        # Bearish condition
        bearish = (ema_fast < ema_med) & (ema_med < ema_slow) & (adx > self.trend_strength)
        
        signals[bullish] = 1.0
        signals[bearish] = -1.0
        return signals


class VolatilityBreakoutStrategy:
    """Volatility Breakout Strategy using Bollinger Bands and ATR channels."""

    def __init__(self, bb_window: int = 20, bb_std: float = 2.0, atr_window: int = 14, multiplier: float = 1.5):
        self.bb_window = bb_window
        self.bb_std = bb_std
        self.atr_window = atr_window
        self.multiplier = multiplier

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        if len(df) < max(self.bb_window, self.atr_window):
            return pd.Series(0.0, index=df.index)
            
        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        
        # Bollinger Bands
        bb_ma = close.rolling(self.bb_window).mean()
        bb_std_val = close.rolling(self.bb_window).std()
        upper_bb = bb_ma + self.bb_std * bb_std_val
        lower_bb = bb_ma - self.bb_std * bb_std_val
        
        # ATR Channel Breakout
        atr = ta.atr(high, low, close, length=self.atr_window)
        if atr is None:
            atr = (high - low).rolling(self.atr_window).mean()
            
        atr_upper = bb_ma + self.multiplier * atr
        atr_lower = bb_ma - self.multiplier * atr

        signals = pd.Series(0.0, index=df.index)
        
        breakout_up = (close > upper_bb) & (close > atr_upper)
        breakout_down = (close < lower_bb) & (close < atr_lower)
        
        signals[breakout_up] = 1.0
        signals[breakout_down] = -1.0
        return signals


class MLSignalAlphaStrategy:
    """ML Signal-Based Alpha Strategy based on 7-layer ensemble predictions."""

    def __init__(self, threshold: float = 0.15):
        self.threshold = threshold

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        # Since we require live predictions, we can use the XGBoost score or dynamic weights
        # For historical series, we'll look for 'xgb_score' or approximate from features
        signals = pd.Series(0.0, index=df.index)
        if "xgb_score" in df.columns:
            xgb_score = df["xgb_score"].astype(float)
            signals[xgb_score > self.threshold] = 1.0
            signals[xgb_score < -self.threshold] = -1.0
        else:
            # Fallback to momentum features if not present in input frame
            ret_5d = np.log(df["close"] / df["close"].shift(5)).fillna(0.0)
            signals[ret_5d > 0.02] = 1.0
            signals[ret_5d < -0.02] = -1.0
        return signals


class StatisticalArbitrageStrategy:
    """Statistical Arbitrage Strategy using cointegrated pairs spread."""

    def __init__(self, window: int = 60, entry_z: float = 2.0):
        self.window = window
        self.entry_z = entry_z
        self.is_active = False

    def generate_signals_pair(self, df_a: pd.DataFrame, df_b: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """Generate long/short signals for a pair of cointegrated assets."""
        if len(df_a) < self.window or len(df_b) < self.window:
            return pd.Series(0.0, index=df_a.index), pd.Series(0.0, index=df_b.index)

        # Align series by index
        combined = pd.DataFrame({"a": df_a["close"], "b": df_b["close"]}).ffill().dropna()
        if len(combined) < self.window:
            return pd.Series(0.0, index=df_a.index), pd.Series(0.0, index=df_b.index)

        close_a = combined["a"].astype(float)
        close_b = combined["b"].astype(float)

        # Run Engle-Granger cointegration test on historical window
        try:
            score, pvalue, _ = ts.coint(close_a.iloc[-self.window:], close_b.iloc[-self.window:])
            self.is_active = pvalue < 0.05
        except Exception:
            self.is_active = False

        if not self.is_active:
            # Pair is not cointegrated, return zero signals
            return pd.Series(0.0, index=df_a.index), pd.Series(0.0, index=df_b.index)

        # Compute rolling spread and z-score
        # spread = a - beta * b
        # For simplicity, we use the price ratio spread: a/b
        ratio = close_a / close_b
        mean_ratio = ratio.rolling(self.window).mean()
        std_ratio = ratio.rolling(self.window).std().replace(0, 1e-6)
        z_ratio = (ratio - mean_ratio) / std_ratio

        signals_a = pd.Series(0.0, index=df_a.index)
        signals_b = pd.Series(0.0, index=df_b.index)

        # Ratio high -> Asset A overvalued, Short A and Long B
        signals_a[z_ratio > self.entry_z] = -1.0
        signals_b[z_ratio > self.entry_z] = 1.0

        # Ratio low -> Asset A undervalued, Long A and Short B
        signals_a[z_ratio < -self.entry_z] = 1.0
        signals_b[z_ratio < -self.entry_z] = -1.0

        return signals_a, signals_b


class SignalGeneratorService:
    """Orchestrates strategy execution, backtests them, and reports metrics."""

    def __init__(self):
        self.strategies = {
            "mean_reversion": MeanReversionStrategy(),
            "momentum_trend": MomentumTrendStrategy(),
            "volatility_breakout": VolatilityBreakoutStrategy(),
            "ml_alpha": MLSignalAlphaStrategy(),
            "statistical_arbitrage": StatisticalArbitrageStrategy(),
        }

    def run_strategy_backtest(
        self,
        strategy_name: str,
        df: pd.DataFrame,
        initial_capital: float = 100000.0,
    ) -> Dict[str, float]:
        """Runs a vectorized backtest for a strategy on historical OHLCV data."""
        if strategy_name not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        strategy = self.strategies[strategy_name]
        signals = strategy.generate_signals(df)
        
        # Setup matrix shapes (T, N) for single-asset backtest engine
        signals_mat = signals.values.reshape(-1, 1)
        prices_mat = df["close"].values.reshape(-1, 1)
        kelly_mat = np.full_like(signals_mat, 0.10) # 10% target allocation

        res = run_vectorized_backtest(
            signals=signals_mat,
            prices=prices_mat,
            kelly_fraction=kelly_mat,
            initial_capital=initial_capital
        )

        daily_rets = res.daily_returns
        sharpe = np.mean(daily_rets) / np.std(daily_rets) * np.sqrt(252) if np.std(daily_rets) > 0 else 0.0
        win_rate = float(np.mean(daily_rets > 0))
        
        # Calculate max drawdown
        equity = res.equity_curve
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        max_dd = float(np.min(drawdown))

        return {
            "sharpe": float(sharpe),
            "win_rate": float(win_rate),
            "max_drawdown": float(max_dd)
        }
