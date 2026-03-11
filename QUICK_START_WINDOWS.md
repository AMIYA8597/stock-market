# 🚀 QUICK START — Windows Local Development (5 minutes)

## What You Need Installed

- ✅ **Node.js 20+** (you have v22 ✓)
- ✅ **pnpm** (you have 8.15.6 ✓)
- ❌ **Python 3.12** (install from https://python.org/downloads)
- ❌ **PostgreSQL 16** (install from https://postgresql.org/download/windows)

---

## 3-Step Setup (10 minutes)

### Step 1: Install Missing Tools

**Python 3.12:**
1. Download: https://www.python.org/downloads/
2. Run installer
3. ✅ **Check "Add Python to PATH"**
4. Finish

**PostgreSQL 16:**
1. Download: https://www.postgresql.org/download/windows/
2. Run installer
3. Set password: `postgres123`
4. Port: `5432` (default)
5. Finish

Test in Command Prompt:
```cmd
python --version
psql -U postgres -c "SELECT 1;"
```

---

### Step 2: Run Setup Script

```powershell
cd d:\work\stock-market-project

powershell -ExecutionPolicy Bypass -File scripts/setup-local.ps1
```

**This automatically:**
- ✅ Creates Python virtual environment
- ✅ Installs Python packages
- ✅ Installs Node packages
- ✅ Creates `.env` file
- ⏱️ Takes ~5 minutes

---

### Step 3: Create Database

Open **Command Prompt** (new window):

```cmd
psql -U postgres -c "CREATE DATABASE neuroquant;"

psql -U postgres -d neuroquant -f infrastructure/postgres/init.sql
```

Verify:
```cmd
psql -U postgres -d neuroquant -c "SELECT COUNT(*) FROM users;"
```

Should show: **17 tables created** ✓

---

## Run the Project

**Open 2 PowerShell terminals:**

### Terminal 1: Backend API

```powershell
cd d:\work\stock-market-project
.\venv\Scripts\Activate.ps1
cd backend
uvicorn app.main:app --reload --port 8000
```

Wait for: `Uvicorn running on http://127.0.0.1:8000`

### Terminal 2: Frontend

```powershell
cd d:\work\stock-market-project
pnpm dev
```

Wait for: `Ready in X.Xs`

---

## 🎉 Done! Open in Browser

| What | URL |
|------|-----|
| **Frontend** | http://localhost:3000 |
| **API Docs** | http://localhost:8000/docs |
| **API Health** | http://localhost:8000/health |

---

## 🆘 If Something Breaks

### "Command not found: python"
- Install Python: https://python.org/downloads
- ✅ Check "Add Python to PATH"
- Restart Command Prompt

### "psql: command not found"
- Install PostgreSQL: https://postgresql.org/download/windows
- Restart Command Prompt

### "Port 8000 already in use"
```powershell
netstat -ano | findstr :8000
taskkill /PID [NUMBER] /F
```

### "Cannot connect to database"
```cmd
psql -U postgres -c "SELECT 1;"
```
- If fails: Start PostgreSQL service

---

## 📚 Next: Coding

👉 See **RUN_LOCAL.md** for detailed commands

👉 See **LOCAL_SETUP.md** for full setup guide

👉 See **PHASE2_PLAN.md** for what to code next

