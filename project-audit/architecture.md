# Architecture Audit

## Current Architecture
The current monorepo structure contains:
- `apps/web`: Next.js frontend application with React, Tailwind CSS, lightweight-charts.
- `backend/`: FastAPI backend with Celery tasks, Redis caching, SQLAlchemy, Alembic migrations, and ML/DL modules.
- `packages/`: Shared TS configuration, UI components, and types.

## Backend Stack
- **API Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache / Message Broker**: Redis
- **Background Tasks**: Celery
- **ML / AI**: PyTorch, XGBoost, LightGBM, SHAP
- **Real-Time**: WebSockets for live data

## Frontend Stack
- **Framework**: Next.js 14 (App Router)
- **State Management**: Zustand, React Query
- **Charting**: TradingView Lightweight Charts
- **UI**: TailwindCSS, Radix UI

## Areas of Improvement
1. **Microservices Separation**: Currently, ML ingestion, prediction, and API are combined in a monolithic FastAPI app. Moving heavy AI inference to dedicated microservices will improve scalability.
2. **Database Engine**: Transitioning heavy time-series data to TimescaleDB (as planned) is necessary for performance on OHLCV data.
3. **Data Pipeline**: The ingestion pipeline needs to support WebSocket streaming concurrently with REST polling.
