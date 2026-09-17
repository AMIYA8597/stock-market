# Issues Audit

## Backend Issues
- **Unused Code**: `statsmodels.tsa.statespace.sarimax.SARIMAX` was imported but unused in `app/services/prediction_engine.py` (Fixed).
- **Scalability**: The database logic currently runs all queries directly on PostgreSQL. For high-frequency time series (intraday stock ticks), this might lead to bottlenecks.

## Frontend Issues
- Initial scan pending for ESLint unused variables/imports.

## Structural Issues
- Heavy ML training tasks (like LightGBM/XGBoost) share the same resource pools as the FastAPI application servers if not deployed separately. This could lead to memory leaks or latency spikes during retraining.

## Data Quality Issues
- The ingestion pipeline occasionally processes ticks that might overlap.
- Backtesting Engine needs walk-forward validation without data leakage.

## Security Vulnerabilities
- Checking dependencies...
