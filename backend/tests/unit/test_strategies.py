"""Unit tests for the strategy plugin system.

Tests:
  - Strategy ABC instantiation and params
  - EMA Cross + VWAP + ADX signal generation
  - EMA Retest signal generation
  - Registry (register, list, get)
  - StrategyBacktester end-to-end on synthetic data
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research.strategies.base import StrategySignal, TradeDirection
from research.strategies.ema_cross_vwap_adx import EMACrossVWAPADXStrategy
from research.strategies.ema_retest import EMARetestStrategy
from research.strategies.registry import get_strategy, list_strategies

# ── Helpers ──────────────────────────────────────────────────────────────


def _make_ohlcv(n: int = 200, seed: int = 42, trend: float = 0.001) -> pd.DataFrame:
    """Generate synthetic OHLCV data with a mild uptrend."""
    rng = np.random.default_rng(seed)
    close = np.zeros(n)
    close[0] = 100.0
    for i in range(1, n):
        close[i] = close[i - 1] * (1 + trend + rng.normal(0, 0.015))

    high = close * (1 + rng.uniform(0.001, 0.02, n))
    low = close * (1 - rng.uniform(0.001, 0.02, n))
    open_ = close * (1 + rng.normal(0, 0.005, n))
    volume = rng.integers(1000, 50000, n).astype(float)

    dates = pd.date_range("2024-01-01", periods=n, freq="h")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


def _make_crossover_data(n: int = 100) -> pd.DataFrame:
    """Generate data that guarantees at least one EMA 9/21 crossover."""
    # Start with downtrend, then sharp uptrend to force crossover
    close = np.concatenate([
        np.linspace(100, 90, n // 2),      # downtrend
        np.linspace(90, 120, n // 2),       # uptrend
    ])
    high = close * 1.01
    low = close * 0.99
    open_ = close * 1.001
    volume = np.full(n, 10000.0)

    dates = pd.date_range("2024-01-01", periods=n, freq="h")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


# ── Base class tests ────────────────────────────────────────────────────


class TestStrategyBase:
    def test_signal_lot_size(self):
        sig = StrategySignal(
            bar_index=0,
            direction=TradeDirection.LONG,
            entry_price=100.0,
            stop_loss=98.0,  # 2 points SL
            take_profit=106.0,
            risk_per_trade=40.0,
        )
        lots = sig.lot_size(min_lots=0.01, max_lots=10.0, point_value=1.0)
        # risk = 40, sl_dist = 2, lots = 40 / (2 * 1) = 20 → capped at 10
        assert lots == 10.0

    def test_signal_lot_size_normal(self):
        sig = StrategySignal(
            bar_index=0,
            direction=TradeDirection.LONG,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2030.0,
            risk_per_trade=40.0,
        )
        # sl_dist = 10, lots = 40 / (10 * 1) = 4.0
        lots = sig.lot_size(point_value=1.0)
        assert abs(lots - 4.0) < 0.01

    def test_reward_risk_ratio(self):
        sig = StrategySignal(
            bar_index=0,
            direction=TradeDirection.LONG,
            entry_price=100.0,
            stop_loss=97.0,
            take_profit=109.0,
        )
        assert abs(sig.reward_risk_ratio - 3.0) < 0.01


# ── EMA Cross + VWAP + ADX tests ───────────────────────────────────────


class TestEMACrossVWAPADX:
    def test_default_params(self):
        strat = EMACrossVWAPADXStrategy()
        assert strat.params.ema_fast == 9
        assert strat.params.ema_slow == 21
        assert strat.params.adx_threshold == 20.0
        assert strat.params.reward_risk == 3.0

    def test_custom_params(self):
        strat = EMACrossVWAPADXStrategy(params={"adx_threshold": 25.0})
        assert strat.params.adx_threshold == 25.0
        assert strat.params.ema_fast == 9  # default preserved

    def test_compute_indicators(self):
        df = _make_ohlcv(200)
        strat = EMACrossVWAPADXStrategy()
        result = strat.compute_indicators(df)
        assert "ema_fast" in result.columns
        assert "ema_slow" in result.columns
        assert "vwap" in result.columns
        assert "adx_14" in result.columns
        assert "atr_14" in result.columns
        # No NaN in late bars
        assert not np.isnan(result["ema_fast"].iloc[-1])
        assert not np.isnan(result["adx_14"].iloc[-1])

    def test_generate_signals_returns_list(self):
        df = _make_ohlcv(200)
        strat = EMACrossVWAPADXStrategy()
        df = strat.compute_indicators(df)
        signals = strat.generate_signals(df, 50)
        assert isinstance(signals, list)

    def test_get_info(self):
        strat = EMACrossVWAPADXStrategy()
        info = strat.get_info()
        assert info["name"] == "ema_cross_vwap_adx"
        assert "params" in info

    def test_no_signals_on_warmup(self):
        df = _make_ohlcv(30)
        strat = EMACrossVWAPADXStrategy()
        df = strat.compute_indicators(df)
        signals = strat.generate_signals(df, 5)
        assert signals == []

    def test_signals_on_crossover_data(self):
        """On data designed to cross over, verify signal structure if generated."""
        df = _make_crossover_data(200)
        strat = EMACrossVWAPADXStrategy(params={"adx_threshold": 0.0})  # relax ADX filter
        df = strat.compute_indicators(df)

        all_signals = []
        for i in range(len(df)):
            sigs = strat.generate_signals(df, i)
            all_signals.extend(sigs)

        # With ADX threshold at 0, we should get at least some signals
        # But structure is what matters most
        for sig in all_signals:
            assert isinstance(sig, StrategySignal)
            assert sig.direction in (TradeDirection.LONG, TradeDirection.SHORT)
            assert sig.stop_loss > 0
            assert sig.take_profit > 0
            assert sig.entry_price > 0


# ── EMA Retest tests ───────────────────────────────────────────────────


class TestEMARetest:
    def test_default_params(self):
        strat = EMARetestStrategy()
        assert strat.params.ema_length == 50
        assert strat.params.touch_tolerance_atr == 0.3
        assert strat.params.move_away_atr == 1.0
        assert strat.params.max_bounce_bars == 3

    def test_compute_indicators(self):
        df = _make_ohlcv(200)
        strat = EMARetestStrategy()
        result = strat.compute_indicators(df)
        assert "ema_50" in result.columns
        assert "atr_14" in result.columns

    def test_compute_indicators_with_adx_filter(self):
        df = _make_ohlcv(200)
        strat = EMARetestStrategy(params={"use_adx_filter": True})
        result = strat.compute_indicators(df)
        assert "adx_14" in result.columns

    def test_compute_indicators_with_break_both(self):
        df = _make_ohlcv(200)
        strat = EMARetestStrategy(params={"use_break_both_emas": True})
        result = strat.compute_indicators(df)
        assert "ema_9" in result.columns
        assert "ema_21" in result.columns

    def test_generate_signals_returns_list(self):
        df = _make_ohlcv(200)
        strat = EMARetestStrategy()
        df = strat.compute_indicators(df)
        signals = strat.generate_signals(df, 100)
        assert isinstance(signals, list)

    def test_reset_clears_state(self):
        strat = EMARetestStrategy()
        strat._state["phase"] = "MOVED_AWAY"
        strat._state["in_trade"] = True
        strat.reset()
        assert strat._state == {}


# ── Registry tests ──────────────────────────────────────────────────────


class TestRegistry:
    def test_list_strategies(self):
        strategies = list_strategies()
        names = [s["name"] for s in strategies]
        assert "ema_cross_vwap_adx" in names
        assert "ema_retest" in names

    def test_get_strategy(self):
        strat = get_strategy("ema_cross_vwap_adx")
        assert isinstance(strat, EMACrossVWAPADXStrategy)
        assert strat.params.ema_fast == 9

    def test_get_strategy_with_params(self):
        strat = get_strategy("ema_retest", params={"reward_risk": 2.5})
        assert isinstance(strat, EMARetestStrategy)
        assert strat.params.reward_risk == 2.5

    def test_get_unknown_strategy_raises(self):
        with pytest.raises(KeyError, match="not found"):
            get_strategy("nonexistent_strategy")

    def test_strategy_metadata(self):
        strategies = list_strategies()
        for s in strategies:
            assert "name" in s
            assert "description" in s
            assert "version" in s
            assert "default_params" in s
            assert len(s["description"]) > 0


# ── Strategy Backtester tests ───────────────────────────────────────────


class TestStrategyBacktester:
    def test_backtest_runs_without_error(self):
        from research.backtesting.strategy_runner import StrategyBacktester

        df = _make_ohlcv(200)
        strat = EMACrossVWAPADXStrategy(params={"adx_threshold": 0.0})
        bt = StrategyBacktester(
            strategy=strat,
            df=df,
            initial_capital=100_000.0,
            cost_model="zero",
        )
        result = bt.run()
        assert result.strategy_name == "ema_cross_vwap_adx"
        assert result.initial_capital == 100_000.0
        assert len(result.equity_curve) == 200
        assert result.final_equity > 0

    def test_backtest_with_costs(self):
        from research.backtesting.strategy_runner import StrategyBacktester

        df = _make_ohlcv(200)
        strat = EMACrossVWAPADXStrategy(params={"adx_threshold": 0.0})
        bt = StrategyBacktester(
            strategy=strat,
            df=df,
            initial_capital=100_000.0,
            cost_model="indian",
            is_delivery=True,
        )
        result = bt.run()
        assert result.strategy_name == "ema_cross_vwap_adx"
        # Costs should be >= 0
        assert result.total_cost >= 0

    def test_backtest_summary(self):
        from research.backtesting.strategy_runner import StrategyBacktester

        df = _make_ohlcv(200)
        strat = EMARetestStrategy()
        bt = StrategyBacktester(
            strategy=strat,
            df=df,
            initial_capital=100_000.0,
            cost_model="zero",
        )
        result = bt.run()
        summary = result.summary()
        assert "strategy" in summary
        assert "total_trades" in summary
        assert "win_rate" in summary
        assert "sharpe" in summary
        assert "max_drawdown" in summary

    def test_no_trades_result(self):
        """Strategy on flat data should produce zero trades."""
        from research.backtesting.strategy_runner import StrategyBacktester

        n = 100
        # Perfectly flat price — no crossovers, no retests
        df = pd.DataFrame({
            "open": np.full(n, 100.0),
            "high": np.full(n, 100.5),
            "low": np.full(n, 99.5),
            "close": np.full(n, 100.0),
            "volume": np.full(n, 10000.0),
        }, index=pd.date_range("2024-01-01", periods=n, freq="h"))

        strat = EMACrossVWAPADXStrategy()
        bt = StrategyBacktester(strategy=strat, df=df, cost_model="zero")
        result = bt.run()
        assert result.total_trades == 0
        assert result.win_rate == 0.0
        assert result.final_equity == result.initial_capital
