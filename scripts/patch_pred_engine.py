import re

file_path = 'backend/app/services/prediction_engine.py'
with open(file_path, 'r', encoding='utf-8') as f:
    code = f.read()

# Replace xgb fallback
code = code.replace('xgb_score = 0.0', 'xgb_score = None')
code = code.replace('xgb_confidence = 0.5', 'xgb_confidence = None')
code = code.replace('xgb_base_value = 0.5', 'xgb_base_value = None')

# Replace lstm fallback
code = code.replace('lstm_score = 0.0', 'lstm_score = None')
code = code.replace('lstm_confidence = 0.5', 'lstm_confidence = None')

# Replace tft fallback
code = code.replace('tft_score = 0.0', 'tft_score = None')
code = code.replace('tft_confidence = 0.5', 'tft_confidence = None')
code = code.replace('tft_p10, tft_p50, tft_p90 = -0.015, 0.002, 0.015', 'tft_p10, tft_p50, tft_p90 = None, None, None')

# Replace gnn fallback
code = code.replace('gnn_score = 0.0', 'gnn_score = None')
code = code.replace('gnn_confidence = 0.5', 'gnn_confidence = None')

# Remove yfinance from GNN
gnn_block = r'''        if _INDEX_DATA_CACHE is None or _INDEX_DATA_CACHE\.empty:
            try:
                import yfinance as yf

                index_ticker = yf\.Ticker\("\^NSEI"\)
                _INDEX_DATA_CACHE = index_ticker\.history\(period="2y", interval="1d"\)
                _INDEX_DATA_CACHE\.index = pd\.DatetimeIndex\(_INDEX_DATA_CACHE\.index\)\.tz_localize\(
                    None
                \)
            except Exception as index_err:
                logger\.warning\(f"Could not fetch index data for GNN: \{index_err\}"\)'''
code = re.sub(gnn_block, '        if _INDEX_DATA_CACHE is None or _INDEX_DATA_CACHE.empty:\n            raise ValueError("GNN requires canonical index data, yfinance is forbidden.")', code)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(code)
print('Patched fallbacks in prediction_engine.py')
