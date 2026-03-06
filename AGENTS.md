# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

NEUROQUANT is an institutional-grade AI-powered stock market platform targeting Indian markets (NSE/NIFTY). It is a monorepo with a Next.js frontend, a FastAPI monolith backend, and several independent Python microservices.

## Build & Development Commands

### Frontend (apps/web)

```
pnpm install                    # install all workspace deps (run from repo root)
pnpm dev                        # start Next.js dev server via Turborepo (port 3000)
pnpm build                      # production build (Turbo-orchestrated)
pnpm lint                       # ESLint across all workspaces
pnpm run type-check             # TypeScript strict check
pnpm run format                 # Prettier format all files
pnpm run format:check           # Prettier check without writing
```

Single-package commands (from `apps/web`):
```
pnpm run dev                    # Next.js dev server
pnpm run test                   # Vitest unit tests
pnpm run test:coverage          # Vitest with v8 coverage
pnpm run test:e2e               # Playwright end-to-end tests
pnpm run lint                   # ESLint (--max-warnings 0)
pnpm run type-check             # tsc --noEmit
```

### Backend monolith (backend/)

```
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --port 8000    # run from backend/
```

Alembic migrations (from `backend/`):
```
alembic upgrade head
alembic revision --autogenerate -m "description"
```

### Python microservices (services/<name>/)

Each service under `services/` is an independent FastAPI app with its own `requirements.txt`. Install and run individually:
```
pip install -r services/gateway/requirements.txt
uvicorn app.main:app --reload --port 8000    # run from services/gateway/
```

Testing a single service:
```
pytest services/gateway/tests/ -v
pytest services/gateway/tests/ --cov=app --cov-report=term-missing
pytest services/ml-engine/tests/ -v
```

### Python linting & type-checking (per service)

```
ruff check app/ --output-format=github       # from service directory
mypy app/ --strict --ignore-missing-imports   # from service directory
```

### Docker (full stack)

```
docker compose up -d                         # start postgres, redis, backend, celery, mlflow, frontend, nginx
docker compose -f infrastructure/docker/docker-compose.yml -f infrastructure/docker/docker-compose.dev.yml up -d   # dev overrides with hot-reload
```

### Initial setup

Run `scripts/setup.sh` (bash) or `scripts/setup.ps1` (PowerShell) to install deps, generate JWT RSA keys in `keys/`, generate a Fernet encryption key, copy `.env.example` to `.env`, and start Docker containers.

## Architecture

### Monorepo layout

- **apps/web** — Next.js 14 (App Router) frontend. pnpm workspace package `@neuroquant/web`. Managed by Turborepo (`turbo.json`).
- **backend/** — FastAPI monolith (the original backend). Contains API routes, ORM models, ML service integrations, Celery tasks, and Alembic migrations. Entry point: `backend/app/main.py`.
- **services/** — Independent Python microservices, each with its own FastAPI app and Dockerfile:
  - `gateway` — unified REST + WebSocket gateway, Alembic migrations, 40+ endpoints
  - `api-gateway` — earlier gateway implementation (Phase 7-8)
  - `ml-engine` — PyTorch/RL-based ML models and training
  - `data-pipeline` — market data ingestion from multiple sources (yfinance, Alpha Vantage, FRED, NSE)
  - `risk-engine` — VaR, CVaR, stress testing, portfolio optimization
  - `backtesting-engine` — event-driven backtesting with strategy support
- **infrastructure/** — Docker Compose files, Nginx configs, Postgres init scripts, Redis config.
- **scripts/** — Setup scripts and data seeding.

### Backend (backend/app/) structure

- `api/v1/` — FastAPI routers: auth, market_data, predictions, portfolio, backtesting, screener, alerts, health.
- `core/` — config (Pydantic Settings from `.env`), database (async SQLAlchemy), security (JWT), celery_app, websocket_manager.
- `models/` — SQLAlchemy ORM models (user, portfolio, ohlcv, alert, signal, prediction, etc.).
- `schemas/` — Pydantic request/response schemas.
- `services/` — Business logic: data_ingestion, ml_engine, risk_engine, signal_generator.

### Frontend (apps/web/src/) structure

- `app/` — Next.js App Router pages. Route groups: `(auth)/`, `dashboard/`, `login/`, `market/[symbol]`.
- `components/` — React components organized by domain: `common/`, `dashboard/`, `layout/`, `market/`, `charts/`.
- `hooks/` — Custom hooks (e.g. `useWebSocket`).
- `lib/` — API client (axios with interceptors), auth config (NextAuth.js v5, JWT RS256 + OAuth), providers.
- `stores/` — Zustand stores for portfolio and alerts state.
- `types/` — TypeScript type definitions.

Path alias: `@/*` maps to `src/*` (configured in `tsconfig.json`).

### Data flow

```
Frontend (Next.js :3000)
  ├── REST (axios) ──→ API Gateway (:8000) ──→ microservices (:8001-8005)
  ├── WebSocket ─────→ /ws/market/{symbol}, /ws/portfolio, /ws/alerts
  └── Auth ──────────→ NextAuth.js v5 → backend JWT (RS256)

Backend services share:
  PostgreSQL + TimescaleDB (:5432)
  Redis (:6379) — cache (db0), Celery broker (db1), Celery results (db2)
  MLflow (:5000) — experiment tracking
```

### Key service ports

- 3000: Next.js frontend
- 8000: Backend / Gateway API
- 8001-8005: ML engine, data pipeline, risk engine, alert service, backtesting
- 5432: PostgreSQL + TimescaleDB
- 6379: Redis
- 5000: MLflow
- 80: Nginx reverse proxy

## Conventions

### TypeScript (frontend)

- Strict mode enabled with all strict flags plus `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes`.
- ESLint: `no-explicit-any` is an error; `explicit-function-return-types` is a warning; `no-console` warns except for `warn`/`error`.
- Unit tests: Vitest with jsdom, `@testing-library/react`. E2E: Playwright.
- State: Zustand for client state, React Query v5 for server state.

### Python (backend + services)

- Python 3.12. All services use FastAPI + Pydantic v2 + async SQLAlchemy 2.0.
- Linting: Ruff (line-length 100, target py312). Type checking: mypy strict mode.
- The `gateway` service has the most detailed ruff config in its `pyproject.toml` — includes bugbear, bandit, annotations, isort, and simplify rules.
- Testing: pytest with `asyncio_mode = "auto"`. Coverage threshold in CI: 80%.
- Auth: RS256 JWT (RSA key pair in `keys/`), Argon2id password hashing, Fernet field-level encryption.
- Logging: structlog (structured JSON) in services, loguru in the backend monolith.

### Environment

- All config via environment variables. Never hardcode secrets. See `.env.example` for the full list (47 variables).
- `FIELD_ENCRYPTION_KEY` and JWT keys are generated by setup scripts — do not commit `keys/` or `.env`.

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs:
1. **node-ci**: pnpm install → lint → type-check → vitest with coverage
2. **python-ci**: per-service matrix (gateway, ml-engine, data-pipeline, risk-engine, alert-service, backtesting) → ruff → mypy strict → pytest with 80% coverage minimum
3. **docker-validate**: compose config validation + image build (main branch only)
4. **e2e**: Playwright tests (main/develop only)
