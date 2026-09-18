# Issues Audit (Phase 1)

## Backend Issues (Python)
We ran `ruff` across the entire backend directory, identifying and automatically fixing 94 linting and code quality issues (such as unused imports, unused variables, and style violations). 
The remaining unresolved issues include:
- Unused variables inside loop bodies and testing scripts.
- Bare `except` blocks in `scripts/check_endpoints.py` and `scripts/recover.py` which could silently swallow important errors.

*Status: Fixed 94 minor issues.*

## Frontend Issues (React / Next.js)
We ran `next lint` across the Next.js frontend (`apps/web`). The codebase is clean, with only a few hook dependency warnings:
- `usePriceFeed.ts` & `useSignalFeed.ts`: Missing dependency `symbols`.

*Status: Non-critical.*

## Structural & Architecture Issues
- **Microservices Separation**: Currently, ML ingestion, prediction, and API are combined in a monolithic FastAPI app. Moving heavy AI inference to dedicated microservices will improve scalability.
- **Database Engine**: Transitioning heavy time-series data to TimescaleDB is necessary for performance on OHLCV data.
- **Data Pipeline**: The ingestion pipeline needs to support WebSocket streaming concurrently with REST polling.
