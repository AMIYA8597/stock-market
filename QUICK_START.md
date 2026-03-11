════════════════════════════════════════════════════════════════════════════════
NEUROQUANT QUICK START GUIDE — PHASE 0 & 1 EXECUTION
════════════════════════════════════════════════════════════════════════════════

## ✅ INFRASTRUCTURE READY — ALL FILES CREATED

All files for PHASE 0 & 1 have been created and are available in the repository.
This guide shows the exact steps to execute them.

════════════════════════════════════════════════════════════════════════════════
## PREREQUISITES (5 minutes)

Verify you have ALL of these installed:

```bash
node --version          # Must be 20.x or higher (LTS)
npm install -g pnpm     # If not installed, install pnpm
docker --version        # Docker Desktop must be running on Windows
docker compose version  # Must support version 3.9+
python3 --version       # Must be 3.12.x or higher
git --version          # For version control
```

If any are missing:
- Node.js: Download from https://nodejs.org (20 LTS)
- Docker: Download Docker Desktop from https://docker.com
- Python 3.12: Download from https://python.org/downloads/
- pnpm: `npm install -g pnpm@9`

════════════════════════════════════════════════════════════════════════════════
## STEP 1: VERIFY DOCKER IS RUNNING (1 minute)

Windows:
```bash
# Make sure Docker Desktop is open (you should see the Docker icon in taskbar)
docker ps
# Should return: CONTAINER ID ... (no errors)
```

If Docker is not running:
1. Click Start Menu
2. Type "Docker Desktop"
3. Launch it
4. Wait for "Docker is running" notification
5. Then run: `docker ps` again

════════════════════════════════════════════════════════════════════════════════
## STEP 2: NAVIGATE TO PROJECT DIRECTORY

```bash
cd d:\work\stock-market-project
```

Verify you're in the right place:
```bash
ls -la
# You should see: apps/, backend/, services/, scripts/, infrastructure/, docker-compose.yml, etc.
```

════════════════════════════════════════════════════════════════════════════════
## STEP 3: RUN COMPLETE SETUP (5-10 minutes)

```bash
bash scripts/setup.sh
```

This will:

**[1/8] Check Prerequisites**
```
✓ Node.js 20 LTS found
✓ Python 3.12 found
✓ Docker running
✓ pnpm v9.0.0 found
```

**[2/8] Create Directory Structure**
```
✓ apps/web created
✓ services/ subdirectories created
✓ infrastructure/ configured
✓ keys/ directory ready
```

**[3/8] Generate RSA Keys** (2 sec)
```
Generating RSA-2048 private key...
✓ keys/private.pem created (1704 bytes)
✓ keys/public.pem created (452 bytes)
```

**[4/8] Generate Fernet Key** (1 sec)
```
Generating encryption key...
✓ .env.key created (base64 string)
```

**[5/8] Create .env File** (1 sec)
```
✓ .env configuration created with 47 variables
✓ DATABASE_URL: postgresql+asyncpg://neuroquant:neuroquant@localhost:5432/neuroquant
✓ REDIS_URL: redis://localhost:6379
✓ JWT keys configured
✓ Encryption key configured
```

**[6/8] Install Python Dependencies** (3-5 min)
```
✓ Python virtual environment created: venv/
✓ pip upgraded
✓ services/gateway/requirements.txt installed
✓ services/ml-engine/requirements.txt installed
✓ services/data-pipeline/requirements.txt installed
✓ services/risk-engine/requirements.txt installed
✓ services/alert-service/requirements.txt installed
✓ services/backtesting/requirements.txt installed
```

**[7/8] Install Node Dependencies** (2-3 min)
```
✓ apps/web/node_modules installed
✓ packages/* packages linked
✓ Total: 500+ packages installed
```

