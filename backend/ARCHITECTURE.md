# QuantEdge Architecture

## System Diagram

```mermaid
graph TD
    Client[Web/Mobile Client] --> API[FastAPI Backend]
    Client --> WS[WebSocket Server]
    
    API --> Cache[(Redis Cache)]
    WS --> Cache
    
    API --> DB[(PostgreSQL + TimescaleDB)]
    
    API --> Auth[JWT Auth Middleware]
    
    subgraph Data Ingestion
        Providers[Market Data Providers]
        Failover[Failover Orchestrator]
        Providers --> Failover
        Failover --> Cache
        Failover --> DB
    end
    
    API --> Failover
    
    subgraph Intelligence
        Signal[Classical Signal Engine]
        ML[ML/AI Prediction Engine]
        Backtest[Event-Driven Backtester]
        Signal --> DB
        ML --> DB
        Backtest --> DB
    end
    
    API --> Intelligence
    
    subgraph Async Workers
        Celery[Celery Task Queue]
        Celery --> Backtest
        Celery --> ML
    end
    
    API --> Celery
```

## Data Flow
1. **Market Data**: Ingested via Failover Orchestrator (yfinance -> Stooq -> NSE). Cached in Redis, persisted to TimescaleDB.
2. **Signals**: Computed by TechnicalSignalEngine on demand or via batch jobs. Vectorized using pandas and cached.
3. **WebSockets**: Broadcasts live prices, signals, and backtest progress via Redis pub/sub to multiple API instances, which push to clients.
4. **Backtesting**: Runs asynchronously in Celery, sending progress via WebSocket.
