# 🗄️ LOCAL PostgreSQL SETUP — Windows Quick Guide

## ⚡ 30-Second Summary

```cmd
# 1. Install PostgreSQL 16 from https://postgresql.org/download/windows
#    Remember password: postgres123

# 2. Create database
psql -U postgres -c "CREATE DATABASE neuroquant;"

# 3. Load schema
psql -U postgres -d neuroquant -f infrastructure/postgres/init.sql

# 4. Verify
psql -U postgres -d neuroquant -c "SELECT COUNT(*) FROM users;"

# Done! Your database is ready.
```

---

## 📋 Complete Installation Steps

### Step 1: Download & Install PostgreSQL

**Download:** https://www.postgresql.org/download/windows/
- Choose PostgreSQL 16.x or later
- Click "Download the installer"

**Installation:**
1. Run the `.exe` file
2. Choose installation directory (default OK)
3. Choose components (keep defaults)
4. Data Directory: `C:\Program Files\PostgreSQL\16\data` (default OK)
5. **Password for "postgres" user: `postgres123`** (IMPORTANT!)
6. Port: `5432` (default)
7. Locale: `[Default]`
8. Click "Next" through remaining screens

**Total time:** 5 minutes

---

### Step 2: Verify Installation

**Command Prompt:**
```cmd
psql --version
```

**Output:**
```
psql (PostgreSQL) 16.x
```

If not found:
- Add PostgreSQL to PATH: `C:\Program Files\PostgreSQL\16\bin`
- Restart Command Prompt

---

### Step 3: Create NeuroQuant Database

**Command Prompt:**
```cmd
psql -U postgres -c "CREATE DATABASE neuroquant;"
```

**Output:**
```
CREATE DATABASE
```

---

### Step 4: Load Database Schema

