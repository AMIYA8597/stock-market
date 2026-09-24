# NeuroQuant 🧠📈

> **Production-Grade Algorithmic Trading & ML Forecasting Engine**

NeuroQuant is a sophisticated, hybrid architecture platform combining quantitative finance, machine learning (ML), and a real-time web terminal. It fuses classical technical analysis with Explainable AI (XAI) to generate high-probability trading signals.

This document serves as the **Ultimate Knowledge Transfer (KT)** guide. By reading this, any engineer can clone, understand, configure, and deploy the entire project.

---

## 📑 Table of Contents
1. [System Architecture & Data Flow](#1-system-architecture--data-flow)
2. [Directory Structure](#2-directory-structure)
3. [Environment Configuration (.env)](#3-environment-configuration-env)
4. [Local Setup & Running the Stack](#4-local-setup--running-the-stack)
5. [ML Pipeline & Model Training](#5-ml-pipeline--model-training)
6. [Trading Strategies & Backtesting](#6-trading-strategies--backtesting)
7. [Production Deployment](#7-production-deployment)
8. [Troubleshooting & Gotchas](#8-troubleshooting--gotchas)

---

## 🏗️ 1. System Architecture & Data Flow

NeuroQuant operates as a decoupled microservices stack:

- **Frontend (Next.js 14 App Router)**: A TradingView-style terminal with real-time WebSockets, Zustand state management, and TailwindCSS.
- **Backend (FastAPI)**: The nerve center. Handles authentication, REST API, WebSocket streams, and triggers ML inference.
- **ML Engine (Python/Celery)**: Runs background tasks for feature engineering (TA-Lib/Pandas TA), model training (XGBoost/LightGBM/RF), and regime detection (HMM/GARCH).
- **Database (PostgreSQL + TimescaleDB)**: Stores high-frequency OHLCV data, model artifacts, and user configurations. (SQLite is used for local dev).
- **Cache / Broker (Redis)**: Powers Celery task queues and caches real-time market quotes.

### Data Flow Pipeline
`Market Data (yfinance/NSE)` ➔ `Celery Ingestion Task` ➔ `Feature Engineering` ➔ `ML Inference` ➔ `FastAPI WebSocket` ➔ `Next.js UI`

---

## 📂 2. Directory Structure

```text
.
├── apps/
│   └── web/                      # Next.js 14 Frontend Application
│       ├── src/components/       # UI Components (Terminal, Charts)
│       ├── src/app/              # Next.js App Router (Pages & API proxies)
│       └── .env.local            # Frontend Environment Variables
├── backend/                      # FastAPI & ML Intelligence Engine
│   ├── app/
│   │   ├── api/v1/               # REST API Routes (market, predictions, trading)
│   │   ├── core/                 # Configs, Security, Celery initialization
│   │   ├── models/               # SQLAlchemy Database Models
│   │   ├── services/             # Core Logic (Data Ingestion, Signal Engines)
│   │   └── tasks/                # Celery Background Tasks
│   ├── scripts/                  # Utilities (DB migration, seeders)
│   └── .env                      # Backend Environment Variables
├── docker-compose.yml            # Production/Dev Docker orchestration
└── README.md                     # You are here
```

---

## ⚙️ 3. Environment Configuration (.env)

Before running anything, you must configure the environment variables.

### Backend (`backend/.env`)
Create a file at `backend/.env` and populate it:
```env
# Database Configuration
# Local SQLite for testing: sqlite+aiosqlite:///./dev.db
# Production Postgres: postgresql+asyncpg://user:pass@host:5432/neuroquant
DATABASE_URL=sqlite+aiosqlite:///./dev.db

# Redis Cache & Celery Broker
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# Security & Auth
SECRET_KEY=generate_a_secure_random_string_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Trading Execution Modes
PAPER_TRADING_MODE=true
```

### Frontend (`apps/web/.env.local`)
Create a file at `apps/web/.env.local`:
```env
# Points to the FastAPI backend
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/v1/ws
```

---

## 🚀 4. Local Setup & Running the Stack

### Prerequisites
- **Node.js** (v20+) & **pnpm** (v8+)
- **Python** (3.10 - 3.12)
- **Redis Server** (Running locally on port 6379)

### Step 1: Start the Backend (FastAPI)
```bash
cd backend
python -m venv .venv

# Activate Virtual Environment
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate    # Windows

# Install Dependencies
pip install -r requirements-core.txt

# Start the API Server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*API is live at `http://localhost:8000`. Swagger Docs at `http://localhost:8000/docs`.*

### Step 2: Start the Background Workers (Celery)
In a new terminal window (with the python venv activated):
```bash
cd backend
# Windows users might need to add: --pool=solo
celery -A app.core.celery_app worker --loglevel=info
```

### Step 3: Start the Frontend UI (Next.js)
In a new terminal window:
```bash
cd apps/web
pnpm install
pnpm run dev
```
*UI is live at `http://localhost:3000`.*

---

## 🤖 5. ML Pipeline & Model Training

The ML engine trains RandomForest, XGBoost, and LightGBM models on historical data, evaluating them against a strict "Honesty Law Guard" to prevent look-ahead bias.

**To manually trigger a training run:**
```bash
cd backend
# Activate venv
python test_train.py
```
*What this does:*
1. Downloads historical OHLCV data.
2. Generates causality-safe technical features.
3. Fits the models and calculates accuracy, precision, and Sharpe ratio.
4. Saves the best model artifacts to the database.

---

## 📈 6. Trading Strategies & Backtesting

The platform natively implements complex Pine Script algorithms in Pandas for high-speed backtesting and live signal generation.

### Implemented Strategies:
1. **EZ Algo EMA Suite** (`backend/app/services/ez_algo_service.py`)
   - Multi-timeframe EMA crossovers.
   - Dynamic filters: ADX > 25, ATR Expansion, Bollinger Squeeze.
2. **Optimized Retest Strategy** (`backend/app/services/optimized_retest_strategy.py`)
   - 10/30/50 EMA Trend alignment.
   - **40% Body Minimum**: Strict candle quality filter to ignore wicks/dojis.
   - **Smart Pyramiding**: Max 2 entries per cycle, adds to position ONLY if the 1st trade is in profit.

**To run a strategy backtest:**
```bash
cd backend
# Runs a 5-minute interval backtest for the Optimized Retest Strategy
python test_retest_5m.py

# Runs 1-hour backtest comparing Risk/Reward ratios
python run_backtest.py
```

---

## 🐳 7. Production Deployment

For production, the entire stack is containerized using Docker.

1. Ensure `.env` files point to production Postgres/Redis URLs.
2. Run Docker Compose:
```bash
docker-compose up --build -d
```
This spins up:
- `frontend` (Next.js production build)
- `backend` (Gunicorn + Uvicorn workers)
- `celery_worker` (Background ML processing)
- `celery_beat` (Cron jobs for daily data ingestion)

---

## ⚠️ 8. Troubleshooting & Gotchas

- **"Model says not trained" in UI**: The Celery worker hasn't finished training, or the database connection failed. Run `python test_train.py` manually to diagnose.
- **Database Locked Errors**: If using local SQLite (`dev.db`), simultaneous writes from Celery and reads from FastAPI can cause locks. Use PostgreSQL for heavy testing.
- **Redis Connection Refused**: Ensure Redis is actually running (`redis-cli ping`). Celery and WebSockets will fail completely without it.
- **UI Hydration Errors**: Mismatch between Server-Side Rendering and Client. Stop Next.js, delete the `apps/web/.next` folder, and restart.
- **PowerShell vs Bash**: If running Celery on Windows, use `--pool=solo` to prevent multiprocess forking errors.

---
*Developed by the NeuroQuant Architecture Team.*
