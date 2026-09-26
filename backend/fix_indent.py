import re

with open('d:/work/stock-market/backend/tests/unit/test_training_pipeline_new.py', encoding='utf-8') as f:
    text = f.read()

# Fix the IndentationError
def fix_indent(match):
    indent = match.group(1)
    return f'{indent}with patch.object(pipeline, "_fetch_ohlcv_data", return_value=dummy_data if "dummy_data" in locals() else pd.DataFrame()):\n{indent}    results = await pipeline.run()'

text = re.sub(r'([ \t]*)with patch\.object\(pipeline, "_fetch_ohlcv_data", return_value=dummy_data if "dummy_data" in locals\(\) else pd\.DataFrame\(\)\):\n[ \t]*results = await pipeline\.run\(\)', fix_indent, text)

with open('d:/work/stock-market/backend/tests/unit/test_training_pipeline_new.py', 'w', encoding='utf-8') as f:
    f.write(text)
