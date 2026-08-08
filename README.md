# NeuroQuant (QuantEdge) - Intelligent Trading Platform

NeuroQuant is a full-stack, ML-driven educational paper-trading platform. It executes statistical models (GARCH, HMM) and gradient boosted trees (XGBoost) to forecast market direction without requiring any paid API keys or subscriptions.

## 🌟 Key Features

- **Honesty Law Validated**: A strict guard ensures any model with >75% walk-forward accuracy is blocked from deployment, preventing look-ahead bias and feature leakage.
- **Resilient Data Layer**: Integrates `yfinance` with an honest fallback to an alternative Indian stock API (`0xramm`), gracefully degrading (HTTP 503) without serving mocked data if both fail.
- **Regime-Aware ML**: Implements HMM-GARCH regime detection. Final signals dynamically weight Technical (40%) and ML (60%) indicators based on the detected market regime (trending vs. mean-reverting).
- **Subscription Billing (Razorpay)**: Includes a full Next.js/FastAPI implementation of Razorpay subscription billing with HMAC webhook verification, strictly gating advanced Explainability routes without hiding user portfolio data.
- **Fully Typed Next.js Terminal**: A real-time WebSocket-powered dashboard built on Tailwind CSS, mimicking production broker UI density.

---

## 🏗️ Architecture & Data Collection

### **Data Ingestion**
- Data is dynamically collected from public APIs (Yahoo Finance via `yfinance`). 
- Feature generation includes 14-day RSI, MACD, Bollinger Bands, ATR, ADX, and Candlestick Patterns.

### **ML Fusion Rule**
The system uses an explicit fusion mechanism to generate trading signals:
`Final Signal = (0.4 * Technicals) + (0.6 * ML Probability) + Sentiment Tilt + Regime Gate`
The Regime Gate suppresses specific directional signals during BEAR/CRISIS regimes.

---

## 💻 Pages & User Workflows

### **1. Registration & Authentication (`/register` & `/login`)**
- **User Flow**: Users can safely register an account. Authentication is handled securely, granting access to the primary dashboard. By default, user accounts operate in **Paper Trading Mode**.
- **Admin Flow**: Admins log in via the same portal but are routed to the Admin Dashboard (Role-Based Access Control) to monitor system health, database pipelines, and trigger manual ML pipeline retrains.

### **2. Main Dashboard & Portfolio (`/dashboard`)**
- High-level overview of portfolio value, unrealized P&L, and open paper-trading positions.
- Connects directly to the backend to fetch live holdings using `Instrument.symbol`.

### **3. Trading Terminal (`/terminal`)**
- Live OHLCV chart interface powered by a custom grid layout.
- **Order Execution Panel**: Place paper trades mapped against real-time quotes.
- **Prediction Overlay**: Visualizes the AI's expected-move directly on the terminal.

### **4. Explainability & Research (`/research/explainability`)**
- Breaks down the ML engine's decision-making process.
- Visualizes the SHAP waterfall for the current prediction.

### **5. Regime Analysis (`/research/regime-analysis`)**
- Real-time HMM regime timelines (BULL, BEAR, CRISIS).

---

## 🚀 Setup & Execution Guide (End-to-End)

### **Prerequisites**
- Node.js (v18+) & `npm` or `pnpm`
- Python 3.10+
- (Optional) Docker for Redis/Postgres if not using SQLite

### **1. Environment Configuration**
You will need to configure `.env` files for both the backend and frontend.

**Backend (`backend/.env`)**:
```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./dev.db
# Redis/Celery (For background tasks)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
# Trading Mode
PAPER_TRADING_MODE=true
# Secret Keys
SECRET_KEY=your-super-secret-jwt-key
# External APIs (Optional for testing)
RAZORPAY_KEY_ID=
ANGEL_ONE_CLIENT_ID=
```

**Frontend (`apps/web/.env.local`)**:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### **2. Start the Backend API (FastAPI)**
Navigate to the `backend` directory, install requirements, and boot FastAPI:

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the API on port 8000
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*The Backend API is now running at `http://localhost:8000/api/v1`*

### **3. Start the Frontend UI (Next.js)**
In a new terminal window, boot the Next.js application:

```bash
cd apps/web

# Install dependencies
npm install

# Start the development server
npm run dev
```
*The web UI is now running at `http://localhost:3000`*

---

## 🛠️ Helpful Commands & Scripts

- **Run Frontend Build**: `cd apps/web && npm run build`
- **Run Backend Tests**: `cd backend && pytest`
- **Start Celery Worker**: `cd backend && celery -A app.core.celery_app worker --loglevel=info`

---

## 📜 Troubleshooting

If you encounter **UI Errors** such as `Attempted import error: 'PanelGroup' is not exported` or **Backend Database Errors** such as `AttributeError: type object 'Instrument' has no attribute 'ticker'`:
1. Ensure you have the latest code pulled (these bugs were resolved by mapping `PanelGroup` -> `Group` and `Instrument.ticker` -> `Instrument.symbol`).
2. **CRITICAL**: Completely stop your Next.js frontend (`Ctrl+C`), delete the `.next` folder (`rm -rf .next`), and restart the dev server (`npm run dev`) to clear cached errors.

## 📱 Mobile Responsiveness (Phase U0-U7 Updates)
The entire application, including the Terminal, Research pages, and Model Monitor, has been fully audited and updated for `375px` mobile responsiveness. If a layout appears broken on mobile, ensure you have cleared your browser cache. All hardcoded/fallback metric loading states have been removed in favor of strict, honest backend data streaming.
