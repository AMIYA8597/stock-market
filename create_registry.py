import sys

content = '''\
\"\"\"
NeuroQuant ML Feature Registry
\"\"\"

import hashlib
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

import pandas as pd


@dataclass
class FeatureMeta:
    name: str
    family: str
    params: Dict[str, Any]
    warmup: int
    dtype: str
    func: Callable
    code_sha: str


_FEATURE_REGISTRY: Dict[str, FeatureMeta] = {}


def feature(name: str, family: str, params: Dict[str, Any], warmup: int, dtype: str = "float32"):
    \"\"\"Decorator to register a pure causal feature function.\"\"\"
    def decorator(func: Callable):
        source = inspect.getsource(func)
        code_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]
        
        meta = FeatureMeta(
            name=name,
            family=family,
            params=params,
            warmup=warmup,
            dtype=dtype,
            func=func,
            code_sha=code_sha
        )
        _FEATURE_REGISTRY[name] = meta
        return func
    return decorator


def list_features(feature_set_id: str = None) -> List[str]:
    \"\"\"List all registered feature names, optionally filtered by feature set.\"\"\"
    # If a feature set is requested, and we have sets defined, filter.
    # Currently we just return all features if fs_v1 is requested.
    return list(_FEATURE_REGISTRY.keys())


def build_features(bars: pd.DataFrame, feature_set_id: str) -> pd.DataFrame:
    \"\"\"
    Compute features over OHLCV bars.
    bars must have columns: open, high, low, close, volume.
    Returns a DataFrame containing only the computed features, aligned to dates.
    \"\"\"
    features_df = pd.DataFrame(index=bars.index)
    
    # Sort features by name for determinism
    for name in sorted(_FEATURE_REGISTRY.keys()):
        meta = _FEATURE_REGISTRY[name]
        
        # Compute feature
        result = meta.func(bars)
        
        # Ensure it is a Series or DataFrame that aligns to the index
        if isinstance(result, pd.Series):
            features_df[name] = result.astype(meta.dtype)
        elif isinstance(result, pd.DataFrame):
            for col in result.columns:
                features_df[col] = result[col].astype(meta.dtype)
                
    return features_df
'''

with open('backend/nqml/features/registry.py', 'w', encoding='utf-8') as f:
    f.write(content)
