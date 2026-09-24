import re

with open("tests/unit/test_prediction_engine_new.py", "r") as f:
    code = f.read()

code = re.sub(r"@patch\('app\.services\.prediction_engine\.TechnicalSignalEngine\.generate_signal'\)\n", '', code)
code = re.sub(r', mock_generate_signal', '', code)
code = re.sub(r'mock_generate_signal\.return_value = \{[^\}]+\}\n', '', code)
code = re.sub(r'mock_generate_signal\.assert_called_once\(\)\n', '', code)
code = re.sub(r'mock_generate_signal,\s*', '', code)
code = re.sub(r'mock_generate_signal\.return_value = \{.*?\}', '', code, flags=re.DOTALL)

with open("tests/unit/test_prediction_engine_new.py", "w") as f:
    f.write(code)
