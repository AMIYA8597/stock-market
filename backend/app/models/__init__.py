"""
SQLAlchemy ORM models.

All models are imported here so Alembic can auto-detect schema changes.
"""

from app.models.user import User  # noqa: F401
from app.models.asset import Asset  # noqa: F401
from app.models.ohlcv import OHLCVData  # noqa: F401
from app.models.portfolio import Portfolio, PortfolioHolding  # noqa: F401
from app.models.prediction import Prediction  # noqa: F401
from app.models.signal import TradingSignal  # noqa: F401
from app.models.backtest import BacktestResult  # noqa: F401
from app.models.alert import Alert  # noqa: F401
from app.models.sentiment import NewsSentiment  # noqa: F401
