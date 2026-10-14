# NeuroQuant Environment Variables Inventory

This inventory documents all environment variables used across the NeuroQuant platform. 
**Security Rule**: Never commit secret values or print them in diagnostic logs or build artifacts. Store secret values in Vercel Project Settings, Google Cloud Secret Manager, or GitHub Actions Secrets.

---

## 1. Web Application (`apps/web` — Vercel)

| Variable | Scope | Type | Required | Description & Default |
|---|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | Public / Client | URL | Yes | Canonical origin for the backend API (e.g. `https://neuroquant-api-6g57r5groa-el.a.run.app`). |
| `NEXT_PUBLIC_WS_URL` | Public / Client | URL | Yes | WebSocket endpoint (e.g. `wss://neuroquant-api-6g57r5groa-el.a.run.app/ws/stream`). |
| `NEXT_PUBLIC_SUPABASE_URL` | Public / Client | URL | Yes | Public Supabase API URL. |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Public / Client | Token | Yes | Public anon key for client-side Supabase authentication. |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only | Secret | No | Service role secret for server actions (never exposed to browser). |

---

## 2. Backend Application (`backend` — Google Cloud Run)

### Core Runtime & Database
| Variable | Scope | Sensitivity | Required | Description |
|---|---|---|---|---|
| `ENVIRONMENT` | Server | Config | Yes | `production`, `staging`, or `development`. |
| `DATABASE_URL` | Server | Secret | Yes | SQLAlchemy async connection string (pgBouncer transaction pool, e.g. `postgresql+asyncpg://postgres.[ref]:[pass]@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres`). |
| `DIRECT_URL` | Server | Secret | Optional | Direct session connection string for Alembic migrations. |
| `REDIS_URL` | Server | Secret | Yes (Prod) | Redis connection string (e.g. `rediss://default:[token]@[host]:6379`). In-memory fallback allowed only in development. |
| `SECRET_KEY` | Server | Secret | Yes | Master secret key used for HMAC ticket signing and internal encryption. |
| `PORT` | Server | Config | Auto | Cloud Run port (defaults to 8080). |

### Authentication & Supabase
| Variable | Scope | Sensitivity | Required | Description |
|---|---|---|---|---|
| `SUPABASE_URL` | Server | Config | Yes | Supabase endpoint URL. |
| `SUPABASE_JWKS_URL` | Server | Config | Yes | Public JWKS endpoint used to verify JWT tokens locally (`https://[ref].supabase.co/auth/v1/.well-known/jwks.json`). |
| `SUPABASE_SERVICE_ROLE_KEY` | Server | Secret | Optional | Admin secret for administrative database operations. |

### Market Data Feeds
| Variable | Scope | Sensitivity | Required | Description |
|---|---|---|---|---|
| `LIVE_DATA_PROVIDER` | Server | Config | Yes | Default live data provider: `upstox`. |
| `UPSTOX_ENABLED` | Server | Config | Yes | Set to `true` to enable Upstox live feed integration. |
| `UPSTOX_ANALYTICS_TOKEN` | Server | Secret | Optional | Read-only analytics token for Upstox market data access. |
| `UPSTOX_API_KEY` | Server | Secret | Optional | Upstox broker API key for OAuth authentication. |
| `UPSTOX_API_SECRET` | Server | Secret | Optional | Upstox broker API secret. |
| `UPSTOX_REDIRECT_URI` | Server | URL | Optional | OAuth callback redirect URL. |

### LLM Providers & Reasoning
| Variable | Scope | Sensitivity | Required | Description |
|---|---|---|---|---|
| `GROQ_API_KEY` | Server | Secret | Optional | Groq API key for low-latency LLaMA-3.1-8B inference. |
| `GEMINI_API_KEY` | Server | Secret | Optional | Google Gemini API key for multimodal reasoning. |
| `OPENAI_API_KEY` | Server | Secret | Optional | OpenAI API key for GPT-4o inference. |
| `ANTHROPIC_API_KEY` | Server | Secret | Optional | Anthropic API key for Claude 3.5 Sonnet inference. |
| `DEEPSEEK_API_KEY` | Server | Secret | Optional | DeepSeek API key for quantitative analysis. |

### Email Delivery (SendGrid)
| Variable | Scope | Sensitivity | Required | Description |
|---|---|---|---|---|
| `SENDGRID_API_KEY` | Server | Secret | Optional | SendGrid API key for transactional emails. |
| `SENDGRID_FROM_EMAIL` | Server | Config | Optional | Verified sender email address (e.g. `notifications@neuroquant.com`). |

---

## 3. Mandatory Safety Guardrails

The following variables are hardcoded safety defaults and **must not be bypassed**:

```bash
# Safety invariants
TRADING_MODE=paper
LIVE_ORDER_EXECUTION_ENABLED=false
AUTOTRADE_MAX_QUOTE_AGE_SECONDS=120
```

- If `LIVE_ORDER_EXECUTION_ENABLED=true` is set in production, the application will refuse to start.
- `TRADING_MODE` must remain `paper`.
