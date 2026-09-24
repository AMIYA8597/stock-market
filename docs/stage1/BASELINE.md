# Database Baseline & Inventory (Stage 1)

## 1. Local SQLite Inventory (`dev.db`)

We executed an inventory script against the existing `dev.db` database and classified the data points found:

| Table Name | Row Count | Classification | Migration Decision |
| :--- | :--- | :--- | :--- |
| `refresh_sessions` | 117 | Test/Log | DO NOT MIGRATE |
| `ohlcv` | 99 | Synthetic | DO NOT MIGRATE |
| `backtest_jobs` | 8 | Test | DO NOT MIGRATE |
| `users` | 5 | Demo/Test | DO NOT MIGRATE |
| `instrument` | 5 | Demo | DO NOT MIGRATE |
| `model_artifact` | 5 | Test | DO NOT MIGRATE |
| `model_metric` | 5 | Test | DO NOT MIGRATE |
| `paper_wallets` | 4 | Test | DO NOT MIGRATE |

**Verdict:** All data in the local SQLite database is classified as Demo, Test, or Synthetic (e.g. static 100/101/105 OHLCV values, and hardcoded `testuser` accounts). None of this data belongs in the production or staging Canonical PostgreSQL database. We will proceed with a fresh slate for real market data ingestion.

## 2. PostgreSQL Target Schema

The Supabase/PostgreSQL schema is established via Alembic in `d3f7c1169f51_stage_1_init.py` and `d7bf2b1f317b_stage_1_init.py`.

### Architecture Alignment
- **Instruments:** `instruments` (canonical symbol, exchange) and `instrument_aliases` (provider mapping).
- **Users:** `users` mapped via `auth_id` to Supabase Auth.
- **Row-Level Security (RLS):** Fully enabled on all tables.
  - Transactions use `set_config('request.jwt.claim.sub', :uid, true)` to impersonate API callers.
  - System bypass enabled via `set_config('app.is_system', 'true', true)` for operations like user registration.
- **Market Data:** `exchanges`, `instruments`, `market_calendar`, `ohlcv`, `quote_snapshots` are appropriately isolated with `SELECT USING (true)` policies for public read.
- **SQLite Usage:** `sqlite3` driver was successfully identified and purged from `app/services/intelligence_service.py` where it was used as a runtime fallback for model monitoring metrics.

## 3. Current PostgreSQL Local State (`neuroquant_stage1`)

| Table Name | Row Count |
| :--- | :--- |
| `market_calendar` | 44 |
| `ohlcv` | 20 |
| `ingestion_runs` | 6 |
| `instruments` | 1 |
| `instrument_aliases` | 1 |
| `exchanges` | 1 |
| `quote_snapshots` | 1 |

The baseline migration sets up the required foundation. We are now ready to implement the canonical market data ingestion path.
