import numpy as np
from scipy.stats import binomtest
from sklearn.metrics import accuracy_score, matthews_corrcoef, roc_auc_score, brier_score_loss

def evaluate_predictions(y_true, y_pred, y_prob=None):
    acc = accuracy_score(y_true, y_pred)
    n = len(y_true)
    
    # Binomial test against 0.5
    test = binomtest(int(acc * n), n, 0.5, alternative='greater')
    p_val = test.pvalue
    ci_low, ci_high = test.proportion_ci(confidence_level=0.95)
    
    # MCC
    mcc = matthews_corrcoef(y_true, y_pred)
    
    # AUC and Brier
    if y_prob is not None:
        try:
            auc = roc_auc_score(y_true, y_prob)
            brier = brier_score_loss(y_true, y_prob)
        except ValueError:
            auc = 0.5
            brier = 0.25
    else:
        auc = np.nan
        brier = np.nan
        
    return {
        "accuracy": acc,
        "ci_lower": ci_low,
        "ci_upper": ci_high,
        "p_value": p_val,
        "mcc": mcc,
        "auc": auc,
        "brier": brier,
        "n_samples": n
    }
