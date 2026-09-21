# PostgreSQL Inventory
Failed to connect/inventory: connection to server at "aws-0-ap-southeast-1.pooler.supabase.com" (52.74.252.201), port 5432 failed: timeout expired
connection to server at "aws-0-ap-southeast-1.pooler.supabase.com" (54.255.219.82), port 5432 failed: timeout expired
connection to server at "aws-0-ap-southeast-1.pooler.supabase.com" (52.77.146.31), port 5432 failed: timeout expired


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
| ohlcv | 0 |
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

## Migration Recommendation
**Recommendation:** The local database contains data in: email_jobs (5 rows), instrument (5 rows), paper_wallets (4 rows), paper_positions (1 rows), paper_orders (1 rows), plans (1 rows), users (5 rows), refresh_sessions (117 rows), backtest_jobs (8 rows), model_artifact (5 rows), payment_transactions (1 rows), subscriptions (3 rows), model_metric (5 rows). 
Evaluate whether these tables contain essential data like actual users or subscriptions that must be preserved. If they are just dummy/seed data, do NOT migrate them.

---

# Advisor Reports (Supabase Dashboard)
*Paste Security and Performance Advisor reports here.*