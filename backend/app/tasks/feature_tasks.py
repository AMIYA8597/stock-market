"""Celery tasks for feature engineering pipeline."""

import asyncio
import logging
from typing import Any

import numpy as np
import pandas as pd
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.database.connection import async_session_factory
from app.models.feature_vectors import FeatureVector
from app.models.instrument import Instrument
from app.models.ohlcv import OHLCV
from app.models.sentiment import NewsSentiment
from research.feature_engineering.pipeline import FeaturePipeline

logger = logging.getLogger(__name__)

FEATURE_VERSION = "v1"

@shared_task(name="build_feature_vectors", bind=True, max_retries=3)
def build_feature_vectors(self: Any, symbol: str) -> dict[str, Any]:
    """Build feature vectors for a given symbol and store them idempotently."""
    return asyncio.run(_build_feature_vectors_async(symbol))

async def _build_feature_vectors_async(symbol: str) -> dict[str, Any]:
    logger.info(f"Building feature vectors for {symbol}")

    async with async_session_factory() as session:
        result = await session.execute(
            select(Instrument).where(Instrument.symbol == symbol)
        )
        instrument = result.scalars().first()

        if not instrument:
            logger.error(f"Instrument not found: {symbol}")
            return {"status": "error", "message": "Instrument not found"}

        # 1. Fetch OHLCV data
        result = await session.execute(
            select(OHLCV)
            .where(OHLCV.symbol_id == instrument.id)
            .order_by(OHLCV.time.asc())
        )
        ohlcv_records = result.scalars().all()

        if not ohlcv_records:
            logger.warning(f"No OHLCV data for {symbol}")
            return {"status": "success", "count": 0}

        df = pd.DataFrame([
            {
                "time": r.time,
                "open": float(r.open),
                "high": float(r.high),
                "low": float(r.low),
                "close": float(r.close),
                "volume": float(r.volume),
            }
            for r in ohlcv_records
        ])

        # 1.5 Fetch Sentiment Data
        from sqlalchemy import or_

        result = await session.execute(
            select(NewsSentiment)
            .where(or_(NewsSentiment.symbol_id == instrument.id, NewsSentiment.symbol_id is None))
        )
        news_records = result.scalars().all()

        sentiment_rows = []
        for n in news_records:
            sentiment_rows.append({
                "time": n.published_at.date(), # normalize to date
                "is_market": n.symbol_id is None,
                "score": float(n.sentiment_score),
                "is_positive": 1 if float(n.sentiment_score) > 0.1 else 0,
                "is_negative": 1 if float(n.sentiment_score) < -0.1 else 0
            })

        sentiment_df = pd.DataFrame(sentiment_rows)
        if not sentiment_df.empty:
            sentiment_df["time"] = pd.to_datetime(sentiment_df["time"])
            # aggregate symbol specific
            sym_sent = sentiment_df[~sentiment_df["is_market"]]
            if not sym_sent.empty:
                sym_agg = sym_sent.groupby("time").agg(
                    sentiment_score=("score", "mean"),
                    news_volume=("score", "count"),
                    pos_count=("is_positive", "sum"),
                    neg_count=("is_negative", "sum")
                ).reset_index()
                sym_agg["sentiment_pos_neg_ratio"] = (sym_agg["pos_count"] / sym_agg["neg_count"].replace(0, 1.0)).astype(float)
                sym_agg = sym_agg.drop(columns=["pos_count", "neg_count"])
            else:
                sym_agg = pd.DataFrame(columns=["time", "sentiment_score", "news_volume", "sentiment_pos_neg_ratio"])

            # aggregate market wide
            mkt_sent = sentiment_df[sentiment_df["is_market"]]
            if not mkt_sent.empty:
                mkt_agg = mkt_sent.groupby("time")["score"].mean().reset_index(name="market_sentiment_index")
            else:
                mkt_agg = pd.DataFrame(columns=["time", "market_sentiment_index"])

            df["date_only"] = df["time"].dt.normalize()
            if not sym_agg.empty:
                df = df.merge(sym_agg, left_on="date_only", right_on="time", how="left", suffixes=("", "_sym")).drop(columns=["time_sym"], errors="ignore")
            if not mkt_agg.empty:
                df = df.merge(mkt_agg, left_on="date_only", right_on="time", how="left", suffixes=("", "_mkt")).drop(columns=["time_mkt"], errors="ignore")
            df = df.drop(columns=["date_only"])

            cols_to_fill = ["sentiment_score", "news_volume", "sentiment_pos_neg_ratio", "market_sentiment_index"]

            # Forward fill missing sentiment with 0 (or forward fill previous sentiment)
            # Actually, it's better to ffill previous day's sentiment if no new news, then fill remaining with 0.
            for c in cols_to_fill:
                if c in df.columns:
                    df[c] = df[c].ffill().fillna(0.0)

            # LAG strictly by 1 bar to prevent intra-day leakage (day t uses news from t-1)
            for c in cols_to_fill:
                if c in df.columns:
                    df[c] = df[c].shift(1).fillna(0.0)

            # 3-day momentum
            if "sentiment_score" in df.columns:
                df["sentiment_momentum_3d"] = df["sentiment_score"] - df["sentiment_score"].shift(3).fillna(0.0)

        # 1.6 Fetch Regime Data
        from app.models.regime_states import RegimeState
        result = await session.execute(
            select(RegimeState).where(RegimeState.symbol_id == instrument.id)
        )
        regimes = result.scalars().all()

        regime_rows = []
        for r in regimes:
            regime_rows.append({
                "time": r.time.date(),
                "regime_state": int(r.viterbi_state),
                "garch_vol": float(r.conditional_vol)
            })

        regime_df = pd.DataFrame(regime_rows)
        if not regime_df.empty:
            regime_df["time"] = pd.to_datetime(regime_df["time"])
            df["date_only"] = df["time"].dt.normalize()
            df = df.merge(regime_df, left_on="date_only", right_on="time", how="left", suffixes=("", "_reg")).drop(columns=["time_reg", "date_only"], errors="ignore")
            # ffill regimes
            df["regime_state"] = df["regime_state"].ffill().fillna(0).astype(int)
            df["garch_vol"] = df["garch_vol"].ffill().fillna(0.0)

            # Lag by 1 bar to prevent leakage
            df["regime_state"] = df["regime_state"].shift(1).fillna(0).astype(int)
            df["garch_vol"] = df["garch_vol"].shift(1).fillna(0.0)

        # 2. Run feature pipeline
        pipeline = FeaturePipeline()
        features_df = pipeline.run(df)

        # 3. Store to DB
        # Drop rows where we don't have enough history to compute meaningful features (e.g., first 252 days)
        # Actually, let's keep it simple: drop where 'ret_1d' is null (first row).
        features_df = features_df.dropna(subset=["ret_1d"])

        # Prepare for bulk upsert
        records = []
        for _, row in features_df.iterrows():
            feature_dict = row.drop(["time", "open", "high", "low", "close", "volume"], errors="ignore").to_dict()

            # Clean nan to None for JSONB
            clean_dict = {
                k: (None if pd.isna(v) else float(v) if isinstance(v, (int, float, np.integer, np.floating)) else v)
                for k, v in feature_dict.items()
            }

            records.append({
                "time": row["time"],
                "symbol_id": instrument.id,
                "features": clean_dict,
                "feature_version": FEATURE_VERSION
            })

        if not records:
            return {"status": "success", "count": 0}

        # Idempotent upsert
        stmt = insert(FeatureVector).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["time", "symbol_id"],
            set_={"features": stmt.excluded.features, "feature_version": stmt.excluded.feature_version}
        )

        await session.execute(stmt)
        await session.commit()

        return {"status": "success", "count": len(records), "symbol": symbol}
