# Risk Engine Service

Portfolio risk calculation service for NeuroQuant platform. Provides comprehensive risk analytics including Value at Risk (VaR), Conditional VaR (CVaR), Monte Carlo simulation, portfolio optimization, and stress testing.

## Features

- **VaR Calculations**: Historical, parametric, and Monte Carlo methods
- **CVaR (Expected Shortfall)**: Conditional Value at Risk calculations
- **Monte Carlo Simulation**: Portfolio simulation with correlation modeling
- **Portfolio Optimization**: Mean-variance, minimum variance, maximum Sharpe ratio, and Hierarchical Risk Parity
- **Stress Testing**: Scenario-based stress testing with custom shocks

## API Endpoints

### Health Check
- `GET /health` - Service health status

### Risk Calculations
- `POST /var` - Calculate Value at Risk
- `POST /cvar` - Calculate Conditional VaR
- `POST /monte-carlo` - Run Monte Carlo simulation
- `POST /optimize` - Portfolio optimization
- `POST /stress-test` - Stress testing

### Utilities
- `GET /methods` - Available calculation methods

## Request Formats

### VaR Request
```json
{
  "returns_data": {
    "Asset1": [0.01, -0.005, 0.008, ...],
    "Asset2": [0.002, 0.003, -0.001, ...]
  },
  "weights": [0.6, 0.4],
  "confidence_level": 0.95,
  "position_size": 1000000,
  "method": "historical"
}
```

### Monte Carlo Request
```json
{
  "returns_data": {...},
  "weights": [0.5, 0.3, 0.2],
  "n_simulations": 1000,
  "n_days": 252,
  "confidence_level": 0.95
}
```

## Running the Service

### Local Development
```bash
pip install -r requirements.txt
python -m app.main
```

### Docker
```bash
docker build -t neuroquant-risk-engine .
docker run -p 8004:8004 neuroquant-risk-engine
```

## Dependencies

- fastapi: Web framework
- pandas/numpy: Data manipulation
- scipy/scikit-learn: Statistical calculations
- cvxpy: Convex optimization
- hmmlearn: Hidden Markov Models (for regime detection integration)

## Integration

The risk engine integrates with:
- **Data Pipeline**: Receives market data and returns
- **ML Engine**: Uses regime detection for risk adjustments
- **Gateway**: REST API endpoints for frontend consumption
- **Backtesting Engine**: Risk metrics for strategy evaluation