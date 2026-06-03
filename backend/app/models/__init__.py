"""
SQLAlchemy ORM models.

All models are imported here for Alembic auto-detection of schema changes.
Models use SQLAlchemy 2.0 with async/await support.
"""

# User & Authentication
# Alerts & Monitoring
from app.models.alert import Alert  # noqa: F401

# Asset Metadata
from app.models.asset import Symbol  # noqa: F401
from app.models.auth_token import PasswordResetToken, RefreshSession  # noqa: F401

# Backtest & Analysis
from app.models.backtest import BacktestJob  # noqa: F401
from app.models.blog import BlogPost  # noqa: F401
from app.models.email_job import EmailJob  # noqa: F401
from app.models.feature_vectors import FeatureVector  # noqa: F401
from app.models.notification import Notification  # noqa: F401

# Time-Series Data (OHLCV & Features)
from app.models.ohlcv import OHLCV  # noqa: F401
from app.models.payment import PaymentTransaction  # noqa: F401

# User Portfolio & Transactions
from app.models.portfolio import PortfolioHolding  # noqa: F401
from app.models.journal import TradeJournal  # noqa: F401

# Model Predictions & Signals
from app.models.prediction import MLPrediction  # noqa: F401

# Market State
from app.models.regime_states import RegimeState  # noqa: F401

# News & Sentiment
from app.models.sentiment import NewsSentiment  # noqa: F401
from app.models.signal import EnsembleSignal  # noqa: F401
from app.models.transactions import Transaction  # noqa: F401
from app.models.user import User  # noqa: F401
