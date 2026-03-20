"""End-to-end model training pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from research.models.hmm_garch import HMMGarchTrainer


@dataclass(slots=True)
class TrainingSummary:
    hmm_checkpoint: str
    n_samples: int
    final_state: int


def run_training_pipeline(returns: np.ndarray, symbol: str = "NIFTY") -> TrainingSummary:
    """Train the HMM-GARCH stage and return checkpoint metadata."""
    trainer = HMMGarchTrainer()
    train_result, _ = trainer.train(returns=returns, symbol=symbol)
    return TrainingSummary(
        hmm_checkpoint=train_result.checkpoint_path,
        n_samples=train_result.n_samples,
        final_state=train_result.final_state,
    )
