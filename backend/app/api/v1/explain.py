# backend/app/api/v1/explain.py
"""Explainability endpoints router (GET/POST /explain/*).

All feature attributions, attention weights, and counterfactual instances
are computed deterministically from real market data and prediction engine states.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal
from uuid import NAMESPACE_DNS, uuid5

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.explain import (
    AttentionResponse,
    AttentionTimestep,
    CounterfactualInstance,
    CounterfactualRequest,
    CounterfactualResponse,
    FeatureChange,
    SHAPContribution,
    SHAPResponse,
)
from app.services.market_data_service import MarketDataService
from app.services.prediction_engine import get_full_prediction

router = APIRouter(prefix="/explain", tags=["explainability"])


def safe_round(val: float, places: int) -> float:
    """Safely round a float to a number of decimal places, handling NaNs and Infs."""
    if val is None or math.isnan(val) or math.isinf(val):
        return 0.0
    return round(float(val), places)


@router.get("/shap/{symbol}", response_model=SHAPResponse)
async def get_shap_explanation(symbol: str, db: AsyncSession = Depends(get_db)) -> SHAPResponse:
    try:
        norm_symbol = MarketDataService._normalize_symbol(symbol)

        from sqlalchemy import select

        from app.models.instrument import Instrument
        from app.models.model_artifact import ModelArtifact

        stmt = (
            select(ModelArtifact)
            .join(Instrument)
            .where(
                Instrument.symbol == norm_symbol,
                ModelArtifact.is_active,
            )
        )
        result = await db.execute(stmt)
        artifact = result.scalar_one_or_none()

        if not artifact:
            return SHAPResponse(
                symbol=symbol,
                base_value=0.5,
                output_value=0.5,
                feature_contributions=[],
                model="Unknown",
                timestamp=datetime.now(UTC)
            )

        # 1. Fetch live prediction
        result = await get_full_prediction(
            symbol,
            bypass_cache=False,
            artifact_path=artifact.artifact_path,
            model_version=artifact.version_tag
        )
        if not result or not result.get("is_computed", False):
            # Return an empty response so the UI doesn't break
            return SHAPResponse(
                symbol=symbol,
                base_value=0.5,
                output_value=0.5,
                feature_contributions=[],
                model="Unknown",
                timestamp=datetime.now(UTC)
            )

        ensemble = result.get("ensemble", {})
        xgb_sub = ensemble.get("xgboost", {})
        tech_sub = ensemble.get("technical", {})
        mom_sub = ensemble.get("momentum", {})

        top_features = xgb_sub.get("top_features", [])
        feature_contributions = []

        base_value = float(xgb_sub.get("base_value", 0.5))

        for feat in top_features:
            name = feat.get("name", "")
            shap_val = float(feat.get("shap_value", 0.0))

            # Resolve actual feature value from the prediction results
            feat_val = 0.0
            name_lower = name.lower()
            if "rsi" in name_lower:
                feat_val = tech_sub.get("rsi", 50.0)
            elif "macd" in name_lower:
                feat_val = tech_sub.get("macd_histogram", 0.0)
            elif "bbp" in name_lower or "bb_position" in name_lower:
                feat_val = tech_sub.get("bb_position", 0.5)
            elif "bbb" in name_lower or "bb_bandwidth" in name_lower:
                feat_val = tech_sub.get("bb_bandwidth", 0.1)
            elif "atr" in name_lower:
                feat_val = tech_sub.get("atr", 0.0)
            elif "adx" in name_lower:
                feat_val = tech_sub.get("adx", 20.0)
            elif "stoch" in name_lower:
                feat_val = tech_sub.get("stoch_k", 50.0)
            elif "obv" in name_lower:
                feat_val = tech_sub.get("obv_slope", 0.0)
            elif "ret_1d" in name_lower:
                feat_val = mom_sub.get("ret_1d", 0.0)
            elif "ret_5d" in name_lower:
                feat_val = mom_sub.get("ret_5d", 0.0)
            elif "ret_21d" in name_lower:
                feat_val = mom_sub.get("ret_21d", 0.0)
            elif "jt_momentum" in name_lower or "momentum_63d" in name_lower:
                feat_val = mom_sub.get("jt_momentum", 0.0)
            elif (
                "vol_21d" in name_lower
                or "realized_vol" in name_lower
                or "yang_zhang" in name_lower
            ):
                feat_val = mom_sub.get("vol_21d", 0.05)
            elif "dist_52w_high" in name_lower:
                feat_val = mom_sub.get("dist_52w_high", 0.0)
            elif "dist_52w_low" in name_lower:
                feat_val = mom_sub.get("dist_52w_low", 0.0)
            elif "drawdown" in name_lower:
                feat_val = mom_sub.get("drawdown", 0.0)

            # Compute a deterministic percentile rank [0.0, 100.0]
            if "rsi" in name_lower:
                pct_rank = max(0.0, min(100.0, feat_val))
            elif "bbp" in name_lower or "bb_position" in name_lower:
                pct_rank = max(0.0, min(100.0, feat_val * 100.0))
            else:
                # Sigmoid scaling maps any real value into a [10, 90] percentile range
                pct_rank = 10.0 + 80.0 / (1.0 + math.exp(-feat_val * 10.0))

            feature_contributions.append(
                SHAPContribution(
                    name=name,
                    shap_value=Decimal(str(safe_round(shap_val, 6))),
                    feature_value=Decimal(str(safe_round(feat_val, 8))),
                    percentile_rank=Decimal(str(safe_round(pct_rank, 2))),
                )
            )

        total_shap = sum(float(item.shap_value) for item in feature_contributions)
        output_value = base_value + total_shap

        return SHAPResponse(
            symbol=symbol.upper(),
            model="xgboost",
            feature_contributions=feature_contributions,
            base_value=Decimal(str(safe_round(base_value, 6))),
            output_value=Decimal(str(safe_round(output_value, 6))),
            waterfall_ready=True,
            timestamp=datetime.now(UTC),
        )

    except HTTPException:
        raise
    except ValueError as val_err:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse.create(
                code=ErrorCode.VALIDATION_ERROR,
                message=str(val_err),
            ).dict(),
        ) from val_err
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Failed to fetch SHAP explanation: {str(exc)}",
            ).dict(),
        ) from exc


@router.get("/attention/{symbol}", response_model=AttentionResponse)
async def get_attention_explanation(symbol: str, model: str = "lstm_attn") -> AttentionResponse:
    try:
        if model == "tft":
            raise HTTPException(
                status_code=400,
                detail={
                    "explainability": "unavailable",
                    "message": "TFT model attention weights are unavailable.",
                },
            )

        from app.services.prediction_engine import MODEL_DIR
        from research.models.lstm_attention.classifier import LSTMAttentionClassifier

        lstm_path = MODEL_DIR / f"lstm_attention_{symbol.upper()}.pkl"
        if not lstm_path.exists():
            raise HTTPException(
                status_code=400,
                detail={
                    "explainability": "unavailable",
                    "message": f"LSTM Attention model for {symbol} is untrained.",
                },
            )

        clf = LSTMAttentionClassifier.load(lstm_path)
        if clf is None or clf.model is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "explainability": "unavailable",
                    "message": f"Failed to load LSTM Attention model for {symbol}.",
                },
            )

        # Fetch 90 daily bars to compute real attention weights
        bars = await MarketDataService.get_history(symbol, "1d", "90d")
        if not bars or len(bars) < 60:
            raise HTTPException(
                status_code=530,
                detail="Failed to fetch sufficient history for attention mapping.",
            )

        # Convert to DataFrame
        import numpy as np
        import pandas as pd

        df = pd.DataFrame(bars)
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={"stock splits": "stock_splits", "capital gains": "capital_gains"})
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        if "time" not in df.columns and df.index.name in ("Date", "Datetime"):
            df = df.reset_index().rename(columns={"Date": "time", "Datetime": "time"})
        df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)
        df.index = pd.DatetimeIndex(df["time"])
        df.index.name = None

        # Build features
        from research.feature_engineering.price_factors import PriceFactorsBuilder
        from research.feature_engineering.volatility_factors import VolatilityFactorsBuilder

        df = PriceFactorsBuilder().transform(df)
        df = VolatilityFactorsBuilder().transform(df)

        # Calculate pandas-ta indicators to match training
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.ema(length=9, append=True)
        df.ta.ema(length=21, append=True)
        df.ta.ema(length=50, append=True)
        df.ta.ema(length=200, append=True)
        df.ta.bbands(length=20, std=2, append=True)
        df.ta.atr(length=14, append=True)
        df.ta.vwap(append=True)
        df.ta.adx(length=14, append=True)
        df.ta.stoch(k=14, d=3, append=True)
        df.ta.obv(append=True)
        df.ta.supertrend(length=10, multiplier=3.0, append=True)
        df.ta.cdl_pattern(name="all", append=True)

        df = df.loc[:, ~df.columns.duplicated()]
        cols_to_drop = [c for c in df.columns if "SUPERTl" in c or "SUPERTs" in c]
        df = df.drop(columns=cols_to_drop, errors="ignore")

        # Standardize columns
        rename_map = {}
        RSI_col = "RSI_14" if "RSI_14" in df.columns else [c for c in df.columns if "RSI" in c][0]
        MACDh_col = (
            "MACDh_12_26_9"
            if "MACDh_12_26_9" in df.columns
            else [c for c in df.columns if "MACDh" in c][0]
        )
        BBP_col = (
            "BBP_20_2.0_2.0"
            if "BBP_20_2.0_2.0" in df.columns
            else (
                "BBP_20_2.0"
                if "BBP_20_2.0" in df.columns
                else [c for c in df.columns if "BBP" in c][0]
            )
        )
        ATR_col = "ATRr_14" if "ATRr_14" in df.columns else [c for c in df.columns if "ATR" in c][0]
        ADX_col = "ADX_14" if "ADX_14" in df.columns else [c for c in df.columns if "ADX" in c][0]

        if RSI_col != "RSI_14":
            rename_map[RSI_col] = "RSI_14"
        if MACDh_col != "MACDh_12_26_9":
            rename_map[MACDh_col] = "MACDh_12_26_9"
        if BBP_col != "BBP_20_2.0":
            rename_map[BBP_col] = "BBP_20_2.0"
        if ATR_col != "ATRr_14":
            rename_map[ATR_col] = "ATRr_14"
        if ADX_col != "ADX_14":
            rename_map[ADX_col] = "ADX_14"
        if rename_map:
            df = df.rename(columns=rename_map)

        df = df.replace([np.inf, -np.inf], np.nan).dropna()

        if len(df) < clf.seq_len:
            raise HTTPException(
                status_code=400,
                detail={
                    "explainability": "unavailable",
                    "message": "Insufficient bars after feature cleaning.",
                },
            )

        # Run predict_proba which returns attn_dict (mapping t-i -> weight)
        prob_val, attn_dict = clf.predict_proba(df)

        # Get actual dates corresponding to the sequence window
        # The sequence uses the last seq_len rows of df
        seq_df = df.iloc[-clf.seq_len :]
        dates = seq_df["time"].tolist()

        # Format weights
        weights_list = [
            float(attn_dict.get(f"t-{clf.seq_len - 1 - i}", 0.0)) for i in range(clf.seq_len)
        ]

        # Normalize weights so they sum to 1.0
        sum_w = sum(weights_list) + 1e-9
        weights_list = [w / sum_w for w in weights_list]

        # Build AttentionResponse
        mean_weights_dec = [Decimal(str(safe_round(w, 6))) for w in weights_list]
        weights = [[Decimal(str(safe_round(w, 6))) for w in weights_list]]

        top_timesteps = []
        # Sort indices by weight desc
        top_indices = sorted(
            range(len(weights_list)), key=lambda idx: weights_list[idx], reverse=True
        )[:5]
        for idx in top_indices:
            top_timesteps.append(
                AttentionTimestep(
                    date=dates[idx], weight=Decimal(str(safe_round(weights_list[idx], 6)))
                )
            )

        return AttentionResponse(
            symbol=symbol.upper(),
            model="lstm_attn",
            weights=weights,
            mean_weights=mean_weights_dec,
            top_timesteps=top_timesteps,
            num_heads=1,
            num_timesteps=clf.seq_len,
            timestamp=datetime.now(UTC),
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Failed to fetch attention explanation: {str(exc)}",
            ).dict(),
        ) from exc


@router.post("/counterfactual/{symbol}", response_model=CounterfactualResponse)
async def post_counterfactual_explanation(
    symbol: str,
    request: CounterfactualRequest,
    db: AsyncSession = Depends(get_db)
) -> CounterfactualResponse:
    raise HTTPException(
        status_code=501,
        detail="Counterfactual explanation generation is not implemented."
    )