**Command Prompt (make sure you're in project directory):**
```cmd
cd d:\work\stock-market-project

psql -U postgres -d neuroquant -f infrastructure/postgres/init.sql
```

**Output:**
```
CREATE EXTENSION
CREATE TABLE
CREATE TABLE
... (more CREATE TABLE statements)
CREATE INDEX
... (more CREATE INDEX statements)
```

This creates:
- ✅ 3 PostgreSQL extensions (uuid-ossp, pgcrypto, timescaledb)
- ✅ 17 tables
- ✅ 7 indices
- ✅ Foreign keys and constraints
- ✅ TimescaleDB hypertables

---

### Step 5: Verify Database Created

**Command Prompt:**
```cmd
psql -U postgres -d neuroquant -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"
```

**Expected output:**
```
 count
-------
    17
(1 row)
```

---

## 🎯 Database Contents (17 Tables)

### Section 1: Authentication (3 tables)
- `users` — User accounts
- `refresh_tokens` — JWT refresh tokens
- `backup_codes` — 2FA backup codes

### Section 2: Market Data (2 hypertables)
- `ohlcv` — OHLCV candle data
- `tick_data` — Tick-level market data

### Section 3: ML Models (2 tables)
- `model_versions` — Trained model versions
- `predictions` — ML predictions

### Section 4: Portfolio (2 tables)
- `portfolios` — User portfolios
- `holdings` — Portfolio holdings

### Section 5: Risk (1 hypertable)
- `portfolio_risk_snapshots` — Risk metrics over time

### Section 6: Alerts (2 tables)
- `alert_definitions` — Alert rules
- `alert_events` — Alert trigger events

### Section 7: Audit (1 hypertable)
- `audit_log` — Immutable audit log

### Section 8: Backtesting (2 tables)
- `backtest_runs` — Backtest executions
- `backtest_trades` — Trades from backtests

### Section 9: Other (2 tables)
- `watchlists` — User watchlists
- `watchlist_symbols` — Symbols in watchlists

---

## 📊 Database Connection Details

**Connection Info:**
```
Host: localhost
Port: 5432
Database: neuroquant
User: postgres
Password: postgres123 (or your chosen password)
```

**In Application (.env):**
```env
DATABASE_URL=postgresql://postgres:postgres123@localhost:5432/neuroquant
```

**Command Line Access:**
```cmd
# Direct access
psql -U postgres -d neuroquant

# Or with password
psql -U postgres -d neuroquant -W
# Then enter password

# Run a query
psql -U postgres -d neuroquant -c "SELECT * FROM users LIMIT 5;"
```

---

## 🛠️ Common Database Tasks

### View All Tables
```cmd
psql -U postgres -d neuroquant -c "\dt"
```

### View Table Structure
```cmd
psql -U postgres -d neuroquant -c "\d users"
```

### View All Indices
```cmd
psql -U postgres -d neuroquant -c "\di"
```

### Count Rows in Table
```cmd
psql -U postgres -d neuroquant -c "SELECT COUNT(*) FROM users;"
```

### Insert Test Data
```cmd
psql -U postgres -d neuroquant -c "INSERT INTO users (email, password_hash, username) VALUES ('test@example.com', 'hashedpw', 'testuser');"
```

### View Recent Data
```cmd
psql -U postgres -d neuroquant -c "SELECT * FROM users LIMIT 10;"
```

---

## 🔄 Reset Database (Start Fresh)

**WARNING:** This deletes all data!

```cmd
# Drop the database
psql -U postgres -c "DROP DATABASE IF EXISTS neuroquant;"

# Recreate it
psql -U postgres -c "CREATE DATABASE neuroquant;"

# Reload schema
psql -U postgres -d neuroquant -f infrastructure/postgres/init.sql
```

---

## 📈 Database GUI Tools (Optional)

### pgAdmin (Free)
```cmd
# Comes with PostgreSQL installer
# Access: http://localhost:5050
```

### DBeaver (Free)
```
Download: https://dbeaver.io/download/
```

### DataGrip (Paid - JetBrains)
```
Download: https://www.jetbrains.com/datagrip/
```

---

## 🚨 Troubleshooting

### "psql: could not translate host name"

**Cause:** PostgreSQL service not running

**Fix:**
```cmd
# Start PostgreSQL service
net start postgresql-x64-16

# Or open Windows Services and start PostgreSQL
```

### "password authentication failed"

**Cause:** Wrong password

**Fix:**
```cmd
# Use correct password (default: postgres123)
psql -U postgres -d neuroquant -W
# Enter password when prompted
```

### "database neuroquant does not exist"

**Cause:** Database not created

**Fix:**
```cmd
psql -U postgres -c "CREATE DATABASE neuroquant;"
```

### "relation 'users' does not exist"

**Cause:** Schema not loaded

**Fix:**
```cmd
psql -U postgres -d neuroquant -f infrastructure/postgres/init.sql
```

### "Cannot connect: port 5432"

**Cause:** PostgreSQL not running on port 5432

**Fix:**
```cmd
# Check if running
netstat -ano | findstr :5432

# Check PostgreSQL status
net status postgresql-x64-16

# Restart if needed
net stop postgresql-x64-16
net start postgresql-x64-16
```

### "Connection refused"

**Cause:** PostgreSQL service stopped

**Fix:**
```cmd
# Start the service
net start postgresql-x64-16

# Verify
psql -U postgres -c "SELECT 1;"
```

---

## ✅ Verification Script

**Save as `test-db.cmd`:**
```cmd
@echo off
echo Testing PostgreSQL connection...
psql -U postgres -c "SELECT 1;" && echo ✓ Connection OK || echo ✗ Connection Failed

echo.
echo Testing neuroquant database...
psql -U postgres -d neuroquant -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" && echo ✓ Database OK || echo ✗ Database Failed

echo.
echo Testing table count...
psql -U postgres -d neuroquant -c "SELECT COUNT(*) FROM users;"

echo.
echo All tests passed!
```

**Run:**
```cmd
test-db.cmd
```

---

## 🔐 Security Notes

### Local Development (Safe)
- Default password `postgres123` is fine
- No encryption needed
- File-based backups OK

### Before Production
- ✅ Change password from `postgres123`
- ✅ Enable SSL connections
- ✅ Set up automated backups
- ✅ Use strong passwords
- ✅ Restrict network access

---

## 📚 PostgreSQL Documentation

Official docs: https://www.postgresql.org/docs/16/

Key topics:
- [SQL Commands](https://www.postgresql.org/docs/16/sql-commands.html)
- [Data Types](https://www.postgresql.org/docs/16/datatype.html)
- [Functions](https://www.postgresql.org/docs/16/functions.html)

---

## 🎯 Next Steps

1. ✅ Install PostgreSQL
2. ✅ Create database
3. ✅ Load schema
4. ✅ Verify tables exist
5. **→ Run backend:** `uvicorn app.main:app --reload`
6. **→ Run frontend:** `pnpm dev`

See `RUN_LOCAL.md` for running services.

