# 📘 COMPLETE LOCAL SETUP GUIDE — Windows Development Platform

## 🎯 Overview

This project is now **100% local Windows compatible** — no Docker required. Everything runs directly on your machine for faster development and easier debugging.

---

## 📦 What You Need (Total ~30 minutes to install)

### Required Tools

| Tool | Version | Download | Time |
|------|---------|----------|------|
| **Python** | 3.12 | https://python.org/downloads | 5 min |
| **PostgreSQL** | 16 | https://postgresql.org/download/windows | 5 min |
| **Node.js** | 20+ | ✅ You have v22 | — |
| **pnpm** | 8+ | ✅ You have 8.15.6 | — |

### Optional Tools

| Tool | Purpose |
|------|---------|
| **Redis** | Caching (optional, can skip for now) |
| **Git Bash** | Better CLI (you have it) |
| **VSCode** | Code editor (recommended) |

---

## 🚀 Setup Timeline

```
Total Time: ~20 minutes

┌─────────────────────────────────────────┐
│  Install Python (5 min)                 │
│  Install PostgreSQL (5 min)             │
│  Run setup-local.ps1 (5 min)            │
│  Create database (3 min)                │
│  Start services (2 min)                 │
│  ✅ DONE!                               │
└─────────────────────────────────────────┘
```

---

## 🔧 Installation Guide

### Step 1: Python 3.12 (5 minutes)

**Download:** https://www.python.org/downloads/

**Installation steps:**
1. Run the installer
2. ✅ **IMPORTANT: Check "Add Python to PATH"**
3. Choose "Install for all users" or "Install for current user"
4. Finish

**Verify:**
```cmd
python --version
# Output: Python 3.12.x
```

---

### Step 2: PostgreSQL 16 (5 minutes)

**Download:** https://www.postgresql.org/download/windows/

**Installation steps:**
1. Run the installer
2. Username: `postgres` (default)
3. Password: `postgres123` (remember this, or use another password)
4. Port: `5432` (default)
5. Locale: `[Default locale]`
6. Finish

**Verify (Command Prompt):**
```cmd
psql -U postgres -c "SELECT version();"
```

---

### Step 3: Automated Setup Script (5 minutes)

**PowerShell (Administrator NOT required):**

```powershell
cd d:\work\stock-market-project

powershell -ExecutionPolicy Bypass -File scripts/setup-local.ps1
```

**What this script does:**
1. ✅ Checks prerequisites (Python, Node, pnpm, PostgreSQL)
2. ✅ Creates `venv` virtual environment
3. ✅ Installs Python packages (FastAPI, SQLAlchemy, ML libraries)
4. ✅ Installs Node packages (React, TypeScript, Tailwind)
5. ✅ Generates `.env` configuration file
6. ✅ Creates folder structure

**Output:**
```
✅ All prerequisites present!
✅ Virtual environment created
✅ Python dependencies installed
✅ Node dependencies installed
✅ .env file created
```

---

### Step 4: Create Database (2 minutes)

**Command Prompt (new window):**

```cmd
cd d:\work\stock-market-project

# Create database
psql -U postgres -c "CREATE DATABASE neuroquant;"

# Load all tables and schema
psql -U postgres -d neuroquant -f infrastructure/postgres/init.sql
```

**Verify:**
```cmd
psql -U postgres -d neuroquant -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"
```

**Expected output:** `17` (number of tables created)

---

## ▶️ Running the Project

### Option A: Frontend Only (Fastest)

```powershell
cd d:\work\stock-market-project
pnpm dev
```

**Browser:** http://localhost:3000

---

### Option B: Full Stack (Backend + Frontend)

**Open 2 PowerShell windows:**

**Terminal 1 — Backend API:**
```powershell
cd d:\work\stock-market-project

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Start backend server
cd backend
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```powershell
cd d:\work\stock-market-project

# Install dependencies (if first time)
pnpm install

# Start frontend
pnpm dev
```

**Access:**
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- API Health: http://localhost:8000/health

---

## 🗺️ Service Architecture (Local)

```
Your Computer
├── Frontend (Next.js)
│   ├── Port: 3000
│   ├── Path: apps/web/
│   └── Browser: http://localhost:3000
│
├── Backend API (FastAPI)
│   ├── Port: 8000
│   ├── Path: backend/
│   ├── Docs: http://localhost:8000/docs
│   └── Reload: Yes (auto on code change)
│
├── PostgreSQL Database
│   ├── Port: 5432
│   ├── Database: neuroquant
│   ├── User: postgres
│   └── Access: psql command line
│
└── Optional Services
    ├── ML Engine (Port 8001)
    ├── Data Pipeline (Port 8002)
    ├── Risk Engine (Port 8003)
    └── Alert Service (Port 8004)
```

---

## 🎯 Daily Workflow

### Morning: Start Development (2 minutes)

**PowerShell Terminal 1:**
```powershell
cd d:\work\stock-market-project

.\venv\Scripts\Activate.ps1

cd backend

uvicorn app.main:app --reload --port 8000
```

**PowerShell Terminal 2:**
```powershell
cd d:\work\stock-market-project

pnpm dev
```

### Development: Write Code

- Edit frontend files: `apps/web/src/` → auto-reloads
- Edit backend files: `backend/app/` → auto-reloads (with `--reload`)
- Use VSCode or any text editor

### Testing: Run Tests

```powershell
cd d:\work\stock-market-project

.\venv\Scripts\Activate.ps1

# Backend tests
cd backend
pytest

# Frontend tests (in another terminal)
pnpm test
```

### End: Commit & Clean

```powershell
# Terminal 3 (for git commands)
cd d:\work\stock-market-project

