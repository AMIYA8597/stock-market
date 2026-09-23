"""Technical indicators and oscillators using pandas-ta."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pandas_ta as ta  # noqa: F401

from research.feature_engineering.base import FeatureBuilder


class TechnicalFactorsBuilder(FeatureBuilder):
    """Build technical factors using pandas-ta (RSI, MACD, Bollinger, etc.)."""

    name = "technical_factors"

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        if "symbol" in frame.columns and frame["symbol"].nunique() > 1:
            results = []
            for _, group in frame.groupby("symbol"):
                results.append(self._transform_single(group))
            return pd.concat(results).sort_index()
        return self._transform_single(frame)

    def _transform_single(self, frame: pd.DataFrame) -> pd.DataFrame:
        data = frame.sort_values("time").copy()

        macd = data.ta.macd(append=False)
        if macd is not None and not macd.empty:
            data["macd"] = macd.iloc[:, 0]
            data["macd_hist"] = macd.iloc[:, 1]
            data["macd_signal"] = macd.iloc[:, 2]

        data["rsi_14"] = data.ta.rsi(length=14, append=False)

        adx = data.ta.adx(length=14, append=False)
        if adx is not None and not adx.empty:
            data["adx_14"] = adx.iloc[:, 0]
            data["dmp_14"] = adx.iloc[:, 1]
            data["dmn_14"] = adx.iloc[:, 2]

        bbands = data.ta.bbands(length=20, std=2, append=False)
        if bbands is not None and not bbands.empty:
            data["bb_width"] = bbands.filter(like="BBB").iloc[:, 0]
            data["bb_percent"] = bbands.filter(like="BBP").iloc[:, 0]

        data["atr_14"] = data.ta.atr(length=14, append=False)

        stoch = data.ta.stoch(append=False)
        if stoch is not None and not stoch.empty:
            data["stoch_k"] = stoch.iloc[:, 0]
            data["stoch_d"] = stoch.iloc[:, 1]

        data["obv"] = data.ta.obv(append=False)

        try:
            temp_data = data.copy()
            if "time" in temp_data.columns:
                temp_data.set_index("time", inplace=True)
            vwap = temp_data.ta.vwap(append=False)
            if vwap is not None and not vwap.empty:
                data["vwap"] = vwap.values
        except Exception:
            typical_price = (data["high"] + data["low"] + data["close"]) / 3
            cum_vol = data["volume"].cumsum()
            cum_pv = (typical_price * data["volume"]).cumsum()
            data["vwap"] = cum_pv / cum_vol.replace(0, np.nan)

        supertrend = data.ta.supertrend(length=7, multiplier=3.0, append=False)
        if supertrend is not None and not supertrend.empty:
            data["supertrend_dir"] = supertrend.filter(like="SUPERTd").iloc[:, 0]
            data["supertrend_dist"] = (
                data["close"] / supertrend.filter(like="SUPERT_").iloc[:, 0]
            ) - 1.0

        ichimoku, _ = data.ta.ichimoku(append=False)
        if ichimoku is not None and not ichimoku.empty:
            data["ichimoku_tenkan"] = (data["close"] / ichimoku.filter(like="ITS").iloc[:, 0]) - 1.0
            data["ichimoku_kijun"] = (data["close"] / ichimoku.filter(like="IKS").iloc[:, 0]) - 1.0

            isa = ichimoku.filter(like="ISA")
            isb = ichimoku.filter(like="ISB")
            if not isa.empty and not isb.empty:
                data["ichimoku_senkou_a"] = (data["close"] / isa.iloc[:, 0]) - 1.0
                data["ichimoku_senkou_b"] = (data["close"] / isb.iloc[:, 0]) - 1.0

        # Drop any leaking columns that pandas_ta might have appended (like Chikou Span ICS_26)
        leaky_cols = [c for c in data.columns if c.startswith("ICS_")]
        if leaky_cols:
            data.drop(columns=leaky_cols, inplace=True)

        if "regime_label" not in data.columns:
            data["regime_label"] = np.nan
        if "sentiment_score" not in data.columns:
            data["sentiment_score"] = np.nan

        return data
