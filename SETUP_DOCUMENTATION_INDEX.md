# 📚 SETUP DOCUMENTATION INDEX — Local Windows Development

## 🎯 START HERE

### **For Your First Time Setup** → Read This First
📖 **[QUICK_START_WINDOWS.md](QUICK_START_WINDOWS.md)**
- 5-minute quick start guide
- 3 simple steps
- Perfect for getting running fast
- **Read time: 5 minutes**

---

## 📑 All Documentation Files

### Quick Reference (Daily Use)
| File | Purpose | Read Time |
|------|---------|-----------|
| [QUICK_START_WINDOWS.md](QUICK_START_WINDOWS.md) | Ultra-fast 5-minute setup | 5 min |
| [RUN_LOCAL.md](RUN_LOCAL.md) | How to run services daily | 10 min |
| [DOCKER_TO_LOCAL_MIGRATION.md](DOCKER_TO_LOCAL_MIGRATION.md) | What changed from Docker | 10 min |

### Detailed Guides (Complete Reference)
| File | Purpose | Read Time |
|------|---------|-----------|
| [LOCAL_SETUP.md](LOCAL_SETUP.md) | Complete step-by-step setup | 20 min |
| [WINDOWS_LOCAL_SETUP_GUIDE.md](WINDOWS_LOCAL_SETUP_GUIDE.md) | Comprehensive guide with FAQ | 30 min |
| [POSTGRES_LOCAL_SETUP.md](POSTGRES_LOCAL_SETUP.md) | Database setup and operations | 15 min |

### Automation
| File | Purpose | How to Run |
|------|---------|-----------|
| [scripts/setup-local.ps1](scripts/setup-local.ps1) | PowerShell setup automation | `powershell -ExecutionPolicy Bypass -File scripts/setup-local.ps1` |
| [requirements-local.txt](requirements-local.txt) | Python dependencies | `pip install -r requirements-local.txt` |

---

## 🚀 Reading Guide by Role

###👨‍💻 **For Developers (Start Here)**
1. [QUICK_START_WINDOWS.md](QUICK_START_WINDOWS.md) ← **Start here!** (5 min)
2. [RUN_LOCAL.md](RUN_LOCAL.md) — Daily commands (10 min)
3. [PHASE2_PLAN.md](PHASE2_PLAN.md) — What to code next

### 🛠️ **For DevOps/System Admins**
1. [DOCKER_TO_LOCAL_MIGRATION.md](DOCKER_TO_LOCAL_MIGRATION.md) — Architecture change (10 min)
2. [LOCAL_SETUP.md](LOCAL_SETUP.md) — Complete setup (20 min)
3. [POSTGRES_LOCAL_SETUP.md](POSTGRES_LOCAL_SETUP.md) — Database ops (15 min)

### 📚 **For Project Managers**
1. [DOCKER_TO_LOCAL_MIGRATION.md](DOCKER_TO_LOCAL_MIGRATION.md) — Summary of changes (10 min)
2. [WINDOWS_LOCAL_SETUP_GUIDE.md](WINDOWS_LOCAL_SETUP_GUIDE.md) — Full context (30 min)
3. [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md) — Timeline & phases

### 🤔 **For Troubleshooting**
1. [QUICK_START_WINDOWS.md](QUICK_START_WINDOWS.md) — Quick fixes (section: If Something Breaks)
2. [RUN_LOCAL.md](RUN_LOCAL.md) — Running services issues
3. [WINDOWS_LOCAL_SETUP_GUIDE.md](WINDOWS_LOCAL_SETUP_GUIDE.md) — Comprehensive troubleshooting (section: Troubleshooting)
4. [POSTGRES_LOCAL_SETUP.md](POSTGRES_LOCAL_SETUP.md) — Database issues

---

## 🎯 Setup Timeline

```
Total Setup: ~20 minutes

├─ [5 min] Install Python 3.12
├─ [5 min] Install PostgreSQL 16
├─ [5 min] Run scripts/setup-local.ps1
├─ [2 min] Create database
├─ [2 min] Start services
└─ [1 min] Open http://localhost:3000 ✅
```

