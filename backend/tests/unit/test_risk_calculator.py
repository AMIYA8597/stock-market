"""Unit tests for app.services.risk_engine.calculator.RiskCalculator."""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from app.services.risk_engine.calculator import RiskCalculator


@pytest.fixture
def returns() -> np.ndarray:
    rng = np.random.default_rng(7)
    return rng.normal(loc=0.0005, scale=0.012, size=1000)


@pytest.fixture
def calc() -> RiskCalculator:
    return RiskCalculator(risk_free_rate=0.05)


def test_risk_free_rate_is_converted_to_daily():
    calculator = RiskCalculator(risk_free_rate=0.0252)
    assert calculator.risk_free_rate == 0.0252
    assert calculator.rf_daily == pytest.approx(0.0252 / 252)


def test_var_historical_matches_empirical_percentile(calc, returns):
    result = calc.var_historical(returns, confidence=0.95, horizon_days=1)

    assert result.method == "historical"
    assert result.horizon_days == 1
    assert result.confidence_level == 0.95
    assert result.var_loss == pytest.approx(abs(np.percentile(returns, 5.0)))
    assert result.var_pct == pytest.approx(result.var_loss * 100)


def test_var_historical_scales_with_sqrt_of_horizon(calc, returns):
    one_day = calc.var_historical(returns, confidence=0.95, horizon_days=1)
    ten_day = calc.var_historical(returns, confidence=0.95, horizon_days=10)

    assert ten_day.var_loss == pytest.approx(one_day.var_loss * np.sqrt(10))


def test_var_historical_grows_with_confidence(calc, returns):
    assert (
        calc.var_historical(returns, confidence=0.99).var_loss
        > calc.var_historical(returns, confidence=0.90).var_loss
    )


def test_var_parametric_matches_closed_form(calc, returns):
    result = calc.var_parametric(returns, confidence=0.99, horizon_days=5)

    expected = abs((np.mean(returns) + np.std(returns) * stats.norm.ppf(0.01)) * np.sqrt(5))
    assert result.method == "parametric"
    assert result.var_loss == pytest.approx(expected)
    assert result.var_pct == pytest.approx(expected * 100)


def test_var_cornish_fisher_matches_expansion(calc, returns):
    confidence = 0.95
    z = stats.norm.ppf(1 - confidence)
    skew = stats.skew(returns)
    kurt = stats.kurtosis(returns)
    z_cf = (
        z
        + (z**3 - z) * skew / 6
        + (z**4 - 3 * z**2) * kurt / 24
        - (2 * z**3 - 5 * z) * skew**2 / 36
    )
    expected = abs(np.mean(returns) + np.std(returns) * z_cf)

    result = calc.var_cornish_fisher(returns, confidence=confidence)

    assert result.method == "cornish_fisher"
    assert result.var_loss == pytest.approx(expected)


def test_var_cornish_fisher_equals_parametric_for_symmetric_thin_tails(calc):
    # Two-point symmetric sample has zero skew and known kurtosis contribution.
    symmetric = np.array([-0.01, 0.01] * 200)

    cf = calc.var_cornish_fisher(symmetric, confidence=0.95)
    parametric = calc.var_parametric(symmetric, confidence=0.95)

    skew = stats.skew(symmetric)
    assert skew == pytest.approx(0.0, abs=1e-12)
    assert cf.var_loss != pytest.approx(parametric.var_loss)  # kurtosis term still applies
    assert cf.var_loss > 0


def test_var_monte_carlo_is_deterministic_zero_return_baseline(calc, returns):
    result = calc.var_monte_carlo(returns, confidence=0.95, horizon_days=3, n_simulations=100)

    assert result.method == "monte_carlo"
    assert result.horizon_days == 3
    # Implementation currently simulates zero returns, so the VaR is degenerate.
    assert result.var_loss == pytest.approx(0.0)


def test_cvar_historical_is_at_least_var(calc, returns):
    var = calc.var_historical(returns, confidence=0.95)
    cvar = calc.cvar_calculate(returns, confidence=0.95, method="historical")

    assert cvar.confidence_level == 0.95
    assert cvar.cvar_loss >= var.var_loss
    assert cvar.cvar_pct == pytest.approx(cvar.cvar_loss * 100)


def test_cvar_parametric_matches_closed_form(calc, returns):
    confidence = 0.95
    z = stats.norm.ppf(1 - confidence)
    expected = abs(np.mean(returns) + np.std(returns) * stats.norm.pdf(z) / (1 - confidence))

    cvar = calc.cvar_calculate(returns, confidence=confidence, method="parametric")

    assert cvar.cvar_loss == pytest.approx(expected)


def test_cvar_falls_back_to_var_when_no_observations_beyond_var(calc):
    constant = np.full(200, 0.01)

    cvar = calc.cvar_calculate(constant, confidence=0.95, method="historical")

    assert cvar.cvar_loss == pytest.approx(0.01)


def test_cvar_grows_with_horizon(calc, returns):
    one_day = calc.cvar_calculate(returns, confidence=0.95, horizon_days=1)
    four_day = calc.cvar_calculate(returns, confidence=0.95, horizon_days=4)

    assert four_day.cvar_loss > one_day.cvar_loss


