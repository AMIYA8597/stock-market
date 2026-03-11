# Simple Local Setup Script - Windows
# Run: powershell -ExecutionPolicy Bypass -File scripts/setup-simple.ps1

Write-Host "=== LOCAL WINDOWS SETUP ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create directories
Write-Host "Creating project directories..." -ForegroundColor Yellow
$dirs = @(
    "keys",
    "venv",
    "backend/alembic/versions",
    "services/ml-engine",
    "services/data-pipeline"
)

foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  Created: $dir" -ForegroundColor Cyan
    }
}

Write-Host ""

# Step 2: Create .env file
Write-Host "Creating .env configuration file..." -ForegroundColor Yellow

$envContent = @"
DATABASE_URL=postgresql://postgres:postgres123@localhost:5432/neuroquant
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
POSTGRES_DB=neuroquant
REDIS_URL=redis://localhost:6379
JWT_ALGORITHM=RS256
NEXTAUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
GATEWAY_PORT=8000
FRONTEND_PORT=3000
LOG_LEVEL=INFO
"@

Set-Content -Path ".env" -Value $envContent -Encoding UTF8
Write-Host "  Created: .env file" -ForegroundColor Cyan

Write-Host ""

# Step 3: Create Python virtual environment
Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "  Virtual environment created" -ForegroundColor Cyan
}

Write-Host ""

# Step 4: Activate venv and install Python packages
Write-Host "Installing Python packages..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1" 2>$null

pip install --upgrade pip setuptools wheel 2>&1 | Out-Null
pip install -r requirements-local.txt 2>&1 | Out-Null

Write-Host "  Python packages installed" -ForegroundColor Cyan

Write-Host ""

# Step 5: Install Node packages
Write-Host "Installing Node packages..." -ForegroundColor Yellow
pnpm install 2>&1 | Out-Null
Write-Host "  Node packages installed" -ForegroundColor Cyan

Write-Host ""
Write-Host "=== SETUP COMPLETE ===" -ForegroundColor Green
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. PostgreSQL Setup (if not done):" -ForegroundColor White
Write-Host "   - Download: https://postgresql.org/download/windows" -ForegroundColor Cyan
Write-Host "   - Install with password: postgres123" -ForegroundColor Cyan
Write-Host "   - Port: 5432" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Create Database:" -ForegroundColor White
Write-Host "   psql -U postgres -c \"CREATE DATABASE neuroquant;\"" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Load Schema:" -ForegroundColor White
Write-Host "   psql -U postgres -d neuroquant -f infrastructure/postgres/init.sql" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Start Backend (in a new terminal):" -ForegroundColor White
Write-Host "   venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "   cd backend" -ForegroundColor Cyan
Write-Host "   uvicorn app.main:app --reload --port 8000" -ForegroundColor Cyan
Write-Host ""
Write-Host "5. Start Frontend (in another terminal):" -ForegroundColor White
Write-Host "   pnpm dev" -ForegroundColor Cyan
Write-Host ""
Write-Host "6. Open Browser:" -ForegroundColor White
Write-Host "   http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