---

## 📋 Quick Checklist

### ✅ Before You Start
- [ ] Windows 10/11 (you have it)
- [ ] 4GB RAM minimum (you probably have it)
- [ ] 5GB free disk space
- [ ] Administrator access

### ✅ During Setup
- [ ] Install Python 3.12 from [python.org](https://python.org)
- [ ] Check "Add Python to PATH" during installation
- [ ] Install PostgreSQL 16 from [postgresql.org](https://postgresql.org)
- [ ] Remember PostgreSQL password: `postgres123`
- [ ] Run `scripts/setup-local.ps1`
- [ ] Create database with `psql` command
- [ ] Verify with test queries

### ✅ After Setup
- [ ] Start backend: `uvicorn app.main:app --reload`
- [ ] Start frontend: `pnpm dev`
- [ ] Open http://localhost:3000
- [ ] Check API docs: http://localhost:8000/docs

---

## 🔗 Quick Links

### Installation Downloads
- **Python 3.12:** https://python.org/downloads
- **PostgreSQL 16:** https://postgresql.org/download/windows
- **Node.js 20:** https://nodejs.org (already have v22 ✓)

### Local Access (After Running)
- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs
- **API Health:** http://localhost:8000/health
- **Database CLI:** `psql -U postgres -d neuroquant`

### Development Tools (Optional)
- **pgAdmin:** Web-based PostgreSQL admin tool
- **DBeaver:** Database GUI client
- **Postman:** API testing tool
- **VSCode:** Code editor

---

## 📖 Document Structure

### [QUICK_START_WINDOWS.md](QUICK_START_WINDOWS.md)
**What:** Ultra-fast setup for experienced developers
**Length:** 100 lines
**Time:** 5 minutes
**Contents:**
- What you need (prerequisites)
- 3-step setup
- Running (2 terminals)
- Quick troubleshooting

### [RUN_LOCAL.md](RUN_LOCAL.md)
**What:** Daily reference for running services
**Length:** 250 lines
**Time:** 10 minutes
**Contents:**
- How to start each service
- Port mapping
- Common commands
- Troubleshooting

### [LOCAL_SETUP.md](LOCAL_SETUP.md)
**What:** Complete step-by-step setup guide
**Length:** 1,000+ lines
**Time:** 20 minutes
**Contents:**
- Detailed installation steps
- Environment configuration
- Database setup
- Running services
- Troubleshooting

### [WINDOWS_LOCAL_SETUP_GUIDE.md](WINDOWS_LOCAL_SETUP_GUIDE.md)
**What:** Comprehensive guide with everything
**Length:** 1,500+ lines
**Time:** 30 minutes
**Contents:**
- Complete installation walkthrough
- Daily workflow
- Project structure
- Troubleshooting FAQ
- Verification checklist

### [POSTGRES_LOCAL_SETUP.md](POSTGRES_LOCAL_SETUP.md)
**What:** Database-specific setup and operations
**Length:** 700 lines
**Time:** 15 minutes
**Contents:**
- PostgreSQL installation
- Database creation
- Schema loading
- Common database tasks
- Troubleshooting

### [DOCKER_TO_LOCAL_MIGRATION.md](DOCKER_TO_LOCAL_MIGRATION.md)
**What:** Summary of changes from Docker-based setup
**Length:** 800 lines
**Time:** 10 minutes
**Contents:**
- What changed and why
- Files created for local setup
- Architecture comparison
- Migration checklist

---

## 🎓 Knowledge Path

### Absolute Beginner
1. [QUICK_START_WINDOWS.md](QUICK_START_WINDOWS.md) ← Start
2. [LOCAL_SETUP.md](LOCAL_SETUP.md)
3. [WINDOWS_LOCAL_SETUP_GUIDE.md](WINDOWS_LOCAL_SETUP_GUIDE.md)

### Some Experience
1. [QUICK_START_WINDOWS.md](QUICK_START_WINDOWS.md) ← Start
2. [RUN_LOCAL.md](RUN_LOCAL.md)
3. Jump to coding!

### Experienced Developer
1. Skim [DOCKER_TO_LOCAL_MIGRATION.md](DOCKER_TO_LOCAL_MIGRATION.md)
2. Run `scripts/setup-local.ps1`
3. Start coding from [PHASE2_PLAN.md](PHASE2_PLAN.md)

---

## ⚡ TL;DR (Super Quick)

```powershell
# 1. Install Python & PostgreSQL manually (search online for instructions)

# 2. Run this:
cd d:\work\stock-market-project
powershell -ExecutionPolicy Bypass -File scripts/setup-local.ps1

# 3. Create database:
psql -U postgres -c "CREATE DATABASE neuroquant;"
psql -U postgres -d neuroquant -f infrastructure/postgres/init.sql

# 4. Run these in 2 terminals:
# Terminal 1:
.\venv\Scripts\Activate.ps1
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2:
pnpm dev

# 5. Open: http://localhost:3000
```

---

## 🤔 FAQ: Which Document Should I Read?

**Q: I'm in a rush, what's the minimum I need to read?**
A: [QUICK_START_WINDOWS.md](QUICK_START_WINDOWS.md) (5 minutes)

**Q: I need complete installation details**
A: [LOCAL_SETUP.md](LOCAL_SETUP.md) (20 minutes)

**Q: I need to understand what changed from Docker**
A: [DOCKER_TO_LOCAL_MIGRATION.md](DOCKER_TO_LOCAL_MIGRATION.md) (10 minutes)

**Q: I keep forgetting how to start services**
A: [RUN_LOCAL.md](RUN_LOCAL.md) (bookmark this!)

**Q: I have a database problem**
A: [POSTGRES_LOCAL_SETUP.md](POSTGRES_LOCAL_SETUP.md)

**Q: I need everything explained in detail**
A: [WINDOWS_LOCAL_SETUP_GUIDE.md](WINDOWS_LOCAL_SETUP_GUIDE.md) (30 minutes)

**Q: I'm ready to start coding**
A: [PHASE2_PLAN.md](PHASE2_PLAN.md)

---

## 🎉 Ready to Start?

1. **Open:** [QUICK_START_WINDOWS.md](QUICK_START_WINDOWS.md)
2. **Follow:** 5-minute setup
3. **Code:** Start with Phase 2 Authentication

---

## 💾 File Organization

```
d:\work\stock-market-project\
├── QUICK_START_WINDOWS.md ← Start here
├── LOCAL_SETUP.md
├── RUN_LOCAL.md
├── WINDOWS_LOCAL_SETUP_GUIDE.md
├── POSTGRES_LOCAL_SETUP.md
├── DOCKER_TO_LOCAL_MIGRATION.md
├── SETUP_DOCUMENTATION_INDEX.md ← You are here
├── PHASE2_PLAN.md ← Next steps
├── DEVELOPMENT_ROADMAP.md
├── scripts/
│   └── setup-local.ps1
├── requirements-local.txt
├── .env ← Auto-generated by setup script
├── backend/
├── apps/web/
└── services/
```

---

## ✉️ Need Help?

1. **Setup problems?** → Check [WINDOWS_LOCAL_SETUP_GUIDE.md](WINDOWS_LOCAL_SETUP_GUIDE.md) troubleshooting
2. **Database issues?** → Check [POSTGRES_LOCAL_SETUP.md](POSTGRES_LOCAL_SETUP.md)
3. **Can't start services?** → Check [RUN_LOCAL.md](RUN_LOCAL.md)
4. **Don't know how?** → Start with [QUICK_START_WINDOWS.md](QUICK_START_WINDOWS.md)

---

**Last Updated:** March 2026
**Setup Type:** Local Windows (No Docker)
**Status:** ✅ Complete and Ready to Use

