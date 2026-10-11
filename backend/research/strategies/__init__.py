"""Strategy plugin system for NeuroQuant backtesting engine."""

from research.strategies.base import Strategy, StrategySignal, TradeDirection
from research.strategies.ema_cross_vwap_adx import EMACrossVWAPADXStrategy
from research.strategies.ema_retest import EMARetestStrategy
from research.strategies.registry import get_strategy, list_strategies, register_strategy

__all__ = [
    "Strategy",
    "StrategySignal",
    "TradeDirection",
    "EMACrossVWAPADXStrategy",
    "EMARetestStrategy",
    "get_strategy",
    "list_strategies",
    "register_strategy",
]
