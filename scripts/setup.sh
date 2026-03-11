#!/bin/bash
# PHASE 0 — Complete Environment Setup Script for NeuroQuant
# This script initializes everything needed to run the full system

set -e

echo "════════════════════════════════════════════════════════════════"
echo "PHASE 0: ENVIRONMENT SETUP - NeuroQuant Platform"
echo "════════════════════════════════════════════════════════════════"

# Check for required tools
echo "✓ Checking prerequisites..."
command -v node >/dev/null || { echo "ERROR: Node.js 20 LTS required"; exit 1; }
command -v python3 >/dev/null || { echo "ERROR: Python 3.12 required"; exit 1; }
command -v docker >/dev/null || { echo "ERROR: Docker required"; exit 1; }
command -v pnpm >/dev/null || npm install -g pnpm@9.0.0

echo "✓ Prerequisites verified"

# Create monorepo structure
echo ""
echo "✓ Creating directory structure..."
mkdir -p apps/web/src/{app,components,hooks,lib,stores,types}
mkdir -p packages/{ui,charts,types,config}
mkdir -p services/{gateway,ml-engine,data-pipeline,risk-engine,alert-service,backtesting}
mkdir -p infrastructure/{docker,nginx,postgres,redis}
mkdir -p scripts keys ml/{artifacts,data} .github/workflows

# Check prerequisites
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 required"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js required"; exit 1; }
command -v pnpm >/dev/null 2>&1 || { echo "❌ pnpm required"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker required"; exit 1; }

# Generate JWT keys
echo "🔐 Generating JWT RSA keys..."
mkdir -p keys
openssl genrsa -out keys/private.pem 2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem

# Generate Fernet key
echo "🔑 Generating Fernet encryption key..."
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > .env.key

# Copy environment template
echo "📋 Setting up environment variables..."
cp .env.example .env

# Install Python dependencies
echo "🐍 Installing Python dependencies..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install backend dependencies
echo "  → Backend gateway service..."
pip install --upgrade pip setuptools wheel
pip install -r services/gateway/requirements.txt

echo "  → ML engine service..."
pip install -r services/ml-engine/requirements.txt

echo "  → Data pipeline service..."
pip install -r services/data-pipeline/requirements.txt

echo "  → Risk engine service..."
pip install -r services/risk-engine/requirements.txt

echo "  → Backtesting service..."
pip install -r services/backtesting/requirements.txt

echo "  → Alert service..."
pip install -r services/alert-service/requirements.txt

# Install frontend dependencies
echo "📦 Installing Node dependencies with pnpm..."
pnpm install

# Generate .env from .env.example if needed
if [ ! -f .env ]; then
  echo "📋 Creating .env configuration..."
  cat > .env << EOF
# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════════════════
DATABASE_URL=postgresql+asyncpg://neuroquant:neuroquant@localhost:5432/neuroquant
POSTGRES_USER=neuroquant
POSTGRES_PASSWORD=neuroquant
POSTGRES_DB=neuroquant

# ═══════════════════════════════════════════════════════════════════════════════
# REDIS
# ═══════════════════════════════════════════════════════════════════════════════
REDIS_URL=redis://localhost:6379
REDIS_CACHE_DB=0
REDIS_CELERY_BROKER_DB=1
REDIS_CELERY_RESULT_DB=2

# ═══════════════════════════════════════════════════════════════════════════════
# S3 / MINIO
# ═══════════════════════════════════════════════════════════════════════════════
MINIO_URL=http://localhost:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
S3_BUCKET=neuroquant-artifacts
AWS_REGION=us-east-1

# ═══════════════════════════════════════════════════════════════════════════════
# JWT + SECURITY
# ═══════════════════════════════════════════════════════════════════════════════
JWT_PRIVATE_KEY_PATH=./keys/private.pem
JWT_PUBLIC_KEY_PATH=./keys/public.pem
JWT_ALGORITHM=RS256
JWT_EXPIRY_SECONDS=3600
REFRESH_TOKEN_EXPIRY_SECONDS=604800

# ═══════════════════════════════════════════════════════════════════════════════
# ENCRYPTION
# ═══════════════════════════════════════════════════════════════════════════════
FIELD_ENCRYPTION_KEY=$(cat .env.key)

# ═══════════════════════════════════════════════════════════════════════════════
# MARKET DATA APIs
# ═══════════════════════════════════════════════════════════════════════════════
YFINANCE_ENABLED=true
ALPHA_VANTAGE_API_KEY=
ALPHA_VANTAGE_ENABLED=false
FRED_API_KEY=
FRED_ENABLED=false
NEWSAPI_API_KEY=
NEWSAPI_ENABLED=false
CCXT_EXCHANGES=binance,upbit

# ═══════════════════════════════════════════════════════════════════════════════
# CELERY
# ═══════════════════════════════════════════════════════════════════════════════
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
CELERY_TASK_TIMEOUT=300

# ═══════════════════════════════════════════════════════════════════════════════
# MLFLOW
# ═══════════════════════════════════════════════════════════════════════════════
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT_NAME=neuroquant-trading

# ═══════════════════════════════════════════════════════════════════════════════
# FRONTEND
# ═══════════════════════════════════════════════════════════════════════════════
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXTAUTH_SECRET=$(openssl rand -base64 32)
NEXTAUTH_URL=http://localhost:3000

# ═══════════════════════════════════════════════════════════════════════════════
# OAUTH (Google)
# ═══════════════════════════════════════════════════════════════════════════════
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# ═══════════════════════════════════════════════════════════════════════════════
# OBSERVABILITY
# ═══════════════════════════════════════════════════════════════════════════════
JAEGER_ENABLED=true
JAEGER_AGENT_HOST=localhost
JAEGER_AGENT_PORT=6831
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════
LOG_LEVEL=INFO
STRUCTLOG_ENABLED=true

# ═══════════════════════════════════════════════════════════════════════════════
# SERVICE PORTS
# ═══════════════════════════════════════════════════════════════════════════════
GATEWAY_PORT=8000
ML_ENGINE_PORT=8001
DATA_PIPELINE_PORT=8002
RISK_ENGINE_PORT=8003
ALERT_SERVICE_PORT=8004
BACKTESTING_PORT=8005
FRONTEND_PORT=3000

# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE FLAGS
# ═══════════════════════════════════════════════════════════════════════════════
ENABLE_2FA=true
ENABLE_PAPER_TRADING=true
ENABLE_BACKTESTING=true
ENABLE_ML_PREDICTIONS=true
ENABLE_SENTIMENT_ANALYSIS=true
ENABLE_ANOMALY_DETECTION=true
ENABLE_LANGGRAPH_RESEARCH=true

EOF
  echo "✓ .env created with defaults"
fi

# Start Docker services
echo ""
echo "🐳 Starting Docker containers..."
docker-compose up -d

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
for i in {1..30}; do
  if docker exec stock-market-project-postgres-1 pg_isready -U neuroquant >/dev/null 2>&1; then
    echo "✓ PostgreSQL is ready"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "❌ PostgreSQL failed to start"
    exit 1
  fi
  sleep 1
done

# Wait for Redis to be ready
echo "⏳ Waiting for Redis..."
for i in {1..30}; do
  if docker exec stock-market-project-redis-1 redis-cli ping >/dev/null 2>&1; then
    echo "✓ Redis is ready"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "❌ Redis failed to start"
    exit 1
  fi
  sleep 1
done

# Run database migrations
echo ""
echo "🗄️  Running database migrations..."
cd backend
alembic upgrade head
cd ..

# Verify database
echo ""
echo "✓ Verifying database schema..."
python3 -c "
from sqlalchemy import create_engine, inspect
engine = create_engine('${DATABASE_URL}')
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f'Tables created: {len(tables)}')
for table in tables:
  print(f'  ✓ {table}')
