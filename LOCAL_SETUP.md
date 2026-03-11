════════════════════════════════════════════════════════════════════════════════
LOCAL WINDOWS SETUP — No Docker Required
════════════════════════════════════════════════════════════════════════════════

Complete local development setup for Windows. Everything runs on your machine.

════════════════════════════════════════════════════════════════════════════════
## STEP 1: INSTALL PREREQUISITES (20 minutes)
════════════════════════════════════════════════════════════════════════════════

### 1. PostgreSQL 16 (Database)
Download: https://www.postgresql.org/download/windows/
- Choose version 16.x or higher
- During installation:
  * Username: postgres
  * Password: postgres123 (remember this!)
  * Port: 5432 (default)
  * Choose "Stack Builder" to install pgAdmin (optional)
- Verify: Open Command Prompt:
  ```cmd
  psql -U postgres -c "SELECT version();"
  ```

### 2. Python 3.12
Download: https://www.python.org/downloads/
- Choose Python 3.12.x
- During installation:
  * ✅ Check "Add Python to PATH"
  * Choose "Install for current user"
- Verify:
  ```cmd
  python --version
  pip --version
  ```

### 3. Node.js 20 LTS
Download: https://nodejs.org/
- Choose LTS version (20.x)
- Default installation is fine
- Verify:
  ```cmd
  node --version
  npm --version
  ```

### 4. pnpm (Node package manager)
Run in Command Prompt:
```cmd
npm install -g pnpm
```
Verify:
```cmd
pnpm --version
```

