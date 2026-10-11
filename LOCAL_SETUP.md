# Local Setup

## Prerequisites

- **Node.js 20+** and **pnpm 8+**
- **Python 3.12+** and **[uv](https://docs.astral.sh/uv/)**
- **Docker** (for Postgres + Redis)

## Quick start

```bash
# 1. Clone and install JS dependencies
git clone https://github.com/AMIYA8597/stock-market.git
cd stock-market
pnpm install

# 2. Start Postgres + Redis
docker compose -f docker-compose.dev.yml up -d

# 3. Set up backend env
cp backend/.env.local.example backend/.env
# Edit backend/.env — fill in SUPABASE_URL, SUPABASE_JWT_SECRET, SUPABASE_SECRET_KEY

# 4. Install Python dependencies
cd backend && uv sync --all-extras && cd ..

# 5. Run migrations
cd backend && uv run alembic upgrade head && cd ..

# 6. Set up frontend env
cp apps/web/.env.example apps/web/.env.local
# Edit apps/web/.env.local — fill in NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY

# 7. Start everything
pnpm dev
```

The backend runs on http://localhost:8000, the frontend on http://localhost:3000.

## What runs where

| Service | Command | Port |
|---------|---------|------|
| Postgres | docker compose | 5432 |
| Redis | docker compose | 6379 |
| Backend (FastAPI/uvicorn) | `pnpm dev` (turbo) | 8000 |
| Frontend (Next.js) | `pnpm dev` (turbo) | 3000 |

## Environment files

- **`backend/.env`** — copy from `backend/.env.local.example`. Uses docker-compose Postgres
  (`postgresql+asyncpg://neuroquant:changeme@localhost:5432/neuroquant_db`).
  **Never** point this at the production Supabase database.
- **`apps/web/.env.local`** — copy from `apps/web/.env.example`.
- See `docs/ENVIRONMENTS.md` for the full variable reference.

## Running checks locally

```bash
# Backend
cd backend
uv run ruff check .
uv run mypy app/
uv run pytest tests/
uv run alembic check

# Frontend
pnpm --filter @neuroquant/web run type-check
pnpm build

# E2E (starts backend + frontend automatically)
pnpm --filter @neuroquant/web exec playwright test --retries=0

# Honesty guard
python scripts/honesty_guard.py
```

Or use the turbo shortcuts from the root:

```bash
pnpm typecheck   # mypy + tsc across all packages
pnpm test        # pytest + vitest across all packages
pnpm build       # build all packages
```

## Docker-compose services

`docker-compose.dev.yml` provides:

- **Postgres 17** — user `neuroquant`, password `changeme`, database `neuroquant_db`
- **Redis 7** — default port 6379

Data is persisted in a Docker volume (`pgdata`). To reset:

```bash
docker compose -f docker-compose.dev.yml down -v   # removes volumes
docker compose -f docker-compose.dev.yml up -d      # fresh start
```

## Notes

- The app degrades gracefully if Redis is unavailable (in-memory fallback).
- Free market-data providers (yfinance, Stooq) are used by default — no API keys needed for basic dev.
- Real-money order placement is disabled. Paper trading mode is the default.
