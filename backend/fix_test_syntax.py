
with open('d:/work/stock-market/backend/tests/unit/test_prediction_engine_new.py', encoding='utf-8') as f:
    text = f.read()

# Fix syntax error left by previous replacement
text = text.replace(r' \ as mock_tech, \\', '')
text = text.replace(r' \ as mock_tech,', '')
text = text.replace(' as mock_tech, \\', '')

with open('d:/work/stock-market/backend/tests/unit/test_prediction_engine_new.py', 'w', encoding='utf-8') as f:
    f.write(text)
