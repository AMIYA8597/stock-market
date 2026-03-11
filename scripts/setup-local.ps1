# ════════════════════════════════════════════════════════════════════════════════
# setup-local.ps1 — Local Windows Development Setup (No Docker)
# ════════════════════════════════════════════════════════════════════════════════
# Run: powershell -ExecutionPolicy Bypass -File scripts/setup-local.ps1

param(
    [switch]$SkipPrerequisites = $false
)

$ErrorActionPreference = "Stop"
$WarningPreference = "Continue"

Write-Host "════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "LOCAL WINDOWS DEVELOPMENT SETUP (No Docker)" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ════════════════════════════════════════════════════════════════════════════════
# STEP 1: Check Prerequisites
# ════════════════════════════════════════════════════════════════════════════════

Write-Host "STEP 1: Checking Prerequisites..." -ForegroundColor Yellow
Write-Host ""

$prerequisites = @{
    "Python 3" = "python --version"
    "Node.js" = "node --version"
    "pnpm" = "pnpm --version"
    "PostgreSQL" = "psql --version"
}

$allPresent = $true

foreach ($name in $prerequisites.Keys) {
    try {
        $version = Invoke-Expression $prerequisites[$name] 2>&1
        Write-Host "✅ $name : $version" -ForegroundColor Green
    } catch {
        Write-Host "❌ $name : NOT FOUND" -ForegroundColor Red
        $allPresent = $false
    }
}

Write-Host ""

if (-not $allPresent -and -not $SkipPrerequisites) {
    Write-Host "ERROR: Some prerequisites are missing!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install missing components from:" -ForegroundColor Yellow
    Write-Host "  - Python 3.12: https://python.org/downloads" -ForegroundColor Cyan
    Write-Host "  - Node.js 20: https://nodejs.org" -ForegroundColor Cyan
    Write-Host "  - PostgreSQL 16: https://postgresql.org/download/windows" -ForegroundColor Cyan
    Write-Host "  - pnpm: npm install -g pnpm" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Then run this script again." -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ All prerequisites present!" -ForegroundColor Green
Write-Host ""

# ════════════════════════════════════════════════════════════════════════════════
# STEP 2: Create Project Structure
# ════════════════════════════════════════════════════════════════════════════════

Write-Host "STEP 2: Creating project structure..." -ForegroundColor Yellow

$dirs = @(
    "keys",
    "venv",
    "backend/alembic/versions",
    "services/ml-engine",
    "services/data-pipeline",
    "services/risk-engine",
    "services/backtesting",
    "services/alert-service"
)

foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  📁 Created: $dir" -ForegroundColor Cyan
    }
}

Write-Host ""

# ════════════════════════════════════════════════════════════════════════════════
# STEP 3: Generate Keys
# ════════════════════════════════════════════════════════════════════════════════

Write-Host "STEP 3: Generating encryption keys..." -ForegroundColor Yellow

# Generate Fernet key (for field encryption)
$fernetKeyGenScript = @"
from cryptography.fernet import Fernet
key = Fernet.generate_key().decode()
print(key)
"@

try {
    $fernetKey = python -c $fernetKeyGenScript 2>$null
    Write-Host "✅ Fernet key generated" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Could not generate Fernet key (optional)" -ForegroundColor Yellow
    $fernetKey = "your-fernet-key-here"
}

Write-Host ""

# ════════════════════════════════════════════════════════════════════════════════
# STEP 4: Create .env file
# ════════════════════════════════════════════════════════════════════════════════

Write-Host "STEP 4: Creating .env configuration file..." -ForegroundColor Yellow

$envContent = @"
# DATABASE (PostgreSQL Local)
DATABASE_URL=postgresql://postgres:postgres123@localhost:5432/neuroquant
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
POSTGRES_DB=neuroquant

# Redis (Optional)
REDIS_URL=redis://localhost:6379
REDIS_CACHE_DB=0
REDIS_CELERY_BROKER_DB=1
REDIS_CELERY_RESULT_DB=2

# JWT Keys
JWT_PRIVATE_KEY_PATH=./keys/private.pem
JWT_PUBLIC_KEY_PATH=./keys/public.pem
JWT_ALGORITHM=RS256
JWT_EXPIRY_SECONDS=3600
REFRESH_TOKEN_EXPIRY_SECONDS=604800

