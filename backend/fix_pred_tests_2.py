import re

with open('d:/work/stock-market/backend/tests/unit/test_prediction_engine_new.py', encoding='utf-8') as f:
    text = f.read()

# Fix short df
text = re.sub(
    r'def test_detect_regime_short_df\(\):\n\s+df = pd\.DataFrame\(.*?\)\n\s+res = detect_regime\(df\)\n\s+assert res\["regime"\] == "unknown"',
    'def test_detect_regime_short_df():\n    df = pd.DataFrame({"close": [1, 2, 3]})\n    import pytest\n    with pytest.raises(ValueError, match="Insufficient data"):\n        detect_regime(df)',
    text
)

# Fix fallback
text = re.sub(
    r'def test_detect_regime_fallback\(\):\n\s+df = pd\.DataFrame\(.*?\)\n\s+with patch\("research\.models\.hmm_garch\.inference\.InferenceEngine"\) as mock_engine:\n\s+mock_engine\.return_value\.predict\.side_effect = Exception\("fail"\)\n\s+res = detect_regime\(df\)\n\s+assert res\["hmm_used"\] is False',
    'def test_detect_regime_fallback():\n    df = pd.DataFrame({"close": [1]*100})\n    import pytest\n    with patch("research.models.hmm_garch.inference.InferenceEngine") as mock_engine:\n        mock_engine.return_value.predict.side_effect = Exception("fail")\n        with pytest.raises(ValueError, match="Regime detection failed"):\n            detect_regime(df)',
    text
)

# Remove TechnicalSignalEngine patches entirely
text = re.sub(r'\s*patch\("app\.services\.prediction_engine\.TechnicalSignalEngine[^"]*"\)[,]?', '', text)
text = re.sub(r'\s*patch\("app\.services\.prediction_engine\.TechnicalSignalEngine[^"]*"[^)]*\)\s*as\s*mock_tech[,]', '', text)


with open('d:/work/stock-market/backend/tests/unit/test_prediction_engine_new.py', 'w', encoding='utf-8') as f:
    f.write(text)