### 5. Redis (Optional - for caching)
Download: https://github.com/microsoftarchive/redis/releases
- Or use Windows Subsystem for Linux (WSL) version
- Or skip for now (we'll use file-based cache in dev)

════════════════════════════════════════════════════════════════════════════════
## STEP 2: CREATE .env FILE (5 minutes)
════════════════════════════════════════════════════════════════════════════════

Create file: `d:\work\stock-market-project\.env`

```env
# DATABASE (PostgreSQL local)
DATABASE_URL=postgresql://postgres:postgres123@localhost:5432/neuroquant
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
POSTGRES_DB=neuroquant

# OPTIONAL: Redis (if installed)
REDIS_URL=redis://localhost:6379
REDIS_CACHE_DB=0
REDIS_CELERY_BROKER_DB=1
REDIS_CELERY_RESULT_DB=2

# JWT KEYS (will be generated)
JWT_PRIVATE_KEY_PATH=./keys/private.pem
JWT_PUBLIC_KEY_PATH=./keys/public.pem
JWT_ALGORITHM=RS256
JWT_EXPIRY_SECONDS=3600
REFRESH_TOKEN_EXPIRY_SECONDS=604800

# ENCRYPTION KEY (will be generated)
FIELD_ENCRYPTION_KEY=your-fernet-key-here

# FRONTEND
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXTAUTH_SECRET=your-secret-here
NEXTAUTH_URL=http://localhost:3000

# SERVICE PORTS
GATEWAY_PORT=8000
ML_ENGINE_PORT=8001
DATA_PIPELINE_PORT=8002
RISK_ENGINE_PORT=8003
ALERT_SERVICE_PORT=8004
BACKTESTING_PORT=8005
FRONTEND_PORT=3000

# FEATURE FLAGS
ENABLE_2FA=true
ENABLE_PAPER_TRADING=true
ENABLE_BACKTESTING=true
ENABLE_ML_PREDICTIONS=true

# LOGGING
LOG_LEVEL=INFO
```

════════════════════════════════════════════════════════════════════════════════
## STEP 3: SETUP DATABASE (5 minutes)
════════════════════════════════════════════════════════════════════════════════

### 3.1 Create Database
```cmd
psql -U postgres -c "CREATE DATABASE neuroquant;"
```

### 3.2 Run Database Schema
```cmd
psql -U postgres -d neuroquant -f infrastructure/postgres/init.sql
```

This creates all 17 tables with proper schema.

### 3.3 Verify
```cmd
psql -U postgres -d neuroquant -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"
```
Expected: Should return 17 (number of tables)

════════════════════════════════════════════════════════════════════════════════
## STEP 4: GENERATE KEYS (2 minutes)
════════════════════════════════════════════════════════════════════════════════

### 4.1 Create keys directory
```cmd
mkdir keys
cd keys
```

### 4.2 Generate RSA keys (for JWT)
```cmd
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem
```

Or on Windows without openssl, use Git Bash or WSL.

### 4.3 Generate Fernet key
Open Python and run:
```python
from cryptography.fernet import Fernet
key = Fernet.generate_key().decode()
print(key)
```
Copy the output and add to .env file as FIELD_ENCRYPTION_KEY

════════════════════════════════════════════════════════════════════════════════
## STEP 5: INSTALL PYTHON DEPENDENCIES (5 minutes)
════════════════════════════════════════════════════════════════════════════════

### 5.1 Create virtual environment
```cmd
cd d:\work\stock-market-project
python -m venv venv
# Activate it
venv\Scripts\activate
```

### 5.2 Install backend dependencies
```cmd
pip install --upgrade pip
pip install -r requirements-local.txt
```

(We'll create requirements-local.txt next)

════════════════════════════════════════════════════════════════════════════════
## STEP 6: INSTALL NODE DEPENDENCIES (5 minutes)
════════════════════════════════════════════════════════════════════════════════

```cmd
cd d:\work\stock-market-project
pnpm install
```

════════════════════════════════════════════════════════════════════════════════
## STEP 7: RUN THE PROJECT
════════════════════════════════════════════════════════════════════════════════

### Option A: Run Frontend Only (Quick Start)
```cmd
# Terminal 1
cd d:\work\stock-market-project
pnpm dev

# Opens http://localhost:3000 (frontend only, no API)
```

### Option B: Run Full Stack (Backend + Frontend)

**Terminal 1: Backend API Server**
```cmd
cd d:\work\stock-market-project
# Activate Python virtual environment
venv\Scripts\activate

# Start FastAPI server on port 8000
cd backend
uvicorn app.main:app --reload --port 8000
```

**Terminal 2: Frontend**
```cmd
cd d:\work\stock-market-project
pnpm dev

# Frontend runs on http://localhost:3000
```

**Terminal 3: ML Service (Optional)**
```cmd
cd d:\work\stock-market-project
venv\Scripts\activate

cd services/ml-engine
uvicorn app.main:app --reload --port 8001
```

════════════════════════════════════════════════════════════════════════════════
## ✅ VERIFY EVERYTHING WORKS
════════════════════════════════════════════════════════════════════════════════

```cmd
# Test PostgreSQL
psql -U postgres -d neuroquant -c "SELECT COUNT(*) FROM users;"

# Test Frontend
Open browser: http://localhost:3000

# Test Backend API
Open browser: http://localhost:8000/docs  (Swagger UI)

# Test API connection
curl http://localhost:8000/health
```

════════════════════════════════════════════════════════════════════════════════
## 📊 SERVICE PORTS
════════════════════════════════════════════════════════════════════════════════

| Service | Port | How to Access |
|---------|------|---------------|
| Frontend | 3000 | http://localhost:3000 |
| Backend API | 8000 | http://localhost:8000 |
| API Docs | 8000 | http://localhost:8000/docs |
| ML Engine | 8001 | http://localhost:8001 |
| PostgreSQL | 5432 | psql -U postgres -d neuroquant |
| Redis | 6379 | redis-cli (if installed) |

════════════════════════════════════════════════════════════════════════════════
## 🛠️ TROUBLESHOOTING
════════════════════════════════════════════════════════════════════════════════

### PostgreSQL won't start
```cmd
# Check if running
tasklist | findstr postgres

# Start PostgreSQL service (Windows)
net start postgresql-x64-16
```

### Port already in use
```cmd
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill the process
taskkill /PID [PID] /F
```

### Python not found
- Make sure Python is added to PATH
- Restart Command Prompt after installing Python
- Verify: `python --version`

### pnpm not found
```cmd
npm install -g pnpm
# Restart Command Prompt
```

### Database connection failed
```cmd
# Check PostgreSQL is running
psql -U postgres -c "SELECT 1;"

# Check .env DATABASE_URL is correct
# Default: postgresql://postgres:postgres123@localhost:5432/neuroquant
```

════════════════════════════════════════════════════════════════════════════════
## 📁 PROJECT STRUCTURE (Local)
════════════════════════════════════════════════════════════════════════════════

```
d:\work\stock-market-project\
├── apps/web/                    # Frontend (Next.js)
├── backend/                     # Gateway API
├── services/
│   ├── ml-engine/               # ML service
│   ├── data-pipeline/           # Data ingestion
│   ├── risk-engine/             # Risk calculations
│   ├── backtesting/             # Backtesting engine
│   └── alert-service/           # Alert service
├── keys/                        # JWT keys (generated)
├── venv/                        # Python virtual environment
├── .env                         # Configuration (local)
├── requirements-local.txt       # Python dependencies
└── pnpm-workspace.yaml         # pnpm configuration
```

════════════════════════════════════════════════════════════════════════════════
## 🚀 NEXT: START CODING
════════════════════════════════════════════════════════════════════════════════

Once everything is running:

1. **Frontend:** Runs on http://localhost:3000
2. **Backend API:** Runs on http://localhost:8000 with Swagger docs

Start PHASE 2: Authentication service!

See PHASE2_PLAN.md for implementation guide.

════════════════════════════════════════════════════════════════════════════════