"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ PHASE 0 COMPLETE!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. npm run dev              # Start frontend (port 3000)"
echo "  2. cd backend && uvicorn app.main:app --reload --port 8000  # Start Gateway API"
echo "  3. docker-compose ps        # Verify all containers healthy"
echo ""
echo "🚀 Platform ready for PHASE 1+ implementation"
echo "════════════════════════════════════════════════════════════════"
pip install -r backend/requirements.txt
for service in services/*/; do
  if [ -f "$service/requirements.txt" ]; then
    pip install -r "$service/requirements.txt"
  fi
done

# Install Node dependencies
echo "📦 Installing Node dependencies..."
pnpm install

# Start Docker services
echo "🐳 Starting Docker containers..."
docker compose up -d

# Wait for database
echo "⏳ Waiting for PostgreSQL..."
sleep 10

# Run database migrations
echo "🗄️ Running Alembic migrations..."
cd backend && alembic upgrade head && cd ..

# Seed initial data
echo "🌱 Seeding market data..."
python scripts/seed_data.py

# Train initial models
echo "🤖 Training ML models..."
python scripts/train_models.py

echo "✅ NEUROQUANT setup complete!"
echo "🌐 Frontend: http://localhost:3000"
echo "🔌 API Gateway: http://localhost:8000"
echo "📊 Docs: http://localhost:3001"