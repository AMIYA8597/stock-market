"""Risk Engine Service for NeuroQuant.

Calculates portfolio risk metrics: VaR, CVaR, stress testing, optimization.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import logging
from scipy.stats import norm, t
from sklearn.covariance import LedoitWolf
import cvxpy as cp

logger = logging.getLogger(__name__)


class RiskEngine:
    """Portfolio risk calculation engine."""

    def __init__(self):
        self.confidence_levels = [0.95, 0.99, 0.999]

    def calculate_var(self, returns: pd.DataFrame, method: str = 'historical',
                     confidence: float = 0.95, position: float = 1.0) -> Dict[str, float]:
        """
        Calculate Value at Risk using different methods.

        Args:
            returns: DataFrame of asset returns [n_periods, n_assets]
            method: 'historical', 'parametric', 'monte_carlo'
            confidence: Confidence level (0.95, 0.99, etc.)
            position: Portfolio position size

        Returns:
            Dict with VaR values for different methods
        """
        if method == 'historical':
            return self._var_historical(returns, confidence, position)
        elif method == 'parametric':
            return self._var_parametric(returns, confidence, position)
        elif method == 'monte_carlo':
            return self._var_monte_carlo(returns, confidence, position)
        else:
            raise ValueError(f"Unknown VaR method: {method}")

    def _var_historical(self, returns: pd.DataFrame, confidence: float, position: float) -> Dict[str, float]:
        """Historical simulation VaR."""
        portfolio_returns = returns.sum(axis=1)  # Equal weighted for simplicity
        var = -np.percentile(portfolio_returns, (1 - confidence) * 100)
        return {'var_historical': var * position}

    def _var_parametric(self, returns: pd.DataFrame, confidence: float, position: float) -> Dict[str, float]:
        """Parametric VaR using normal distribution."""
        portfolio_returns = returns.sum(axis=1)
        mean = portfolio_returns.mean()
        std = portfolio_returns.std()

        # DCC-GARCH would be more sophisticated, but this is simplified
        var = -(mean + std * norm.ppf(1 - confidence))
        return {'var_parametric': var * position}

    def _var_monte_carlo(self, returns: pd.DataFrame, confidence: float, position: float,
                        n_simulations: int = 10000) -> Dict[str, float]:
        """Monte Carlo VaR simulation."""
        portfolio_returns = returns.sum(axis=1)

        # Fit t-distribution to returns
        params = t.fit(portfolio_returns)
        df, loc, scale = params

        # Generate simulations
        simulated_returns = t.rvs(df, loc=loc, scale=scale, size=n_simulations)

        # Calculate VaR
        var = -np.percentile(simulated_returns, (1 - confidence) * 100)
        return {'var_monte_carlo': var * position}

    def calculate_cvar(self, returns: pd.DataFrame, confidence: float = 0.95,
                      position: float = 1.0) -> Dict[str, float]:
        """Calculate Conditional VaR (Expected Shortfall)."""
        portfolio_returns = returns.sum(axis=1)

        # Find returns beyond VaR threshold
        var_threshold = -np.percentile(portfolio_returns, (1 - confidence) * 100)
        tail_returns = portfolio_returns[portfolio_returns <= -var_threshold]

        if len(tail_returns) == 0:
            cvar = var_threshold  # Fallback
        else:
            cvar = -tail_returns.mean()

        return {'cvar': cvar * position}

    def monte_carlo_simulation(self, returns: pd.DataFrame, weights: np.ndarray,
                              n_simulations: int = 1000, n_days: int = 252) -> Dict[str, Any]:
        """
        Monte Carlo portfolio simulation.

        Args:
            returns: Historical returns DataFrame
            weights: Portfolio weights array
            n_simulations: Number of simulation paths
            n_days: Number of days to simulate

        Returns:
            Dict with simulation results
        """
        # Estimate parameters
        mu = returns.mean().values
        cov_matrix = returns.cov().values

        # Cholesky decomposition for correlated simulations
        L = np.linalg.cholesky(cov_matrix)

        # Generate simulations
        simulated_returns = []
        for _ in range(n_simulations):
            # Generate random normal returns
            z = np.random.normal(0, 1, (n_days, len(weights)))
            # Apply correlation structure
            correlated_returns = z @ L.T
            # Apply historical mean and volatility scaling
            scaled_returns = correlated_returns * returns.std().values + mu

            # Calculate portfolio returns
            portfolio_returns = scaled_returns @ weights
            simulated_returns.append(portfolio_returns)

        simulated_returns = np.array(simulated_returns)

        # Calculate statistics
        final_values = np.exp(np.sum(simulated_returns, axis=1))  # Assuming log returns
        percentiles = np.percentile(final_values, [10, 25, 50, 75, 90])

        return {
            'simulations': simulated_returns,
            'final_values': final_values,
            'percentiles': {
                'p10': percentiles[0],
                'p25': percentiles[1],
                'p50': percentiles[2],
                'p75': percentiles[3],
                'p90': percentiles[4]
            },
            'mean_final_value': np.mean(final_values),
            'std_final_value': np.std(final_values)
        }

    def optimize_portfolio(self, returns: pd.DataFrame, method: str = 'mean_variance',
                          target_return: Optional[float] = None) -> Dict[str, Any]:
        """
        Portfolio optimization using different methods.

        Args:
            returns: Historical returns DataFrame
            method: 'mean_variance', 'min_variance', 'max_sharpe', 'hrp'
            target_return: Target portfolio return (for mean-variance)

        Returns:
            Dict with optimal weights and metrics
        """
        n_assets = len(returns.columns)
        mu = returns.mean().values
        cov = returns.cov().values

        if method == 'mean_variance':
            return self._optimize_mean_variance(mu, cov, target_return)
        elif method == 'min_variance':
            return self._optimize_min_variance(cov)
        elif method == 'max_sharpe':
            return self._optimize_max_sharpe(mu, cov)
        elif method == 'hrp':
            return self._optimize_hrp(returns)
        else:
            raise ValueError(f"Unknown optimization method: {method}")

    def _optimize_mean_variance(self, mu: np.ndarray, cov: np.ndarray,
                               target_return: Optional[float]) -> Dict[str, Any]:
        """Mean-variance optimization."""
        n = len(mu)
        w = cp.Variable(n)

        if target_return is None:
            target_return = np.mean(mu)

        # Objective: minimize portfolio variance
        objective = cp.Minimize(cp.quad_form(w, cov))

        # Constraints
        constraints = [
            cp.sum(w) == 1,  # Fully invested
            w >= 0,          # Long only
            mu @ w >= target_return  # Target return
        ]

        problem = cp.Problem(objective, constraints)
        problem.solve()

        if problem.status != 'optimal':
            raise ValueError("Optimization failed")

        weights = w.value
        portfolio_return = mu @ weights
        portfolio_vol = np.sqrt(weights @ cov @ weights)

        return {
            'weights': weights,
            'expected_return': portfolio_return,
            'volatility': portfolio_vol,
            'sharpe_ratio': portfolio_return / portfolio_vol if portfolio_vol > 0 else 0
        }

    def _optimize_min_variance(self, cov: np.ndarray) -> Dict[str, Any]:
        """Minimum variance portfolio."""
        n = cov.shape[0]
        w = cp.Variable(n)

        objective = cp.Minimize(cp.quad_form(w, cov))
        constraints = [cp.sum(w) == 1, w >= 0]

        problem = cp.Problem(objective, constraints)
        problem.solve()

        weights = w.value
        portfolio_vol = np.sqrt(weights @ cov @ weights)

        return {
            'weights': weights,
            'volatility': portfolio_vol
        }

    def _optimize_max_sharpe(self, mu: np.ndarray, cov: np.ndarray) -> Dict[str, Any]:
        """Maximum Sharpe ratio portfolio."""
        n = len(mu)
        w = cp.Variable(n)

        objective = cp.Maximize(mu @ w / cp.sqrt(cp.quad_form(w, cov)))
        constraints = [cp.sum(w) == 1, w >= 0]

        problem = cp.Problem(objective, constraints)
        problem.solve()

        weights = w.value
        portfolio_return = mu @ weights
        portfolio_vol = np.sqrt(weights @ cov @ weights)

        return {
            'weights': weights,
            'expected_return': portfolio_return,
            'volatility': portfolio_vol,
            'sharpe_ratio': portfolio_return / portfolio_vol
        }

    def _optimize_hrp(self, returns: pd.DataFrame) -> Dict[str, Any]:
        """Hierarchical Risk Parity optimization."""
        # Simplified HRP implementation
        # In practice, this involves clustering assets and recursive bisection
        n = len(returns.columns)
        weights = np.ones(n) / n  # Equal weight as simplification

        return {
            'weights': weights,
            'method': 'hrp_simplified'
        }

    def stress_test(self, returns: pd.DataFrame, weights: np.ndarray,
                   scenarios: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """
        Stress testing with predefined scenarios.

        Args:
            returns: Historical returns DataFrame
            weights: Portfolio weights
            scenarios: Dict of scenario_name -> {asset: shock_value}

        Returns:
            Dict with stress test results
        """
        results = {}

        for scenario_name, shocks in scenarios.items():
            # Apply shocks to expected returns
            stressed_mu = returns.mean().copy()
            for asset, shock in shocks.items():
                if asset in stressed_mu.index:
                    stressed_mu[asset] *= (1 + shock)

            # Calculate stressed portfolio return
            portfolio_return = weights @ stressed_mu.values

            results[scenario_name] = {
                'portfolio_return': portfolio_return,
                'shocks': shocks
            }

        return results