# Scalability Audit

## System Scale
The platform aims to handle the entire NSE/BSE universe with multiple timeframes (1m to 1Y) and multiple deep learning models.

## Current Limitations
- **Database**: Standard PostgreSQL without TimescaleDB partitions will degrade rapidly past 100M rows of tick data.
- **WebSocket Broadcasting**: A single FastAPI instance handling WebSocket connections will hit concurrent connection limits quickly.
- **Model Deployment**: Models are loaded directly into the PredictionEngine. Managing 50+ models (LSTM, BiLSTM, TFT, Informer, XGBoost) per asset requires a dedicated Model Serving layer (like TorchServe or Triton).

## Roadmap for Scalability
1. **TimescaleDB Integration**: Enable hypertables on the `ohlcv` and `predictions` tables.
2. **Redis Pub/Sub for WebSockets**: Implement Redis Pub/Sub to allow multiple FastAPI workers to broadcast tick data seamlessly.
3. **MLFlow**: Use MLFlow for model registry and tracking to decouple training from serving.
