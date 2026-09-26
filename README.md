# NeuroQuant 🧠📈

> Paper-trading algorithmic research platform: real-time market terminal (Next.js) + ML/quant backend (FastAPI).

This is the **Knowledge Transfer (KT) document** for this repository. It is written to be accurate against the actual code as of the last verification pass (noted per section) rather than aspirational — every command below has been run and confirmed working. If something here stops matching reality, trust the code and fix this file, not the other way around.

---

## Table of Contents
1. [What this actually is](#1-what-this-actually-is)
2. [Monorepo layout](#2-monorepo-layout)
3. [Tech stack](#3-tech-stack)
4. [Prerequisites](#4-prerequisites)
5. [Environment configuration (.env)](#5-environment-configuration-env)
6. [Running the stack locally](#6-running-the-stack-locally)
7. [Database & migrations](#7-database--migrations)
8. [Testing](#8-testing)
9. [ML training & backtesting](#9-ml-training--backtesting)
10. [Background workers (Celery)](#10-background-workers-celery)
11. [Deployment](#11-deployment)
12. [Known gaps & things to treat with caution](#12-known-gaps--things-to-treat-with-caution)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. What this actually is

NeuroQuant is a **paper-trading** (simulated money, no real orders unless you explicitly wire up a broker) research terminal:

- Real-time-feeling market dashboard (quotes, charts, screener, alerts) fed by free data sources (yfinance, NSE public JSON, Stooq — no API key needed for basic operation).
- An ML/quant backend that generates trading signals from an ensemble of models (technical indicators, regime detection via HMM/GARCH, gradient-boosted trees, optionally deep models if you install the heavier requirements set) and lets you backtest them.
- A "Honesty Law" design principle followed throughout the backend: the app is meant to never fabricate data, prices, model results, or payment confirmations — if something is unavailable, it returns an explicit unavailable/pending state instead of making something up. Keep this in mind if you're extending it: don't add silent fallbacks that fake success.

Auth and (optionally) the primary database are **Supabase**-based. There is no custom JWT signing scheme and no MongoDB anywhere in this codebase, despite what older drafts of this file or `LOCAL_SETUP.md` used to say.

## 2. Monorepo layout

Managed with **pnpm workspaces + Turborepo**.

```text
.
├── apps/
│   └── web/                        # Next.js 14 (App Router) frontend
│       ├── src/app/[locale]/       # Routes, under a locale segment (en/hi/bn)
│       ├── src/components/         # UI (terminal, charts, layout, market widgets)
│       ├── src/lib/                # api-client.ts (canonical API client), realtime.ts
│       │                           #   (single WebSocket manager), supabase/ (auth client)
│       ├── src/i18n/               # next-intl routing + locale-aware navigation
│       ├── src/middleware.ts       # Supabase session refresh + protected-route redirects
│       └── .env.local              # Frontend env (see §5)
│
├── backend/                        # FastAPI + ML/quant engine
│   ├── app/
│   │   ├── api/v1/                 # REST routers (market, predictions, backtest, payments, ...)
│   │   ├── core/                   # Settings (config.py), security (JWT/JWKS verification),
│   │   │                           #   celery_app.py, websocket_manager.py
│   │   ├── database/               # SQLAlchemy engine/session (connection.py), redis_client.py
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   ├── services/               # Business logic: prediction_engine, market_data_service,
│   │   │                           #   strategies (ez_algo_service.py, optimized_retest_strategy.py), etc.
│   │   └── tasks/                  # Celery tasks (market data, features, regime, retraining)
│   ├── research/                   # ML models, feature engineering, backtesting statistics
│   ├── alembic/                    # DB migrations (for Postgres/Supabase — see §7)
│   ├── scripts/                    # Mixed bag of dev/ops utilities — read §12 before using any of these
│   ├── tests/                      # pytest suite (unit/, integration/, leakage/, meta/)
│   ├── .env                        # Backend env (see §5)
│   ├── requirements-core.txt       # Fast install: API + classical ML, no deep learning
│   └── requirements.txt            # requirements-core.txt + torch/transformers (full ML stack)
│
├── packages/
│   ├── types/                      # @neuroquant/types — shared TS types (frontend<->contracts)
│   ├── ui/                         # @neuroquant/ui — shared React components
│   └── config/                     # @neuroquant/config — shared tooling config
│
├── services/gateway/                # A skeleton FastAPI app (health-check only). Not wired
│                                    #   into anything else — see §12.
│
├── Dockerfile                       # Backend image, Poetry-based, port 7860 (Hugging Face Spaces target)
├── backend/Dockerfile               # Backend image, pip-based, port 7860
├── Dockerfile.web                   # Frontend image, port 3000
├── docker-compose.dev.yml           # Postgres + Redis only, for local dev parity — no compose file
│                                    #   runs the whole stack end-to-end (see §11)
└── docker-compose.test.yml          # Postgres for CI
```

## 3. Tech stack

**Frontend** (`apps/web`)
- Next.js 14 (App Router), TypeScript, TailwindCSS
- `next-intl` v4 for i18n routing (`en`/`hi`/`bn`, default `en`) — see `src/i18n/routing.ts` and `src/i18n/navigation.ts`. Always import `Link`/`useRouter`/`usePathname`/`redirect` from `@/i18n/navigation`, never from `next/link`/`next/navigation`, or you'll reintroduce a locale-dropping navigation bug that was fixed here.
- Supabase Auth via `@supabase/ssr` + `@supabase/supabase-js` (`src/lib/supabase/`)
- Zustand for client state, TanStack Query for server state
- A single centralized WebSocket manager (`src/lib/realtime.ts`) — all live price/signal subscriptions go through it, not ad-hoc `WebSocket` instances
- All backend calls go through `src/lib/api-client.ts` (`fetchApi`, `marketApi`, `paperTradingApi`, `paymentsApi`, ...) — never raw `fetch()` from a component

**Backend** (`backend/`)
- FastAPI, SQLAlchemy 2.0 (async), Pydantic Settings v2 (`app/core/config.py` is the single source of truth for every env var — if in doubt about what a variable does, read it there, not in this file)
- SQLite for local dev (zero setup) or Supabase/self-hosted Postgres for anything persistent
- Supabase Auth: JWTs are verified via JWKS fetched from your Supabase project automatically (`app/core/security.py`) — no shared secret needed for a normal project
- Redis for caching, rate limiting, Celery broker, and WebSocket fan-out — **optional in dev**: if unreachable, the app transparently falls back to an in-memory implementation (`app/database/redis_client.py`) and logs a warning instead of failing
- Celery for background jobs (market data ingestion, feature computation, regime detection, model retraining)
- ML: scikit-learn, XGBoost, statsmodels (HMM/GARCH regime detection), optionally PyTorch/transformers if you install the full `requirements.txt`

## 4. Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Node.js | ≥ 20 | |
| pnpm | ≥ 8 (pinned to `8.15.6` via `packageManager`) | `corepack enable` will get you the right version automatically |
| Python | ≥ 3.12 | `backend/pyproject.toml` enforces this |
| Redis | any recent version | **Optional** for local dev — install it or run it via Docker if you want real caching/rate-limiting instead of the in-memory fallback |
| A Supabase project | free tier is fine | Required for auth to work at all — see §5 |

Nothing else is required to get a working local instance. Everything else (Postgres, broker APIs, payment provider, extra data providers) is optional and documented per-variable in the `.env.example` files.

## 5. Environment configuration (.env)

Two files, both git-ignored (never commit real secrets into either):

### `backend/.env`
```bash
cd backend
cp .env.example .env
```
Then fill in, from your Supabase project's **Project Settings → API Keys**:
```env
SUPABASE_URL=https://<project_ref>.supabase.co
SUPABASE_SECRET_KEY=sb_secret_...          # "Secret keys" section — backend only, never expose to a browser
```
`SUPABASE_JWT_SECRET` can stay blank for a normal project — JWKS verification is used instead (see `app/core/security.py`). `DATABASE_URL` defaults to local SQLite so the API boots with zero external accounts beyond Supabase.

Every other variable in `backend/.env.example` is optional and commented with what it does and where to get it (data-provider keys, broker keys, Razorpay, email/SMTP).

### `apps/web/.env.local`
```bash
cd apps/web
cp .env.example .env.local
```
```env
NEXT_PUBLIC_SUPABASE_URL=https://<project_ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_...   # "Publishable key" section of the same API Keys page
NEXT_PUBLIC_API_URL=http://localhost:8000           # bare origin, no /api/v1 suffix — the client adds it
NEXT_PUBLIC_WS_URL=ws://localhost:8000              # optional — derived from NEXT_PUBLIC_API_URL if omitted
```
Note the naming mismatch: Supabase's dashboard now calls these "Publishable key" / "Secret key" (its newer key system). Our code still reads the older variable names `NEXT_PUBLIC_SUPABASE_ANON_KEY` / `SUPABASE_SECRET_KEY` — use Supabase's *values* under *our* variable names.

Also worth doing once, in the Supabase dashboard, under **Authentication → URL Configuration**: set Site URL to your frontend's URL and add it (with `/**`) as a redirect URL, so password-reset/confirmation email links resolve correctly.

## 6. Running the stack locally

### Everything at once (from repo root)
```bash
pnpm install
pnpm dev        # turbo run dev --parallel — starts every app/package with a `dev` script
```

### Backend only
```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-core.txt      # fast path: API + classical ML, no deep learning
# pip install -r requirements.txt         # full path: adds torch/transformers/torch-geometric
cp .env.example .env               # then fill in SUPABASE_URL / SUPABASE_SECRET_KEY, see §5
python scripts/init_dev_db.py      # creates the SQLite tables (safe to re-run)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- API: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`
- Health check: `GET http://localhost:8000/api/v1/health` → `{"status":"healthy",...}`

### Frontend only
```bash
cd apps/web
pnpm install
cp .env.example .env.local         # then fill in Supabase values, see §5
pnpm dev
```
- UI: `http://localhost:3000` → redirects into `/en` (or `/hi`, `/bn`)

If you edit files under `apps/web` and Next.js starts throwing stale type errors that don't match what's actually in the file, delete the cache and restart: `rm -rf apps/web/.next`.

## 7. Database & migrations

Two supported paths:

**SQLite (default, zero setup)** — `DATABASE_URL=sqlite+aiosqlite:///./dev.db`. Run `python scripts/init_dev_db.py` once to create tables. Good for local development; not meant for concurrent/production use (SQLite serializes writes).

**Postgres (Supabase or self-hosted)** — get the connection string from Supabase's **Connect** panel (or your own Postgres), then in `backend/.env`:
```env
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:<port>/postgres
MIGRATIONS_DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>:<port>/postgres
```
Then run migrations with Alembic:
```bash
cd backend
alembic upgrade head
```
The migration set is intentionally small (2 revisions as of this writing) — most of the schema is created via `Base.metadata.create_all` (see `create_all_for_tests()` in `app/database/connection.py`), which is what `scripts/init_dev_db.py` calls. Alembic is there for the migrations that do exist and for future schema changes; it isn't yet the only source of truth for the schema.

## 8. Testing

**Backend**
```bash
cd backend
source .venv/bin/activate
python -m pytest -q
```
As of this writing: 210 tests passing. One integration test (`tests/integration/test_websocket.py::test_ws_prices_subscription`) is a known order-dependent flake — it fails only when run as part of the full suite and passes standalone; not something to chase if you see it once.

Lint: `ruff check .` (from `backend/`).

**Frontend**
```bash
cd apps/web
pnpm run type-check     # tsc --noEmit
pnpm run build          # full production build — the strongest signal something is actually broken
pnpm run lint           # next lint (pre-existing warnings exist in a handful of older files; don't let unrelated ones block you)
pnpm run test           # vitest run
```

**Everything, backend + frontend, from repo root:**
```bash
pnpm run test:full
```

## 9. ML training & backtesting

**Training a model for one symbol:**
```bash
cd backend
source .venv/bin/activate
python scripts/run_training.py     # trains against "RELIANCE.NS" — edit the symbol in the script for others
```
This drives `app.services.ml_engine.training_pipeline.TrainingPipeline`.

**Backtesting** is done through the API, not a standalone script (the frontend's Backtest Lab, `/backtest-lab`, is a thin UI over this):
```
POST /api/v1/backtest/run           -> kicks off an async backtest job, returns a job_id
GET  /api/v1/backtest/status/{id}   -> poll job status
GET  /api/v1/backtest/results/{id}  -> fetch results once complete
```
See `backend/app/api/v1/backtest.py` for the request schema.

Two signal-generation strategies are implemented directly in `backend/app/services/`: `ez_algo_service.py` (multi-timeframe EMA crossover with ADX/ATR/Bollinger filters) and `optimized_retest_strategy.py` (EMA trend alignment with candle-body-quality and pyramiding rules).

## 10. Background workers (Celery)

```bash
cd backend
source .venv/bin/activate
celery -A app.core.celery_app worker --loglevel=info
```
(Windows: add `--pool=solo`.) Requires `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` (Redis) to be reachable — without Redis, Celery itself won't start (this is different from the rest of the app, which degrades gracefully without Redis). Registered task modules live under `app/tasks/` and are wired into the worker via the `include=[...]` list in `app/core/celery_app.py`.

In `ENVIRONMENT=development`, `task_always_eager` is enabled, meaning Celery tasks called via `.delay()`/`.apply_async()` run synchronously in-process — you often don't need a worker running at all for local dev.

## 11. Deployment

There is **no single `docker-compose up` that stands up the entire production stack** — don't trust older docs (or memory) claiming otherwise. What actually exists:

- `Dockerfile` (repo root): backend image built with Poetry, listens on port `7860` — sized for Hugging Face Spaces, which expects that port.
- `backend/Dockerfile`: an alternative backend image, pip-based, also port `7860`.
- `Dockerfile.web`: frontend image (Next.js standalone-style build), port `3000`.
- `docker-compose.dev.yml`: Postgres + Redis only, for local dev parity with a production-like database — not the app itself.
- `docker-compose.test.yml`: Postgres for CI.

In practice, deploy the backend and frontend as separate services (e.g., backend to a container host or Hugging Face Spaces, frontend to Vercel or its own container), each with its own env vars set per §5, both pointed at the same Supabase project. If you want a genuine one-command full-stack `docker-compose.yml`, it doesn't exist yet — write and test one deliberately rather than assuming one is already there.

## 12. Known gaps & things to treat with caution

- **`services/gateway/`** is an unused skeleton FastAPI app (health-check endpoints only). Nothing else in the repo calls it. Don't assume it's part of the request path.
- **`backend/scripts/`** is large and mixed quality — it accumulated real utilities (`run_training.py`, `init_dev_db.py`) alongside one-off debug/patch scripts (`patch.py` through `patch6.py`, `debug_crash.py`, `prove_*.py`, `trace_*.py`) and at least one broken/stale script (`train.py` imports a `pipelines` module that doesn't exist — use `run_training.py` instead) plus one that hardcodes a foreign machine's Windows path (`run_walk_forward_backtest.py` — from a previous agent session, not meant for general use). **Read a script before running it**; don't assume everything in that directory is maintained or safe.
- **i18n content**: the locale-aware navigation infrastructure (`next-intl`, `src/i18n/`) is fully wired, but no component actually calls `useTranslations()` yet — the `hi`/`bn` locales route correctly but render English text. Message catalogs exist but are placeholder-sized.
- **`FIELD_ENCRYPTION_KEY`/`ENCRYPTION_ENABLED`**: field-level encryption exists in `app/core/config.py` but defaults to disabled — enable and generate a key (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) before storing anything sensitive in it for real.
- **Root `.env.example`** intentionally just points at `backend/.env.example` and `apps/web/.env.example` now — the backend explicitly does not read a root-level `.env` (see the docstring on `get_settings()` in `app/core/config.py`).

## 13. Troubleshooting

- **`Redis connection failed, falling back to in-memory cache`** at backend startup: expected and harmless if you don't have Redis running locally. Live WebSocket fan-out and rate limiting are degraded (single-process only) until you run Redis, but the app works.
- **Frontend shows stale/incorrect TypeScript errors after deleting or renaming a route file**: `rm -rf apps/web/.next` and restart `pnpm dev` — Next.js's type-checking cache under `.next/types` doesn't always self-invalidate.
- **A page's internal links reset the URL back to `/en/...`** even though you're browsing `/hi/...`: something is importing `Link`/`useRouter`/`usePathname` from `next/link`/`next/navigation` instead of `@/i18n/navigation`. Grep for that pattern and fix the import.
- **`ImportError` in a `backend/scripts/*.py` file**: several of these are stale (see §12) — check `git log`/`git blame` on the specific script, or just use the documented entry points in §9/§10 instead.
- **Celery worker won't start**: Redis must actually be reachable for Celery specifically (unlike the rest of the app). `redis-cli ping` to confirm.
- **`SUPABASE_SECRET_KEY`/`SUPABASE_JWT_SECRET` confusion**: the web app itself never needs the secret key or the JWT secret — it talks to Supabase directly with the publishable/anon key, and the backend verifies tokens via JWKS. The secret key is only needed for the backend's own `/api/v1/auth/register`, `/login`, `/refresh` endpoints, which the frontend doesn't call.
