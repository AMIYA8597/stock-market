import os

dirs = [
    "backend/nqml/features",
    "backend/nqml/labels",
    "backend/nqml/data",
    "backend/nqml/validation",
    "backend/nqml/models",
    "backend/nqml/calibration",
    "backend/nqml/stats",
    "backend/nqml/costs",
    "backend/nqml/gate",
    "backend/nqml/registry",
    "backend/nqml/regime",
    "backend/nqml/volatility",
    "backend/nqml/fusion",
    "backend/nqml/scoring",
    "backend/nqml/explain",
    "backend/nqml/forecast",
    "backend/nqml/llm"
]

for d in dirs:
    os.makedirs(d, exist_ok=True)