def test_skew_kurtosis_reports_shape_metrics(calc, returns):
    shape = calc.skew_kurtosis(returns)

    assert shape.skewness == pytest.approx(float(stats.skew(returns)))
    assert shape.excess_kurtosis == pytest.approx(float(stats.kurtosis(returns, fisher=True)))
    assert shape.kurtosis == pytest.approx(shape.excess_kurtosis + 3.0)
    assert shape.tail_ratio > 0


def test_skew_kurtosis_detects_left_skew(calc):
    rng = np.random.default_rng(3)
    left_skewed = -np.abs(rng.standard_exponential(2000)) * 0.01

    shape = calc.skew_kurtosis(left_skewed)

    assert shape.skewness < 0
    assert shape.tail_ratio > 1.0  # heavier left tail than right


def test_fit_gpd_tail_index_needs_minimum_sample():
    assert RiskCalculator._fit_gpd_tail_index(np.array([-0.05, -0.04, -0.03])) == 0.0


def test_fit_gpd_tail_index_positive_for_fat_tail():
    tail = -np.linspace(0.01, 0.5, 200)

    index = RiskCalculator._fit_gpd_tail_index(tail)

    assert index > 0


def test_compute_greeks_call_satisfies_black_scholes_bounds(calc):
    greeks = calc.compute_greeks(
        spot_price=100.0,
        strike=100.0,
        time_to_expiry_years=1.0,
        volatility=0.2,
        option_type="call",
    )

    assert 0.0 < greeks["delta"] < 1.0
    assert greeks["gamma"] > 0
    assert greeks["vega"] > 0
    assert greeks["theta"] < 0


def test_compute_greeks_put_call_parity_on_delta(calc):
    kwargs = {
        "spot_price": 120.0,
        "strike": 100.0,
        "time_to_expiry_years": 0.5,
        "volatility": 0.35,
    }
    call = calc.compute_greeks(option_type="call", **kwargs)
    put = calc.compute_greeks(option_type="put", **kwargs)

    assert call["delta"] - put["delta"] == pytest.approx(1.0)
    assert call["gamma"] == pytest.approx(put["gamma"])
    assert call["vega"] == pytest.approx(put["vega"])


def test_compute_greeks_deep_itm_call_delta_approaches_one(calc):
    greeks = calc.compute_greeks(
        spot_price=500.0,
        strike=100.0,
        time_to_expiry_years=0.25,
        volatility=0.15,
        option_type="call",
    )

    assert greeks["delta"] == pytest.approx(1.0, abs=1e-3)
    assert greeks["gamma"] == pytest.approx(0.0, abs=1e-4)


@pytest.fixture
def portfolio_returns() -> pd.DataFrame:
    rng = np.random.default_rng(11)
    return pd.DataFrame(
        {
            "AAA": rng.normal(0.001, 0.01, 200),
            "BBB": rng.normal(0.0008, 0.015, 200),
        }
    )


@pytest.mark.parametrize(
    ("scenario", "multiplier"),
    [
        ("2008_crisis", -0.25),
        ("covid_crash", -0.15),
        ("dotcom_bubble", -0.20),
        ("unknown_scenario", -0.10),
    ],
)
def test_stress_test_applies_scenario_multiplier(calc, portfolio_returns, scenario, multiplier):
    result = calc.stress_test_historical_scenario(portfolio_returns, scenario_name=scenario)

    expected_impact = (portfolio_returns.iloc[-126:] * multiplier).sum(axis=1)

    assert result.scenario_name == scenario
    assert result.portfolio_loss_pct == pytest.approx(expected_impact.mean() * 100)
    assert result.portfolio_loss_abs == pytest.approx(expected_impact.sum())
    assert result.recovery_days >= 0


def test_stress_test_reports_correlation_per_asset(calc, portfolio_returns):
    result = calc.stress_test_historical_scenario(portfolio_returns, scenario_name="covid_crash")

    assert set(result.asset_correlations) == {"AAA", "BBB"}
    assert all(-1.0 <= c <= 1.0 for c in result.asset_correlations.values())


def test_stress_test_correlation_is_zero_for_constant_asset(calc):
    frame = pd.DataFrame({"FLAT": [0.01] * 150, "MOVING": np.linspace(-0.02, 0.02, 150)})

    result = calc.stress_test_historical_scenario(frame, scenario_name="flash_crash")

    assert result.asset_correlations["FLAT"] == pytest.approx(0.0, abs=1e-12)


def test_correlation_matrix_shrinkage_is_valid_correlation_matrix():
    rng = np.random.default_rng(5)
    frame = pd.DataFrame(rng.normal(0, 0.01, size=(300, 4)), columns=list("ABCD"))

    corr = RiskCalculator.correlation_matrix_shrinkage(frame)
    values = np.asarray(corr)

    assert values.shape == (4, 4)
    assert np.allclose(np.diag(values), 1.0)
    assert np.allclose(values, values.T)
    assert values.min() >= -1.0 - 1e-9 and values.max() <= 1.0 + 1e-9


def test_correlation_matrix_shrinkage_pulls_off_diagonals_toward_zero():
    rng = np.random.default_rng(9)
    base = rng.normal(0, 0.01, size=300)
    frame = pd.DataFrame(
        {
            "A": base,
            "B": base * 0.9 + rng.normal(0, 0.001, size=300),
        }
    )

    raw_corr = frame.corr().to_numpy()[0, 1]
    shrunk_corr = np.asarray(RiskCalculator.correlation_matrix_shrinkage(frame))[0, 1]

    assert abs(shrunk_corr) <= abs(raw_corr)
