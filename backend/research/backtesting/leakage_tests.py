import pandas as pd
import numpy as np
import pytest
import re
from pathlib import Path

def test_truncation_invariance(bars, feature_fn):
    """
    A feature computed on bars[:T] must exactly match the feature computed on bars, evaluated at T.
    """
    res_full = feature_fn(bars)
    
    # Pick 3 random cut points
    cut_indices = np.random.choice(range(50, len(bars)), 3, replace=False)
    
    for cut_idx in cut_indices:
        bars_cut = bars.iloc[:cut_idx]
        res_cut = feature_fn(bars_cut)
        
        pd.testing.assert_series_equal(
            res_full.iloc[:cut_idx], 
            res_cut,
            check_dtype=False,
            check_exact=False,
            rtol=1e-5,
            atol=1e-8,
            obj=f"Truncation invariance failed at {cut_idx}"
        )

def test_static_scan_no_leakage_methods():
    """
    Scan source code for forbidden methods that look into the future or leak global state.
    """
    features_dir = Path(__file__).parent.parent / "feature_engineering"
    
    forbidden_patterns = [
        r"shift\(\s*-[1-9]", # negative shift
        r"center\s*=\s*True",
        r"\.bfill\(",
        r"\.backfill\(",
        r"iloc\[.+?\+",      # iloc[i + 1]
        r"\.expanding\("
    ]
    
    for py_file in features_dir.rglob("*.py"):
        with open(py_file, "r", encoding="utf-8") as f:
            content = f.read()
            for pattern in forbidden_patterns:
                match = re.search(pattern, content)
                assert not match, f"Leakage detected in {py_file.name}: {match.group(0)}"
