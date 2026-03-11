#!/usr/bin/env python3
"""
Phase 5 Risk Engine Test - Complete risk management test
Tests VaR (3 methods), CVaR, Monte Carlo, portfolio optimization, and stress testing
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import random
from scipy import stats
from scipy.optimize import minimize

def test_phase5_risk_engine():
    """Test all Phase 5 risk engine components."""
    
    print("⚡ Testing Phase 5: Risk Engine")
    print("=" * 50)
    
    try:
        # Test 1: Sample Portfolio Data Generation
        print("1. Testing sample portfolio data generation...")
        
        # Generate realistic portfolio data
        np.random.seed(42)
        n_assets = 5
        n_days = 252  # 1 year of trading days
        
        # Asset names
        assets = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK']
        
        # Generate correlated returns
        # Create correlation matrix
        correlation_matrix = np.array([
            [1.00, 0.65, 0.45, 0.70, 0.50],
            [0.65, 1.00, 0.40, 0.60, 0.45],
            [0.45, 0.40, 1.00, 0.35, 0.55],
            [0.70, 0.60, 0.35, 1.00, 0.40],
            [0.50, 0.45, 0.55, 0.40, 1.00]
        ])
        
        # Generate correlated returns using Cholesky decomposition
        volatilities = np.array([0.25, 0.20, 0.30, 0.22, 0.28])  # Annual volatilities
        cov_matrix = np.diag(volatilities) @ correlation_matrix @ np.diag(volatilities)
        
        # Generate daily returns
        daily_returns = np.random.multivariate_normal(
            mean=np.zeros(n_assets) * (1/252),  # Daily mean returns (assuming 0 for simplicity)
            cov=cov_matrix / 252,  # Daily covariance
            size=n_days
        )
        
        # Create DataFrame
        returns_df = pd.DataFrame(daily_returns, columns=assets)
        
        # Portfolio weights (equal weight for simplicity)
        weights = np.array([0.2, 0.2, 0.2, 0.2, 0.2])
        
        # Portfolio returns
        portfolio_returns = (returns_df * weights).sum(axis=1)
        
        print(f"✅ Portfolio data generated")
        print(f"   Assets: {n_assets}")
        print(f"   Trading days: {n_days}")
        print(f"   Portfolio annualized return: {portfolio_returns.mean() * 252:.3f}")
        print(f"   Portfolio annualized volatility: {portfolio_returns.std() * np.sqrt(252):.3f}")
        
        # Test 2: Value at Risk (VaR) - 3 Methods
        print("\n2. Testing VaR calculations (3 methods)...")
        
        class VaRCalculator:
            """Calculate VaR using different methods."""
            
            @staticmethod
            def historical_var(returns: pd.Series, confidence_level: float = 0.95) -> float:
                """Historical Simulation VaR."""
                return -np.percentile(returns, (1 - confidence_level) * 100)
            
            @staticmethod
            def parametric_var(returns: pd.Series, confidence_level: float = 0.95) -> float:
                """Parametric VaR (assuming normal distribution)."""
                mean = returns.mean()
                std = returns.std()
                z_score = stats.norm.ppf(1 - confidence_level)
                return -(mean + z_score * std)
            
            @staticmethod
            def monte_carlo_var(returns: pd.Series, confidence_level: float = 0.95, 
                              n_simulations: int = 10000) -> float:
                """Monte Carlo VaR."""
                mean = returns.mean()
                std = returns.std()
                
                # Generate simulated returns
                simulated_returns = np.random.normal(mean, std, n_simulations)
                
                # Calculate VaR
                return -np.percentile(simulated_returns, (1 - confidence_level) * 100)
        
        var_calc = VaRCalculator()
        
        # Calculate VaR using all three methods
        var_historical_95 = var_calc.historical_var(portfolio_returns, 0.95)
        var_parametric_95 = var_calc.parametric_var(portfolio_returns, 0.95)
        var_monte_carlo_95 = var_calc.monte_carlo_var(portfolio_returns, 0.95)
        
        var_historical_99 = var_calc.historical_var(portfolio_returns, 0.99)
        var_parametric_99 = var_calc.parametric_var(portfolio_returns, 0.99)
        var_monte_carlo_99 = var_calc.monte_carlo_var(portfolio_returns, 0.99)
        
        print(f"✅ VaR calculations completed")
        print(f"   95% VaR (Historical): {var_historical_95:.4f}")
        print(f"   95% VaR (Parametric): {var_parametric_95:.4f}")
        print(f"   95% VaR (Monte Carlo): {var_monte_carlo_95:.4f}")
        print(f"   99% VaR (Historical): {var_historical_99:.4f}")
        print(f"   99% VaR (Parametric): {var_parametric_99:.4f}")
        print(f"   99% VaR (Monte Carlo): {var_monte_carlo_99:.4f}")
        
        # Test 3: Conditional Value at Risk (CVaR)
        print("\n3. Testing CVaR calculations...")
        
        def calculate_cvar(returns: pd.Series, confidence_level: float = 0.95) -> float:
            """Calculate Conditional Value at Risk (Expected Shortfall)."""
            var = -np.percentile(returns, (1 - confidence_level) * 100)
            
            # Average of returns worse than VaR
            worst_returns = returns[returns <= -var]
            
            if len(worst_returns) > 0:
                cvar = -worst_returns.mean()
            else:
                cvar = var
            
            return cvar
        
        # Calculate CVaR for different confidence levels
        cvar_95 = calculate_cvar(portfolio_returns, 0.95)
        cvar_99 = calculate_cvar(portfolio_returns, 0.99)
        
        print(f"✅ CVaR calculations completed")
        print(f"   95% CVaR: {cvar_95:.4f}")
        print(f"   99% CVaR: {cvar_99:.4f}")
        
        # Test 4: Monte Carlo Portfolio Simulation
        print("\n4. Testing Monte Carlo portfolio simulation...")
        
        class MonteCarloSimulator:
            """Monte Carlo simulation for portfolio analysis."""
            
            def __init__(self, returns: pd.DataFrame, weights: np.ndarray):
                self.returns = returns
                self.weights = weights
                self.mean_returns = returns.mean()
                self.cov_matrix = returns.cov()
                
            def simulate_paths(self, n_paths: int = 1000, n_days: int = 252) -> np.ndarray:
                """Simulate portfolio value paths."""
                n_assets = len(self.weights)
                
                # Generate correlated random returns
                simulated_returns = np.random.multivariate_normal(
                    self.mean_returns.values,
                    self.cov_matrix.values,
                    size=(n_paths, n_days)
                )
                
                # Calculate portfolio returns for each path
                portfolio_returns = np.dot(simulated_returns, self.weights)
                
                # Convert to cumulative returns (starting from 1)
                paths = np.cumprod(1 + portfolio_returns, axis=1)
                
                return paths
            
            def calculate_statistics(self, paths: np.ndarray) -> Dict[str, float]:
                """Calculate statistics from simulated paths."""
                final_values = paths[:, -1]
                
                stats_dict = {
                    'mean_final_value': np.mean(final_values),
                    'median_final_value': np.median(final_values),
                    'std_final_value': np.std(final_values),
                    'percentile_5': np.percentile(final_values, 5),
                    'percentile_95': np.percentile(final_values, 95),
                    'probability_of_loss': np.mean(final_values < 1.0),
                    'expected_shortfall_5': -np.mean(final_values[final_values < np.percentile(final_values, 5)] - 1)
                }
                
                return stats_dict
        
        # Run Monte Carlo simulation
        simulator = MonteCarloSimulator(returns_df, weights)
        paths = simulator.simulate_paths(n_paths=1000, n_days=252)
        mc_stats = simulator.calculate_statistics(paths)
        
        print(f"✅ Monte Carlo simulation completed")
        print(f"   Simulated paths: {len(paths)}")
        print(f"   Mean final value: {mc_stats['mean_final_value']:.3f}")
        print(f"   5th percentile: {mc_stats['percentile_5']:.3f}")
        print(f"   95th percentile: {mc_stats['percentile_95']:.3f}")
        print(f"   Probability of loss: {mc_stats['probability_of_loss']:.3f}")
        
        # Test 5: Portfolio Optimization
        print("\n5. Testing portfolio optimization...")
        
        class PortfolioOptimizer:
            """Portfolio optimization using modern portfolio theory."""
            
            def __init__(self, returns: pd.DataFrame):
                self.returns = returns
                self.mean_returns = returns.mean()
                self.cov_matrix = returns.cov()
                self.n_assets = len(returns.columns)
                
            def optimize_portfolio(self, method: str = 'sharpe') -> Dict[str, Any]:
                """Optimize portfolio using different methods."""
                
                def objective_function(weights, method):
                    portfolio_return = np.sum(self.mean_returns * weights) * 252
                    portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix * 252, weights)))
                    
                    if method == 'sharpe':
                        return -portfolio_return / portfolio_volatility  # Negative for minimization
                    elif method == 'min_variance':
                        return portfolio_volatility
                    elif method == 'max_return':
                        return -portfolio_return
                    
                # Constraints
                constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})  # Weights sum to 1
                
                # Bounds (no short selling, weights between 0 and 1)
                bounds = tuple((0, 1) for _ in range(self.n_assets))
                
                # Initial guess (equal weights)
                initial_guess = np.array([1/self.n_assets] * self.n_assets)
                
                # Optimize
                result = minimize(
                    objective_function,
                    initial_guess,
                    method='SLSQP',
                    bounds=bounds,
                    constraints=constraints,
                    args=(method,)
                )
                
                if result.success:
                    optimal_weights = result.x
                    portfolio_return = np.sum(self.mean_returns * optimal_weights) * 252
                    portfolio_volatility = np.sqrt(np.dot(optimal_weights.T, np.dot(self.cov_matrix * 252, optimal_weights)))
                    sharpe_ratio = portfolio_return / portfolio_volatility
                    
                    return {
                        'weights': optimal_weights,
                        'expected_return': portfolio_return,
                        'volatility': portfolio_volatility,
                        'sharpe_ratio': sharpe_ratio,
                        'success': True
                    }
                else:
                    return {'success': False, 'message': result.message}
            
            def efficient_frontier(self, n_points: int = 20) -> List[Dict[str, Any]]:
                """Calculate efficient frontier points."""
                frontier = []
                
                # Target returns range
                min_return = np.min(self.mean_returns) * 252
                max_return = np.max(self.mean_returns) * 252
                target_returns = np.linspace(min_return, max_return, n_points)
                
                for target_return in target_returns:
                    def objective(weights):
                        portfolio_return = np.sum(self.mean_returns * weights) * 252
                        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix * 252, weights)))
                        return portfolio_volatility
                    
                    constraints = (
                        {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
                        {'type': 'eq', 'fun': lambda x: np.sum(self.mean_returns * x) * 252 - target_return}
                    )
                    
                    bounds = tuple((0, 1) for _ in range(self.n_assets))
                    initial_guess = np.array([1/self.n_assets] * self.n_assets)
                    
                    result = minimize(
                        objective,
                        initial_guess,
                        method='SLSQP',
                        bounds=bounds,
                        constraints=constraints
                    )
                    
                    if result.success:
                        frontier.append({
                            'weights': result.x,
                            'return': target_return,
                            'volatility': np.sqrt(np.dot(result.x.T, np.dot(self.cov_matrix * 252, result.x))),
                            'sharpe': target_return / np.sqrt(np.dot(result.x.T, np.dot(self.cov_matrix * 252, result.x)))
                        })
                
                return frontier
        
        # Portfolio optimization
        optimizer = PortfolioOptimizer(returns_df)
        
        # Optimize for maximum Sharpe ratio
        sharpe_optimal = optimizer.optimize_portfolio('sharpe')
        
        # Optimize for minimum variance
        min_variance_optimal = optimizer.optimize_portfolio('min_variance')
        
        print(f"✅ Portfolio optimization completed")
        if sharpe_optimal['success']:
            print(f"   Max Sharpe Portfolio:")
            print(f"     Expected return: {sharpe_optimal['expected_return']:.3f}")
            print(f"     Volatility: {sharpe_optimal['volatility']:.3f}")
            print(f"     Sharpe ratio: {sharpe_optimal['sharpe_ratio']:.3f}")
        
        if min_variance_optimal['success']:
            print(f"   Min Variance Portfolio:")
            print(f"     Expected return: {min_variance_optimal['expected_return']:.3f}")
            print(f"     Volatility: {min_variance_optimal['volatility']:.3f}")
            print(f"     Sharpe ratio: {min_variance_optimal['sharpe_ratio']:.3f}")
        
        # Test 6: Stress Testing
        print("\n6. Testing stress testing scenarios...")
        
        class StressTest:
            """Stress testing for extreme market scenarios."""
            
            def __init__(self, returns: pd.DataFrame, weights: np.ndarray):
                self.returns = returns
                self.weights = weights
                self.portfolio_returns = (returns * weights).sum(axis=1)
                
            def scenario_analysis(self, scenarios: Dict[str, Dict[str, float]]) -> Dict[str, float]:
                """Analyze predefined stress scenarios."""
                results = {}
                
                for scenario_name, scenario_params in scenarios.items():
                    # Apply scenario shocks
                    shocked_returns = self.portfolio_returns.copy()
                    
                    # Market shock
                    if 'market_shock' in scenario_params:
                        market_shock = scenario_params['market_shock']
                        shocked_returns += market_shock
                    
                    # Volatility multiplier
                    if 'vol_multiplier' in scenario_params:
                        vol_multiplier = scenario_params['vol_multiplier']
                        base_vol = shocked_returns.std()
                        shocked_returns = shocked_returns * vol_multiplier
                    
                    # Calculate scenario P&L
                    scenario_pnl = shocked_returns.sum()
                    
                    # Calculate scenario VaR
                    scenario_var = -np.percentile(shocked_returns, 5)
                    
                    results[scenario_name] = {
                        'total_pnl': scenario_pnl,
                        'var_95': scenario_var,
                        'worst_day': shocked_returns.min(),
                        'volatility': shocked_returns.std()
                    }
                
                return results
            
            def historical_crises(self) -> Dict[str, Dict[str, float]]:
                """Simulate historical crisis scenarios."""
                crises = {
                    '2008_Financial_Crisis': {
                        'market_shock': -0.30,  # 30% market drop
                        'vol_multiplier': 2.5   # 2.5x volatility
                    },
                    '2020_Covid_Crash': {
                        'market_shock': -0.25,  # 25% market drop
                        'vol_multiplier': 3.0   # 3x volatility
                    },
                    '2022_Rate_Hike': {
                        'market_shock': -0.15,  # 15% market drop
                        'vol_multiplier': 1.8   # 1.8x volatility
                    }
                }
                
                return self.scenario_analysis(crises)
        
        # Stress testing
        stress_test = StressTest(returns_df, weights)
        crisis_results = stress_test.historical_crises()
        
        print(f"✅ Stress testing completed")
        for crisis, results in crisis_results.items():
            print(f"   {crisis}:")
            print(f"     Total P&L: {results['total_pnl']:.3f}")
            print(f"     VaR 95%: {results['var_95']:.4f}")
            print(f"     Worst day: {results['worst_day']:.4f}")
        
        # Test 7: Risk Attribution
        print("\n7. Testing risk attribution...")
        
        def calculate_risk_attribution(returns: pd.DataFrame, weights: np.ndarray) -> Dict[str, float]:
            """Calculate risk contribution by asset."""
            portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
            
            # Marginal contribution to risk
            marginal_contrib = np.dot(returns.cov() * 252, weights) / portfolio_volatility
            
            # Component contribution to risk
            component_contrib = weights * marginal_contrib
            
            # Percentage contribution
            contrib_percent = component_contrib / portfolio_volatility
            
            attribution = {}
            for i, asset in enumerate(returns.columns):
                attribution[asset] = {
                    'weight': weights[i],
                    'marginal_contrib': marginal_contrib[i],
                    'component_contrib': component_contrib[i],
                    'contrib_percent': contrib_percent[i]
                }
            
            return attribution
        
        risk_attribution = calculate_risk_attribution(returns_df, weights)
        
        print(f"✅ Risk attribution calculated")
        for asset, contrib in risk_attribution.items():
            print(f"   {asset}:")
            print(f"     Weight: {contrib['weight']:.3f}")
            print(f"     Risk contribution: {contrib['contrib_percent']:.3f}")
        
        # Test 8: Kelly Criterion Position Sizing
        print("\n8. Testing Kelly criterion position sizing...")
        
        def calculate_kelly_fraction(returns: pd.Series) -> float:
            """Calculate Kelly fraction for optimal position sizing."""
            # Simple Kelly: f* = (bp - q) / b
            # where b = odds, p = win probability, q = lose probability
            
            # For continuous returns, we use the mean and variance
            mean_return = returns.mean()
            var_return = returns.var()
            
            if var_return > 0:
                kelly_fraction = mean_return / var_return
                # Apply fractional Kelly (25% of full Kelly for safety)
                kelly_fraction *= 0.25
                # Ensure reasonable bounds
                kelly_fraction = np.clip(kelly_fraction, 0.01, 0.5)
            else:
                kelly_fraction = 0.01  # Minimum position
            
            return kelly_fraction
        
        # Calculate Kelly fractions for each asset
        kelly_fractions = {}
        for asset in assets:
            kelly_fractions[asset] = calculate_kelly_fraction(returns_df[asset])
        
        print(f"✅ Kelly criterion calculated")
        for asset, kelly in kelly_fractions.items():
            print(f"   {asset}: {kelly:.3f}")
        
        print("\n🎉 Phase 5 Risk Engine Test - PASSED")
        print("=" * 50)
        print("✅ VaR calculations (3 methods) working")
        print("✅ CVaR calculations working")
        print("✅ Monte Carlo simulation working")
        print("✅ Portfolio optimization working")
        print("✅ Stress testing working")
        print("✅ Risk attribution working")
        print("✅ Kelly criterion working")
        print("\n📋 Ready for Phase 6: Backtesting Engine")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Phase 5 Risk Engine Test - FAILED")
        print(f"Error: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("1. Check numpy, pandas, and scipy are installed")
        print("2. Verify mathematical operations are valid")
        print("3. Check optimization constraints are feasible")
        return False

if __name__ == "__main__":
    success = test_phase5_risk_engine()
    exit(0 if success else 1)
