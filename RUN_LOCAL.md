# ════════════════════════════════════════════════════════════════════════════════
# RUN_LOCAL.md — Quick Reference for Running Services Locally
# ════════════════════════════════════════════════════════════════════════════════

## 🚀 Quick Start (Frontend Only - Fastest)

```powershell
cd d:\work\stock-market-project
pnpm dev
```

Open: http://localhost:3000

---

## 🔧 Full Stack (Backend + Frontend)

### Terminal 1: Start Backend API

```powershell
cd d:\work\stock-market-project

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Navigate to backend
cd backend

# Start server
uvicorn app.main:app --reload --port 8000
```

Backend runs on: http://localhost:8000

API Docs: http://localhost:8000/docs (Swagger)

### Terminal 2: Start Frontend

```powershell
cd d:\work\stock-market-project

# Make sure venv is activated
.\venv\Scripts\Activate.ps1

# Start development server
pnpm dev
```

Frontend runs on: http://localhost:3000

---

## 🧠 Individual Microservices (Optional)

### Terminal 3: ML Engine

```powershell
cd d:\work\stock-market-project

.\venv\Scripts\Activate.ps1

cd services/ml-engine

uvicorn app.main:app --reload --port 8001
```

### Terminal 4: Data Pipeline

```powershell
cd d:\work\stock-market-project

.\venv\Scripts\Activate.ps1

cd services/data-pipeline

uvicorn app.main:app --reload --port 8002
```

### Terminal 5: Risk Engine

```powershell
cd d:\work\stock-market-project

.\venv\Scripts\Activate.ps1

cd services/risk-engine

uvicorn app.main:app --reload --port 8003
```

---

## 📊 Service Ports Reference

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| Frontend | 3000 | http://localhost:3000 | React Application |
| Backend API | 8000 | http://localhost:8000 | Main Gateway |
| API Docs | 8000 | http://localhost:8000/docs | Swagger Documentation |
| ML Engine | 8001 | http://localhost:8001 | ML Model Service |
| Data Pipeline | 8002 | http://localhost:8002 | Data Ingestion |
| Risk Engine | 8003 | http://localhost:8003 | Risk Calculations |
| Alert Service | 8004 | http://localhost:8004 | Alert Service |
| Backtesting | 8005 | http://localhost:8005 | Backtesting Engine |

---

## ✅ Verify Everything Works

### Test Database
```powershell
psql -U postgres -d neuroquant -c "SELECT COUNT(*) FROM users;"
```

### Test Backend API
```powershell
curl http://localhost:8000/health
# or open in browser: http://localhost:8000/docs
```

### Test Frontend
Open: http://localhost:3000

---

## 🛠️ Common Commands

### Restart Virtual Environment
```powershell
cd d:\work\stock-market-project
.\venv\Scripts\Activate.ps1
```

### Run Tests
```powershell
cd d:\work\stock-market-project
.\venv\Scripts\Activate.ps1

# Backend tests
cd backend
pytest

# ML Engine tests
cd ../services/ml-engine
pytest
```

### Reset Database
```powershell
# Drop all tables
psql -U postgres -d neuroquant -f infrastructure/postgres/drop_all.sql

# Reload schema
psql -U postgres -d neuroquant -f infrastructure/postgres/init.sql
```

### Stop All Services
1. Each terminal: Press `Ctrl + C`
2. Or kill processes:
```powershell
# Kill by port
netstat -ano | findstr :8000
taskkill /PID [PID] /F
```

---

## 🔄 Development Workflow

### Make Code Changes
- **Frontend:** Edit files in `apps/web/src/` and it auto-reloads
- **Backend:** Edit files in `backend/app/` and it auto-reloads (with `--reload` flag)

### Add Python Packages
```powershell
.\venv\Scripts\Activate.ps1
pip install [package-name]
pip freeze > requirements-local.txt
```

### Add Node Packages
```powershell
pnpm add [package-name]
```

---

## 📝 Typical Development Session

**Time: 10 minutes to fully running**

1. **Setup (one-time):**
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/setup-local.ps1
   
   # Then create database manually:
   psql -U postgres -c "CREATE DATABASE neuroquant;"
   psql -U postgres -d neuroquant -f infrastructure/postgres/init.sql
   ```

2. **Daily Start (3 terminals):**
   ```powershell
   # Terminal 1: Backend
   cd d:\work\stock-market-project
   .\venv\Scripts\Activate.ps1
   cd backend
   uvicorn app.main:app --reload --port 8000
   
   # Terminal 2: Frontend
   cd d:\work\stock-market-project
   pnpm dev
   
   # Terminal 3: For git commits, running tests, etc.
   cd d:\work\stock-market-project
   # Use for git commands, running specific tests, etc.
   ```

3. **Access:**
   - Frontend: http://localhost:3000
   - API Docs: http://localhost:8000/docs
   - Work in code editor - changes auto-reload

---

## 🐛 Troubleshooting

### Virtual Environment Not Activating
```powershell
# If Activate.ps1 fails, manually set Python path:
$env:Path = "d:\work\stock-market-project\venv\Scripts:$env:Path"
```

### Port Already in Use
```powershell
# Find what's using the port
netstat -ano | findstr :[PORT]

# Kill it (replace [PID] with actual number)
taskkill /PID [PID] /F
```

### PostgreSQL Connection Failed
```powershell
# Check if PostgreSQL is running
psql -U postgres -c "SELECT 1;"

# If not running, start it:
# (Services > PostgreSQL or net start postgresql-x64-16)
```

### Python Imports Not Found
```powershell
# Deactivate and reactivate venv
deactivate
.\venv\Scripts\Activate.ps1

# Verify modules installed
pip list
```

---

## 📚 Next Steps

1. **Frontend Development:** Start with `pnpm dev`
2. **Backend Development:** Implement Phase 2 Auth
3. **Testing:** Run `pytest` for each service
4. **Database:** Modify schema in `infrastructure/postgres/init.sql`

See LOCAL_SETUP.md for detailed setup instructions.

