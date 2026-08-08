$ErrorActionPreference = "Stop"
python -m venv venv2
.\venv2\Scripts\Activate.ps1
pip install pip-audit
pip install -r requirements.txt
pip install -r requirements-core.txt
pip install -r requirements-ci.txt
pip install -r requirements-dev.txt
pip-audit
