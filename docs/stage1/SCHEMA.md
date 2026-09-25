# Canonical Schema

## Core Domains
- **Market Data**: `exchanges`, `instruments`, `market_calendar`, `ohlcv`, `quote_snapshots`
- **Operational**: `ingestion_runs`, `data_quality_events`, `model_registry`
- **Identity & Billing**: `users`, `organizations`, `org_members`, `plans`

## Standards
- Tables use Plural naming.
- UUIDs for all primary keys.
- Timestamp with timezone for all dates/times.
- JSONB for flexible payload storage where necessary.
