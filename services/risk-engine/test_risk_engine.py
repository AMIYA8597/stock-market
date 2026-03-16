"""Test Risk Engine functionality."""

import numpy as np
import pandas as pd
from app.risk_engine import RiskEngine


def test_risk_engine():
    """Test basic risk engine functionality."""
    # Create sample returns data
    np.random.seed(42)
    n_periods = 1000
    n_assets = 3

    # Generate correlated returns
    mu = np.array([0.001, 0.0008, 0.0012])
    cov = np.array([
        [0.0004, 0.0001, 0.0002],
        [0.0001, 0.0003, 0.00015],
        [0.0002, 0.00015, 0.0005]
    ])

    # Generate returns
    returns = np.random.multivariate_normal(mu, cov, n_periods)
    returns_df = pd.DataFrame(returns, columns=['Asset1', 'Asset2', 'Asset3'])

    # Initialize risk engine
    engine = RiskEngine()

    # Test VaR calculations
    print("Testing VaR calculations...")

    # Historical VaR
    var_hist = engine.calculate_var(returns_df, method='historical', confidence=0.95)
    print(f"Historical VaR (95%): {var_hist}")

    # Parametric VaR
    var_param = engine.calculate_var(returns_df, method='parametric', confidence=0.95)
    print(f"Parametric VaR (95%): {var_param}")

    # Monte Carlo VaR
    var_mc = engine.calculate_var(returns_df, method='monte_carlo', confidence=0.95)
    print(f"Monte Carlo VaR (95%): {var_mc}")

    # Test CVaR
    print("\nTesting CVaR calculation...")
    cvar = engine.calculate_cvar(returns_df, confidence=0.95)
    print(f"CVaR (95%): {cvar}")

    # Test Monte Carlo simulation
    print("\nTesting Monte Carlo simulation...")
    weights = np.array([0.4, 0.3, 0.3])
    mc_result = engine.monte_carlo_simulation(returns_df, weights, n_simulations=100, n_days=30)
    print(f"MC Simulation - Mean final value: {mc_result['mean_final_value']:.4f}")
    print(f"MC Simulation - Std final value: {mc_result['std_final_value']:.4f}")

    # Test portfolio optimization
    print("\nTesting portfolio optimization...")
    opt_result = engine.optimize_portfolio(returns_df, method='min_variance')
    print(f"Min Variance weights: {opt_result['weights']}")
    print(f"Portfolio volatility: {opt_result['volatility']:.4f}")

    print("\nAll tests completed successfully!")


if __name__ == "__main__":
    test_risk_engine()