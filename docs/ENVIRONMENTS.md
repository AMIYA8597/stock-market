# Environments

NeuroQuant runs in four environments. This document lists every configuration
variable, where each value lives, and whether it is required.

| Symbol | Meaning |
|--------|---------|
| ✅ | Required — the app will not start or will behave incorrectly without it |
| ⚙️ | Optional — sensible default is built in; set to override |
| 🔒 | Secret — must never be committed; inject via the runtime secret store |

---

## Runtime environments

| Environment | Backend host | Frontend host | Database |
|-------------|-------------|---------------|----------|
| **local** | `localhost:8000` (uvicorn) | `localhost:3000` (Next.js dev) | docker-compose Postgres `localhost:5432` |
| **test** | pytest in-process | — | SQLite in-memory (pytest) |
| **staging** | Cloud Run (auto-deploy on `main`) | Vercel preview | Supabase staging project |
| **production** | Cloud Run | Vercel (neuroquant-sm.vercel.app) | Supabase production project |

---

## Where secrets live

| Store | Used by |
|-------|---------|
| `backend/.env` (gitignored) | Local backend dev |
| `apps/web/.env.local` (gitignored) | Local frontend dev |
| **GitHub Secrets** | CI (backend tests, E2E, smoke) |
| **Cloud Run environment** | Staging and production backend |
| **Vercel environment** | Staging and production frontend |

---

## Backend variables (`backend/app/core/config.py`)

Copy `backend/.env.example` → `backend/.env` for production-Supabase local dev.  
Copy `backend/.env.local.example` → `backend/.env` to use the docker-compose stack instead.

### App

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `ENVIRONMENT` | `development` | set in `.env` | — | ✅ set to `production` | ✅ |
| `DEBUG` | `false` | `true` | — | `false` | ⚙️ |
| `LOG_LEVEL` | `INFO` | `DEBUG` | — | `INFO` | ⚙️ |
| `PROJECT_NAME` | `NeuroQuant` | — | — | — | ⚙️ |
| `API_V1_PREFIX` | `/api/v1` | — | — | — | ⚙️ |

### Database

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `DATABASE_URL` | — | set in `.env` | `DATABASE_URL` | ✅ | ✅ |
| `MIGRATIONS_DATABASE_URL` | — | set in `.env` | `MIGRATIONS_DATABASE_URL` | ✅ | ✅ |
| `INGEST_DATABASE_URL` | `DATABASE_URL` | set in `.env` | — | ✅ | ⚙️ |
| `DB_POOL_MODE` | `session` | — | — | — | ⚙️ |
| `DB_POOL_SIZE` | `5` | — | — | — | ⚙️ |
| `DB_MAX_OVERFLOW` | `2` | — | — | — | ⚙️ |
| `DB_POOL_RECYCLE` | `1800` | — | — | — | ⚙️ |
| `DB_SSL_REQUIRED` | `true` | `false` (docker) | — | `true` | ⚙️ |

### Redis

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `REDIS_URL` | `redis://localhost:6379/0` | set in `.env` | `REDIS_URL` | ✅ | ⚙️ |
| `REDIS_MAX_CONNECTIONS` | `50` | — | — | — | ⚙️ |

### Celery

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | set in `.env` | — | ✅ | ⚙️ |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | set in `.env` | — | ✅ | ⚙️ |
| `CELERY_TASK_SOFT_TIME_LIMIT` | `600` | — | — | — | ⚙️ |
| `CELERY_TASK_HARD_TIME_LIMIT` | `900` | — | — | — | ⚙️ |

### Supabase / Auth

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `SUPABASE_URL` | — | set in `.env` | `SUPABASE_URL` | ✅ | ✅ |
| `SUPABASE_ANON_KEY` | — | set in `.env` | `SUPABASE_ANON_KEY` | ✅ | ✅ 🔒 |
| `SUPABASE_SECRET_KEY` | — | set in `.env` | `SUPABASE_SECRET_KEY` | ✅ | ✅ 🔒 |
| `SUPABASE_JWT_SECRET` | — | blank (JWKS) | — | — | ⚙️ 🔒 |
| `TOKEN_BLACKLIST_ENABLED` | `true` | — | — | — | ⚙️ |
| `LOGIN_MAX_FAILED_ATTEMPTS` | `5` | — | — | — | ⚙️ |
| `LOGIN_LOCKOUT_MINUTES` | `15` | — | — | — | ⚙️ |

### OTP

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `OTP_LENGTH` | `6` | — | — | — | ⚙️ |
| `OTP_EXPIRE_MINUTES` | `10` | — | — | — | ⚙️ |
| `OTP_MAX_ATTEMPTS` | `5` | — | — | — | ⚙️ |
| `OTP_RESEND_COOLDOWN_SECONDS` | `60` | — | — | — | ⚙️ |

