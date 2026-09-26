import re

with open('d:/work/stock-market/backend/app/services/prediction_engine.py', encoding='utf-8') as f:
    text = f.read()

# Fix detect_regime
def replace_detect_regime(match):
    return '''def detect_regime(df: pd.DataFrame) -> dict[str, Any]:
    if len(df) < 60:
        raise ValueError("Insufficient data for HMM-GARCH regime detection.")

    try:
        from research.models.hmm_garch.inference import InferenceEngine

        ohlcv_data = df[["open", "high", "low", "close", "volume"]].astype(float).values

        symbol = df.attrs.get("symbol", "DEFAULT")
        if symbol in _HMM_CACHE:
            engine = _HMM_CACHE[symbol]
            train_flag = False
        else:
            engine = InferenceEngine()
            train_flag = True

        res = engine.predict(ohlcv_data, train=train_flag)
        if train_flag:
            _HMM_CACHE[symbol] = engine

        current_state = res.current_state
        probs = res.state_probs

        state_to_regime = {0: "BULL", 1: "BEAR", 2: "SIDEWAYS", 3: "CRISIS"}
        regime = state_to_regime.get(current_state, "SIDEWAYS")
        bull_prob = float(probs[0])
        bear_prob = float(probs[1])
        regime_confidence = float(probs[current_state])
        hmm_used = True

        conditional_vol = float(res.conditional_vol)
        forecast_5d = res.vol_forecast_5d
        forecast_21d = res.vol_forecast_21d
        tm = engine.get_transition_matrix()
        transition_matrix = tm.tolist() if tm is not None else None

        return {
            "regime": regime,
            "bull_prob": bull_prob,
            "bear_prob": bear_prob,
            "regime_confidence": regime_confidence,
            "hmm_used": hmm_used,
            "conditional_vol": conditional_vol,
            "vol_forecast_5d": float(forecast_5d[-1]) if len(forecast_5d) > 0 else conditional_vol,
            "vol_forecast_21d": float(forecast_21d[-1])
            if len(forecast_21d) > 0
            else conditional_vol,
            "transition_matrix": transition_matrix,
        }
    except Exception as e:
        logger.error(f"Real HMM-GARCH solver failed: {e}")
        raise ValueError(f"Regime detection failed: {e}")'''

text = re.sub(r'def detect_regime\(df: pd\.DataFrame\) -> dict\[str, Any\]:.*?(?=\n\n# -{75})', replace_detect_regime, text, flags=re.DOTALL)

with open('d:/work/stock-market/backend/app/services/prediction_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
