"""
Risk engine service.

Computes portfolio risk metrics:
- VaR / CVaR (Historical + Monte Carlo)
- Position sizing (Kelly Criterion, volatility-scaled)
- Drawdown analysis, Sharpe/Sortino/Calmar ratios
- Correlation matrices, factor exposures
- Efficient frontier optimization via PyPortfolioOpt

Fully implemented in Phase 5.
"""
