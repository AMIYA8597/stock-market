# NeuroQuant (QuantEdge)
**Institutional-Grade Indian Stock Market AI Prediction & Trading Platform**

NeuroQuant is a full-stack, local-first ML-driven educational paper-trading and live-trading platform. It executes statistical models (GARCH, HMM) alongside gradient-boosted trees (XGBoost/LightGBM) and deep sequence models (LSTM, TFT) to forecast market direction—without relying on paid API keys or subscriptions.

This README serves as the **Comprehensive Knowledge Transfer (KT) Document** for new engineers joining the team. Read it top-to-bottom to understand the entire system architecture, data flows, and operational procedures.

---

## 🌟 1. Core Philosophy & Features

- **The Honesty Law Guard**: Financial markets are highly stochastic. A strict guard mechanism ensures any model claiming >75% walk-forward accuracy is immediately blocked from deployment, preventing look-ahead bias and feature leakage.
- **Regime-Aware ML Fusion**: The system detects the current market regime (Bull, Bear, Sideways) via 3-State Gaussian HMMs. The final trading signal dynamically fuses Technical Indicators (40%) and ML Probabilities (60%), gating aggressive trades during CRISIS regimes.
- **Resilient Data Layer**: Integrates primarily with `yfinance` with an honest fallback to NSE APIs and `0xramm`, gracefully degrading rather than serving mocked/stale data.
- **Explainable AI (XAI)**: SHAP values are extracted post-inference for feature attribution, proving to the user *why* a model made a specific prediction via an interactive SHAP waterfall.
- **Production-Grade UI**: A fully-typed Next.js App Router frontend mimicking production broker UI density with real-time WebSocket-powered TradingView charts.

---

## 🏗️ 2. Infrastructure & Services Stack

The system relies on a hybrid microservice and monolithic architecture orchestrated via Docker Compose.

| Service | Port | Role | Notes |
|---------|------|------|-------|
| **Frontend** | `3000` | Next.js 14 App Router | React 18, Tailwind CSS, Zustand, React Query |
| **Backend** | `8000` | FastAPI | Uvicorn running `app.main:app` (Python 3.10+) |
| **Database** | `5432` | PostgreSQL (TimescaleDB) | Primary persistence, partitioned via hypertables |
| **Redis** | `6379` | Cache / Celery Broker | In-memory cache and WebSocket Pub/Sub backend |
| **Celery** | N/A | Background Workers | ML Training, daily data ingestion, HMM/GARCH fitting |

---

## 🛤️ 3. Request Pipeline & API Surfaces

The backend API acts as the nerve center.

**The Pipeline**: `Next.js Client` → `API Route / Proxy` → `FastAPI Middlewares (CORS, Rate Limit, Auth)` → `Router Endpoint` → `Domain Service` → `Data/ML Layer` → `JSON Response`.

**Primary API Mounts:**
- `/api/v1` - Primary Modern REST API.
- `/api` - Academic/Compatibility REST API (QuantEdge legacy routes).
- `ws://...` - WebSocket routes for live pricing and signals.

**Key Routers (`backend/app/api/v1/`):**
- `market.py`: Live quotes, history, indices, heatmaps.
- `predictions.py`: ML forecasting, ensemble generation, historical accuracy.
- `trading.py` / `paper_trading.py`: Live broker integrations (Upstox/Angel One) and paper execution.
- `explain.py`: SHAP, attention weights, and counterfactuals.
- `models.py`: Monitor drift, accuracy, and ensemble weights over time.

---

## 🧠 4. ML Pipeline & Research Architecture

All heavy AI lifting occurs in `backend/research/` and `backend/app/services/ml_engine/`.

### **Data Flow (Prediction End-to-End)**
1. **Ingest**: End-of-day or intraday OHLCV is fetched via `MarketDataService`.
2. **Features**: 40+ cross-sectional and temporal features are computed (TA-Lib, Pandas TA). Features are strictly **causality-safe** to prevent look-ahead bias.
3. **Regime & Volatility**: GARCH(1,1) computes conditional volatility/cones. HMM detects the regime.
4. **Inference**: The `PredictionEngine` loads the best-performing trained artifact (XGBoost/LightGBM/LSTM).
5. **Fusion**: ML probability + classical technical signals + regime gate are combined to produce a final `STRONG_BUY` to `STRONG_SELL` signal.
6. **Delivery & UI**: Served via `/api/v1/predictions/latest/{symbol}`. The Next.js frontend renders the probability gauge, SHAP waterfall, and GARCH cone directly on the price chart.

