"""Regression tests for research/backtesting/statistical_tests.py.

sharpe_inference() previously computed skew/kurtosis and then never used
them in the standard-error formula, despite its own comment claiming the
formula "accounts for skew/kurt" (it used the plain Gaussian-IID SE).
These tests would fail against that implementation.
"""

from __future__ import annotations

import numpy as np

from research.backtesting.statistical_tests import (
    min_backtest_length_days,
    sharpe_inference,
)


def test_sharpe_inference_uses_skew_and_kurtosis() -> None:
    rng = np.random.default_rng(42)

    symmetric_returns = rng.normal(loc=0.001, scale=0.01, size=500)

    # A right-skewed series with the same mean/std as the symmetric one:
    # square a centered normal, rescale, then shift to match mean/std -
    # this changes skewness/kurtosis materially without changing sr's
    # first two moments in a way that would trivially change the result
    # through mean_ret/std_ret alone.
    skewed_base = rng.chisquare(df=2, size=500)
    skewed_returns = (skewed_base - skewed_base.mean()) / skewed_base.std()
    skewed_returns = skewed_returns * symmetric_returns.std() + symmetric_returns.mean()

    _, _, symmetric_ci = sharpe_inference(symmetric_returns)
    _, _, skewed_ci = sharpe_inference(skewed_returns)

    # If skew/kurtosis were dropped from the formula (the bug), a series
    # with the same mean/std but very different higher moments would
    # produce a near-identical confidence interval width. They must differ.
    symmetric_width = symmetric_ci[1] - symmetric_ci[0]
    skewed_width = skewed_ci[1] - skewed_ci[0]
    assert not np.isclose(symmetric_width, skewed_width, rtol=0.02)


def test_sharpe_inference_degenerate_inputs() -> None:
    assert sharpe_inference(np.array([])) == (0.0, 1.0, (0.0, 0.0))
    assert sharpe_inference(np.array([1.0])) == (0.0, 1.0, (0.0, 0.0))
    assert sharpe_inference(np.zeros(10)) == (0.0, 1.0, (0.0, 0.0))


def test_min_backtest_length_days_is_defined_once() -> None:
    # Regression: this function used to be defined twice in a row
    # (identical dead duplicate); make sure only one definition survives
    # and it still returns the expected value.
    assert min_backtest_length_days() == 30
