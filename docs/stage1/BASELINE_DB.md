# PostgreSQL Inventory

## Version
`PostgreSQL 18.0 on x86_64-windows, compiled by msvc-19.44.35217, 64-bit`

## Installed Extensions
- plpgsql (v1.0)

## Schemas
- public
- information_schema
- pg_catalog
- pg_toast

## Tables (public)
| Table | Row Count | Size | RLS Enabled | Owner |
|---|---|---|---|---|

## Alembic Version
`No alembic_version table found`

## DB vs ORM Differences
- **In DB, not in ORM:** None
- **In ORM, not in DB:** {'paper_wallets', 'payment_transactions', 'portfolio_holdings', 'instrument', 'model_metric', 'regime_states', 'wallet_ledger', 'email_jobs', 'csrf_tokens', 'news_sentiment', 'backtest_jobs', 'refresh_sessions', 'billing_audit_logs', 'model_artifact', 'users', 'blog_posts', 'ml_predictions', 'ohlcv', 'paper_orders', 'transactions', 'password_reset_tokens', 'paper_positions', 'ensemble_signals', 'plans', 'feature_vectors', 'notifications', 'subscriptions', 'user_watchlist', 'alerts', 'trade_journals'}

## Indexes

## Roles and Privileges on Public Tables
| Role | Table | Privilege |
|---|---|---|

## Specific Capabilities Availability
- **timescaledb:** Not Installed
- **pg_cron:** Not Installed
- **pg_net:** Not Installed


---

# SQLite Inventory (`backend/dev.db`)
## Tables
| Table | Row Count |
|---|---|
| email_jobs | 5 |
| instrument | 5 |
| paper_wallets | 4 |
| paper_positions | 1 |
| paper_orders | 1 |
| plans | 1 |
| billing_audit_logs | 0 |
| users | 5 |
| alerts | 0 |
| refresh_sessions | 117 |
| password_reset_tokens | 0 |
| backtest_jobs | 8 |
| blog_posts | 0 |
| feature_vectors | 0 |
| trade_journals | 0 |
| model_artifact | 5 |
| notifications | 0 |
| payment_transactions | 1 |
| subscriptions | 3 |
| wallet_ledger | 0 |
| portfolio_holdings | 0 |
| ml_predictions | 0 |
| regime_states | 0 |
| sqlite_sequence | 0 |
| news_sentiment | 0 |
| ensemble_signals | 0 |
| transactions | 0 |
| user_watchlist | 0 |
| model_metric | 5 |
| alembic_version | 0 |
| universes | 1 |
| symbols | 1 |
| universe_memberships | 2 |
| datasets | 2 |
| ohlcv | 99 |

## Migration Recommendation
**Recommendation:** The local database contains data in: email_jobs (5 rows), instrument (5 rows), paper_wallets (4 rows), paper_positions (1 rows), paper_orders (1 rows), plans (1 rows), users (5 rows), refresh_sessions (117 rows), backtest_jobs (8 rows), model_artifact (5 rows), payment_transactions (1 rows), subscriptions (3 rows), model_metric (5 rows), universes (1 rows), symbols (1 rows), universe_memberships (2 rows), datasets (2 rows), ohlcv (99 rows). 
Evaluate whether these tables contain essential data like actual users or subscriptions that must be preserved. If they are just dummy/seed data, do NOT migrate them.

---

# Advisor Reports (Supabase Dashboard)
*Paste Security and Performance Advisor reports here.*