### **Model Lifecycle (MLOps)**
- Models are trained using `backend/scripts` and persisted in `model_artifact` (SQLAlchemy).
- Evaluation statistics (Sharpe, Precision, Recall, Regime Breakdown) are saved in `model_metric`.
- A daily **Celery Beat** job (`check_drift_for_watchlist`) evaluates live PSI/KS metrics and triggers automated retraining if a model degrades.

---

## ⚡ 5. Real-Time Terminal & WebSockets

The terminal (`/terminal`) uses a hybrid data pattern:
1. **Initial Mount**: Fetches REST baseline data (watchlists, historical candles, last signal).
2. **Live Connection**: Establishes WebSockets (`useSignalFeed`, `usePriceFeed`) to the FastAPI backend.
3. **Reconciliation**: Incoming tick data seamlessly updates the Lightweight Charts without full HTTP re-renders, providing sub-second latency akin to Zerodha/TradingView.

---

## 🗺️ 6. Where to Change What (Developer Map)

If you are a new engineer, use this map to find where logic lives:

| Task | Location / File |
|------|-----------------|
| **Add a new REST endpoint** | `backend/app/api/v1/<domain>.py` |
| **Tweak signal/fusion logic** | `backend/app/services/signal_engine.py` & `prediction_engine.py` |
| **Add a new Technical Feature** | `backend/research/feature_engineering/` |
| **Add/Tune an ML Model** | `backend/research/models/` (Update metadata artifacts too!) |
| **Change Data Providers** | `backend/app/services/data_ingestion/` & `MarketDataService` |
| **Modify Terminal UI/Charts** | `apps/web/src/components/terminal/` & `hooks/useTerminalData.ts` |
| **Change DB Schema** | `backend/app/models/` & run `alembic revision --autogenerate` |
| **Add a Background Task** | `backend/app/tasks/` & register in `backend/app/core/celery_app.py` |

---

## 🚀 7. Local Setup & Execution Guide

### **Prerequisites**
- Node.js (v20+) & `pnpm` (v8+)
- Python 3.10 - 3.12
- Local Redis Server (or Docker equivalent)

### **1. Environment Configuration**
You will need `.env` files for the backend and frontend.
**Backend (`backend/.env`)**:
```env
# Database & Cache
DATABASE_URL=sqlite+aiosqlite:///./dev.db  # Use Postgres connection string for prod
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# Core settings
PAPER_TRADING_MODE=true
SECRET_KEY=your-super-secret-jwt-key
```

**Frontend (`apps/web/.env.local`)**:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### **2. Start the Backend API (FastAPI)**
```bash
cd backend
python -m venv .venv

# Activate:
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Mac/Linux

pip install -r requirements-core.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*API is now running at `http://localhost:8000/api/v1` (Swagger UI at `/docs`)*

### **3. Start the Frontend UI (Next.js)**
Open a new terminal:
```bash
pnpm install
cd apps/web
pnpm run dev
```
*The web UI is now running at `http://localhost:3000`*

### **4. Start Celery (For Background ML Tasks)**
```bash
cd backend
celery -A app.core.celery_app worker --loglevel=info
```

---

## 📜 8. Troubleshooting & Gotchas

1. **"Model says not trained" / Missing Predictions**: Ensure the background Celery workers have processed the initial training pipeline, and `model_artifact` has an active record for the symbol.
2. **"Failed to fetch" on Login**: Double-check `NEXT_PUBLIC_API_URL`. Ensure CORS settings in FastAPI (`app/main.py`) allow your frontend origin.
3. **Database locked / SQLAlchemy Errors (SQLite)**: If using SQLite locally, concurrent ML writes and API reads might lock the DB. Switch to PostgreSQL for true concurrency.
4. **Hydration Errors in Terminal**: This happens if the server-rendered HTML mismatches the client. Delete `.next` folder and run `pnpm run dev` again to clear caching issues.
5. **Two Task Namespaces**: Note there is `backend/tasks/` (legacy) and `backend/app/tasks/` (active). Ensure new jobs are registered in `backend/app/core/celery_app.py`.
6. **Performance Hit on Quotes**: The inference path can perform synchronous external data work if cache misses. Always ensure Redis is running!

---
*Maintained by the NeuroQuant Architecture Team. Welcome aboard!*