**[8/8] Start Docker Services** (30 sec - 2 min)
```
✓ PostgreSQL 16 + TimescaleDB starting...
✓ Redis 7.2 starting...
✓ MinIO starting...
✓ Meilisearch starting...
✓ Prometheus starting...
✓ Grafana starting...
✓ Jaeger starting...
✓ MLflow starting...
✓ Nginx starting...

⏳ Waiting for PostgreSQL to be healthy...
✓ PostgreSQL ready (30 sec)

⏳ Waiting for Redis to be healthy...
✓ Redis ready (5 sec)

🗄️ Running database migrations...
✓ Alembic migration executed
✓ All 17 tables created
✓ Indices created
✓ Constraints enforced
✓ TimescaleDB hypertables configured

✓ Database verification passed

════════════════════════════════════════════════════════════════════════════════
✅ PHASE 0 COMPLETE — Environment fully configured
════════════════════════════════════════════════════════════════════════════════
```

**Expected Total Time: 10-15 minutes**

════════════════════════════════════════════════════════════════════════════════
## STEP 4: VERIFY ALL CONTAINERS ARE HEALTHY (1 minute)

```bash
docker-compose ps
```

**Expected Output:**
```
NAME                              STATUS
postgres                          healthy
redis                             healthy
minio                             healthy
meilisearch                       healthy
prometheus                        healthy
grafana                           healthy
jaeger                            healthy
mlflow                            healthy
nginx                             running
```

If you see "unhealthy" or "exited":
```bash
# Check logs
docker-compose logs postgres
# Or restart:
docker-compose restart postgres
```

════════════════════════════════════════════════════════════════════════════════
## STEP 5: RUN DATABASE TESTS (2 minutes)

```bash
cd backend
python -m pytest tests/test_phase1_database.py -v
```

**Expected Output:**
```
✓ Database connection successful
✓ Table users exists
✓ Table refresh_tokens exists
✓ Table backup_codes exists
✓ Table ohlcv exists
✓ Table tick_data exists
✓ Table model_versions exists
✓ Table predictions exists
✓ Table portfolios exists
✓ Table holdings exists
✓ Table alert_definitions exists
✓ Table alert_events exists
✓ Table portfolio_risk_snapshots exists
✓ Table audit_log exists
✓ Table backtest_runs exists
✓ Table backtest_trades exists
✓ Table watchlists exists
✓ Table watchlist_items exists
✓ Column id exists
✓ Column username exists
... (more columns)
✓ OHLCV is configured as TimescaleDB hypertable
✓ Tick data is configured as TimescaleDB hypertable
✓ Index ix_ohlcv_symbol_time exists
... (more indices and constraints verified)

============================================================
PHASE 1 DATABASE TESTS: 12 passed, 0 failed
============================================================
```

If any tests fail:
```bash
# Check what went wrong
docker-compose logs postgres
# Or reconnect to DB:
psql -U neuroquant -d neuroquant -h localhost
# Query to check tables:
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';
# Should return 17
```

════════════════════════════════════════════════════════════════════════════════
## STEP 6: TEST SERVICE CONNECTIVITY (2 minutes)

### Test PostgreSQL
```bash
psql -U neuroquant -d neuroquant -h localhost -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';"
# Expected: 17 (number of tables)
```

### Test Redis
```bash
redis-cli PING
# Expected: PONG
```

### Test MinIO (S3-compatible storage)
```bash
curl http://localhost:9001/
# Expected: MinIO console HTML (or open browser: http://localhost:9001)
```

### Test Meilisearch
```bash
curl http://localhost:7700/health
# Expected: {"status":"available"}
```

### Test Grafana (Monitoring)
```bash
curl http://localhost:3001/
# Expected: Grafana login page HTML
# Or open browser: http://localhost:3001 (login: admin/admin)
```

### Test Jaeger (Distributed Tracing)
```bash
curl http://localhost:16686/
# Expected: Jaeger UI HTML
# Or open browser: http://localhost:16686
```