### Password Policy

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `PASSWORD_MIN_LENGTH` | `12` | — | — | — | ⚙️ |
| `PASSWORD_REQUIRE_UPPERCASE` | `true` | — | — | — | ⚙️ |
| `PASSWORD_REQUIRE_NUMBERS` | `true` | — | — | — | ⚙️ |
| `PASSWORD_REQUIRE_SPECIAL` | `true` | — | — | — | ⚙️ |
| `PASSWORD_HASH_ALGORITHM` | `argon2` | — | — | — | ⚙️ |
| `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` | `30` | — | — | — | ⚙️ |

### Field Encryption

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `ENCRYPTION_ENABLED` | `false` | — | — | — | ⚙️ |
| `FIELD_ENCRYPTION_KEY` | — | — | `FIELD_ENCRYPTION_KEY` | ✅ (if enabled) | 🔒 |

### CORS & Security

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `BACKEND_CORS_ORIGINS` | `[]` | set in `.env` | — | ✅ | ✅ |
| `FRONTEND_URL` | `http://localhost:3000` | set in `.env` | — | ✅ | ✅ |
| `FRONTEND_PRODUCTION_URL` | — | — | — | ✅ | ✅ |
| `FRONTEND_STAGING_URL` | — | — | — | ✅ (staging) | ⚙️ |
| `CORS_ALLOW_METHODS` | `GET,POST,...` | — | — | — | ⚙️ |
| `CORS_ALLOW_HEADERS` | (standard set) | — | — | — | ⚙️ |
| `ALLOWED_HOSTS` | `[]` (allow all) | — | — | ✅ set in prod | ⚙️ |
| `SECURITY_CSP_POLICY` | (strict default) | — | — | — | ⚙️ |

### Email / SendGrid

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `SENDGRID_API_KEY` | — | blank (auto-verify) | `SENDGRID_API_KEY` | ✅ | ✅ (prod) 🔒 |
| `SENDGRID_FROM_EMAIL` | `noreply@neuroquant.local` | — | — | ✅ | ⚙️ |
| `ALERT_EMAIL_ENABLED` | `false` | — | — | — | ⚙️ |

### Payments / Razorpay

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `RAZORPAY_KEY_ID` | — | test key | `RAZORPAY_KEY_ID` | ✅ | ✅ 🔒 |
| `RAZORPAY_KEY_SECRET` | — | test secret | `RAZORPAY_KEY_SECRET` | ✅ | ✅ 🔒 |
| `RAZORPAY_WEBHOOK_SECRET` | — | — | `RAZORPAY_WEBHOOK_SECRET` | ✅ | ✅ 🔒 |

### Rate Limiting

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `RATE_LIMIT_ENABLED` | `true` | — | — | — | ⚙️ |
| `DEFAULT_RATE_LIMIT` | `100/minute` | — | — | — | ⚙️ |
| `AUTH_RATE_LIMIT` | `10/minute` | — | — | — | ⚙️ |
| `PREMIUM_RATE_LIMIT` | `1000/minute` | — | — | — | ⚙️ |

### Live Market Data

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `LIVE_DATA_PROVIDER` | `upstox` | — | — | — | ⚙️ |
| `LIVE_DATA_YFINANCE_RATE_LIMIT` | `5` | — | — | — | ⚙️ |
| `LIVE_DATA_ALPHA_VANTAGE_RATE_LIMIT` | `5` | — | — | — | ⚙️ |

### Upstox

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `UPSTOX_API_KEY` | — | — | `UPSTOX_API_KEY` | ✅ | ✅ 🔒 |
| `UPSTOX_API_SECRET` | — | — | `UPSTOX_API_SECRET` | ✅ | ✅ 🔒 |
| `UPSTOX_REDIRECT_URI` | — | set in `.env` | — | ✅ | ✅ |
| `UPSTOX_ENABLED` | `true` | — | — | — | ⚙️ |
| `UPSTOX_MAX_ORDER_VALUE` | `10000.0` | — | — | — | ⚙️ |
| `UPSTOX_ANALYTICS_TOKEN` | — | — | `UPSTOX_ANALYTICS_TOKEN` | ⚙️ | ⚙️ 🔒 |
| `UPSTOX_BASE_URL` | `https://api.upstox.com` | — | — | — | ⚙️ |
| `UPSTOX_WS_ENABLED` | `false` | — | — | — | ⚙️ |
| `UPSTOX_WS_MODE` | `full` | — | — | — | ⚙️ |

### Angel One

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `ANGEL_ONE_CLIENT_ID` | — | — | `ANGEL_ONE_CLIENT_ID` | ⚙️ | ⚙️ 🔒 |
| `ANGEL_ONE_CLIENT_SECRET` | — | — | `ANGEL_ONE_CLIENT_SECRET` | ⚙️ | ⚙️ 🔒 |
| `ANGEL_ONE_TOTP_SECRET` | — | — | `ANGEL_ONE_TOTP_SECRET` | ⚙️ | ⚙️ 🔒 |

### External Data APIs

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `ALPHA_VANTAGE_API_KEY` | — | — | — | ⚙️ | ⚙️ 🔒 |
| `NEWSAPI_KEY` | — | — | — | ⚙️ | ⚙️ 🔒 |
| `FRED_API_KEY` | — | — | — | ⚙️ | ⚙️ 🔒 |
| `COINGECKO_API_KEY` | — | — | — | ⚙️ | ⚙️ 🔒 |
| `FINNHUB_API_KEY` | — | — | — | ⚙️ | ⚙️ 🔒 |

