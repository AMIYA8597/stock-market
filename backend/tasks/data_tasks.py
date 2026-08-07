"""Scheduled data tasks."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from app.database.connection import async_session_factory
from app.models.feature_vectors import FeatureVector
from app.models.instrument import Instrument
from app.models.ohlcv import OHLCV
from app.models.regime_states import RegimeState
from app.models.sentiment import NewsSentiment
from research.feature_engineering.pipeline import FeaturePipeline

logger = logging.getLogger(__name__)


async def _process_symbol(symbol_id: int) -> int:
    """Process features for a single symbol."""
    async with async_session_factory() as session:
        # Fetch OHLCV data
        stmt = select(OHLCV).where(
            OHLCV.symbol_id == symbol_id,
            OHLCV.interval == "1d"
        ).order_by(OHLCV.time)
        result = await session.execute(stmt)
        rows = result.scalars().all()

        if not rows:
            return 0

        import pandas as pd

        df = pd.DataFrame([{
            "time": r.time,
            "open": float(r.open),
            "high": float(r.high),
            "low": float(r.low),
            "close": float(r.close),
            "volume": float(r.volume),
            "symbol_id": r.symbol_id
        } for r in rows])

        # Ensure time is properly formatted for merging
        df['date'] = df['time'].dt.date

        # Fetch sentiment for this symbol
        from sqlalchemy import case, func
        stmt_sent = select(
            func.date(NewsSentiment.published_at).label("date"),
            func.avg(NewsSentiment.sentiment_score).label("sentiment_score"),
            func.count(NewsSentiment.id).label("news_volume"),
            func.sum(
                case(
                    (NewsSentiment.sentiment_label == 'POSITIVE', 1),
                    else_=0
                )
            ).label("pos_count"),
            func.sum(
                case(
                    (NewsSentiment.sentiment_label == 'NEGATIVE', 1),
                    else_=0
                )
            ).label("neg_count")
        ).where(
            NewsSentiment.symbol_id == symbol_id
        ).group_by(func.date(NewsSentiment.published_at))

        sent_rows = await session.execute(stmt_sent)
        sent_records = []
        for r in sent_rows:
            pos_ratio = r.pos_count / (r.neg_count + 1)
            # SQLite func.date returns a string, so we must parse it back to date
            date_val = r.date
            if isinstance(date_val, str):
                date_val = datetime.strptime(date_val, "%Y-%m-%d").date()
            sent_records.append({
                "date": date_val,
                "sentiment_score": float(r.sentiment_score or 0.0),
                "news_volume": float(r.news_volume or 0),
                "sentiment_pos_neg_ratio": float(pos_ratio)
            })

        sent_df = pd.DataFrame(sent_records)
        if not sent_df.empty:
            df = df.merge(sent_df, on="date", how="left")
        else:
            df["sentiment_score"] = 0.0
            df["news_volume"] = 0.0
            df["sentiment_pos_neg_ratio"] = 0.0

        # Fetch market-wide sentiment
        stmt_market = select(
            func.date(NewsSentiment.published_at).label("date"),
            func.avg(NewsSentiment.sentiment_score).label("market_sentiment_index")
        ).where(
            NewsSentiment.symbol_id.is_(None)
        ).group_by(func.date(NewsSentiment.published_at))

        market_rows = await session.execute(stmt_market)
        market_records = []
        for r in market_rows:
            date_val = r.date
            if isinstance(date_val, str):
                date_val = datetime.strptime(date_val, "%Y-%m-%d").date()
            market_records.append({
                "date": date_val,
                "market_sentiment_index": float(r.market_sentiment_index or 0.0)
            })

        market_df = pd.DataFrame(market_records)
        if not market_df.empty:
            df = df.merge(market_df, on="date", how="left")
        else:
            df["market_sentiment_index"] = 0.0

        # Drop temporary 'date' column for news merging
        df = df.drop(columns=["date"])

        # Fill missing sentiment with 0
        df["sentiment_score"] = df["sentiment_score"].fillna(0.0)
        df["news_volume"] = df["news_volume"].fillna(0.0)
        df["sentiment_pos_neg_ratio"] = df["sentiment_pos_neg_ratio"].fillna(0.0)
        df["market_sentiment_index"] = df["market_sentiment_index"].fillna(0.0)

        # ─── Fetch Regime States ───
        stmt_reg = select(
            RegimeState.time,
            RegimeState.viterbi_state,
            RegimeState.conditional_vol
        ).where(RegimeState.symbol_id == symbol_id)

        reg_rows = await session.execute(stmt_reg)
        reg_records = []
        for r in reg_rows:
            reg_records.append({
                "time": r.time,
                "regime_state": int(r.viterbi_state),
                "regime_cond_vol": float(r.conditional_vol)
            })

        reg_df = pd.DataFrame(reg_records)
        if not reg_df.empty:
            df = df.merge(reg_df, on="time", how="left")
        else:
            df["regime_state"] = None
            df["regime_cond_vol"] = None

        # Fetch market-wide regime
        stmt_mkt_reg = select(
            RegimeState.time,
            RegimeState.viterbi_state.label("market_regime_state"),
            RegimeState.conditional_vol.label("market_regime_cond_vol")
        ).where(RegimeState.symbol_id.is_(None))

        mkt_reg_rows = await session.execute(stmt_mkt_reg)
        mkt_reg_records = []
        for r in mkt_reg_rows:
            mkt_reg_records.append({
                "time": r.time,
                "market_regime_state": int(r.market_regime_state),
                "market_regime_cond_vol": float(r.market_regime_cond_vol)
            })

        mkt_reg_df = pd.DataFrame(mkt_reg_records)
        if not mkt_reg_df.empty:
            df = df.merge(mkt_reg_df, on="time", how="left")
        else:
            df["market_regime_state"] = None
            df["market_regime_cond_vol"] = None

        # Forward fill regimes as they are computed at market close and persist until updated
        df["regime_state"] = df["regime_state"].ffill()
        df["regime_cond_vol"] = df["regime_cond_vol"].ffill()
        df["market_regime_state"] = df["market_regime_state"].ffill()
        df["market_regime_cond_vol"] = df["market_regime_cond_vol"].ffill()

        pipeline = FeaturePipeline()
        features_df = pipeline.run(df)

        # Prepare records for upsert
        records = []
        for _, row in features_df.iterrows():
            # Skip if basic data is missing
            if pd.isna(row["close"]):
                continue

            time_val = row["time"]
            target_val = None
            if "target_direction_1d" in row and not pd.isna(row["target_direction_1d"]):
                target_val = int(row["target_direction_1d"])

            # Extract features (exclude time, symbol_id, base ohlcv, and target)
            skip_cols = {"time", "symbol_id", "open", "high", "low", "close", "volume", "target_direction_1d"}
            feature_dict = {}
            for col in features_df.columns:
                if col not in skip_cols:
                    val = row[col]
                    # Convert pandas NaNs to None for JSON
                    feature_dict[col] = None if pd.isna(val) else float(val)

            records.append({
                "time": time_val,
                "symbol_id": symbol_id,
                "features": feature_dict,
                "feature_version": "v1",
                "target_direction_1d": target_val
            })

        if not records:
            return 0

        # Bulk upsert using PostgreSQL ON CONFLICT DO UPDATE
        stmt = insert(FeatureVector).values(records)
        update_dict = {
            c.name: c
            for c in stmt.excluded
            if c.name not in ["time", "symbol_id"]
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["time", "symbol_id"],
            set_=update_dict
        )

        await session.execute(stmt)
        await session.commit()
        return len(records)


async def _refresh_features_async() -> dict[str, int]:
    """Async implementation of refresh_features."""
    async with async_session_factory() as session:
        result = await session.execute(select(Instrument.id))
        symbol_ids = result.scalars().all()

    total_processed = 0
    for sid in symbol_ids:
        try:
            count = await _process_symbol(sid)
            total_processed += count
        except Exception as e:
            logger.error(f"Failed to process features for symbol_id {sid}: {e}")

    return {"status": "ok", "processed": total_processed}


@shared_task(name="tasks.data_tasks.refresh_features")
def refresh_features() -> dict[str, str]:
    """Compute features for all symbols and persist idempotently."""
    result = asyncio.run(_refresh_features_async())
    return result
