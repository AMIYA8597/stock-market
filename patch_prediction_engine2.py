import re

with open('backend/app/services/prediction_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. TFT quantiles -> null with status untrained
content = re.sub(
    r'tft_p10, tft_p50, tft_p90 = -0\.015, 0\.002, 0\.015',
    'tft_p10, tft_p50, tft_p90 = None, None, None',
    content
)

# 2. embedding_norm -> removed
content = re.sub(
    r'"embedding_norm": 1\.0,\s*',
    '',
    content
)

# 3. gnn_status -> heuristic and renamed correlation_contagion
content = re.sub(
    r'gnn_status = "untrained"',
    'gnn_status = "heuristic"',
    content
)
content = re.sub(
    r'gnn_status = "unavailable"',
    'gnn_status = "heuristic"',
    content
)
content = re.sub(
    r'"gnn": \{',
    '"correlation_contagion": {',
    content
)
content = re.sub(
    r'"gnn":',
    '"correlation_contagion":',
    content
)

# 4. model_status "trained" only when an ML directional model contributed
content = re.sub(
    r'any_trained = any\(status == "trained" for status in model_statuses\.values\(\)\)',
    'any_trained = model_statuses.get("xgboost") == "trained" or model_statuses.get("lstm_attention") == "trained"',
    content
)

# 5. Kelly returns null without measured stats
kelly_func = '''def compute_kelly_fraction(symbol: str, signal: float, confidence: float) -> float | None:
    stats_path = MODEL_DIR / f"xgboost_backtest_{symbol.upper()}.json"
    if not stats_path.exists():
        return None
    try:
        with open(stats_path) as f:
            stats = json.load(f)
        p = stats.get("win_rate")
        b = stats.get("payoff_ratio")
        if p is None or b is None:
            return None
    except Exception as e:
        logger.warning(f"Failed to load backtest metrics for Kelly: {e}")
        return None

    q = 1.0 - p
    f_star = (p * b - q) / b if b > 0 else 0
    f_half = f_star / 2.0
    f_scaled = f_half * confidence * abs(signal)
    return float(np.clip(f_scaled, 0.0, 0.25))'''
content = re.sub(
    r'def compute_kelly_fraction\(.*?\).*?return float\(np\.clip\(f_scaled, 0\.0, 0\.25\)\)',
    kelly_func,
    content,
    flags=re.DOTALL
)

# 6. LLM call removal
content = re.sub(
    r'# Generate plain-language reasoning via LLM Engine.*?reasons = \[llm_reason\]\s*except Exception as re_err:\s*logger\.warning\(f"Failed to generate plain-language reasoning message: \{re_err\}"\)',
    'reasons = []',
    content,
    flags=re.DOTALL
)

# 7. Regime labels
content = re.sub(
    r'state_to_regime = \{0: "BULL", 1: "BEAR", 2: "SIDEWAYS", 3: "CRISIS"\}\s*regime = state_to_regime\.get\(current_state, "SIDEWAYS"\)',
    'regime = "unknown"\n        regime_source = "pending_refactor"',
    content
)
content = re.sub(
    r'regime, bull_prob, bear_prob = "BULL", 0\.75, 0\.25\s*elif sharpe_proxy < -0\.5:\s*regime, bull_prob, bear_prob = "BEAR", 0\.25, 0\.75\s*else:\s*regime, bull_prob, bear_prob = "SIDEWAYS", 0\.5, 0\.5',
    'regime, bull_prob, bear_prob = "unknown", 0.5, 0.5\n        regime_source = "pending_refactor"',
    content
)
content = re.sub(
    r'"hmm_used": hmm_used,',
    '"hmm_used": hmm_used,\n            "regime_source": "pending_refactor",',
    content
)
content = re.sub(
    r'"hmm_used": False,',
    '"hmm_used": False,\n            "regime_source": "pending_refactor",',
    content
)
content = re.sub(
    r'"regime": \{\s*"regime": regime_info\["regime"\],\s*"bull_prob": regime_info\["bull_prob"\],\s*"bear_prob": regime_info\["bear_prob"\],\s*"regime_confidence": regime_info\["regime_confidence"\],\s*"hmm_used": True,',
    '"regime": {\\n            "regime": regime_info["regime"],\\n            "bull_prob": regime_info["bull_prob"],\\n            "bear_prob": regime_info["bear_prob"],\\n            "regime_confidence": regime_info["regime_confidence"],\\n            "hmm_used": regime_info.get("hmm_used", False),\\n            "regime_source": regime_info.get("regime_source", "pending_refactor"),',
    content
)

# forecast_prices and forecast_multi_horizon
forecast_prices_func = '''def forecast_prices(df: pd.DataFrame, horizons: list[int]) -> list[dict[str, Any]]:
    return []'''
content = re.sub(
    r'def forecast_prices\(df: pd\.DataFrame, horizons: list\[int\]\) -> list\[dict\[str, Any\]\]:.*?return output',
    forecast_prices_func,
    content,
    flags=re.DOTALL
)

forecast_multi_func = '''async def forecast_multi_horizon(symbol: str, horizon_labels: list[str]) -> dict[str, Any]:
    from fastapi import HTTPException
    raise HTTPException(status_code=503, detail={"code": "FORECAST_NOT_AVAILABLE"})'''
content = re.sub(
    r'async def forecast_multi_horizon\(symbol: str, horizon_labels: list\[str\]\) -> dict\[str, Any\]:.*?return \{.*?\}',
    forecast_multi_func,
    content,
    flags=re.DOTALL
)

# Remove _fit_and_forecast just in case
content = re.sub(
    r'def _fit_and_forecast\(closes: np\.ndarray, steps: int\) -> tuple\[np\.ndarray, np\.ndarray\]:.*?return pred_mean, pred_ci',
    '',
    content,
    flags=re.DOTALL
)

with open('backend/app/services/prediction_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
