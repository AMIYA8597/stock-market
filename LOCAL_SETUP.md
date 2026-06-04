# Local Setup

This repository should be run locally in a Mongo-first, paper-trading mode before any live broker execution is enabled.

## What to use

- Use `MongoDB Atlas` or a local MongoDB instance for application state.
- Use `SQLite` locally for the legacy SQLAlchemy layer until the remaining SQL-only modules are removed.
- Use free market-data providers for quotes and candles.
- Use `paper trading` locally first. Real order placement requires a broker account and broker API approval.

## MongoDB

One MongoDB connection string is enough to start.

Use a single cluster and separate data with collections:

- `users`
- `refresh_sessions`
- `portfolios`
- `transactions`
- `paper_wallets`
- `paper_payments`
- `paper_payment_intents`
- `alerts`
- `notifications`
- `market_cache`

You do not need one Mongo URL per module. Start with one cluster and add retention rules:

- Keep `market_cache` short-lived with TTL indexes.
- Keep order, wallet, and user data in the primary cluster.
- Archive historical analytics later if you approach Atlas free-tier limits.

## Recommended `.env`

Backend:

```env
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
API_V1_PREFIX=/api/v1

DATABASE_URL=sqlite+aiosqlite:///./dev.db
MONGODB_URL=mongodb+srv://<user>:<pass>@<cluster>/<db>?retryWrites=true&w=majority
REDIS_URL=redis://localhost:6379/0

FRONTEND_URL=http://localhost:3000
BACKEND_CORS_ORIGINS=["http://localhost:3000"]

ALPHA_VANTAGE_API_KEY=
FINNHUB_API_KEY=
FRED_API_KEY=
NEWSAPI_KEY=
```

Frontend:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## Provider plan

Best practical local stack:

1. `Yahoo Finance` fallback for broad free historical coverage during development.
2. `Finnhub` for quote and websocket enrichment where free access fits your symbol usage.
3. `Alpha Vantage` for REST fallback and indicator endpoints.
4. `Upstox` or `Kite Connect` only when you want real Indian broker execution.

## Local run order

1. Start MongoDB and keep the connection string ready.
2. Start Redis if you want websocket/cache behavior; otherwise the app should degrade without it.
3. Run backend with a standard CPython 3.12 or 3.13 install.
4. Run frontend from `apps/web`.

Example commands:

```powershell
# backend
cd D:\work\stock-market
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r backend\requirements-ci.txt
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
# frontend
cd D:\work\stock-market\apps\web
npm install
npm run dev
```

## Live trading reality

Free market data is possible.

Free real-money broker execution generally is not.

To place live NSE/BSE orders, you will need:

- a funded broker account
- broker app registration
- OAuth/session login flow
- broker-specific instrument master sync
- exchange/regulatory compliance for algo usage where applicable

Until that is configured, keep the app in paper-trading mode.