### WebSocket

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `WEBSOCKET_URL` | `ws://localhost:8000/ws` | set in `.env` | — | ✅ | ✅ |
| `WEBSOCKET_HEARTBEAT_INTERVAL` | `30` | — | — | — | ⚙️ |
| `WEBSOCKET_MAX_CONNECTIONS_PER_USER` | `5` | — | — | — | ⚙️ |

### ML / Models

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `MODEL_CHECKPOINT_DIR` | `./data/models` | — | — | ✅ (mounted volume) | ⚙️ |
| `ENABLE_GPU` | `false` | — | — | — | ⚙️ |
| `ONLINE_LEARNING_ENABLED` | `true` | — | — | — | ⚙️ |
| `DRIFT_DETECTION_ENABLED` | `true` | — | — | — | ⚙️ |
| `MAX_TRACKED_SYMBOLS` | `100` | — | — | — | ⚙️ |
| `BATCH_SIZE` | `20` | — | — | — | ⚙️ |
| `SEQUENCE_LENGTH` | `60` | — | — | — | ⚙️ |
| `TRAINING_BATCH_SIZE` | `64` | — | — | — | ⚙️ |
| `INFERENCE_BATCH_SIZE` | `32` | — | — | — | ⚙️ |
| `FORECAST_HORIZON` | `5` | — | — | — | ⚙️ |
| `FEATURE_CACHE_TTL_HOURS` | `24` | — | — | — | ⚙️ |
| `FEATURE_NORMALIZATION_METHOD` | `robust` | — | — | — | ⚙️ |
| `RETRAIN_MIN_INTERVAL_HOURS` | `24` | — | — | — | ⚙️ |
| `RETRAIN_SAMPLE_SIZE` | `500` | — | — | — | ⚙️ |
| `DRIFT_DETECTION_ALPHA` | `0.002` | — | — | — | ⚙️ |

### Monitoring

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `SENTRY_DSN` | — | — | `SENTRY_DSN` | ✅ | ⚙️ 🔒 |
| `ENABLE_PROMETHEUS_METRICS` | `false` | — | — | — | ⚙️ |
| `METRICS_COLLECTION_INTERVAL_SECONDS` | `60` | — | — | — | ⚙️ |
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` | — | — | ⚙️ | ⚙️ |
| `MLFLOW_EXPERIMENT_NAME` | `neuroquant-prod` | `neuroquant-local` | — | — | ⚙️ |

### Backtest

| Variable | Default | Local | GitHub Secrets | Cloud Run | Required |
|----------|---------|-------|----------------|-----------|----------|
| `BACKTEST_MAX_WORKERS` | `4` | — | — | — | ⚙️ |
| `BACKTEST_CACHE_DIR` | `./data/backtest_cache` | — | — | — | ⚙️ |

---

## Frontend variables (`apps/web/.env.local`)

Copy `apps/web/.env.example` → `apps/web/.env.local`.

All five variables are `NEXT_PUBLIC_*` — they are inlined at build time and
visible in the browser bundle. **Never put secrets here.**

| Variable | Local | Vercel (staging) | Vercel (prod) | Required |
|----------|-------|-----------------|----------------|----------|
| `NEXT_PUBLIC_SUPABASE_URL` | staging or local | staging Supabase URL | prod Supabase URL | ✅ |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | staging or local | staging anon key | prod anon key | ✅ |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | staging Cloud Run URL | prod Cloud Run URL | ✅ |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000` | staging Cloud Run WS URL | prod Cloud Run WS URL | ✅ |
| `NEXT_PUBLIC_RAZORPAY_KEY_ID` | test key | test key | live key | ✅ |

---

## Local dev quick-start

```bash
# 1. Start Postgres + Redis
docker compose -f docker-compose.dev.yml up -d

# 2. Configure backend
cp backend/.env.local.example backend/.env
# (edit backend/.env — at minimum set SUPABASE_* if you need auth,
#  or leave blank to use email auto-verify mode)

# 3. Run migrations
cd backend && uv run alembic upgrade head && cd ..

# 4. Configure frontend
cp apps/web/.env.example apps/web/.env.local
# edit apps/web/.env.local with your Supabase project URL and anon key

# 5. Start backend
cd backend && uv run uvicorn app.main:app --reload --port 8000

# 6. Start frontend (in another terminal)
pnpm --filter @neuroquant/web run dev
```

---

## Adding a new environment variable

1. Add the field to `backend/app/core/config.py` (or `apps/web/.env.local` for
   frontend-only vars).
2. Add a commented line to `backend/.env.example` (and `backend/.env.local.example`).
3. The unit test `test_all_settings_fields_present_in_env_example` will fail in
   CI if you forget step 2.
4. Add the secret to GitHub Secrets, Cloud Run env, and/or Vercel env as
   appropriate per the table above.
