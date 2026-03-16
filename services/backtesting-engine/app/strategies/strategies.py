"""Base strategy class and strategy implementations."""

from __future__ import annotations

import abc
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
import logging

from .event_driven_backtester import SignalEvent, EventType

logger = logging.getLogger(__name__)


class BaseStrategy(abc.ABC):
    """Abstract base class for trading strategies."""

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        self.name = name
        self.params = params or {}

    @abc.abstractmethod
    def generate_signals(self, data_handler: Any, portfolio: Any) -> List[SignalEvent]:
        """Generate trading signals."""
        pass

    @abc.abstractmethod
    def get_params(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        pass

    def optimize(self, data: pd.DataFrame, metric: str = 'sharpe') -> Dict[str, Any]:
        """Optimize strategy parameters using Optuna."""
        # Placeholder for optimization - would implement Optuna optimization
        return self.params


class KalmanFilterPairsTrading(BaseStrategy):
    """Kalman Filter Pairs Trading Strategy."""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__("Kalman Filter Pairs Trading", params)
        self.lookback = self.params.get('lookback', 60)
        self.entry_threshold = self.params.get('entry_threshold', 2.0)
        self.exit_threshold = self.params.get('exit_threshold', 0.5)
        self.stop_threshold = self.params.get('stop_threshold', 3.5)

    def generate_signals(self, data_handler: Any, portfolio: Any) -> List[SignalEvent]:
        """Generate pairs trading signals using Kalman filter."""
        signals = []

        # For simplicity, implement basic cointegration-based pairs trading
        # In production, this would use Kalman filter for time-varying hedge ratio

        symbols = data_handler.symbols
        if len(symbols) < 2:
            return signals

        # Simple pair: first two symbols
        symbol1, symbol2 = symbols[0], symbols[1]

        # Get historical data
        data1 = data_handler.get_historical_data(symbol1)
        data2 = data_handler.get_historical_data(symbol2)

        if len(data1) < self.lookback or len(data2) < self.lookback:
            return signals

        # Calculate spread using simple ratio (simplified Kalman filter)
        prices1 = data1['close'].tail(self.lookback)
        prices2 = data2['close'].tail(self.lookback)

        # Simple hedge ratio (would be Kalman filtered in production)
        hedge_ratio = np.cov(prices1, prices2)[0, 1] / np.var(prices2)

        spread = prices1 - hedge_ratio * prices2
        spread_zscore = (spread - spread.mean()) / spread.std()

        current_zscore = spread_zscore.iloc[-1]

        # Generate signals
        if abs(current_zscore) > self.stop_threshold:
            # Close existing positions
            for symbol in [symbol1, symbol2]:
                if portfolio.positions.get(symbol, 0) != 0:
                    signals.append(SignalEvent(
                        type=EventType.SIGNAL,
                        timestamp=data_handler.current_date,
                        symbol=symbol,
                        direction=0,  # Close position
                        strength=1.0,
                        strategy_name=self.name,
                        data={'reason': 'stop_loss', 'zscore': current_zscore}
                    ))

        elif abs(current_zscore) > self.entry_threshold:
            # Open positions
            direction1 = 1 if current_zscore < -self.entry_threshold else -1
            direction2 = -direction1  # Opposite direction

            signals.extend([
                SignalEvent(
                    type=EventType.SIGNAL,
                    timestamp=data_handler.current_date,
                    symbol=symbol1,
                    direction=direction1,
                    strength=abs(current_zscore) / self.entry_threshold,
                    strategy_name=self.name,
                    data={'zscore': current_zscore, 'hedge_ratio': hedge_ratio}
                ),
                SignalEvent(
                    type=EventType.SIGNAL,
                    timestamp=data_handler.current_date,
                    symbol=symbol2,
                    direction=direction2,
                    strength=abs(current_zscore) / self.entry_threshold,
                    strategy_name=self.name,
                    data={'zscore': current_zscore, 'hedge_ratio': hedge_ratio}
                )
            ])

        elif abs(current_zscore) < self.exit_threshold:
            # Close positions if any
            for symbol in [symbol1, symbol2]:
                if portfolio.positions.get(symbol, 0) != 0:
                    signals.append(SignalEvent(
                        type=EventType.SIGNAL,
                        timestamp=data_handler.current_date,
                        symbol=symbol,
                        direction=0,  # Close position
                        strength=1.0,
                        strategy_name=self.name,
                        data={'reason': 'exit', 'zscore': current_zscore}
                    ))

        return signals

    def get_params(self) -> Dict[str, Any]:
        return {
            'lookback': self.lookback,
            'entry_threshold': self.entry_threshold,
            'exit_threshold': self.exit_threshold,
            'stop_threshold': self.stop_threshold
        }


class AdaptiveMomentumStrategy(BaseStrategy):
    """Adaptive Momentum Strategy with Regime Filter."""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__("Adaptive Momentum", params)
        self.momentum_period = self.params.get('momentum_period', 126)  # 6 months
        self.vol_lookback = self.params.get('vol_lookback', 20)
        self.regime_filter = self.params.get('regime_filter', True)

    def generate_signals(self, data_handler: Any, portfolio: Any) -> List[SignalEvent]:
        """Generate momentum signals with regime filtering."""
        signals = []

        for symbol in data_handler.symbols:
            data = data_handler.get_historical_data(symbol)
            if len(data) < self.momentum_period:
                continue

            # Calculate momentum
            current_price = data['close'].iloc[-1]
            past_price = data['close'].iloc[-self.momentum_period]
            momentum = (current_price - past_price) / past_price

            # Calculate volatility
            returns = data['close'].pct_change().dropna()
            volatility = returns.tail(self.vol_lookback).std() * np.sqrt(252)

            # Regime filter (simplified - would use HMM in production)
            regime_ok = True
            if self.regime_filter:
                # Simple regime detection based on volatility
                avg_vol = returns.std() * np.sqrt(252)
                regime_ok = volatility < avg_vol * 1.5  # Not in high vol regime

            # Generate signal
            if momentum > 0 and regime_ok:
                # Long signal
                position_size = min(1.0, momentum * 2)  # Scale position by momentum strength
                signals.append(SignalEvent(
                    type=EventType.SIGNAL,
                    timestamp=data_handler.current_date,
                    symbol=symbol,
                    direction=1,
                    strength=position_size,
                    strategy_name=self.name,
                    data={'momentum': momentum, 'volatility': volatility}
                ))
            elif momentum < -0.1:  # Strong negative momentum
                # Short signal (optional)
                signals.append(SignalEvent(
                    type=EventType.SIGNAL,
                    timestamp=data_handler.current_date,
                    symbol=symbol,
                    direction=-1,
                    strength=min(1.0, abs(momentum)),
                    strategy_name=self.name,
                    data={'momentum': momentum, 'volatility': volatility}
                ))

        return signals

    def get_params(self) -> Dict[str, Any]:
        return {
            'momentum_period': self.momentum_period,
            'vol_lookback': self.vol_lookback,
            'regime_filter': self.regime_filter
        }


class MLAlphaStrategy(BaseStrategy):
    """ML Alpha Strategy using model predictions."""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__("ML Alpha Strategy", params)
        self.confidence_threshold = self.params.get('confidence_threshold', 0.6)
        self.max_positions = self.params.get('max_positions', 10)
        self.horizon = self.params.get('horizon', 5)  # 5-day prediction

    def generate_signals(self, data_handler: Any, portfolio: Any) -> List[SignalEvent]:
        """Generate signals based on ML model predictions."""
        signals = []

        # In production, this would call the ML engine service
        # For now, simulate with simple technical signals

        for symbol in data_handler.symbols:
            data = data_handler.get_historical_data(symbol)
            if len(data) < 50:
                continue

            # Simulate ML prediction (would be from AMSTAN model)
            # Simple momentum + mean-reversion signal
            returns = data['close'].pct_change().dropna()
            momentum = returns.tail(20).mean()
            mean_reversion = (data['close'].iloc[-1] - data['close'].rolling(50).mean().iloc[-1]) / data['close'].rolling(50).std().iloc[-1]

            # Combine signals (simplified ML ensemble)
            ml_score = 0.6 * momentum - 0.4 * mean_reversion
            confidence = min(abs(ml_score) * 2, 1.0)

            if confidence > self.confidence_threshold:
                direction = 1 if ml_score > 0 else -1
                signals.append(SignalEvent(
                    type=EventType.SIGNAL,
                    timestamp=data_handler.current_date,
                    symbol=symbol,
                    direction=direction,
                    strength=confidence,
                    strategy_name=self.name,
                    data={'ml_score': ml_score, 'confidence': confidence}
                ))

        # Sort by confidence and limit positions
        signals.sort(key=lambda x: x.strength, reverse=True)
        signals = signals[:self.max_positions]

        return signals

    def get_params(self) -> Dict[str, Any]:
        return {
            'confidence_threshold': self.confidence_threshold,
            'max_positions': self.max_positions,
            'horizon': self.horizon
        }


class StatisticalArbitrageStrategy(BaseStrategy):
    """Statistical Arbitrage - Index Rebalancing."""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__("Statistical Arbitrage", params)
        self.index_symbol = self.params.get('index_symbol', 'NIFTY')
        self.lookback_days = self.params.get('lookback_days', 30)
        self.min_weight_change = self.params.get('min_weight_change', 0.01)

    def generate_signals(self, data_handler: Any, portfolio: Any) -> List[SignalEvent]:
        """Generate signals based on index rebalancing events."""
        signals = []

        # In production, this would monitor NSE announcements
        # For simulation, create synthetic rebalancing signals

        for symbol in data_handler.symbols:
            if symbol == self.index_symbol:
                continue

            data = data_handler.get_historical_data(symbol)
            if len(data) < self.lookback_days:
                continue

            # Simulate rebalancing signal (simplified)
            # In reality, this would be triggered by actual index changes
            volume_spike = data['volume'].iloc[-1] > data['volume'].tail(self.lookback_days).mean() * 2

            if volume_spike:
                # Assume this stock was added to index
                signals.append(SignalEvent(
                    type=EventType.SIGNAL,
                    timestamp=data_handler.current_date,
                    symbol=symbol,
                    direction=1,  # Buy on inclusion
                    strength=0.8,
                    strategy_name=self.name,
                    data={'reason': 'index_inclusion', 'volume_spike': volume_spike}
                ))

        return signals

    def get_params(self) -> Dict[str, Any]:
        return {
            'index_symbol': self.index_symbol,
            'lookback_days': self.lookback_days,
            'min_weight_change': self.min_weight_change
        }


class VolatilityRegimeStrategy(BaseStrategy):
    """Volatility Regime Strategy."""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__("Volatility Regime Strategy", params)
        self.vol_lookback = self.params.get('vol_lookback', 20)
        self.regime_threshold = self.params.get('regime_threshold', 1.5)

    def generate_signals(self, data_handler: Any, portfolio: Any) -> List[SignalEvent]:
        """Generate signals based on volatility regime."""
        signals = []

        for symbol in data_handler.symbols:
            data = data_handler.get_historical_data(symbol)
            if len(data) < self.vol_lookback * 2:
                continue

            # Calculate current and historical volatility
            returns = data['close'].pct_change().dropna()
            current_vol = returns.tail(self.vol_lookback).std() * np.sqrt(252)
            historical_vol = returns.std() * np.sqrt(252)

            # Determine regime
            is_high_vol = current_vol > historical_vol * self.regime_threshold

            if is_high_vol:
                # High vol regime: mean reversion strategy
                ma_short = data['close'].rolling(10).mean().iloc[-1]
                ma_long = data['close'].rolling(50).mean().iloc[-1]
                current_price = data['close'].iloc[-1]

                if current_price < ma_short * 0.98:  # Below short MA
                    signals.append(SignalEvent(
                        type=EventType.SIGNAL,
                        timestamp=data_handler.current_date,
                        symbol=symbol,
                        direction=1,  # Buy on dips
                        strength=0.7,
                        strategy_name=self.name,
                        data={'regime': 'high_vol', 'current_vol': current_vol}
                    ))
            else:
                # Low vol regime: momentum strategy
                momentum = returns.tail(20).mean()
                if momentum > 0.001:  # Positive momentum
                    signals.append(SignalEvent(
                        type=EventType.SIGNAL,
                        timestamp=data_handler.current_date,
                        symbol=symbol,
                        direction=1,
                        strength=min(momentum * 100, 1.0),
                        strategy_name=self.name,
                        data={'regime': 'low_vol', 'momentum': momentum}
                    ))

        return signals

    def get_params(self) -> Dict[str, Any]:
        return {
            'vol_lookback': self.vol_lookback,
            'regime_threshold': self.regime_threshold
        }


class DeepRLAgentStrategy(BaseStrategy):
    """Deep RL Agent Strategy using PPO."""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__("Deep RL Agent", params)
        self.model_path = self.params.get('model_path', None)
        self.max_position_size = self.params.get('max_position_size', 1.0)

    def generate_signals(self, data_handler: Any, portfolio: Any) -> List[SignalEvent]:
        """Generate signals using trained RL agent."""
        signals = []

        # In production, this would load and run the PPO agent
        # For simulation, use simple rule-based approximation

        for symbol in data_handler.symbols:
            data = data_handler.get_historical_data(symbol)
            if len(data) < 50:
                continue

            # Simulate RL agent decision (simplified)
            returns = data['close'].pct_change().dropna()
            rsi = self._calculate_rsi(data['close'], 14)
            volatility = returns.tail(20).std()

            # Simple RL-like decision
            if rsi < 30 and volatility < 0.02:  # Oversold, low vol
                direction = 1
                strength = min((30 - rsi) / 30, self.max_position_size)
            elif rsi > 70 and volatility > 0.03:  # Overbought, high vol
                direction = -1
                strength = min((rsi - 70) / 30, self.max_position_size)
            else:
                continue

            signals.append(SignalEvent(
                type=EventType.SIGNAL,
                timestamp=data_handler.current_date,
                symbol=symbol,
                direction=direction,
                strength=strength,
                strategy_name=self.name,
                data={'rsi': rsi, 'volatility': volatility}
            ))

        return signals

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs)).iloc[-1]

    def get_params(self) -> Dict[str, Any]:
        return {
            'model_path': self.model_path,
            'max_position_size': self.max_position_size
        }