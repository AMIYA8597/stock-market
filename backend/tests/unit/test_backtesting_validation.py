"""Unit tests for backtesting statistical tests, Monte Carlo and CPCV utilities."""

import math

import numpy as np
import pytest

from research.backtesting.monte_carlo import (
    bootstrap_paths,
    merton_jump_diffusion_paths,
    summarize_monte_carlo,
)
from research.backtesting.statistical_tests import (
    deflated_sharpe_ratio,
    diebold_mariano_test,
    min_backtest_length_days,
)
from research.backtesting.walk_forward import evaluate_cpcv, generate_cpcv_splits

# ── statistical_tests ──────────────────────────────────────────────────────


def test_diebold_mariano_matches_manual_statistic():
    loss_a = np.array([1.0, 1.2, 0.9, 1.1, 1.3])
    loss_b = np.array([0.8, 0.9, 0.7, 1.0, 0.95])

    dm, p = diebold_mariano_test(loss_a, loss_b)

    d = loss_a - loss_b
    expected_dm = float(np.mean(d)) / math.sqrt(float(np.var(d, ddof=1)) / len(d))
    assert dm == pytest.approx(expected_dm)
    assert 0.0 <= p <= 1.0


def test_diebold_mariano_is_symmetric_in_sign():
    loss_a = np.array([1.0, 1.2, 0.9, 1.1])
    loss_b = np.array([0.6, 1.0, 0.8, 0.7])

    dm_ab, p_ab = diebold_mariano_test(loss_a, loss_b)
    dm_ba, p_ba = diebold_mariano_test(loss_b, loss_a)

    assert dm_ab == pytest.approx(-dm_ba)
    assert p_ab == pytest.approx(p_ba)


def test_diebold_mariano_returns_neutral_result_for_zero_variance():
    losses = np.array([1.0, 2.0, 3.0])

    assert diebold_mariano_test(losses, losses - 0.5) == (0.0, 1.0)


def test_diebold_mariano_large_difference_is_significant():
    rng = np.random.default_rng(4)
    loss_a = rng.normal(1.0, 0.01, 200)
    loss_b = rng.normal(0.5, 0.01, 200)

    dm, p = diebold_mariano_test(loss_a, loss_b)

    assert dm > 3.0
    assert p < 0.01


def test_diebold_mariano_requires_matching_shapes():
    with pytest.raises(ValueError, match="same shape"):
        diebold_mariano_test(np.ones(3), np.ones(5))


def test_deflated_sharpe_is_unchanged_for_single_trial():
    assert deflated_sharpe_ratio(1.8, n_trials=1) == 1.8
    assert deflated_sharpe_ratio(1.8, n_trials=0) == 1.8


def test_deflated_sharpe_penalizes_multiple_trials():
    for n_trials in (2, 10, 100, 1000):
        haircut = 1.8 - deflated_sharpe_ratio(1.8, n_trials=n_trials)
        # Haircut converges downward to sqrt(2)/2 as the trial count grows.
        assert 0.5 < haircut < 1.5


def test_deflated_sharpe_matches_expected_maximum_formula():
    n = 50
    e_sr_max = (0.5772156649 + math.sqrt(2.0 * math.log(n))) / (2.0 * math.sqrt(math.log(n)))

    assert deflated_sharpe_ratio(2.0, n_trials=n) == pytest.approx(2.0 - e_sr_max)


def test_min_backtest_length_matches_formula_and_rounds_up():
    expected = math.ceil((1.96 * 0.4 / 1.0) ** 2)

    assert min_backtest_length_days(target_sharpe=1.0, sharpe_se=0.4) == expected


def test_min_backtest_length_shrinks_as_target_sharpe_grows():
    assert min_backtest_length_days(2.0, 0.5) < min_backtest_length_days(0.5, 0.5)


@pytest.mark.parametrize(
    ("target_sharpe", "sharpe_se"),
    [(0.0, 0.5), (-1.0, 0.5), (1.0, 0.0), (1.0, -0.2)],
)
def test_min_backtest_length_returns_zero_for_invalid_inputs(target_sharpe, sharpe_se):
    assert min_backtest_length_days(target_sharpe, sharpe_se) == 0


# ── monte_carlo ────────────────────────────────────────────────────────────


def test_bootstrap_paths_resamples_only_observed_returns():
    returns = np.array([-0.02, 0.0, 0.01, 0.03])

    paths = bootstrap_paths(returns, n_simulations=50)

    assert paths.shape == (50, 4)
    assert set(np.unique(paths)).issubset(set(returns.tolist()))


def test_bootstrap_paths_is_reproducible_with_seed():
    returns = np.linspace(-0.01, 0.01, 20)

    first = bootstrap_paths(returns, n_simulations=25, random_seed=123)
    second = bootstrap_paths(returns, n_simulations=25, random_seed=123)
    other = bootstrap_paths(returns, n_simulations=25, random_seed=124)

    assert np.array_equal(first, second)
    assert not np.array_equal(first, other)


