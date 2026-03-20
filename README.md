# NEUROQUANT Stock Market Platform

Production-focused monorepo for an advanced stock market platform with:

- Modern Next.js frontend UI
- FastAPI backend monolith
- Optional domain microservices (kept in `services/`)

This repository has been cleaned to keep core app code and reduce unused root-level clutter.

## Core Structure

- `apps/web/` - Next.js 14 frontend (App Router)
- `backend/` - FastAPI backend API and business logic
- `services/` - Independent Python services (optional)
- `packages/` - Shared TypeScript packages
- `scripts/` - Utility scripts

## Frontend Structure

- `apps/web/src/app/` - Routes and layouts
- `apps/web/src/components/` - UI components
- `apps/web/src/lib/` - API client and providers
- `apps/web/src/stores/` - Zustand state stores
- `apps/web/src/types/` - Shared frontend types

## Backend Structure

- `backend/app/main.py` - FastAPI entry point
- `backend/app/api/` - API routes
- `backend/app/core/` - Config, DB, security
- `backend/app/models/` - SQLAlchemy models
- `backend/app/schemas/` - Pydantic schemas
- `backend/app/services/` - Business services

## Local Development (UI + Backend Only)

1. Install Node dependencies:

```bash
pnpm install
```

2. Run frontend:

```bash
pnpm --filter @neuroquant/web dev
```

3. Create Python environment and install backend dependencies:

```bash
pip install -r backend/requirements.txt
```

4. Run backend from `backend/`:

```bash
uvicorn app.main:app --reload --port 8000
```

## Sequential Build Pipeline (Backend)

From `backend/`, run the strict sequence used for schema/data/features/model setup:

```bash
python scripts/run_sequential_build.py --years 5 --interval 1d --model all --symbol NIFTY --universe NSE
```

You can also run steps individually:

```bash
python scripts/verify_schema.py
python scripts/data_pipeline.py --full-history --years 5
python scripts/data_pipeline.py --features-only --interval 1d
python scripts/model_trainer.py --model all --symbol NIFTY --universe NSE
```

## Notes

- Heavy infrastructure setup (Docker/AWS/etc.) is intentionally not required for the basic UI + backend workflow.
- Keep future additions inside existing app/service folders instead of adding root-level phase/status files.
