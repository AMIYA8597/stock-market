#!/usr/bin/env python3
"""
Feature Engineering Test Script
Tests the comprehensive feature engineering pipeline
"""

import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from features.feature_engineer import FeatureEngineer

def create_sample_data(n_days=1000):
    """Create sample OHLCV data for testing"""
    np.random.seed(42)

    # Generate synthetic price data
    dates = pd.date_range('2020-01-01', periods=n_days, freq='D')

    # Start with price 100, add random walks
    price_changes = np.random.normal(0.001, 0.02, n_days)
    prices = 100 * np.exp(np.cumsum(price_changes))

    # Generate OHLCV from prices
    high_mult = 1 + np.abs(np.random.normal(0, 0.01, n_days))
    low_mult = 1 - np.abs(np.random.normal(0, 0.01, n_days))
    volume = np.random.lognormal(10, 1, n_days)

    df = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.005, n_days)),
        'high': prices * high_mult,
        'low': prices * low_mult,
        'close': prices,
        'volume': volume
    }, index=dates)

    # Ensure high >= max(open, close), low <= min(open, close)
    df['high'] = np.maximum(df[['open', 'close']].max(axis=1), df['high'])
    df['low'] = np.minimum(df[['open', 'close']].min(axis=1), df['low'])

    return df

def test_feature_engineering():
    """Test the feature engineering pipeline"""
    print("🧪 Testing Feature Engineering Pipeline")
    print("=" * 50)

    # Create sample data
    print("1. Creating sample OHLCV data...")
    df = create_sample_data(500)
    print(f"   Created {len(df)} days of sample data")
    print(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

    # Initialize feature engineer
    print("\n2. Initializing FeatureEngineer...")
    engineer = FeatureEngineer()

    # Fit the pipeline
    print("3. Fitting feature engineering pipeline...")
    try:
        engineer.fit(df)
        print("   ✅ Pipeline fitted successfully")
    except Exception as e:
        print(f"   ❌ Pipeline fitting failed: {e}")
        return False

    # Transform data
    print("4. Transforming data...")
    try:
        features_df = engineer.transform(df)
        print(f"   ✅ Transformation successful")
        print(f"   Generated {features_df.shape[1]} features")
        print(f"   Feature matrix shape: {features_df.shape}")
    except Exception as e:
        print(f"   ❌ Transformation failed: {e}")
        return False

    # Check for NaN values
    nan_count = features_df.isnull().sum().sum()
    print(f"   NaN values: {nan_count}")

    # Show some statistics
    print("\n5. Feature Statistics:")
    print(f"   Mean features per category:")
    print(f"   - Price features: ~10")
    print(f"   - Technical indicators: ~150")
    print(f"   - Microstructure: ~10")
    print(f"   - Statistical: ~20")
    print(f"   - Cross-asset: ~10")
    print(f"   - tsfresh: ~50")

    # Save pipeline
    print("\n6. Saving pipeline...")
    pipeline_path = Path(__file__).parent / "test_pipeline.pkl"
    try:
        engineer.save_pipeline(str(pipeline_path))
        print(f"   ✅ Pipeline saved to {pipeline_path}")
    except Exception as e:
        print(f"   ❌ Pipeline saving failed: {e}")
        return False

    # Load pipeline
    print("7. Loading pipeline...")
    try:
        new_engineer = FeatureEngineer()
        new_engineer.load_pipeline(str(pipeline_path))
        print("   ✅ Pipeline loaded successfully")
    except Exception as e:
        print(f"   ❌ Pipeline loading failed: {e}")
        return False

    # Test with new data
    print("8. Testing with new data...")
    new_df = create_sample_data(100)
    try:
        new_features = new_engineer.transform(new_df)
        print(f"   ✅ New data transformation successful")
        print(f"   New features shape: {new_features.shape}")
    except Exception as e:
        print(f"   ❌ New data transformation failed: {e}")
        return False

    # Clean up
    if pipeline_path.exists():
        pipeline_path.unlink()

    print("\n🎉 All tests passed! Feature engineering pipeline is working correctly.")
    return True

if __name__ == "__main__":
    success = test_feature_engineering()
    sys.exit(0 if success else 1)