# QuantEdge Knowledge Transfer (KT) Document

Welcome to the QuantEdge project! This Knowledge Transfer (KT) document is designed to onboard new developers, explain the core architecture, detail the machine learning pipeline, and outline how to run and maintain the project.

---

## 1. Project Overview

**QuantEdge** (also referred to as NeuroQuant) is a full-stack, ML-driven educational paper-trading platform. It leverages advanced statistical models (GARCH, Hidden Markov Models) and machine learning (XGBoost, LightGBM, LSTM, TFT) to forecast market direction and provide real-time trading insights.

The platform is designed to:
- Ingest real-time and historical market data (via `yfinance` and fallback APIs).
- Compute 40+ technical indicators and sentiment features.
- Evaluate market regimes (Bull, Bear, Sideways, Crisis).
- Provide a paper-trading terminal to test strategies against ML predictions without risking real capital.

---

## 2. System Architecture

The project is structured as a modern monorepo with distinct frontend and backend services.

### A. Frontend (`apps/web`)
- **Framework**: Next.js 14 (App Router), React 18
- **Styling**: Tailwind CSS
- **State Management**: Zustand (local state) & React Query (server state & caching)
- **Data Visualization**: Lightweight Charts (TradingView) for candlestick rendering and prediction overlays.
- **Key Routes**:
  - `/dashboard`: Portfolio overview, unrealized P&L, and open paper-trading positions.
  - `/terminal`: The core trading interface with live charts, order panels, and prediction overlays.
  - `/research/explainability`: Deep dive into ML models using SHAP value waterfalls.

### B. Backend (`backend`)
- **Framework**: FastAPI (Async Python)
- **Database**: PostgreSQL (or SQLite for local dev via `aiosqlite`) managed by SQLAlchemy 2.0 ORM and Alembic migrations.
- **Background Tasks**: Celery with Redis for asynchronous ML training, heavy HMM/GARCH fitting, and end-of-day data ingestion.
- **Cache**: Redis for rapid API responses and WebSocket state.

---

## 3. The ML Pipeline (`backend/app/services/prediction_engine.py`)

The true engine of QuantEdge is its 7-layer predictive pipeline.

1. **Data Ingestion**: Fetches OHLCV data using `MarketDataService` (primarily relying on `yfinance`).
2. **Feature Engineering**: Runs a causality-safe `FeaturePipeline` that calculates RSI, MACD, Bollinger Bands, ATR, ADX, Candlestick Patterns, and Jegadeesh-Titman momentum using `pandas-ta`.
3. **Regime Detection (Layer 4)**: A 3-State Gaussian Hidden Markov Model (HMM) + GARCH(1,1) detects the current market environment (Bull, Bear, Sideways, Crisis).
4. **Base Models (Layer 5)**:
   - **XGBoost**: Trained via expanding-window walk-forward CV.
   - **LSTM-Attention**: Captures temporal sequences.
   - **TFT (Temporal Fusion Transformer)**: Generates quantile forecasts (p10, p50, p90) via LightGBM.
5. **Ensemble Fusion (Layer 6)**: 
   - Combines classical technical signals and ML probability.
   - `Final Signal = (0.4 * Technicals) + (0.6 * ML Probability) + Sentiment Tilt + Regime Gate`.
   - The Regime Gate suppresses counter-trend signals (e.g., blocks BUYs during CRISIS).
6. **Kelly Sizing**: Dynamically computes position sizing recommendations based on walk-forward out-of-sample win-rates.
7. **Forecast & Delivery (Layer 7)**: SARIMAX/HoltWinters projects future price paths to draw prediction cones on the frontend chart.

