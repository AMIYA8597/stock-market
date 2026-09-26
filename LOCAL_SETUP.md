# Local Setup

Run this repository in paper-trading mode locally before any live broker
execution is enabled.

## What's actually used

- **SQLAlchemy + SQLite** for local dev (no server to install), or
  **Supabase Postgres** for anything resembling production. There is no
  MongoDB anywhere in this codebase — an earlier draft of this file
  described a MongoDB-first design that was never implemented; ignore any
  reference to `MONGODB_URL` you may see elsewhere.
- **Supabase Auth** for sign-up/login (the frontend talks to Supabase
  directly; the backend verifies the resulting JWT).
- Free market-data providers (yfinance, NSE public JSON, Stooq) for quotes
  and candles — no key required.
- **Paper trading** by default. Real order placement requires a funded
  broker account (Upstox / Angel One) and is off unless you configure it.

## Recommended `.env`

The full, commented, authoritative list of variables lives in
`backend/.env.example` and `apps/web/.env.example` — copy those rather than
retyping a list here (this file used to keep its own copy and it drifted
out of sync with `app/core/config.py`). The short version:

Backend (`backend/.env`):
```env
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

DATABASE_URL=sqlite+aiosqlite:///./dev.db
REDIS_URL=redis://localhost:6379/0

# Supabase project -> Project Settings -> API
SUPABASE_URL=https://<project_ref>.supabase.co
SUPABASE_JWT_SECRET=
SUPABASE_SECRET_KEY=

FRONTEND_URL=http://localhost:3000
BACKEND_CORS_ORIGINS=["http://localhost:3000"]

# Optional data-source keys (blank = that provider is skipped)
ALPHA_VANTAGE_API_KEY=
FINNHUB_API_KEY=
FRED_API_KEY=
NEWSAPI_KEY=
```

Frontend (`apps/web/.env.local`):
```env
NEXT_PUBLIC_SUPABASE_URL=https://<project_ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## Provider plan

Best practical local stack:

1. `yfinance` fallback for broad free historical coverage during development.
2. `Finnhub` for quote and websocket enrichment where free access fits your symbol usage.
3. `Alpha Vantage` for REST fallback and indicator endpoints.
4. `Upstox` or Angel One SmartAPI only when you want real Indian broker execution.

## Local run order

1. (Optional) Start Redis if you want real caching/rate-limiting/WebSocket
   fan-out; the app degrades to an in-memory fallback automatically if
   Redis is unreachable, so this can be skipped for a first run.
2. Run the backend with CPython 3.12.
3. Run the frontend from `apps/web`.

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-core.txt
cp .env.example .env   # then fill in SUPABASE_* — see above
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
# frontend
cd apps/web
pnpm install
cp .env.example .env.local   # then fill in NEXT_PUBLIC_SUPABASE_* — see above
pnpm dev
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
