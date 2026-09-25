import pandas as pd

def generate_walk_forward_splits(dates, test_year_start, test_year_end, h_days, embargo_days):
    """
    Generate purged and embargoed walk-forward splits based on years.
    dates: series or array of dates
    h_days: forecast horizon (purge overlap)
    embargo_days: embargo period (usually >= h_days)
    """
    df = pd.DataFrame({'date': pd.to_datetime(dates)}).sort_values('date').drop_duplicates().reset_index(drop=True)
    df['year'] = df['date'].dt.year
    
    splits = []
    
    for test_year in range(test_year_start, test_year_end + 1):
        # Test block
        test_mask = df['year'] == test_year
        if not test_mask.any():
            continue
            
        test_start_idx = df[test_mask].index[0]
        test_end_idx = df[test_mask].index[-1]
        
        # Calibration block: 1 year before test block, minus embargo and purge
        calib_year = test_year - 1
        calib_mask = df['year'] == calib_year
        if not calib_mask.any():
            continue
            
        # Calibration starts at beginning of calib_year
        calib_start_idx = df[calib_mask].index[0]
        # Calibration ends right before test_start_idx - embargo_days - h_days
        # But for simplicity, we just use the year boundary minus embargo+purge
        calib_end_idx_proposed = df[calib_mask].index[-1]
        calib_end_idx = min(calib_end_idx_proposed, test_start_idx - embargo_days - h_days - 1)
        
        if calib_end_idx <= calib_start_idx:
            continue
            
        # Train block: everything before calib block, minus embargo and purge
        train_start_idx = 0
        train_end_idx = calib_start_idx - embargo_days - h_days - 1
        
        if train_end_idx <= train_start_idx:
            continue
            
        splits.append({
            'test_year': test_year,
            'train': df.loc[train_start_idx:train_end_idx, 'date'].tolist(),
            'calib': df.loc[calib_start_idx:calib_end_idx, 'date'].tolist(),
            'test': df.loc[test_start_idx:test_end_idx, 'date'].tolist()
        })
        
    return splits

if __name__ == "__main__":
    dates = pd.date_range(start="2010-01-01", end="2026-01-01", freq="B")
    splits = generate_walk_forward_splits(dates, 2013, 2026, 5, 5)
    for s in splits:
        train_max = max(s['train'])
        calib_min = min(s['calib'])
        calib_max = max(s['calib'])
        test_min = min(s['test'])
        
        purge_1 = (calib_min - train_max).days
        purge_2 = (test_min - calib_max).days
        
        assert purge_1 >= 5, "Train/Calib overlap"
        assert purge_2 >= 5, "Calib/Test overlap"
        print(f"Test Year {s['test_year']}: Train until {train_max.date()}, Calib {calib_min.date()} to {calib_max.date()}, Test starts {test_min.date()}")
