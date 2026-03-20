"""Training orchestration for HMM-GARCH regime model."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from research.models.hmm_garch.regime_detector import RegimeDetectionResult, detect_regime


@dataclass(slots=True)
class TrainResult:
    n_samples: int
    final_state: int
    mean_conditional_vol: float
    checkpoint_path: str


class HMMGarchTrainer:
    """Fit HMM-GARCH pipeline and persist checkpoint artifacts."""

    def __init__(self, checkpoint_dir: str | Path = "data/models/hmm_garch") -> None:
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def train(self, returns: np.ndarray, symbol: str = "NIFTY") -> tuple[TrainResult, RegimeDetectionResult]:
        """Train on return series and persist serialized state."""
        result = detect_regime(returns)

        checkpoint = {
            "symbol": symbol,
            "n_samples": int(len(returns)),
            "states": result.states.tolist(),
            "posterior_probs": result.posterior_probs.tolist(),
            "conditional_vol": result.conditional_vol.tolist(),
            "forecast_5d": result.forecast_5d.tolist(),
            "forecast_21d": result.forecast_21d.tolist(),
            "state_garch_params": {str(k): asdict(v) for k, v in result.state_garch_params.items()},
        }

        path = self.checkpoint_dir / f"{symbol.lower()}_hmm_garch.json"
        path.write_text(json.dumps(checkpoint, indent=2), encoding="utf-8")

        train_result = TrainResult(
            n_samples=int(len(returns)),
            final_state=int(result.states[-1]),
            mean_conditional_vol=float(np.mean(result.conditional_vol)),
            checkpoint_path=str(path),
        )
        return train_result, result
