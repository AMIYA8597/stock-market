# QuantEdge API Contract

## Base URL
`/api/v1`

## Authentication
Routes marked with `[AUTH]` require a valid JWT Bearer token in the `Authorization` header.

## Market Data (`/market`)

### `GET /market/universe`
Returns a list of tradable instruments.
**Response**: `List[InstrumentSchema]`
```json
[
  {
    "symbol": "RELIANCE",
    "displayName": "Reliance Industries",
    "exchange": "NSE",
    "yfinanceTicker": "RELIANCE.NS"
  }
]
```

### `GET /market/quote/{symbol}`
Returns real-time quote for a symbol.
**Response**: `QuoteSchema`
```json
{
  "symbol": "RELIANCE",
  "price": 2900.5,
  "change": 15.2,
  "changePercent": 0.52,
  "volume": 1250000,
  "timestamp": 1718204500,
  "source": "yfinance"
}
```

### `GET /market/history/{symbol}?interval=1d&period=1y`
Returns de-duplicated ascending OHLCV bars.
**Response**: `HistorySchema` (Array of objects)
```json
[
  {
    "time": 1718204500,
    "open": 2800.0,
    "high": 2900.0,
    "low": 2790.0,
    "close": 2900.5,
    "volume": 1250000
  }
]
```

## Signals (`/signals`)

### `GET /signals/{symbol}`
Returns computed signals and technical breakdown.
**Response**: `SignalSchema`
```json
{
  "symbol": "RELIANCE",
  "signal": "BUY",
  "confidence": 75.5,
  "timestamp": 1718204500,
  "indicators": [
    {"name": "RSI", "value": "45.0", "signal": "BUY"},
    {"name": "MACD", "value": "1.2", "signal": "BUY"}
  ]
}
```

## Backtesting (`/backtest`) [AUTH]

### `POST /backtest/run`
Submit a backtest job.
**Request**:
```json
{
  "strategy_name": "ml_alpha",
  "strategy_params": {"commission_pct": 0.001},
  "universe": ["RELIANCE", "TCS"],
  "date_from": "2023-01-01",
  "date_to": "2023-12-31",
  "initial_capital": 100000.0
}
```
**Response**: `202 Accepted` with `{"job_id": "uuid", "status": "PENDING"}`

### `GET /backtest/status/{job_id}`
### `GET /backtest/results/{job_id}`

## WebSockets
`ws://localhost:8000/ws/alerts`
`ws://localhost:8000/ws/prices`
`ws://localhost:8000/ws/signals`
`ws://localhost:8000/ws/backtest-progress`
`ws://localhost:8000/ws/live/{symbol}`
