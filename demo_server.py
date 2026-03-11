#!/usr/bin/env python
"""
Simple FastAPI demo server for NeuroQuant project.
Shows that the backend can run without complex dependencies.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from datetime import datetime

app = FastAPI(title="NeuroQuant API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {"message": "NeuroQuant API Running", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "NeuroQuant backend is running"
    }

@app.get("/api/v1/health")
async def api_health():
    return {"status": "ok", "service": "neuroquant-gateway"}

@app.get("/api/v1/market/symbols")
async def get_symbols():
    """Get list of available market symbols"""
    return {
        "symbols": [
            {"symbol": "NIFTY50", "name": "NIFTY 50", "active": True},
            {"symbol": "BANKEX", "name": "Bank Index", "active": True},
            {"symbol": "IT", "name": "IT Index", "active": True},
            {"symbol": "REALTY", "name": "Realty Index", "active": True},
        ]
    }

@app.get("/api/v1/market/{symbol}/ohlcv")
async def get_ohlcv(symbol: str):
    """Get OHLCV data for a symbol"""
    return {
        "symbol": symbol,
        "data": [
            {
                "time": "2026-03-10T09:00:00",
                "open": 24500,
                "high": 24800,
                "low": 24450,
                "close": 24750,
                "volume": 1000000
            }
        ]
    }

@app.get("/api/v1/portfolio")
async def get_portfolio():
    """Get user portfolio"""
    return {
        "username": "demo_user",
        "total_value": 500000,
        "cash": 100000,
        "invested": 400000,
        "holdings": [
            {
                "symbol": "NIFTY50",
                "quantity": 10,
                "buy_price": 24000,
                "current_price": 24750,
                "value": 247500,
                "pnl": 7500
            }
        ]
    }

@app.get("/api/v1/predictions/{symbol}")
async def get_predictions(symbol: str):
    """Get ML price predictions"""
    return {
        "symbol": symbol,
        "current_price": 24750,
        "predictions": {
            "24h": {"price": 24850, "confidence": 0.75},
            "7d": {"price": 25200, "confidence": 0.65},
            "30d": {"price": 26000, "confidence": 0.55}
        }
    }

@app.post("/api/v1/auth/login")
async def login(credentials: dict = None):
    """Demo login endpoint"""
    return {
        "token": "demo-jwt-token-12345",
        "user": "demo_user",
        "expires_in": 3600
    }

# ============================================================================
# FRONTEND - Simple HTML/JavaScript
# ============================================================================

FRONTEND_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NeuroQuant - Stock Market AI Platform</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        h1 {
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #666;
            font-size: 14px;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .card h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 18px;
        }
        
        .stat {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        
        .stat:last-child {
            border-bottom: none;
        }
        
        .stat-value {
            color: #667eea;
            font-weight: bold;
        }
        
        .status {
            display: inline-block;
            background: #4caf50;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            margin-top: 10px;
        }
        
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin-top: 15px;
        }
        
        button:hover {
            background: #764ba2;
        }
        
        .loading {
            color: #999;
            font-style: italic;
        }
        
        .error {
            color: #d32f2f;
            padding: 10px;
            background: #ffebee;
            border-radius: 4px;
            margin-top: 10px;
        }
        
        .features {
            background: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
        }
        
        .features h2 {
            color: #667eea;
            margin-bottom: 20px;
        }
        
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        
        .feature {
            padding: 15px;
            background: #f5f5f5;
            border-radius: 4px;
            border-left: 4px solid #667eea;
        }
        
        .feature h3 {
            color: #333;
            margin-bottom: 5px;
        }
        
        .feature p {
            color: #666;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 NeuroQuant</h1>
            <p class="subtitle">Institutional-Grade AI-Powered Stock Market Platform</p>
            <span class="status">✓ Backend Running</span>
        </header>
        
        <div class="grid">
            <div class="card">
                <h2>📊 Market Data</h2>
                <div id="market-data" class="loading">Loading...</div>
                <button onclick="loadMarketData()">Refresh Market Data</button>
            </div>
            
            <div class="card">
                <h2>💼 Portfolio</h2>
                <div id="portfolio-data" class="loading">Loading...</div>
                <button onclick="loadPortfolio()">Refresh Portfolio</button>
            </div>
            
            <div class="card">
                <h2>🤖 AI Predictions</h2>
                <div id="predictions-data" class="loading">Loading...</div>
                <button onclick="loadPredictions()">Refresh Predictions</button>
            </div>
        </div>
        
        <div class="features">
            <h2>✨ Platform Features</h2>
            <div class="feature-grid">
                <div class="feature">
                    <h3>Real-Time Market Data</h3>
                    <p>Stream live OHLCV data from NSE/NIFTY with WebSocket support</p>
                </div>
                <div class="feature">
                    <h3>AI Price Predictions</h3>
                    <p>Machine learning models (LSTM, XGBoost) for trend forecasting</p>
                </div>
                <div class="feature">
                    <h3>Risk Management</h3>
                    <p>VaR, CVaR, stress testing, and portfolio optimization</p>
                </div>
                <div class="feature">
                    <h3>Backtesting Engine</h3>
                    <p>Event-driven backtesting with realistic trade execution</p>
                </div>
                <div class="feature">
                    <h3>User Authentication</h3>
                    <p>JWT RS256, 2FA, Argon2id password hashing</p>
                </div>
                <div class="feature">
                    <h3>Alerts & Notifications</h3>
                    <p>Price alerts, technical signals, sentiment analysis, anomalies</p>
                </div>
            </div>
        </div>
        
        <div class="features">
            <h2>🏗️ Architecture</h2>
            <div class="feature-grid">
                <div class="feature">
                    <h3>Frontend</h3>
                    <p>Next.js 14, React 18, TypeScript, Tailwind CSS</p>
                </div>
                <div class="feature">
                    <h3>Backend</h3>
                    <p>FastAPI, SQLAlchemy 2.0, async/await, WebSocket</p>
                </div>
                <div class="feature">
                    <h3>Database</h3>
                    <p>PostgreSQL 16 + TimescaleDB, Redis 7.2, MinIO</p>
                </div>
                <div class="feature">
                    <h3>ML Pipeline</h3>
                    <p>PyTorch, XGBoost, LightGBM, CatBoost, FinBERT</p>
                </div>
                <div class="feature">
                    <h3>Infrastructure</h3>
                    <p>Docker, Kubernetes, Nginx, Prometheus, Grafana, Jaeger</p>
                </div>
                <div class="feature">
                    <h3>Security</h3>
                    <p>RS256 JWT, Argon2id, Fernet encryption, TLS 1.3</p>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>🔗 API Status</h2>
            <div id="api-status" class="loading">Checking...</div>
        </div>
    </div>
    
    <script>
        const API_BASE = "http://localhost:8000/api/v1";
        
        async function loadMarketData() {
            try {
                const response = await fetch(`${API_BASE}/market/symbols`);
                const data = await response.json();
                const html = data.symbols.map(s => 
                    `<div class="stat"><label>${s.symbol}</label><span class="stat-value">${s.name}</span></div>`
                ).join('');
                document.getElementById('market-data').innerHTML = html || '<p>No data</p>';
            } catch (e) {
                document.getElementById('market-data').innerHTML = `<div class="error">Error: ${e.message}</div>`;
            }
        }
        
        async function loadPortfolio() {
            try {
                const response = await fetch(`${API_BASE}/portfolio`);
                const data = await response.json();
                const html = `
                    <div class="stat"><label>Total Value</label><span class="stat-value">₹${data.total_value}</span></div>
                    <div class="stat"><label>Invested</label><span class="stat-value">₹${data.invested}</span></div>
                    <div class="stat"><label>Cash</label><span class="stat-value">₹${data.cash}</span></div>
                `;
                document.getElementById('portfolio-data').innerHTML = html;
            } catch (e) {
                document.getElementById('portfolio-data').innerHTML = `<div class="error">Error: ${e.message}</div>`;
            }
        }
        
        async function loadPredictions() {
            try {
                const response = await fetch(`${API_BASE}/predictions/NIFTY50`);
                const data = await response.json();
                const pred = data.predictions;
                const html = `
                    <div class="stat"><label>24h Prediction</label><span class="stat-value">₹${pred['24h'].price}</span></div>
                    <div class="stat"><label>7d Prediction</label><span class="stat-value">₹${pred['7d'].price}</span></div>
                    <div class="stat"><label>30d Prediction</label><span class="stat-value">₹${pred['30d'].price}</span></div>
                `;
                document.getElementById('predictions-data').innerHTML = html;
            } catch (e) {
                document.getElementById('predictions-data').innerHTML = `<div class="error">Error: ${e.message}</div>`;
            }
        }
        
        async function checkAPIStatus() {
            try {
                const response = await fetch("http://localhost:8000/health");
                const data = await response.json();
                const html = `
                    <div class="stat"><label>Status</label><span class="stat-value">${data.status}</span></div>
                    <div class="stat"><label>Time</label><span class="stat-value">${new Date(data.timestamp).toLocaleTimeString()}</span></div>
                `;
                document.getElementById('api-status').innerHTML = html;
            } catch (e) {
                document.getElementById('api-status').innerHTML = `<div class="error">Backend not responding: ${e.message}</div>`;
            }
        }
        
        // Load data on page load
        window.addEventListener('load', () => {
            checkAPIStatus();
            loadMarketData();
            loadPortfolio();
            loadPredictions();
        });
    </script>
</body>
</html>
"""

@app.get("/app", response_class=HTMLResponse)
async def frontend():
    return FRONTEND_HTML

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
