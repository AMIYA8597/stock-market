import numpy as np
from scipy.stats import binom

def learn_then_test_selection(p_calib, y_calib, alpha=0.40, delta=0.10):
    """
    Learn-then-Test fixed-sequence binomial test for selective prediction.
    p_calib: calibrated probabilities on the calibration set
    y_calib: true labels
    alpha: target maximum selective risk (e.g. 0.40 means minimum precision 60%)
    delta: significance level (e.g. 0.10)
    
    Returns: threshold tau*
    """
    confidences = np.maximum(p_calib, 1 - p_calib)
    
    # Sort thresholds in decreasing order
    taus = np.sort(np.unique(confidences))[::-1]
    
    tau_star = 1.0 # default to max confidence if nothing passes
    
    for tau in taus:
        # subset predictions above threshold
        mask = confidences >= tau
        if np.sum(mask) == 0:
            continue
            
        n_selected = np.sum(mask)
        
        # Predict 1 if p >= 0.5 else 0
        preds = (p_calib[mask] >= 0.5).astype(int)
        errors = np.sum(preds != y_calib[mask])
        
        # Binomial test: H_0: R(tau) > alpha
        # p-value = P(Bin(n, alpha) <= errors)
        p_val = binom.cdf(errors, n_selected, alpha)
        
        if p_val <= delta:
            # Reject null hypothesis, accept this threshold
            tau_star = tau
        else:
            # Fixed-sequence testing stops at the first failure to reject
            break
            
    return tau_star

if __name__ == "__main__":
    # Mock
    p_calib = np.random.uniform(0.3, 0.7, 1000)
    y_calib = (p_calib + np.random.normal(0, 0.2, 1000) > 0.5).astype(int)
    tau = learn_then_test_selection(p_calib, y_calib, alpha=0.45, delta=0.1)
    print(f"Selected tau*: {tau:.4f}")
