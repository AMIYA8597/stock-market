import re

with open("app/services/prediction_engine.py", "r") as f:
    code = f.read()

new_code = re.sub(r'from app\.services\.signal_engine import TechnicalSignalEngine\n?', '', code)

with open("app/services/prediction_engine.py", "w") as f:
    f.write(new_code)
