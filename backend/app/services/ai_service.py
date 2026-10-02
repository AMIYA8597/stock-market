"""AI service – routes calls to the PredictionEngine.

Train / predict wrappers used by app.api.v1.ai and app.services.signals_service.
If the underlying PredictionEngine is unavailable (models not trained yet), raises
ServiceUnavailableError so callers can surface a clean 503 instead of an invented stub.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ServiceUnavailableError(RuntimeError):
    """Raised when the ML engine is not ready (models not trained)."""


async def train_model(db: Any) -> None:  # noqa: ANN401
    """Launch training for XGBoost and LSTM models on top Nifty 50 symbols.

    Trains from real OHLCV data in the DB or via yfinance fallback.
    Saves .pkl artifacts to the models/ directory.
    """
    try:
        from app.services.prediction_engine import MODEL_DIR, build_ensemble_signal
        from app.services.market_data_service import MarketDataService

        import pandas as pd

        symbols_to_train = MarketDataService.NSE_NIFTY50[:10]
        trained = 0

        for symbol in symbols_to_train:
            try:
                bars = await MarketDataService.get_history(symbol, "1d", "2y")
                if not bars or len(bars) < 100:
                    logger.warning(f"Skipping {symbol}: insufficient data ({len(bars) if bars else 0} bars)")
                    continue

                df = pd.DataFrame(bars)
                if df.empty:
                    continue

                result = await build_ensemble_signal(symbol, df)
                if result:
                    trained += 1
                    logger.info(f"Trained ensemble for {symbol}: direction={result.get('direction')}")
            except Exception as e:
                logger.warning(f"Training failed for {symbol}: {e}")
                continue

        logger.info(f"Training complete: {trained}/{len(symbols_to_train)} symbols processed")

    except ImportError as exc:
        raise ServiceUnavailableError(
            "PredictionEngine module is unavailable – required dependencies not installed."
        ) from exc


async def predict(db: Any, payload: dict[str, Any]) -> dict[str, Any]:  # noqa: ANN401
    """Run inference via get_full_prediction.

    Returns a dictionary with: symbol, direction, confidence, ensemble details.
    Raises ServiceUnavailableError when prediction fails.
    """
    symbol: str = str(payload.get("symbol", "")).upper()

    try:
        from app.services.prediction_engine import get_full_prediction

        result = await get_full_prediction(symbol, bypass_cache=True)
        if not result:
            raise ServiceUnavailableError(
                f"No prediction could be generated for {symbol}. Ensure market data is available."
            )
        return result
    except ImportError as exc:
        raise ServiceUnavailableError(
            f"PredictionEngine unavailable – dependencies not installed for {symbol or 'unknown'}."
        ) from exc
    except FileNotFoundError as exc:
        raise ServiceUnavailableError(
            f"No trained model found for symbol '{symbol}'. Run the training pipeline first."
        ) from exc
