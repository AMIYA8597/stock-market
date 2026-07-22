# NeuroQuant

NeuroQuant is an AI-powered stock market intelligence system built with a modern stack: Next.js 14 App Router, React 18, TailwindCSS, and FastAPI. It integrates real-time free market data, interactive financial charts, predictive modeling, and paper trading capabilities into a high-performance single-page application dashboard.

## Key Features
- **Real-time Free Data**: Connects exclusively to free market data sources (Yahoo Finance, NSE) — no paid keys required.
- **Predictive AI Models**: Uses statistical and ML models (HMM, TFT) located in `backend/research/` to generate trading signals and regimes.
- **Portfolio & Paper Trading**: Manage watchlists, track active simulated positions, and execute virtual trades based on ML signals.
- **Responsive Web Dashboard**: Clean hierarchy and dark mode Radix/Tailwind components via `@neuroquant/ui`. 
- **Graceful Degradation**: Truthful representation of data. If models haven't converged or the market is closed, the UI accurately reflects the empty state instead of faking data.

## Monorepo Structure
- `apps/web/`: Next.js 14 App Router frontend.
- `packages/ui/`: Radix-based design system and UI components.
- `packages/types/`: Shared TypeScript definitions.
- `backend/`: FastAPI backend with SQLAlchemy (SQLite/Postgres), Redis, and WebSockets.
  - `backend/app/`: Core FastAPI server, routers, WebSocket tickers.
  - `backend/research/`: ML pipelines, backtesting engine, statistical tests.

## Requirements
- Node.js 20+, pnpm 8+
- Python 3.12+ (or your preferred Python 3 environment)
- Redis server (for WebSocket PubSub and task queue caching)

## Quick Start (Local Development)

### 1. Frontend Setup
```bash
# Install dependencies from the monorepo root
pnpm install

# Start the Next.js development server
pnpm --filter @neuroquant/web dev
```

### 2. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt

# Start the FastAPI backend
python -m uvicorn app.main:app --reload --port 8000
```

### 3. Environment Variables
Copy `.env.example` to `.env` in both the root and `backend/` directories.
```bash
cp .env.example .env
```
Broker keys (Razorpay, Upstox, AngelOne) are strictly optional. The application is designed to function comprehensively without them.

## Testing & Validation
To run the unified test gate that validates the frontend build and backend tests:
```bash
pnpm test
```
The backend tests run using `pytest` inside the `backend/` directory:
```bash
cd backend
pytest tests/ -v
```
