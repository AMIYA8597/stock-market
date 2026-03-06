#!/bin/bash
# ════════════════════════════════════════════════════════════════════════════════
# NEUROQUANT SETUP SCRIPT
# One-command full environment setup for development
# ════════════════════════════════════════════════════════════════════════════════

set -e

echo "🚀 Starting NEUROQUANT setup..."

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