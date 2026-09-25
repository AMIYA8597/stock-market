import os

DOCS_DIR = r"d:\work\stock-market\docs\stage1"
os.makedirs(DOCS_DIR, exist_ok=True)

files = {
    "BASELINE.md": """# Stage 1: Baseline Architecture

## Overview
Stage 1 sets up the core Supabase PostgreSQL database architecture, implements canonical canonical data models, and integrates Row-Level Security (RLS) for multi-tenant isolation.
The architecture avoids SQLite as a hidden fallback and MongoDB as a hidden runtime data store.

## Key Decisions
- **PostgreSQL**: Canonical production database. Free-tier capacity (500MB) acts as a hard engineering constraint.
- **SQLAlchemy & Alembic**: Used for ORM and migrations.
- **Unified Ingestion**: Consolidated market data ingestion into a single module. No synthetic data.
- **Strict RLS**: True Row Level Security integrated with identity propagation (`app.user_id`, `app.is_system`).
""",
    "SCHEMA.md": """# Canonical Schema

## Core Domains
- **Market Data**: `exchanges`, `instruments`, `market_calendar`, `ohlcv`, `quote_snapshots`
- **Operational**: `ingestion_runs`, `data_quality_events`, `model_registry`
- **Identity & Billing**: `users`, `organizations`, `org_members`, `plans`

## Standards
- Tables use Plural naming.
- UUIDs for all primary keys.
- Timestamp with timezone for all dates/times.
- JSONB for flexible payload storage where necessary.
""",
    "MIGRATION_MAP.md": """# Database Migration Map

- `53aef4df1952_stage_1_init.py`: The single unified baseline migration representing the completed Stage 1 schema. Includes the base schema models, RLS policies, constraints, and initial indices.
- All legacy patches and fix scripts were purged.
""",
    "PROVIDER_MATRIX.md": """# Provider Matrix

| Provider | Data Domains | Regions | Status |
|---|---|---|---|
| yfinance | Quotes, OHLCV | Global | Active (Primary) |
| NSE (via raw HTTP) | Quotes, Universe | India | Secondary |
| Stooq | Quotes, OHLCV | Global | Secondary |

- **YFinance**: Primary for historical data. Implemented directly via `yfinance` python library to circumvent cookie/crumb scraping issues natively.
- **Stooq / NSE**: Configured as failovers.
""",
    "INGESTION_RUNBOOK.md": """# Ingestion Runbook

## Philosophy
No synthetic data. Prefer EMPTY / UNAVAILABLE / DEGRADED over fake data.

## Process
1. Initialize an `IngestionRun` tracking object to capture dataset provenance, job type, counts, and status.
2. Ensure Exchanges and Instruments exist in canonical master tables.
3. Fetch data via primary provider (e.g., `yfinance`).
4. Perform canonical transformations mapping to `OHLCV` or `QuoteSnapshot` models.
5. Use `ON CONFLICT DO UPDATE` patterns to achieve idempotency for market data ingestion.

## Schedulers
Unbounded loops using `APScheduler` were removed. Schedulers of record (like Github Actions or Celery) orchestrate heavy jobs to external triggers, freeing API concurrency.
""",
    "ACCEPTANCE.md": """# Stage 1 Acceptance Criteria

1. **Database Baseline**: `alembic upgrade head` applies cleanly. (PASS)
2. **Identity & RLS**: RLS policies applied via `rls.sql` injection. Proper role usage. (PASS)
3. **Data Quality**: Real ingestion of 5 instruments and 1 year history. No fake data. (PASS)
4. **Validation Check**: `check_stage1_ready.py` strictly verifies required tables, RLS rules, Alembic HEAD, and OHLCV records. All checks return `[PASS]`. (PASS)
"""
}

for name, content in files.items():
    path = os.path.join(DOCS_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

print("Docs generated.")
