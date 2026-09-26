with open('d:/work/stock-market/backend/tests/unit/test_prediction_engine_new.py', encoding='utf-8') as f:
    text = f.read()

text = text.replace('mock_tech.return_value = {"score": 0.5}', '')

with open('d:/work/stock-market/backend/tests/unit/test_prediction_engine_new.py', 'w', encoding='utf-8') as f:
    f.write(text)
