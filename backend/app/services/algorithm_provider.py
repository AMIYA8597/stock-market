
# Simple algorithm registry mapping identifiers to implementation import paths.
# This can be extended to load algorithms dynamically.
ALGORITHM_MAP: dict[str, str] = {
    "candlestick": "app.components.charts.LightweightCandlestickChart",
    "line": "app.components.charts.SimpleLineAreaChart",
    "ohlcv": "app.components.charts.OHLCVChart",
    "xgboost": "app.services.ml.fallback_model.FallbackModel",
    "ensemble": "app.services.intelligence_service",
    # Add more algorithms as needed.
}

def get_algorithm_path(name: str) -> str:
    """Return the import path for a given algorithm identifier.

    Raises:
        KeyError: If the algorithm is not registered.
    """
    if name not in ALGORITHM_MAP:
        raise KeyError(f"Algorithm '{name}' is not registered.")
    return ALGORITHM_MAP[name]

def list_algorithms() -> list[str]:
    """Return a list of all available algorithm identifiers."""
    return list(ALGORITHM_MAP.keys())