### Test Prometheus (Metrics)
```bash
curl http://localhost:9090/
# Expected: Prometheus UI HTML
# Or open browser: http://localhost:9090
```

### Test MLflow (ML Tracking)
```bash
curl http://localhost:5000/
# Expected: MLflow UI HTML
# Or open browser: http://localhost:5000
```

════════════════════════════════════════════════════════════════════════════════
## FILES CREATED IN THIS EXECUTION
════════════════════════════════════════════════════════════════════════════════

Infrastructure:
✓ keys/private.pem (JWT private key)
✓ keys/public.pem (JWT public key)
✓ .env (47 configuration variables)
✓ .env.key (Fernet encryption key)
✓ venv/ (Python virtual environment)

Database:
✓ All 17 tables in PostgreSQL
✓ All 7 indices
✓ All constraints enforced
✓ TimescaleDB hypertables configured

Docker Services:
✓ postgres:5432 (PostgreSQL + TimescaleDB)
✓ redis:6379 (Redis cache)
✓ minio:9000-9001 (S3-compatible storage)
✓ meilisearch:7700 (Full-text search)
✓ prometheus:9090 (Metrics collection)
✓ grafana:3001 (Monitoring dashboards)
✓ jaeger:16686 (Distributed tracing)
✓ mlflow:5000 (ML experiment tracking)
✓ nginx:80-443 (Reverse proxy)

════════════════════════════════════════════════════════════════════════════════
## TROUBLESHOOTING
════════════════════════════════════════════════════════════════════════════════

### Docker startup timeout
```bash
# Wait longer for services to start
# Or manually check Docker:
docker ps -a
docker logs postgres

# If stuck, restart Docker Desktop:
# - Click tray menu → Restart Docker Engine
# - Wait 1 minute
# - Run setup again
```

### Port already in use
```bash
# Find what's using port 5432:
netstat -ano | findstr :5432
# Kill the process:
taskkill /PID [PID] /F

# Or change docker-compose.yml port mapping:
# Change "5432:5432" to "5433:5432" for external port
```

### Python dependency conflicts
```bash
# Delete venv and recreate:
rm -rf venv
python -m venv venv
source venv/Scripts/activate  # On Windows: venv\Scripts\activate.bat
pip install -r backend/requirements.txt
```

### Database migration failed
```bash
# Check migration status:
cd backend
alembic current

# Downgrade:
alembic downgrade base

# Then upgrade again:
alembic upgrade head

# Check logs:
docker-compose logs postgres
```

### Can't connect to PostgreSQL
```bash
# Verify container running:
docker-compose ps postgres
# Should say: healthy

# Check password in .env:
grep DATABASE_URL .env

# Try connecting with psql:
psql -U neuroquant -d neuroquant -h localhost -W
# Password: neuroquant

# If still fails, check Docker network:
docker network inspect stock-market-project_neuroquant
```

════════════════════════════════════════════════════════════════════════════════
## WHAT'S NEXT: PHASE 2
════════════════════════════════════════════════════════════════════════════════

Once PHASE 1 is complete and all tests pass:

1. Read PHASE2_PLAN.md for complete specification
2. Create 6 Python files for authentication service
3. Implement user registration, login, JWT, TOTP 2FA
4. Write 300+ lines of tests
5. All tests must pass (90%+ coverage)

Estimated time: 3-4 hours for experienced developer

════════════════════════════════════════════════════════════════════════════════
## DOCUMENTATION REFERENCE
════════════════════════════════════════════════════════════════════════════════

Read in this order:
1. This file (QUICK_START.md) - Overview & execution
2. PHASE1_COMPLETION.md - What was created in Phase 1
3. DEVELOPMENT_ROADMAP.md - Complete specification for phases 1-10
4. PHASE2_PLAN.md - Detailed Phase 2 file structure

════════════════════════════════════════════════════════════════════════════════
Good luck! 🚀
════════════════════════════════════════════════════════════════════════════════
