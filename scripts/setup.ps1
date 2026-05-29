# PowerShell setup script for Windows users
# Run in repository root in an elevated PowerShell if needed.

Write-Host "PHASE 0: ENVIRONMENT SETUP (Windows) - NeuroQuant" -ForegroundColor Cyan

# Prerequisites check
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Write-Error "Node.js is required. Install Node 20+ and retry."; exit 1 }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { Write-Error "Python is required. Install Python 3.12+ and retry."; exit 1 }
if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) { Write-Host "pnpm not found, installing..."; npm i -g pnpm@8.15.6 }

# Create venv
Write-Host "Creating Python virtual environment .venv..."
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install backend requirements
Write-Host "Installing backend requirements (may take time)"
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r backend\requirements.txt

# Install frontend dependencies
Write-Host "Installing node dependencies with pnpm"
pnpm install

Write-Host "Setup complete. Activate venv with '.\\.venv\\Scripts\\Activate.ps1' and run 'pnpm --filter @neuroquant/web dev' to start the frontend." -ForegroundColor Green
