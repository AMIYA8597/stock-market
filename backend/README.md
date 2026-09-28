---
title: NeuroQuant API
emoji: 📈
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# NeuroQuant Backend

This directory contains the FastAPI backend and Machine Learning research engine for NeuroQuant.

> If deploying this folder as a Hugging Face Space: the YAML block above
> must be the literal first thing in this file (Spaces reads it to pick
> the Docker SDK and which port `EXPOSE`d by `Dockerfile` to route to -
> without it, the Space won't start). Don't move it below this heading.

## Architecture
The backend is split into two primary domains:
- **`app/`**: The FastAPI server. Contains API endpoints (`api/v1`), WebSocket hubs (`websocket/`), background tasks, database models, and service layer integrations with external providers (yfinance, NSE, etc).
- **`research/`**: The quant/ML research environment. Contains the `ML_Engine`, backtesting engine, data loaders, and model definitions (HMM, TFT, Metalearners).

## Principles
1. **Free-tier Native**: The application is 100% functional out-of-the-box using `yfinance` and public NSE/BSE data.
2. **Honest Data**: The API accurately reflects reality. It raises an HTTP 503 instead of generating mock/dummy numbers when real data is unavailable.
3. **Asynchronous Execution**: Data ingestion, model inference, and real-time WebSocket ticks are fully async.

## Running the Server
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-core.txt
# Optional: For ML model training only
pip install -r requirements-ml.txt

python -m uvicorn app.main:app --reload --port 8000
```

## Running Tests
All tests must use dummy/mock data natively using `pytest` fixtures, rather than live network calls.
```bash
pytest tests/ -v
```

## Machine Learning & AI
Models are trained offline via scripts in `research/` or triggered by the celery pipeline. The models output `.pkl` or `.pt` artifacts.
The API serves predictions using these artifacts natively. If an artifact is not found, the backend safely raises an error rather than faking a prediction output.
