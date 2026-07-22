import re

text = open('pyproject.toml', encoding='utf-8').read()

text = re.sub(r'"pandas==2\.1\.4"', '"pandas>=2.1.4",\n    "pandas-ta"', text)
text = re.sub(r'"scipy==1\.11\.4"', '"scipy>=1.11.4"', text)
text = re.sub(r'"matplotlib==3\.8\.2"', '"matplotlib>=3.8.2"', text)

text = re.sub(r'"yfinance==0\.2\.32"', '"yfinance==0.2.32",\n    "alpha_vantage==2.3.1",\n    "ccxt==4.1.48",\n    "pandas-datareader==0.10.0",\n    "upstox-python-sdk",\n    "smartapi-python"', text)
text = re.sub(r'\s*"alpha-vantage==2\.3\.1",\n\s*"fred-api==3\.2\.0",\n\s*"newsapi==1\.1\.0",', '', text)

text = re.sub(r'"cryptography==41\.0\.7"', '"cryptography>=41.0.7",\n    "pyotp>=2.9.0",\n    "email-validator>=2.1.0",\n    "razorpay==1.4.1",\n    "setuptools"', text)

text = re.sub(r'"structlog==23\.3\.0"', '"structlog==23.3.0",\n    "loguru",\n    "slowapi"', text)
text = re.sub(r'"xgboost==2\.0\.3"', '"xgboost>=2.0.3",\n    "lightgbm>=4.0.0"', text)

with open('pyproject.toml', 'w', encoding='utf-8') as f:
    f.write(text)