# Encryption
FIELD_ENCRYPTION_KEY=$fernetKey

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXTAUTH_SECRET=neuroquant-development-secret-key-change-in-production
NEXTAUTH_URL=http://localhost:3000

# Service Ports
GATEWAY_PORT=8000
ML_ENGINE_PORT=8001
DATA_PIPELINE_PORT=8002
RISK_ENGINE_PORT=8003
ALERT_SERVICE_PORT=8004
BACKTESTING_PORT=8005
FRONTEND_PORT=3000

# Feature Flags
ENABLE_2FA=true
ENABLE_PAPER_TRADING=true
ENABLE_BACKTESTING=true
ENABLE_ML_PREDICTIONS=true

# Logging
LOG_LEVEL=INFO
"@

Set-Content -Path ".env" -Value $envContent -Encoding UTF8
Write-Host "✅ .env file created" -ForegroundColor Green
Write-Host ""

# ════════════════════════════════════════════════════════════════════════════════
# STEP 5: Create Python Virtual Environment
# ════════════════════════════════════════════════════════════════════════════════

Write-Host "STEP 5: Creating Python virtual environment..." -ForegroundColor Yellow

if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
& ".\venv\Scripts\Activate.ps1" 2>$null
Write-Host "✅ Virtual environment activated" -ForegroundColor Green
Write-Host ""

# ════════════════════════════════════════════════════════════════════════════════
# STEP 6: Install Python Dependencies
# ════════════════════════════════════════════════════════════════════════════════

Write-Host "STEP 6: Installing Python dependencies..." -ForegroundColor Yellow
Write-Host "(This may take 2-3 minutes...)" -ForegroundColor Cyan

pip install --upgrade pip setuptools wheel | Out-Null
pip install -r requirements-local.txt --quiet

Write-Host "✅ Python dependencies installed" -ForegroundColor Green
Write-Host ""

# ════════════════════════════════════════════════════════════════════════════════
# STEP 7: Install Node Dependencies
# ════════════════════════════════════════════════════════════════════════════════

Write-Host "STEP 7: Installing Node dependencies..." -ForegroundColor Yellow
Write-Host "(This may take 2-3 minutes...)" -ForegroundColor Cyan

pnpm install --quiet 2>$null

Write-Host "✅ Node dependencies installed" -ForegroundColor Green
Write-Host ""

# ════════════════════════════════════════════════════════════════════════════════
# STEP 8: Database Setup Instructions
# ════════════════════════════════════════════════════════════════════════════════

Write-Host "STEP 8: Database Setup" -ForegroundColor Yellow
Write-Host ""
Write-Host "Run these commands in a NEW Command Prompt:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Create database:" -ForegroundColor White
Write-Host "     psql -U postgres -c `"CREATE DATABASE neuroquant;`"" -ForegroundColor Cyan
Write-Host ""
Write-Host "  2. Load schema:" -ForegroundColor White
Write-Host "     psql -U postgres -d neuroquant -f infrastructure/postgres/init.sql" -ForegroundColor Cyan
Write-Host ""
Write-Host "  3. Verify:" -ForegroundColor White
Write-Host "     psql -U postgres -d neuroquant -c `"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';`"" -ForegroundColor Cyan
Write-Host ""
Write-Host "Expected output: 17 (number of tables)" -ForegroundColor Green
Write-Host ""

# ════════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ════════════════════════════════════════════════════════════════════════════════

Write-Host "════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ LOCAL SETUP COMPLETE!" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Create the database (see Step 8 above)" -ForegroundColor White
Write-Host ""
Write-Host "2. Start Backend (in a new Terminal):" -ForegroundColor White
Write-Host "   cd d:\work\stock-market-project" -ForegroundColor Cyan
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "   cd backend" -ForegroundColor Cyan
Write-Host "   uvicorn app.main:app --reload --port 8000" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Start Frontend (in another Terminal):" -ForegroundColor White
Write-Host "   cd d:\work\stock-market-project" -ForegroundColor Cyan
Write-Host "   pnpm dev" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Open in Browser:" -ForegroundColor White
Write-Host "   http://localhost:3000  (Frontend)" -ForegroundColor Cyan
Write-Host "   http://localhost:8000/docs  (API Docs)" -ForegroundColor Cyan
Write-Host ""

Write-Host "For detailed instructions, see: LOCAL_SETUP.md" -ForegroundColor Yellow
Write-Host ""
