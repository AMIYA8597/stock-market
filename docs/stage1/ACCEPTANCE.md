# Stage 1 Acceptance Criteria

1. **Database Baseline**: `alembic upgrade head` applies cleanly. (PASS)
2. **Identity & RLS**: RLS policies applied via `rls.sql` injection. Proper role usage. (PASS)
3. **Data Quality**: Real ingestion of 5 instruments and 1 year history. No fake data. (PASS)
4. **Validation Check**: `check_stage1_ready.py` strictly verifies required tables, RLS rules, Alembic HEAD, and OHLCV records. All checks return `[PASS]`. (PASS)
