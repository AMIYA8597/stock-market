import os

import pandas as pd

try:
    from neuralforecast.core import NeuralForecast
    from neuralforecast.models import NBEATS, Informer, PatchTST
except ImportError:
    NeuralForecast = None

try:
    from nixtla import NixtlaClient
except ImportError:
    NixtlaClient = None

class NeuralForecastWrapper:
    def __init__(self, model_type: str = "patchtst", input_size: int = 60, horizon: int = 5):
        self.model_type = model_type.lower()
        self.horizon = horizon
        self.input_size = input_size

        if NeuralForecast is None:
            raise ImportError("neuralforecast is not installed.")

        if self.model_type == "informer":
            m = Informer(h=horizon, input_size=input_size, max_steps=100)
        elif self.model_type == "nbeats":
            m = NBEATS(h=horizon, input_size=input_size, max_steps=100)
        elif self.model_type == "patchtst":
            m = PatchTST(h=horizon, input_size=input_size, max_steps=100)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        self.nf = NeuralForecast(models=[m], freq="1D")

    def fit(self, df: pd.DataFrame):
        # df must have columns: unique_id, ds, y
        self.nf.fit(df)

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.nf.predict(df)

class TimeGPTWrapper:
    def __init__(self, api_key: str = None):
        if NixtlaClient is None:
            raise ImportError("nixtla is not installed.")
        key = api_key or os.getenv("TIMEGPT_API_KEY", "dummy_key_for_offline")
        self.nixtla = NixtlaClient(api_key=key)

    def predict(self, df: pd.DataFrame, horizon: int = 5):
        # TimeGPT requires unique_id, ds, y
        try:
            return self.nixtla.forecast(df=df, h=horizon, freq="1D")
        except Exception as e:
            print(f"TimeGPT API Error (expected if dummy key): {e}")
            return pd.DataFrame()