git add .
git commit -m "Your message"
git push
```

---

## 📂 Project Structure

```
d:\work\stock-market-project\
├── apps/
│   └── web/                          # Frontend (Next.js, React)
│       ├── src/app/                  # Pages & routing
│       ├── src/components/           # React components
│       ├── src/hooks/                # Custom hooks
│       └── src/lib/                  # Utilities
│
├── backend/                          # Backend API (FastAPI)
│   ├── app/
│   │   ├── api/v1/                   # REST endpoints
│   │   ├── core/                     # Config, database, security
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   ├── schemas/                  # Pydantic request/response
│   │   └── services/                 # Business logic
│   ├── alembic/                      # Database migrations
│   └── tests/                        # Tests
│
├── services/                         # Microservices (optional)
│   ├── ml-engine/                    # ML & predictions
│   ├── data-pipeline/                # Data ingestion
│   ├── risk-engine/                  # Risk calculations
│   ├── backtesting/                  # Backtesting
│   └── alert-service/                # Alerts
│
├── infrastructure/
│   └── postgres/
│       └── init.sql                  # Database schema (17 tables)
│
├── keys/                             # JWT RSA keys (generated)
├── venv/                             # Python virtual environment
├── .env                              # Environment configuration
├── requirements-local.txt            # Python dependencies
└── pnpm-workspace.yaml              # pnpm configuration
```

---

## 🐛 Troubleshooting

### "python: command not found"

**Cause:** Python not installed or not in PATH

**Fix:**
1. Install Python: https://python.org/downloads
2. ✅ Check "Add Python to PATH"
3. Restart Command Prompt
4. Verify: `python --version`

---

### "psql: command not found"

**Cause:** PostgreSQL not installed or not in PATH

**Fix:**
1. Install PostgreSQL: https://postgresql.org/download/windows
2. Restart Command Prompt
3. Verify: `psql -U postgres -c "SELECT 1;"`

---

### "Port 8000 already in use"

**Cause:** Another service is using the port

**Fix:**
```powershell
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID)
taskkill /PID [PID] /F
```

---

### "Cannot connect to database"

**Cause:** PostgreSQL not running or wrong credentials

**Fix:**
```cmd
# Check if PostgreSQL is running
psql -U postgres -c "SELECT 1;"

# If not, start PostgreSQL service:
# Windows Services > PostgreSQL > Start

# Or via Command Prompt:
net start postgresql-x64-16
```

---

### "ModuleNotFoundError: No module named 'fastapi'"

**Cause:** Virtual environment not activated

**Fix:**
```powershell
cd d:\work\stock-market-project

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Should show (venv) prefix in terminal
```

---

### "pnpm: command not found"

**Cause:** pnpm not installed globally

**Fix:**
```cmd
npm install -g pnpm
# Restart Command Prompt
```

---

## 📊 Environment Variables (.env)

The `.env` file is **auto-generated** by `setup-local.ps1`. Key variables:

```env
DATABASE_URL=postgresql://postgres:postgres123@localhost:5432/neuroquant
REDIS_URL=redis://localhost:6379
JWT_ALGORITHM=RS256
NEXTAUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

**Never commit `.env` to git!** It contains sensitive data.

---

## 🔐 Security Notes

### Local Development (Safe)
- JWT keys are in `keys/` directory (ignored in .env)
- Database password is simple (`postgres123` - OK for local)
- Encryption key is generated fresh

### Before Production
- ✅ Change database password
- ✅ Generate strong JWT keys
- ✅ Use strong `NEXTAUTH_SECRET`
- ✅ Enable HTTPS with proper certificates
- ✅ Use proper environment management (Docker, K8s, etc.)

---

## ✅ Verification Checklist

After setup, verify everything:

```powershell
# 1. Python
python --version

# 2. Node & pnpm
node --version
pnpm --version

# 3. PostgreSQL
psql -U postgres -d neuroquant -c "SELECT COUNT(*) FROM users;"

# 4. Backend API (if running)
curl http://localhost:8000/health

# 5. Frontend (open in browser)
http://localhost:3000
```

All working? ✅ You're ready to code!

---

## 🎓 Next Steps

1. **Read**
   - See `RUN_LOCAL.md` for daily commands
   - See `QUICK_START_WINDOWS.md` for quick overview
   - See `PHASE2_PLAN.md` for what to build next

2. **Code**
   - Start with Phase 2: Authentication
   - Implement JWT login, registration, 2FA
   - Write tests for each endpoint

3. **Deploy** (later)
   - Docker is optional for production
   - Can use WSL 2, native Windows, or cloud

---

## 📞 FAQ

**Q: Why remove Docker?**
A: Faster startup, easier debugging, direct file access, simpler for Windows.

**Q: Can I add Docker later?**
A: Yes! Just create a `docker-compose.yml` when needed.

**Q: Do I need Redis?**
A: No, it's optional. File-based cache works for development.

**Q: Can I use SQLite instead of PostgreSQL?**
A: Not recommended. PostgreSQL features (JSONB, TimescaleDB) are used.

**Q: How do I add new Python packages?**
A: 
```powershell
.\venv\Scripts\Activate.ps1
pip install [package]
pip freeze > requirements-local.txt
```

**Q: How do I add new Node packages?**
A: 
```powershell
pnpm add [package]
```

**Q: Where are logs?**
A: Terminal where service runs. Scroll up in terminal.

---

## 🎉 You're All Set!

Everything is ready for local development on Windows.

**Next:** Follow `QUICK_START_WINDOWS.md` and start coding!
