"""CLI runner for ML training pipeline."""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from pipelines.training_pipeline import main

if __name__ == "__main__":
    main()
