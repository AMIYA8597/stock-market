# Stage 1: Baseline Architecture

## Overview
Stage 1 sets up the core Supabase PostgreSQL database architecture, implements canonical canonical data models, and integrates Row-Level Security (RLS) for multi-tenant isolation.
The architecture avoids SQLite as a hidden fallback and MongoDB as a hidden runtime data store.

## Key Decisions
- **PostgreSQL**: Canonical production database. Free-tier capacity (500MB) acts as a hard engineering constraint.
- **SQLAlchemy & Alembic**: Used for ORM and migrations.
- **Unified Ingestion**: Consolidated market data ingestion into a single module. No synthetic data.
- **Strict RLS**: True Row Level Security integrated with identity propagation (`app.user_id`, `app.is_system`).
