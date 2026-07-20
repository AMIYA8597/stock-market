from flask import Blueprint, jsonify, request, current_app
from .data_service import get_latest_price, get_historical
from .indicator_service import compute_indicators
from .ml_service import predict_price
from .backtest_service import run_backtest

api_bp = Blueprint('api', __name__)

@api_bp.route('/prices/<ticker>', methods=['GET'])
def get_price(ticker):
    """Return the latest OHLC data for the given ticker."""
    data = get_latest_price(ticker)
    if not data:
        return jsonify({'error': 'No data found'}), 404
    return jsonify(data)

@api_bp.route('/historical/<ticker>', methods=['GET'])
def get_historical_route(ticker):
    """Return historical OHLC data for the past N days (default 30)."""
    days = int(request.args.get('days', 30))
    data = get_historical(ticker, days)
    return jsonify([d for d in data])

@api_bp.route('/indicators/<ticker>', methods=['GET'])
def get_indicators(ticker):
    """Compute and return technical indicators for the latest N days."""
    days = int(request.args.get('days', 30))
    df = compute_indicators(ticker, days)
    # Convert DataFrame to list of dicts
    return jsonify(df.to_dict(orient='records'))

@api_bp.route('/predict/<ticker>', methods=['GET'])
def predict_route(ticker):
    """Return model predictions for the next time step.
    Query param `model` can specify which model to use (default: 'lstm').
    """
    model_name = request.args.get('model', 'lstm')
    prediction = predict_price(ticker, model_name)
    return jsonify({'ticker': ticker, 'model': model_name, 'prediction': prediction})

@api_bp.route('/signal/<ticker>', methods=['GET'])
def signal_route(ticker):
    """Generate a buy/sell/hold signal based on rule‑based logic.
    Simple moving‑average crossover is used as a demo.
    """
    days = int(request.args.get('days', 30))
    df = compute_indicators(ticker, days)
    # Simple rule: if SMA_20 > EMA_20 => BUY, else SELL
    latest = df.iloc[-1]
    if latest['SMA_20'] > latest['EMA_20']:
        signal = 'BUY'
    else:
        signal = 'SELL'
    return jsonify({'ticker': ticker, 'signal': signal, 'date': latest['time']})

@api_bp.route('/backtest/<ticker>', methods=['POST'])
def backtest_route(ticker):
    """Run a backtest over a date range.
    Expected JSON body: {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
    """
    payload = request.get_json() or {}
    start = payload.get('start')
    end = payload.get('end')
    if not start or not end:
        return jsonify({'error': 'start and end dates required'}), 400
    results = run_backtest(ticker, start, end)
    return jsonify(results)

# Register blueprint with the app (imported in create_app)
