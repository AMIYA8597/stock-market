import sys
import re

with open('backend/app/services/prediction_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace standardize_df_columns logic
new_func = '''\
class FeatureUnavailableError(Exception):
    pass

def standardize_df_columns(df: pd.DataFrame, expected_features: list[str]) -> pd.DataFrame:
    df_copy = df.copy()

    # Drop any duplicate columns first
    df_copy = df_copy.loc[:, ~df_copy.columns.duplicated()]

    # We select EXACTLY expected_features in order.
    # Missing or NaN -> FeatureUnavailableError.
    
    missing = [exp for exp in expected_features if exp not in df_copy.columns]
    if missing:
        raise FeatureUnavailableError(f"Missing expected features: {missing}")
        
    df_copy = df_copy[expected_features]
    
    # Check for NaNs
    if df_copy.isna().any().any():
        raise FeatureUnavailableError("Features contain NaNs")
        
    return df_copy
'''

content = re.sub(
    r'def standardize_df_columns\(df: pd\.DataFrame, expected_features: list\[str\]\) -> pd\.DataFrame:.*?return df_copy\n',
    new_func,
    content,
    flags=re.DOTALL
)

with open('backend/app/services/prediction_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
