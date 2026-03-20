# ════════════════════════════════════════════════════════════════════════════════
# MAKEFILE — Algorithmic Trading Platform (new-prompt.txt MASTER BUILD)
# ════════════════════════════════════════════════════════════════════════════════

.PHONY: help dev test lint migrate data-fetch features train-hmm train-tft train-gnn train-all backtest-full notebooks docs docker-up docker-down

help:
	@echo "╔════════════════════════════════════════════════════════════════════════════════╗"
	@echo "║ NEUROQUANT — Algorithmic Trading Intelligence Platform                       ║"
	@echo "║ Master Build Commands                                                         ║"
	@echo "╚════════════════════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Development:"
	@echo "  make dev                    Start local development stack (docker compose)"
	@echo "  make docker-up              Start Docker compose services"
	@echo "  make docker-down            Stop Docker compose services"
	@echo ""
	@echo "Database & Schema:"
	@echo "  make migrate                Run Alembic migrations"
	@echo "  make migrate-new            Generate new migration (use: make migrate-new name=my_migration)"
	@echo ""
	@echo "Data Pipeline:"
	@echo "  make data-fetch             Fetch 5y OHLCV history for all assets"
	@echo "  make features               Compute feature vectors (pipeline)"
	@echo ""
	@echo "Model Training:"
	@echo "  make train-hmm              Train HMM-GARCH regime detection"
	@echo "  make train-tft              Train Temporal Fusion Transformer"
	@echo "  make train-gnn              Train Graph Neural Network"
	@echo "  make train-all              Sequential: HMM → GNN → TFT → Ensemble calibration"
	@echo ""
	@echo "Analysis & Backtesting:"
	@echo "  make backtest-full          Run full CPCV walk-forward backtest"
	@echo "  make notebooks              Open Jupyter Lab with analysis notebooks"
	@echo ""
	@echo "Quality:"
	@echo "  make test                   Run all tests (backend + frontend)"
	@echo "  make test-backend           Run pytest on backend/tests/"
	@echo "  make test-frontend          Run jest on frontend tests"
	@echo "  make lint                   Lint all code (ruff, mypy, eslint)"
	@echo "  make format                 Auto-format all code"
	@echo "  make type-check             Python type checking (mypy strict)"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs                   Generate API docs from FastAPI schema"
	@echo ""

# ── Development ──────────────────────────────────────────────────────────────────
dev:
	docker compose up --build

docker-up:
	docker compose up -d
	@echo "✓ Docker services started (frontend :3000, backend :8000, postgres :5432, redis :6379)"

docker-down:
	docker compose down
	@echo "✓ Docker services stopped"

# ── Database ─────────────────────────────────────────────────────────────────────
migrate:
	cd backend && alembic upgrade head
	@echo "✓ Migrations applied"

migrate-new:
	cd backend && alembic revision --autogenerate -m "$(name)"
	@echo "✓ Migration created (edit alembic/versions/ and run 'make migrate')"

# ── Data Pipeline ────────────────────────────────────────────────────────────────
data-fetch:
	cd backend && python -m research.pipelines.data_pipeline --full-history --years 5
	@echo "✓ Historical OHLCV data fetched"

features:
	cd backend && python -m research.feature_engineering.pipeline compute --all
	@echo "✓ Feature vectors computed"

# ── Model Training ───────────────────────────────────────────────────────────────
train-hmm:
	cd backend && python -m research.models.hmm_garch.trainer --data-years 5 --epochs 200
	@echo "✓ HMM-GARCH model trained"

train-tft:
	cd backend && python -m research.models.tft.trainer --batch-size 64 --epochs 200 --early-stop 20
	@echo "✓ Temporal Fusion Transformer trained"

train-gnn:
	cd backend && python -m research.models.gnn.trainer --n-heads 8 --hidden-dim 128
	@echo "✓ Graph Neural Network trained"

train-all: train-hmm train-gnn train-tft
	cd backend && python -m research.models.ensemble.calibrator --retrain

# ── Analysis & Backtesting ──────────────────────────────────────────────────────
backtest-full:
	cd backend && python -m research.backtesting.engine \
	  --strategy ensemble \
	  --date-from 2018-01-01 \
	  --date-to 2024-12-31 \
	  --initial-capital 1000000 \
	  --walk-forward 8 \
	  --monte-carlo 10000
	@echo "✓ Full CPCV backtest completed"

notebooks:
	cd backend && jupyter lab --notebook-dir=research/notebooks
	@echo "✓ Jupyter Lab started"

# ── Testing & Quality ────────────────────────────────────────────────────────────
test: test-backend test-frontend
	@echo "✓ All tests completed"

test-backend:
	cd backend && pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=80
	@echo "✓ Backend tests completed (80% coverage threshold)"

test-frontend:
	pnpm --filter @neuroquant/web test:run
	@echo "✓ Frontend tests completed"

lint: lint-backend lint-frontend
	@echo "✓ All linting completed"

lint-backend:
	cd backend && ruff check app/ research/
	cd backend && mypy app/ research/ --strict --ignore-missing-imports
	@echo "✓ Backend linting clean"

lint-frontend:
	pnpm --filter @neuroquant/web run lint
	pnpm --filter @neuroquant/web run type-check
	@echo "✓ Frontend linting clean"

format:
	cd backend && ruff format app/ research/ tests/
	pnpm --filter @neuroquant/web run format
	@echo "✓ Code formatted"

type-check:
	cd backend && mypy app/ research/ --strict --ignore-missing-imports
	pnpm --filter @neuroquant/web run type-check
	@echo "✓ Type checking complete"

# ── Documentation ────────────────────────────────────────────────────────────────
docs:
	cd backend && python -c "from app.main import app; import json; open('api-schema.json', 'w').write(json.dumps(app.openapi(), indent=2))"
	@echo "✓ API schema exported to api-schema.json"

# ── Utility ──────────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".DS_Store" -delete
	@echo "✓ Cleaned up"

.DEFAULT_GOAL := help
