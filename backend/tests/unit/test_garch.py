from __future__ import annotations

import numpy as np
from research.models.hmm_garch.garch import fit_garch_11, garch_conditional_variance, GarchParams

def test_garch_fit_and_variance() -> None:
    np.random.seed(42)
    n_samples = 100
    eps = np.random.normal(0, 0.015, n_samples)
    
    # Fit GARCH model
    params = fit_garch_11(eps)
    
    assert isinstance(params, GarchParams)
    assert params.omega > 0
    assert params.alpha >= 0
    assert params.beta >= 0
    
    # Compute conditional variance
    sig2 = garch_conditional_variance(eps, params)
    assert len(sig2) == n_samples
    assert np.all(sig2 > 0)
