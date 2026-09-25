import numpy as np
import pandas as pd
import pytest

from app.services.risk_engine.calculator import (
    RiskCalculator,
)


@pytest.fixture
def calc():
    return RiskCalculator(risk_free_rate=0.025)

@pytest.fixture
def sample_returns():
    np.random.seed(42)
    # create a sample array of returns
    return np.random.normal(0.001, 0.02, 1000)

@pytest.fixture
def sample_df_returns():
    np.random.seed(42)
    data = np.random.normal(0.001, 0.02, (200, 3))
    return pd.DataFrame(data, columns=["AAPL", "GOOG", "MSFT"])

def test_init(calc):
    assert calc.risk_free_rate == 0.025
    assert calc.rf_daily == 0.025 / 252

def test_var_historical(calc, sample_returns):
    result = calc.var_historical(sample_returns, confidence=0.95, horizon_days=1)
    assert result.method == "historical"
    assert result.horizon_days == 1
    assert result.confidence_level == 0.95
    assert result.var_loss > 0
    assert result.var_pct == result.var_loss * 100

def test_var_parametric(calc, sample_returns):
    result = calc.var_parametric(sample_returns, confidence=0.95, horizon_days=1)
    assert result.method == "parametric"
    assert result.var_loss > 0

def test_var_cornish_fisher(calc, sample_returns):
    result = calc.var_cornish_fisher(sample_returns, confidence=0.95, horizon_days=1)
    assert result.method == "cornish_fisher"
    assert result.var_loss > 0

def test_var_monte_carlo(calc, sample_returns):
    result = calc.var_monte_carlo(sample_returns, confidence=0.95, horizon_days=1, n_simulations=100)
    assert result.method == "monte_carlo"
    assert result.var_loss >= 0

def test_cvar_calculate_historical_with_tail(calc, sample_returns):
    result = calc.cvar_calculate(sample_returns, confidence=0.95, horizon_days=1, method="historical")
    assert result.cvar_loss > 0
    assert result.cvar_pct == result.cvar_loss * 100
    assert isinstance(result.tail_index, float)

def test_cvar_calculate_historical_no_tail(calc):
    # force no tail by having identical positive returns
    returns = np.array([0.01, 0.01, 0.01])
    result = calc.cvar_calculate(returns, confidence=0.95, horizon_days=1, method="historical")
    assert result.cvar_loss > 0

def test_cvar_calculate_parametric(calc, sample_returns):
    result = calc.cvar_calculate(sample_returns, confidence=0.95, horizon_days=1, method="parametric")
    assert result.cvar_loss > 0

def test_skew_kurtosis(calc, sample_returns):
    result = calc.skew_kurtosis(sample_returns)
    assert isinstance(result.skewness, float)
    assert isinstance(result.kurtosis, float)
    assert isinstance(result.excess_kurtosis, float)
    assert isinstance(result.tail_ratio, float)

def test_skew_kurtosis_empty_tail(calc):
    # to hit empty upper tail condition
    returns = np.array([-0.1, -0.05, -0.02, -0.01])
    result = calc.skew_kurtosis(returns)
    assert isinstance(result.tail_ratio, float)

def test_compute_greeks_call(calc):
    result = calc.compute_greeks(spot_price=100, strike=100, time_to_expiry_years=1, volatility=0.2, option_type="call")
    assert "delta" in result
    assert "gamma" in result
    assert "vega" in result
    assert "theta" in result

def test_compute_greeks_put(calc):
    result = calc.compute_greeks(spot_price=100, strike=100, time_to_expiry_years=1, volatility=0.2, option_type="put")
    assert "delta" in result
    assert "theta" in result

def test_stress_test_historical_scenario_2008(calc, sample_df_returns):
    result = calc.stress_test_historical_scenario(sample_df_returns, scenario_name="2008_crisis")
    assert result.scenario_name == "2008_crisis"
    assert "AAPL" in result.asset_correlations

def test_stress_test_historical_scenario_covid(calc, sample_df_returns):
    result = calc.stress_test_historical_scenario(sample_df_returns, scenario_name="covid_crash")
    assert result.scenario_name == "covid_crash"

def test_stress_test_historical_scenario_dotcom(calc, sample_df_returns):
    result = calc.stress_test_historical_scenario(sample_df_returns, scenario_name="dotcom_bubble")
    assert result.scenario_name == "dotcom_bubble"

def test_stress_test_historical_scenario_flash_crash(calc, sample_df_returns):
    result = calc.stress_test_historical_scenario(sample_df_returns, scenario_name="flash_crash")
    assert result.scenario_name == "flash_crash"

def test_stress_test_empty_dataframe(calc):
    df = pd.DataFrame()
    with pytest.raises(IndexError):
        calc.stress_test_historical_scenario(df, scenario_name="2008_crisis")

def test_fit_gpd_tail_index_small(calc):
    result = calc._fit_gpd_tail_index(np.array([1, 2, 3]))
    assert result == 0.0

def test_fit_gpd_tail_index_large(calc, sample_returns):
    result = calc._fit_gpd_tail_index(sample_returns)
    assert isinstance(result, float)

def test_correlation_matrix_shrinkage(calc, sample_df_returns):
    # sample_df_returns has real, non-degenerate variance across 3 assets, so
    # shrinkage should succeed and return a valid correlation matrix - not raise.
    corr_matrix = calc.correlation_matrix_shrinkage(sample_df_returns)
    n_assets = sample_df_returns.shape[1]
    assert corr_matrix.shape == (n_assets, n_assets)
    assert np.allclose(np.diag(corr_matrix), 1.0)
    assert np.all(np.isfinite(corr_matrix))

def test_correlation_matrix_shrinkage_zero_variance():
    # this might trigger some specific edge cases in correlation matrix shrinkage
    df = pd.DataFrame({'A': [1,1,1], 'B': [2,2,2]})
    calc = RiskCalculator()
    with pytest.raises(ValueError):
         calc.correlation_matrix_shrinkage(df)
