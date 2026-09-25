# Ingestion Runbook

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