*(Note: If a model artifact isn't trained for a symbol, the `/api/v1/predictions/{symbol}` endpoint returns `503 MODEL_NOT_TRAINED`. This is intentional and prevents the UI from displaying hallucinated data).*

---

## 4. Local Setup & Execution

### Prerequisites
- Node.js (v18+) & `npm`
- Python 3.10+
- Redis Server (Running locally on `localhost:6379`)

### Running the Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# Boot the FastAPI server on port 8000
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Running the Frontend
```powershell
cd apps/web
npm install
# Boot the Next.js dev server on port 3000
npm run dev
```

---

## 5. Recent Fixes & Known Issues (July 2026)

If you are just joining the project, be aware of the following critical fixes that were just implemented to stabilize the system:

1. **Login loop fixed (`apps/web/src/lib/runtime-config.ts`)**:
   - *Issue*: Browser auth requests were hitting the backend as absolute cross-origin `http://localhost:8000/...` calls even though Next.js already exposed `/api/v1` rewrites.
   - *Impact*: Login failed in the UI with `Failed to fetch`, leaving users stuck on `/login`.
   - *Fix*: Local browser REST calls now prefer the same-origin Next.js proxy (`/api/v1/...`) whenever both frontend and backend are local.
2. **Registration lag fixed (`backend/app/services/email_service.py`)**:
   - *Issue*: Successful registration was blocked by a slow Celery broker failure while trying to enqueue welcome emails.
   - *Impact*: Signup looked frozen for several seconds even though the user record was created correctly.
   - *Fix*: Email task dispatch is skipped when alert/email delivery is disabled in local development, so registration returns immediately.
3. **Wrong post-root landing fixed (`apps/web/src/app/(app)/page.tsx`)**:
   - *Issue*: The authenticated app root redirected to `/terminal`.
   - *Impact*: Users expected the main landing screen/dashboard after auth, but instead saw `/terminal` in the URL.
   - *Fix*: The authenticated root now redirects to `/dashboard`.
4. **Double navbar on terminal fixed (`apps/web/src/components/layout/app-shell.tsx`)**:
   - *Issue*: The global shell only treated `/` as the terminal route.
   - *Impact*: `/terminal` rendered both the shell topbar and the terminal topbar.
   - *Fix*: Terminal route detection now correctly matches `/terminal` and nested terminal paths.
5. **Double shell on dashboard fixed (`apps/web/src/app/(app)/dashboard/layout.tsx`)**:
   - *Issue*: Dashboard had its own nested `AppShell` inside the main authenticated `AppShell`.
   - *Impact*: Sidebar/topbar content rendered twice on dashboard pages.
   - *Fix*: The dashboard route layout now returns children directly.
6. **Still expected in local dev**:
   - Backend `/health` remains `degraded` if Redis is not running locally.
   - Some model logs still warn about optional dependencies like `river` and `TA-Lib`.
   - Market/provider warnings do not block the basic auth flow anymore, but they still affect advanced live-signal quality.

---

## 6. Verified Local Flow (July 28, 2026)

The following flow was re-tested locally on **Tuesday, July 28, 2026**:

1. Open `http://localhost:3000/register`
2. Create a new account
3. Redirect to `http://localhost:3000/login`
4. Sign in with the new credentials
5. Land on `http://localhost:3000/dashboard`
6. Open `http://localhost:3000/terminal`
7. Confirm the terminal now shows a single top navigation/header stack

---

## 7. Important Current Limitation: 10,000+ Live Stocks

This repository is **not yet a true 10,000+ live-symbol production data platform**.

Today it still relies on a mixed local/free-provider setup (`yfinance`, NSE fallbacks, optional broker integrations, optional Redis/Celery workers). That is enough for development and paper-trading flows, but not enough to claim:

- guaranteed real-time coverage for 10,000+ instruments,
- exchange-grade accuracy at scale,
- production-grade market data SLAs,
- resilient streaming for all symbols simultaneously.

To truly support 10,000+ live-updating stocks, the next phase should define:

1. a canonical instrument master,
2. a dedicated market-data provider strategy,
3. symbol ingestion + normalization jobs,
4. Redis/pub-sub or stream fan-out architecture,
5. backpressure/rate-limit handling,
6. provider-health monitoring and replay/recovery paths.

---

## 8. Where to go from here?
- To understand how new ML models are trained, look at `backend/scripts/train_model.py` and `backend/research/models/`.
- To modify the trading UI grid, check `apps/web/src/components/terminal/TradingTerminal.tsx`.
- To adjust the fusion weights for technicals vs ML, edit `build_ensemble_signal` in `backend/app/services/prediction_engine.py`.
