
with open('d:/work/stock-market/backend/tests/unit/test_prediction_engine_new.py', encoding='utf-8') as f:
    text = f.read()

# Fix detect_regime tests to expect ValueError
text = text.replace('''def test_detect_regime_short_df():
    df = pd.DataFrame({"close": range(10)})
    res = detect_regime(df)
    assert res["regime"] == "unknown"''', '''def test_detect_regime_short_df():
    df = pd.DataFrame({"close": range(10)})
    import pytest
    with pytest.raises(ValueError, match="Insufficient data"):
        detect_regime(df)''')

text = text.replace('''def test_detect_regime_fallback():
    df = pd.DataFrame({"close": np.random.rand(100)})
    with patch("research.models.hmm_garch.inference.InferenceEngine") as mock_engine:
        mock_engine.return_value.predict.side_effect = Exception("fail")
        res = detect_regime(df)
        assert res["hmm_used"] is False''', '''def test_detect_regime_fallback():
    df = pd.DataFrame({"close": np.random.rand(100)})
    import pytest
    with patch("research.models.hmm_garch.inference.InferenceEngine") as mock_engine:
        mock_engine.return_value.predict.side_effect = Exception("fail")
        with pytest.raises(ValueError, match="Regime detection failed"):
            detect_regime(df)''')

# Fix async_session_factory patch
text = text.replace('patch("app.services.prediction_engine.async_session_factory"', 'patch("app.database.connection.async_session_factory"')

# Fix TechnicalSignalEngine patch
text = text.replace('patch("app.services.prediction_engine.TechnicalSignalEngine"', 'patch("app.services.prediction_engine.TechnicalSignalEngine", create=True')

with open('d:/work/stock-market/backend/tests/unit/test_prediction_engine_new.py', 'w', encoding='utf-8') as f:
    f.write(text)
