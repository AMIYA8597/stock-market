# Performance Audit

## Backend (FastAPI / PyTorch)
- **Bottlenecks identified**:
  - Training tasks running synchronously or on the same nodes as the main API could freeze the event loop.
  - Ingestion tasks (fetching 1-minute candles for all NSE stocks) currently do not utilize a distributed cluster, limiting ingestion speed.
- **Recommendations**:
  - Offload heavy ML inference (XGBoost, LSTMs) to dedicated GPU instances or separate Ray clusters.
  - Implement a TimescaleDB continuous aggregate for querying OHLCV rollups (5m, 15m, 1H) efficiently.

## Frontend (Next.js)
- **Rendering**: TradingView charts are optimized but rendering hundreds of signals simultaneously may drop framerates.
- **Recommendations**:
  - Implement windowing/virtualization for long lists of signals or stocks.
  - Move chart data fetching to WebSockets entirely to reduce HTTP overhead for live ticks.
