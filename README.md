# NeuroQuant — Local Run & Test Guide

This repository contains the NeuroQuant monorepo (frontend + backend). These instructions show how to get a working local dev environment and run the unified test gate that validates both frontend and backend.

Prerequisites
- Node.js 20+, pnpm 8+ (or as specified in `package.json`)
- Python 3.12+ (or your preferred py3 virtualenv)
- Docker (for optional services)
- git

Quick start (development)
1. Install node dependencies (root):

```bash
pnpm install
```

2. Create Python virtualenv and activate (recommended):

On macOS / Linux:
```bash
python -m venv .venv
source .venv/bin/activate
```
On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Copy the example env and tweak if needed:
```bash
cp .env.example .env
# or on Windows PowerShell:
Copy-Item .env.example .env
```

4. Run frontend in dev:
```bash
pnpm --filter @neuroquant/web dev
```

5. Run backend (local dev):
```bash
cd backend
# Install lightweight dev deps for local testing
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Unified validation (what CI should run locally)
- Run the repo-level test (this builds the frontend and executes backend pytest):

```bash
pnpm test
```

Notes and troubleshooting
- `pnpm test` runs `pnpm --filter @neuroquant/web build` then runs `pytest` in `backend/`.
- On Windows, building some Python packages (pandas, numpy) may require Visual Studio Build Tools. To avoid heavy installs, the repository test gate only installs the lightweight test runtime packages (`pytest`, `aiosqlite`) before running tests.
- If CI or GitHub shows push errors, check branch protection rules and required status checks on the repository settings. Locally, `git push --dry-run` will tell you if a push will be accepted.

Files changed in this update
- `scripts/setup.sh` — updated to install `backend/requirements.txt` instead of nonexistent `services/*` paths.
- `.github/workflows/deploy.yml` — removed references to `services/gateway` and build only the `backend` image.
- `package.json` — added `test:full` and made `test` run it.

If you want, I can:
- Commit these changes and push them on your behalf (I will show commands),
- Update CI to run the `pnpm test` root gate, or
- Harden the `setup.sh` script for cross-platform behavior.

Would you like me to commit the current edits and push, or continue with `setup.sh` cross-platform improvements now?
