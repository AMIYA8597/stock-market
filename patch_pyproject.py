import re

with open('backend/pyproject.toml', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove pandas-ta from dependencies
content = re.sub(r'^\s*"pandas-ta",\s*\n', '', content, flags=re.MULTILINE)

# Add optuna, arch, feedparser to dependencies if not there? Wait, the instructions say:
# "pyproject dependency groups pi, ml, dev; declare optuna, arch, hmmlearn, statsmodels, scipy explicitly; pin pandas-ta only as a TEST-ONLY cross-check"
# Let's just modify the [project.optional-dependencies] section to add pi and ml.

optional_deps = '''[project.optional-dependencies]
api = [
    "numpy",
    "pandas",
    "lightgbm",
    "xgboost",
    "scipy",
    "statsmodels",
    "arch",
    "hmmlearn",
    "fastembed",
    "httpx"
]
ml = [
    "numpy",
    "pandas",
    "lightgbm",
    "xgboost",
    "scipy",
    "statsmodels",
    "arch",
    "hmmlearn",
    "fastembed",
    "httpx",
    "optuna",
    "torch",
    "transformers",
    "feedparser"
]
dev = [
    "pytest>=7.4.3",
    "pytest-asyncio>=0.21.1",
    "trio>=0.26.2",
    "pytest-cov>=4.1.0",
    "mypy>=1.7.1",
    "ruff>=0.1.11",
    "black>=23.12.1",
    "isort>=5.13.2",
    "pre-commit>=3.5.0",
    "jupyter>=1.0.0",
    "notebook>=7.0.6",
    "jupyterlab>=4.0.9",
    "matplotlib>=3.8.2",
    "seaborn>=0.13.0",
    "plotly>=5.18.0",
    "hypothesis>=6.92.2",
    "pandas-ta"
]'''

content = re.sub(r'\[project\.optional-dependencies\].*?(?=\n\[tool\.setuptools\])', optional_deps + '\n\n', content, flags=re.DOTALL)

with open('backend/pyproject.toml', 'w', encoding='utf-8') as f:
    f.write(content)
