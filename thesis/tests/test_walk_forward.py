import os
import sys
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.walk_forward import generate_walk_forward_splits

def test_walk_forward_overlap():
    dates = pd.date_range(start="2010-01-01", end="2026-01-01", freq="B")
    h_days = 20
    embargo = 20
    
    splits = generate_walk_forward_splits(dates, 2013, 2026, h_days, embargo)
    
    for s in splits:
        train_max = max(s['train'])
        calib_min = min(s['calib'])
        calib_max = max(s['calib'])
        test_min = min(s['test'])
        
        # Test timestamp must be > max train label end (train_max + h_days) + embargo
        # However, our splits define business days. So calendar days difference should be >= h_days + embargo.
        cal_diff_1 = (calib_min - train_max).days
        cal_diff_2 = (test_min - calib_max).days
        
        # In business days, 20 days is about 28 calendar days.
        # Our generator subtracted `embargo_days + h_days` index positions, which means exactly that many business days.
        assert cal_diff_1 >= (h_days + embargo), f"Train/Calib overlap violation: {cal_diff_1} < {h_days + embargo}"
        assert cal_diff_2 >= (h_days + embargo), f"Calib/Test overlap violation: {cal_diff_2} < {h_days + embargo}"

if __name__ == "__main__":
    test_walk_forward_overlap()
