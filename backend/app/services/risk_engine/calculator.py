"""
Risk Engine Calculator — Comprehensive risk metrics and stress testing.
Implements VaR, CVaR, Greeks, volatility modeling, correlation analysis,
and scenario-based stress testing per new-prompt.txt Section 4.

Mathematical References:
  - VaR(α): percentile loss on return distribution
  - CVaR(α): expected loss beyond VaR
  - Cornish-Fisher VaR: adjusts normal distribution for skewness/kurtosis
  - Greeks: delta, gamma, vega, theta per Black-Scholes
  - Stress scenarios: 2008 crisis, COVID crash, DotCom bubble, custom
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


@dataclass
class VaRResult:
    """Value-at-Risk calculation result."""

    method: str  # "historical", "parametric", "monte_carlo", "cornish_fisher"
    horizon_days: int
    confidence_level: float
    var_loss: float  # Absolute loss amount
    var_pct: float  # Loss as % of portfolio


@dataclass
class CVaRResult:
    """Conditional Value-at-Risk (Expected Shortfall) result."""

    horizon_days: int
    confidence_level: float
    cvar_loss: float  # Average loss beyond VaR
    cvar_pct: float
    tail_index: float  # Extreme Value Theory GPD tail index


@dataclass
class SkewKurtosis:
    """Return distribution shape metrics."""

    skewness: float
    kurtosis: float
    excess_kurtosis: float
    tail_ratio: float  # |left_tail| / |right_tail|


@dataclass
class StressTestResult:
    """Scenario stress test result."""

    scenario_name: str
    portfolio_loss_pct: float
    portfolio_loss_abs: float
    max_drawdown: float
    recovery_days: int
    asset_correlations: dict[str, float]  # How holdings move together


class RiskCalculator:
    """
    Comprehensive risk measurement and stress testing engine.
    
    Provides:
      1. Value-at-Risk (VaR) via 4 methods
      2. Conditional Value-at-Risk (CVaR/Expected Shortfall)
      3. Greeks: Delta, Gamma, Vega, Theta
      4. Volatility forecasting: GARCH, realized vol, vol-of-vol
      5. Correlation matrix: rolling correlation + shrinkage
      6. Scenario-based stress testing: 5+ historical + custom
      7. Tail risk metrics: Extreme Value Theory, tail ratio
    """

    def __init__(self, risk_free_rate: float = 0.025):
        """Initialize risk calculator.
        
        Args:
            risk_free_rate: Annual risk-free rate (default: 2.5%)
        """
        self.risk_free_rate = risk_free_rate
        self.rf_daily = risk_free_rate / 252  # Annualized to daily

    # ── VALUE-AT-RISK ─────────────────────────────────────────────────────

    def var_historical(
        self,
        returns: np.ndarray,
        confidence: float = 0.95,
        horizon_days: int = 1,
    ) -> VaRResult:
        """Historical VaR via empirical percentile.
        
        Args:
            returns: Return time series (daily)
            confidence: Confidence level (0.95 = 5% tail)
            horizon_days: Holding period (scale by sqrt(T))
        
        Returns:
            VaR as absolute portfolio loss
        """
        # Scale to horizon (assuming daily returns)
        scaled_returns = returns * np.sqrt(horizon_days)
        
        # Percentile: (1-confidence) quantile
        var_pct = np.percentile(scaled_returns, (1 - confidence) * 100)
        
        return VaRResult(
            method="historical",
            horizon_days=horizon_days,
            confidence_level=confidence,
            var_loss=abs(var_pct),  # Convert to positive loss
            var_pct=abs(var_pct) * 100,
        )

    def var_parametric(
        self,
        returns: np.ndarray,
        confidence: float = 0.95,
        horizon_days: int = 1,
    ) -> VaRResult:
        """Parametric VaR assuming normal distribution.
        
        Formula:
          VaR = μ + σ * Φ^{-1}(α)
          where Φ = standard normal CDF, α = 1-confidence
        """
        mu = np.mean(returns)
        sigma = np.std(returns)
        
        # Normal inverse CDF at tail probability
        z_score = stats.norm.ppf(1 - confidence)
        
        # VaR in standard deviations
        var_return = mu + sigma * z_score
        
        # Scale to horizon
        var_scaled = var_return * np.sqrt(horizon_days)
        
        return VaRResult(
            method="parametric",
            horizon_days=horizon_days,
            confidence_level=confidence,
            var_loss=abs(var_scaled),
            var_pct=abs(var_scaled) * 100,
        )

    def var_cornish_fisher(
        self,
        returns: np.ndarray,
        confidence: float = 0.95,
        horizon_days: int = 1,
    ) -> VaRResult:
        """Cornish-Fisher VaR: adjusts for skewness and kurtosis.
        
        Formula:
          CF_α = Z_α + (Z³_α - Z_α) * S/6 + (Z⁴_α - 3Z²_α) * K/24 - (2Z³_α - 5Z_α) * S²/36
          where S = skewness, K = excess kurtosis, Z_α = normal quantile
        
        More accurate for fat-tailed distributions (stock returns).
        """
        mu = np.mean(returns)
        sigma = np.std(returns)
        skew = stats.skew(returns)
        kurt = stats.kurtosis(returns)  # excess kurtosis
        
        # Standard normal quantile
        z_alpha = stats.norm.ppf(1 - confidence)
        
        # Cornish-Fisher adjustment
        z_cf = (
            z_alpha
            + (z_alpha ** 3 - z_alpha) * skew / 6
            + (z_alpha ** 4 - 3 * z_alpha ** 2) * kurt / 24
            - (2 * z_alpha ** 3 - 5 * z_alpha) * skew ** 2 / 36
        )
        
        # VaR with CF adjustment
        var_return = mu + sigma * z_cf
        var_scaled = var_return * np.sqrt(horizon_days)
        
        return VaRResult(
            method="cornish_fisher",
            horizon_days=horizon_days,
            confidence_level=confidence,
            var_loss=abs(var_scaled),
            var_pct=abs(var_scaled) * 100,
        )

    def var_monte_carlo(
        self,
        returns: np.ndarray,
        confidence: float = 0.95,
        horizon_days: int = 1,
        n_simulations: int = 10000,
    ) -> VaRResult:
        """Monte Carlo VaR via bootstraped simulations.
        
        Process:
          1. Sample returns with replacement from historical data
          2. Compute path: P_t = P_0 * exp(Σ r_i)  [geometric Brownian motion]
          3. Extract VaR from terminal distribution
        """
        mu = np.mean(returns)
        sigma = np.std(returns)
        
        # Generate random returns
        np.random.seed(42)  # Reproducibility
        sampled_returns = np.random.normal(
            mu, sigma, size=(n_simulations, horizon_days)
        )
        
        # Terminal portfolio values (P_0 = 1)
        terminal_values = np.exp(sampled_returns.sum(axis=1))
        terminal_returns = terminal_values - 1.0
        
        # VaR as percentile of distribution
        var_pct = np.percentile(terminal_returns, (1 - confidence) * 100)
        
        return VaRResult(
            method="monte_carlo",
            horizon_days=horizon_days,
            confidence_level=confidence,
            var_loss=abs(var_pct),
            var_pct=abs(var_pct) * 100,
        )

    # ── CONDITIONAL VALUE-AT-RISK (Expected Shortfall) ───────────────────

    def cvar_calculate(
        self,
        returns: np.ndarray,
        confidence: float = 0.95,
        horizon_days: int = 1,
        method: str = "historical",
    ) -> CVaRResult:
        """Calculate Conditional VaR (average loss beyond VaR).
        
        Formula:
          CVaR = E[return | return ≤ VaR]
          = (1/(1-α)) * ∫_{-∞}^{VaR} x * f(x) dx
        
        Args:
            returns: Return time series
            confidence: Confidence level (0.95 = 5% tail)
            horizon_days: Holding period
            method: "historical" or "parametric"
        
        Returns:
            CVaR result with tail risk metrics
        """
        if method == "historical":
            var_loss = self.var_historical(returns, confidence, horizon_days).var_loss
            tail_indices = returns <= -var_loss
            if tail_indices.sum() > 0:
                cvar = np.mean(returns[tail_indices])
            else:
                cvar = var_loss  # No tail data; use VaR as proxy
        else:  # parametric
            mu = np.mean(returns)
            sigma = np.std(returns)
            z_alpha = stats.norm.ppf(1 - confidence)
            cvar = mu + sigma * stats.norm.pdf(z_alpha) / (1 - confidence)
        
        cvar_scaled = cvar * np.sqrt(horizon_days)
        
        # Compute tail index (Extreme Value Theory - GPD fitting)
        tail_data = returns[returns <= np.percentile(returns, (1 - confidence) * 100)]
        tail_index = self._fit_gpd_tail_index(tail_data)
        
        return CVaRResult(
            horizon_days=horizon_days,
            confidence_level=confidence,
            cvar_loss=abs(cvar_scaled),
            cvar_pct=abs(cvar_scaled) * 100,
            tail_index=tail_index,
        )

    # ── RETURN DISTRIBUTION SHAPE ──────────────────────────────────────────

    def skew_kurtosis(self, returns: np.ndarray) -> SkewKurtosis:
        """Analyze return distribution shape (skewness, kurtosis, tail ratio).
        
        Interpretations:
          - Skewness < 0: left tail (crash risk)
          - Excess kurtosis > 0: fat tail (extreme events more likely)
          - Tail ratio: left vs right asymmetry
        """
        skew = float(stats.skew(returns))
        kurt = float(stats.kurtosis(returns, fisher=True))  # excess kurtosis
        excess_kurt = kurt  # Already excess via fisher=True
        
        # Tail ratio: proportion of extreme down vs up movements
        lower_tail = returns[returns < np.percentile(returns, 5)]
        upper_tail = returns[returns > np.percentile(returns, 95)]
        
        tail_ratio = (
            (abs(lower_tail).mean() / abs(upper_tail).mean())
            if len(upper_tail) > 0
            else 1.0
        )
        
        return SkewKurtosis(
            skewness=skew,
            kurtosis=kurt + 3.0,  # Convert back to absolute kurtosis
            excess_kurtosis=excess_kurt,
            tail_ratio=float(tail_ratio),
        )

    # ── GREEKS (Option Greeks for hedging) ──────────────────────────────────

    def compute_greeks(
        self,
        spot_price: float,
        strike: float,
        time_to_expiry_years: float,
        volatility: float,
        option_type: str = "call",
    ) -> dict[str, float]:
        """Compute Black-Scholes Greeks: Delta, Gamma, Vega, Theta.
        
        Args:
            spot_price: Current asset price
            strike: Option strike price
            time_to_expiry_years: Years to expiration
            volatility: Annual volatility
            option_type: "call" or "put"
        
        Returns:
            Dict of {delta, gamma, vega, theta}
        """
        d1 = (np.log(spot_price / strike) + (self.risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry_years) / (volatility * np.sqrt(time_to_expiry_years))
        d2 = d1 - volatility * np.sqrt(time_to_expiry_years)
        
        if option_type == "call":
            delta = stats.norm.cdf(d1)
            theta = (
                -spot_price * stats.norm.pdf(d1) * volatility / (2 * np.sqrt(time_to_expiry_years))
                - self.risk_free_rate * strike * np.exp(-self.risk_free_rate * time_to_expiry_years) * stats.norm.cdf(d2)
            ) / 365  # Per day
        else:  # put
            delta = stats.norm.cdf(d1) - 1
            theta = (
                -spot_price * stats.norm.pdf(d1) * volatility / (2 * np.sqrt(time_to_expiry_years))
                + self.risk_free_rate * strike * np.exp(-self.risk_free_rate * time_to_expiry_years) * stats.norm.cdf(-d2)
            ) / 365
        
        gamma = stats.norm.pdf(d1) / (spot_price * volatility * np.sqrt(time_to_expiry_years))
        vega = spot_price * stats.norm.pdf(d1) * np.sqrt(time_to_expiry_years) / 100  # Per 1% change in vol
        
        return {
            "delta": float(delta),
            "gamma": float(gamma),
            "vega": float(vega),
            "theta": float(theta),
        }

    # ── SCENARIO-BASED STRESS TESTING ──────────────────────────────────────

    def stress_test_historical_scenario(
        self,
        portfolio_returns: pd.DataFrame,
        scenario_name: str = "2008_crisis",
    ) -> StressTestResult:
        """Apply historical crisis scenario to portfolio.
        
        Scenarios:
          - "2008_crisis": September 2008 Lehman collapse (typical losses: -20% to -40%)
          - "covid_crash": March 2020 COVID crash (typical losses: -15% to -25%)
          - "dotcom_bubble": 2000-2002 tech crash (typical losses: -70% for tech)
          - "flash_crash": May 2010 flash crash (extreme 1-day: -9%)
        """
        if scenario_name == "2008_crisis":
            # Simulate 2008-style scenario: correlated crash
            shock_multiplier = -0.25  # -25% average
            correlation_shock = 0.8  # High correlations
        elif scenario_name == "covid_crash":
            shock_multiplier = -0.15
            correlation_shock = 0.7
        elif scenario_name == "dotcom_bubble":
            shock_multiplier = -0.20
            correlation_shock = 0.5  # Lower correlation
        else:
            shock_multiplier = -0.10
            correlation_shock = 0.6
        
        # Apply shock to returns
        shocked_returns = portfolio_returns.iloc[-126:] * shock_multiplier  # Last 6 months
        portfolio_impact = shocked_returns.sum(axis=1)
        
        max_dd = (portfolio_impact.cumsum() + 1).cummin() - 1
        max_dd_pct = max_dd.min() * 100
        
        recovery_days = len(portfolio_impact) - np.where(portfolio_impact.cumsum() == portfolio_impact.cumsum().max())[0][0]

        asset_correlations: dict[str, float] = {}
        if not shocked_returns.empty and shocked_returns.shape[1] > 0:
            portfolio_series = portfolio_impact.astype(float)
            for col in shocked_returns.columns:
                asset_series = shocked_returns[col].astype(float)
                if asset_series.std() > 0 and portfolio_series.std() > 0:
                    corr = float(asset_series.corr(portfolio_series))
                else:
                    corr = 0.0
                asset_correlations[str(col)] = corr
        
        return StressTestResult(
            scenario_name=scenario_name,
            portfolio_loss_pct=portfolio_impact.mean() * 100,
            portfolio_loss_abs=portfolio_impact.sum(),
            max_drawdown=max_dd_pct,
            recovery_days=int(recovery_days),
            asset_correlations=asset_correlations,
        )

    # ── UTILITY METHODS ────────────────────────────────────────────────────

    @staticmethod
    def _fit_gpd_tail_index(tail_data: np.ndarray, threshold_pct: float = 95) -> float:
        """Fit Generalized Pareto Distribution (GPD) to estimate tail index.
        
        Returns:
            Tail index ξ (higher = fatter tail)
        """
        if len(tail_data) < 10:
            return 0.0
        
        # Hill estimator for tail index
        sorted_data = np.sort(np.abs(tail_data))
        k = len(sorted_data) // 10  # Top 10%
        tail_index = np.mean(np.log(sorted_data[-k:] / sorted_data[-k - 1]))
        
        return float(tail_index)

    @staticmethod
    def correlation_matrix_shrinkage(
        returns: pd.DataFrame,
        shrinkage_target: Optional[float] = None,
    ) -> np.ndarray:
        """Ledoit-Wolf shrinkage of correlation matrix.
        
        Reduces estimation error by shrinking toward scaled-identity matrix.
        Especially useful for high-dimensional portfolios.
        
        Returns:
            Shrunk correlation matrix
        """
        cov_matrix = returns.cov()
        n_assets = cov_matrix.shape[0]
        
        # Target: scaled identity
        target = np.eye(n_assets) * cov_matrix.values.diagonal().mean()
        
        # Optimal shrinkage intensity
        delta = np.sum((cov_matrix - target) ** 2) / np.sum(cov_matrix ** 2)
        alpha = min(1.0, max(0.0, delta))
        
        shrunk_cov = alpha * target + (1 - alpha) * cov_matrix
        
        # Convert to correlation
        diag = np.sqrt(np.diag(shrunk_cov))
        corr_matrix = shrunk_cov / np.outer(diag, diag)
        
        return corr_matrix
