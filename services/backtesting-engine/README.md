# Backtesting Engine Service

Advanced event-driven backtesting service for NeuroQuant platform. Implements 6 sophisticated trading strategies with comprehensive performance analysis, risk metrics, and PDF report generation.

## Features

- **Event-Driven Architecture**: Market events, signals, orders, fills with proper timestamp ordering
- **6 Trading Strategies**: Kalman pairs trading, adaptive momentum, ML alpha, statistical arbitrage, volatility regime, deep RL agent
- **Comprehensive Analysis**: Sharpe ratio, Sortino, Calmar, maximum drawdown, win rate, profit factor
- **Risk Management**: Position sizing, stop losses, portfolio constraints
- **Walk-Forward Optimization**: Out-of-sample validation with multiple windows
- **Monte Carlo Testing**: Statistical significance testing with permutation analysis
- **PDF Reports**: Professional reports with charts, metrics, and trade logs (WeasyPrint backend)

## Strategies Implemented

### 1. Kalman Filter Pairs Trading
- Cointegration-based pairs trading with time-varying hedge ratios
- Kalman filter for dynamic beta estimation
- Z-score entry/exit thresholds with stop losses

### 2. Adaptive Momentum Strategy
- Dual momentum: absolute + relative momentum
- Regime filtering using volatility-based market state detection
- Volatility-scaled position sizing

### 3. ML Alpha Strategy
- Uses AMSTAN transformer predictions for alpha signals
- Ensemble confidence weighting
- Risk-adjusted position sizing

### 4. Statistical Arbitrage
- Index rebalancing arbitrage
- NSE/BSE announcement monitoring
- Price pressure modeling

### 5. Volatility Regime Strategy
- GARCH-based regime detection
- Mean reversion in high vol, momentum in low vol
- Smooth regime transitions

### 6. Deep RL Agent Strategy
- PPO-trained agent with custom StockTradingEnv
- LSTM backbone for temporal state
- Intrinsic curiosity exploration

## API Endpoints

### Core Backtesting
- `POST /backtest` - Run complete backtest with specified strategy
- `POST /backtest/walk-forward` - Walk-forward parameter optimization
- `POST /backtest/monte-carlo` - Monte Carlo significance testing

### Reporting
- `POST /report/generate` - Generate PDF backtest report

### Utilities
- `GET /strategies` - List available strategies
- `GET /strategies/{name}/params` - Get strategy parameters

## Request Examples

### Run Backtest
```json
{
  "strategy_name": "adaptive_momentum",
  "strategy_params": {
    "momentum_period": 126,
    "vol_lookback": 20,
    "regime_filter": true
  },
  "symbols": ["RELIANCE.NS", "TCS.NS", "INFY.NS"],
  "start_date": "2020-01-01",
  "end_date": "2024-01-01",
  "initial_capital": 1000000,
  "commission_rate": 0.001,
  "slippage_rate": 0.0005
}
```

### Walk-Forward Optimization
```json
{
  "strategy_name": "adaptive_momentum",
  "param_ranges": {
    "momentum_period": [60, 90, 126, 252],
    "vol_lookback": [10, 20, 30]
  },
  "symbols": ["NIFTY50"],
  "start_date": "2020-01-01",
  "end_date": "2024-01-01",
  "n_windows": 5,
  "metric": "sharpe"
}
```

## Performance Metrics

- **Return Metrics**: Total return, annual return, CAGR
- **Risk Metrics**: Volatility, Sharpe ratio, Sortino ratio, Calmar ratio, max drawdown
- **Trade Metrics**: Win rate, profit factor, average win/loss, total trades
- **Portfolio Metrics**: Beta, correlation, VaR contributions

## PDF Report Features

- Executive summary with key metrics
- Performance charts (equity curve, drawdown)
- Monthly returns calendar heatmap
- Trade analysis with top winners/losers
- Risk decomposition
- Statistical significance tests
- Mathematical methodology (LaTeX-rendered)

## Dependencies

- fastapi: Web framework
- pandas/numpy: Data manipulation
- weasyprint: PDF generation
- scipy: Statistical calculations
- scikit-learn: ML utilities

## Running the Service

### Local Development
```bash
pip install -r requirements.txt
python -m app.main
```

### Docker
```bash
docker build -t neuroquant-backtesting .
docker run -p 8005:8005 neuroquant-backtesting
```

## Integration

The backtesting engine integrates with:
- **Data Pipeline**: Historical OHLCV data for backtesting
- **ML Engine**: Strategy signals and predictions
- **Risk Engine**: Position sizing and risk constraints
- **Gateway**: REST API for frontend backtesting interface
- **Alert Service**: Trade execution notifications

## Testing

Run comprehensive tests:
```bash
python test_backtesting.py
```

Tests validate:
- All 6 strategies execute without errors
- Performance metrics calculation accuracy
- PDF report generation
- Monte Carlo significance testing
- Walk-forward optimization logic