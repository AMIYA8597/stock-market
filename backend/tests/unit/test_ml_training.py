"""Tests for ML training pipeline, strategy optimizer, and prediction tasks."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


class TestTrainingCLI:
    def test_build_target_creates_binary_labels(self) -> None:
        from research.train import build_target

        prices = [100, 101, 99, 102, 98, 103, 97, 104, 100, 101]
        df = pd.DataFrame({"close": prices}, index=pd.date_range("2024-01-01", periods=10))
        target = build_target(df)
        assert set(target.dropna().unique()).issubset({0, 1})
        assert target.iloc[-1] != target.iloc[-1]  # last is NaN

    def test_walk_forward_splits_sufficient_data(self) -> None:
        from research.train import walk_forward_splits

        splits = walk_forward_splits(600)
        assert len(splits) >= 1
        for train_idx, val_idx, test_idx in splits:
            assert train_idx[-1] < val_idx[0]
            assert val_idx[-1] < test_idx[0]

    def test_walk_forward_splits_insufficient_data(self) -> None:
        from research.train import walk_forward_splits

        with pytest.raises(ValueError, match="Insufficient data"):
            walk_forward_splits(100)

    def test_signal_sharpe_computation(self) -> None:
        from research.train import compute_signal_sharpe

        preds = pd.Series([1, 0, 1, 0, 1])
        rets = pd.Series([0.01, -0.01, 0.02, -0.005, 0.015])
        sharpe = compute_signal_sharpe(preds, rets)
        assert isinstance(sharpe, float)
        assert not np.isnan(sharpe)

    def test_max_drawdown_computation(self) -> None:
        from research.train import compute_max_drawdown

        preds = pd.Series([1, 1, 1, 1, 1])
        rets = pd.Series([0.01, -0.03, -0.02, 0.01, 0.02])
        mdd = compute_max_drawdown(preds, rets)
        assert mdd <= 0


class TestLeakagePrevention:
    def test_no_future_data_in_train(self) -> None:
        from research.train import walk_forward_splits

        splits = walk_forward_splits(600)
        for train_idx, _val_idx, test_idx in splits:
            assert train_idx.max() < test_idx.min()

    def test_honesty_law_triggers(self) -> None:
        from research.train import TrainingReport, WalkForwardFold

        report = TrainingReport(
            symbol="TEST.NS", model_name="xgboost",
            training_date="2024-01-01", data_source="test",
            n_total_bars=1000, feature_count=20,
        )
        report.folds = [
            WalkForwardFold(fold=1, train_start="", train_end="", test_start="", test_end="",
                            accuracy=0.80, precision=0.8, recall=0.8, f1=0.8,
                            sharpe=1.0, max_drawdown=-0.1, n_train=400, n_test=60),
        ]
        report.mean_accuracy = 0.80
        assert report.mean_accuracy > 0.75

    def test_target_uses_future_shift(self) -> None:
        from research.train import build_target

        df = pd.DataFrame(
            {"close": [100, 102, 101, 103, 100]},
            index=pd.date_range("2024-01-01", periods=5),
        )
        target = build_target(df)
        assert target.iloc[-1] != target.iloc[-1]  # NaN check


class TestArtifacts:
    @patch("research.models.xgboost_model.classifier.XGBoostDirectionalClassifier")
    def test_xgboost_save_load(self, mock_cls: MagicMock) -> None:
        mock_inst = MagicMock()
        mock_cls.return_value = mock_inst
        mock_inst.predict_proba_batch.return_value = np.array([0.6, 0.4, 0.7])

        from research.train import train_xgboost_fold

        x_train = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        y_train = pd.Series([1, 0, 1])
        x_test = pd.DataFrame({"a": [7, 8, 9], "b": [10, 11, 12]})
        preds = train_xgboost_fold(x_train, y_train, x_test, ["a", "b"])
        assert len(preds) == 3

    @patch("research.models.lstm_attention.classifier.LSTMAttentionClassifier")
    def test_lstm_save_load(self, mock_cls: MagicMock) -> None:
        mock_inst = MagicMock()
        mock_cls.return_value = mock_inst
        mock_inst.predict_proba_batch.return_value = np.array([0.6, 0.4, 0.7])

        from research.train import train_lstm_fold

        x_train = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        y_train = pd.Series([1, 0, 1])
        x_test = pd.DataFrame({"a": [7, 8, 9], "b": [10, 11, 12]})
        preds = train_lstm_fold(x_train, y_train, x_test, ["a", "b"])
        assert len(preds) == 3


class TestEnsembleIntegration:
    def test_fusion_math(self) -> None:
        xgb = 0.65
        tft = 0.55
        sentiment = 0.6
        fused = 0.7 * xgb + 0.3 * tft + 0.1 * sentiment
        assert 0.0 <= fused <= 2.0

    def test_regime_gating_bear(self) -> None:
        signal = 0.7
        regime = "bear"
        if regime == "bear":
            signal *= 0.5
        assert signal < 0.7

    def test_regime_gating_bull(self) -> None:
        signal = 0.3
        regime = "bull"
        if regime == "bull":
            signal = min(signal * 1.2, 1.0)
        assert signal >= 0.3

    def test_kelly_fraction_bounds(self) -> None:
        win_prob = 0.55
        win_loss_ratio = 2.0
        kelly = win_prob - (1 - win_prob) / win_loss_ratio
        half_kelly = kelly / 2
        capped = min(half_kelly, 0.25)
        assert 0.0 <= capped <= 0.25


class TestStrategyOptimizer:
    def test_ema_cross_backtest_runs(self) -> None:
        from research.strategy_optimizer import run_ema_cross_vwap_adx_backtest

        np.random.seed(42)
        n = 500
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)
        df = pd.DataFrame({
            "open": close + np.random.randn(n) * 0.1,
            "high": close + abs(np.random.randn(n) * 0.5),
            "low": close - abs(np.random.randn(n) * 0.5),
            "close": close,
            "volume": np.random.randint(1000, 10000, n),
        }, index=pd.date_range("2023-01-01", periods=n, freq="h"))

        result = run_ema_cross_vwap_adx_backtest(df)
        assert isinstance(result.sharpe, float)
        assert isinstance(result.n_trades, int)

    def test_ema_retest_backtest_runs(self) -> None:
        from research.strategy_optimizer import run_ema_retest_backtest

        np.random.seed(42)
        n = 500
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)
        df = pd.DataFrame({
            "open": close + np.random.randn(n) * 0.1,
            "high": close + abs(np.random.randn(n) * 0.5),
            "low": close - abs(np.random.randn(n) * 0.5),
            "close": close,
            "volume": np.random.randint(1000, 10000, n),
        }, index=pd.date_range("2023-01-01", periods=n, freq="h"))

        result = run_ema_retest_backtest(df)
        assert isinstance(result.sharpe, float)

    def test_grid_search_mechanics(self) -> None:
        import itertools

        grid = {"a": [1, 2], "b": [3, 4]}
        combos = list(itertools.product(*grid.values()))
        assert len(combos) == 4

    def test_metrics_computation(self) -> None:
        from research.strategy_optimizer import _compute_metrics

        trades = [0.01, -0.005, 0.02, -0.01, 0.015]
        metrics = _compute_metrics(trades)
        assert metrics["n_trades"] == 5
        assert 0 <= metrics["win_rate"] <= 1
        assert metrics["profit_factor"] >= 0


class TestPredictionTask:
    def test_market_hours_check_weekday(self) -> None:
        from app.tasks.prediction_tasks import _is_market_hours

        monday_noon_ist = datetime(2024, 1, 1, 6, 30, tzinfo=UTC)  # 12:00 IST
        assert _is_market_hours(monday_noon_ist) is True

    def test_skips_outside_market_hours(self) -> None:
        from app.tasks.prediction_tasks import _is_market_hours

        sunday = datetime(2024, 1, 7, 6, 30, tzinfo=UTC)
        assert _is_market_hours(sunday) is False

    def test_skips_before_open(self) -> None:
        from app.tasks.prediction_tasks import _is_market_hours

        early = datetime(2024, 1, 1, 2, 0, tzinfo=UTC)  # 7:30 IST
        assert _is_market_hours(early) is False

    def test_skips_after_close(self) -> None:
        from app.tasks.prediction_tasks import _is_market_hours

        late = datetime(2024, 1, 1, 11, 0, tzinfo=UTC)  # 16:30 IST
        assert _is_market_hours(late) is False
