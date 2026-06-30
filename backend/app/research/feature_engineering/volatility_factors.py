import numpy as np
import pandas as pd
import pandas_ta as ta
from research.models.hmm_garch.garch import fit_garch_11, garch_conditional_variance, GarchParams

class VolatilityFactorsBuilder:
    """Computes volatility-derived features, ATR, Bollinger Bands, and GARCH forecasts."""

    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df.copy()

        # Work on a copy sorted by index/time
        data = df.copy()
        if "time" in data.columns:
            data = data.sort_values("time")
        
        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)

        log_ret = np.log(close / close.shift(1))
        # Fill first NaN return with 0 to prevent issues in standard deviations
        log_ret_filled = log_ret.fillna(0.0)

        # 1. Realized Volatilities (annualized)
        data["realized_vol_5d"] = log_ret.rolling(5).std() * np.sqrt(252)
        data["realized_vol_20d"] = log_ret.rolling(20).std() * np.sqrt(252)
        data["realized_vol_60d"] = log_ret.rolling(60).std() * np.sqrt(252)

        # 2. ATR-14
        atr_series = ta.atr(high, low, close, length=14)
        data["ATRr_14"] = atr_series if atr_series is not None else (high - low).rolling(14).mean()

        # 3. Bollinger Bands (20-day, 2 std)
        bb_ma = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = bb_ma + 2.0 * bb_std
        bb_lower = bb_ma - 2.0 * bb_std
        
        # Bollinger Band Width
        data["BBB_20_2.0"] = ((bb_upper - bb_lower) / bb_ma.replace(0, np.nan)) * 100.0
        data["BBB_20_2.0"] = data["BBB_20_2.0"].fillna(0.0)

        # Bollinger %B
        denom = bb_upper - bb_lower
        data["BBP_20_2.0"] = (close - bb_lower) / denom.replace(0, 1e-6)
        data["BBP_20_2.0"] = data["BBP_20_2.0"].fillna(0.5)

        # 4. GARCH(1,1) Conditional Volatility Forecast
        # We fit GARCH(1,1) on all returns up to the current point, or fit once for speed.
        # Fitting once for the entire series is fast and stable.
        try:
            returns_np = log_ret_filled.values
            params = fit_garch_11(returns_np)
            cond_var = garch_conditional_variance(returns_np, params)
            data["garch_vol"] = np.sqrt(cond_var)
            
            # 1-day ahead conditional volatility forecast for each point:
            # sigma_{t+1}^2 = omega + alpha * eps_t^2 + beta * sigma_t^2
            # eps_t is the log return at t.
            # sigma_t^2 is the conditional variance at t.
            forecast_var = params.omega + params.alpha * (returns_np ** 2) + params.beta * cond_var
            data["garch_vol_forecast_1d"] = np.sqrt(forecast_var)
        except Exception as e:
            # Fallback to rolling standard deviation if GARCH fit fails
            data["garch_vol"] = log_ret_filled.rolling(20).std()
            data["garch_vol_forecast_1d"] = data["garch_vol"]

        return data
