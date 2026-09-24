with open("pyproject.toml", "r") as f:
    text = f.read()

text = text.replace('"statsmodels>=0.14.0",\n    "hmmlearn>=0.3.0",', '"statsmodels>=0.14.0",\n    "hmmlearn>=0.3.0",\n    "arch>=5.3.1",\n    "optuna>=3.5.0",\n    "openai>=1.12.0",\n    "google-generativeai>=0.4.0",')

with open("pyproject.toml", "w") as f:
    f.write(text)