def test_merton_paths_shape_and_reproducibility():
    kwargs = {
        "mu": 0.08,
        "sigma": 0.2,
        "lambda_jump": 5.0,
        "jump_mu": -0.02,
        "jump_sigma": 0.05,
        "horizon_days": 30,
        "n_simulations": 100,
    }

    paths = merton_jump_diffusion_paths(**kwargs)

    assert paths.shape == (100, 30)
    assert np.array_equal(paths, merton_jump_diffusion_paths(**kwargs))


def test_merton_paths_without_jumps_reduce_to_diffusion():
    common = {
        "mu": 0.10,
        "sigma": 0.25,
        "jump_mu": -0.05,
        "jump_sigma": 0.1,
        "horizon_days": 10,
        "n_simulations": 500,
        "random_seed": 1,
    }

    no_jumps = merton_jump_diffusion_paths(lambda_jump=0.0, **common)
    with_jumps = merton_jump_diffusion_paths(lambda_jump=250.0, **common)

    assert np.std(with_jumps) > np.std(no_jumps)
    assert no_jumps.mean() == pytest.approx((0.10 - 0.5 * 0.25**2) / 252, abs=5e-3)


def test_summarize_monte_carlo_percentiles_are_ordered():
    rng = np.random.default_rng(2)
    paths = rng.normal(0.0005, 0.01, size=(2000, 120))

    result = summarize_monte_carlo(paths, initial_capital=100.0)

    p = result.percentiles
    assert p["p5"] < p["p25"] < p["p50"] < p["p75"] < p["p95"]
    assert result.paths.shape == (2000, 120)
    assert 0.0 <= result.prob_ruin_25pct <= result.prob_ruin_10pct <= 1.0


def test_summarize_monte_carlo_compounds_equity_from_returns():
    paths = np.array([[0.1, 0.1], [-0.5, 0.0]])

    result = summarize_monte_carlo(paths, initial_capital=100.0)

    assert result.paths[0].tolist() == pytest.approx([110.0, 121.0])
    assert result.paths[1].tolist() == pytest.approx([50.0, 50.0])
    assert result.percentiles["p50"] == pytest.approx((121.0 + 50.0) / 2)


def test_summarize_monte_carlo_flags_ruin_thresholds():
    steady = np.full((10, 50), 0.001)
    crashing = np.full((10, 50), -0.05)

    assert summarize_monte_carlo(steady).prob_ruin_10pct == 0.0
    assert summarize_monte_carlo(crashing).prob_ruin_25pct == 1.0


# ── walk_forward (CPCV) ────────────────────────────────────────────────────


def test_generate_cpcv_splits_produces_all_fold_pairs():
    splits = generate_cpcv_splits(n_samples=100, n_splits=5, purge_days=0, embargo_days=0)

    assert len(splits) == 10  # C(5, 2)
    for split in splits:
        assert len(split.test_idx) == 40
        assert np.array_equal(split.test_idx, np.sort(split.test_idx))


def test_generate_cpcv_splits_keeps_train_and_test_disjoint():
    splits = generate_cpcv_splits(n_samples=120, n_splits=4, purge_days=3, embargo_days=2)

    for split in splits:
        assert not set(split.train_idx.tolist()) & set(split.test_idx.tolist())
        assert len(split.train_idx) + len(split.test_idx) <= 120


def test_generate_cpcv_splits_purge_and_embargo_remove_adjacent_samples():
    no_gap = generate_cpcv_splits(n_samples=100, n_splits=4, purge_days=0, embargo_days=0)
    with_gap = generate_cpcv_splits(n_samples=100, n_splits=4, purge_days=5, embargo_days=5)

    assert len(with_gap[0].train_idx) < len(no_gap[0].train_idx)


def test_generate_cpcv_splits_requires_at_least_two_folds():
    with pytest.raises(ValueError, match="n_splits must be >= 2"):
        generate_cpcv_splits(n_samples=50, n_splits=1, purge_days=0, embargo_days=0)


def test_evaluate_cpcv_scores_every_split():
    returns = np.linspace(-0.01, 0.01, 60)

    scores = evaluate_cpcv(
        returns, n_splits=4, purge_days=1, embargo_days=1, scorer=lambda r: float(np.mean(r))
    )

    assert scores.shape == (6,)
    assert np.isfinite(scores).all()


def test_evaluate_cpcv_scorer_sees_only_test_samples():
    returns = np.arange(40, dtype=float)
    splits = generate_cpcv_splits(40, n_splits=4, purge_days=0, embargo_days=0)

    scores = evaluate_cpcv(
        returns, n_splits=4, purge_days=0, embargo_days=0, scorer=lambda r: float(len(r))
    )

    assert scores.tolist() == [float(len(s.test_idx)) for s in splits]
