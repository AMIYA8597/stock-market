# QuantEdge API Documentation

## Base URL
`/api/v1`

## Endpoints

### 1. General & Market
* **`GET /health`** - System health check.
* **`GET /market/status`** - Market timings and status (open/close, next holidays).
* **`GET /market/indices`** - Broad market indices performance.

### 2. Machine Learning & Predictions
* **`GET /predictions/latest/{symbol}`** - Latest ML prediction for `{symbol}`. Returns direction probability, expected move range (from GARCH), current regime (from HMM), and model confidence.
* **`GET /predictions/history/{symbol}`** - Historical walk-forward CV performance of the models for `{symbol}`.
* **`GET /explain/shap/{symbol}`** - SHAP feature importances for the current model for `{symbol}`. Used for explainability waterfalls.
* **`GET /regime/{symbol}/current`** - Returns the current identified market regime (Bull, Bear, Sideways) for the symbol.
* **`GET /regime/{symbol}/history`** - Returns the HMM regime timeline over a specified lookback period.

### 3. Signals & Screener
* **`GET /signals/algorithmic/{symbol}`** - Returns composite technical signals (RSI, MACD, Bollinger Bands, etc.) for `{symbol}`.
* **`GET /screener/movers`** - Market movers screeners (top gainers/losers).

### 4. News & Sentiment
* **`GET /news/{symbol}`** - Real live-news stream for `{symbol}` tagged with FinBERT sentiment scores.

### 5. Paper Trading & Portfolio
* **`POST /trading/order`** - Place a mock order in the paper trading engine.
* **`GET /portfolio/holdings`** - Current positions and unrealized PnL.
* **`GET /portfolio/performance`** - Historical portfolio performance and risk metrics (Sharpe, Beta, Alpha).

### 6. Admin & Payments (Test-Mode)
* **`POST /payments/create-order`** - Initiates a Razorpay-style test-mode order for subscription handling.
* **`POST /payments/verify`** - Verifies test-mode payment signatures.
* **`GET /auth/me`** - Returns the current authenticated user's session profile.

## Error Handling
The API strictly uses typed JSON error responses (e.g., `404 Not Found`, `422 Validation Error`, `503 Service Unavailable`). Fake dummy data is never served for a missing resource.
