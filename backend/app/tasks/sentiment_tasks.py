"""Celery tasks for live news ingestion and sentiment analysis."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import dateutil.parser
from celery import shared_task
from sqlalchemy import select

from app.database.connection import async_session_factory
from app.models.instrument import Instrument
from app.models.sentiment import NewsSentiment
from app.services.sentiment_analyzer import FinBERTSentimentAnalyzer

logger = logging.getLogger(__name__)


@shared_task(name="update_news_sentiment", bind=True, max_retries=3)
def update_news_sentiment(self: Any) -> dict[str, Any]:
    """Pull news from RSS, score with FinBERT, and save to database."""
    return asyncio.run(_update_news_sentiment_async())


async def _update_news_sentiment_async() -> dict[str, Any]:
    logger.info("Starting news sentiment update pipeline...")
    analyzer = FinBERTSentimentAnalyzer()
    analyzer.initialize()

    records_added = 0

    async with async_session_factory() as session:
        # Fetch active instruments
        result = await session.execute(select(Instrument).where(Instrument.is_active))
        instruments = result.scalars().all()

        # We need to deduplicate headlines. We'll load recent headlines from DB into memory.
        three_days_ago = datetime.now(UTC) - timedelta(days=3)
        recent_news = await session.execute(
            select(NewsSentiment).where(NewsSentiment.published_at >= three_days_ago)
        )
        existing_headlines = {news.headline for news in recent_news.scalars().all()}

        # 1. Fetch market headlines (MC, ET) and market-wide Google News
        market_headlines = analyzer.scrape_market_news()
        market_google_hl = analyzer.scrape_google_news("Nifty OR Sensex OR Indian Stock Market")

        all_market_headlines = market_headlines + market_google_hl

        # Process in batch
        new_market_hls = []
        for hl in all_market_headlines:
            text = hl["text"]
            if not text or text in existing_headlines:
                continue
            new_market_hls.append(hl)
            existing_headlines.add(text)  # Dedupe internally for the batch

        if new_market_hls:
            texts = [hl["text"] for hl in new_market_hls]
            sentiments = analyzer.analyze_sentiment_batch(texts)

            for hl, sent in zip(new_market_hls, sentiments, strict=False):
                dt_str = hl.get("date", "")
                try:
                    dt = dateutil.parser.parse(dt_str) if dt_str else datetime.now(UTC)
                except Exception:
                    dt = datetime.now(UTC)

                score = sent["positive"] - sent["negative"]
                label = "POSITIVE" if score > 0.1 else ("NEGATIVE" if score < -0.1 else "NEUTRAL")

                session.add(
                    NewsSentiment(
                        symbol_id=None,
                        headline=hl["text"],
                        source=hl.get("source", "RSS"),
                        url=hl.get("url"),
                        sentiment_label=label,
                        sentiment_score=score,
                        published_at=dt,
                        processed_at=datetime.now(UTC),
                    )
                )
                records_added += 1

        # 2. Process per-ticker headlines
        new_ticker_hls = []
        for inst in instruments:
            clean_symbol = inst.canonical_symbol.split(".")[0]
            query = f'"{clean_symbol}" OR "{inst.display_name}" stock'
            google_hl = analyzer.scrape_google_news(query)

            for hl in google_hl:
                text = hl["text"]
                if not text or text in existing_headlines:
                    continue
                new_ticker_hls.append({"hl": hl, "inst_id": inst.id})
                existing_headlines.add(text)

        # Batch analyze ticker headlines (chunked to prevent any memory issue if extremely large, though analyzer handles 32 internally)
        if new_ticker_hls:
            texts = [item["hl"]["text"] for item in new_ticker_hls]
            sentiments = analyzer.analyze_sentiment_batch(texts)

            for item, sent in zip(new_ticker_hls, sentiments, strict=False):
                hl = item["hl"]
                inst_id = item["inst_id"]
                dt_str = hl.get("date", "")
                try:
                    dt = dateutil.parser.parse(dt_str) if dt_str else datetime.now(UTC)
                except Exception:
                    dt = datetime.now(UTC)

                score = sent["positive"] - sent["negative"]
                label = "POSITIVE" if score > 0.1 else ("NEGATIVE" if score < -0.1 else "NEUTRAL")

                session.add(
                    NewsSentiment(
                        symbol_id=inst_id,
                        headline=hl["text"],
                        source=hl.get("source", "Google News"),
                        url=hl.get("url"),
                        sentiment_label=label,
                        sentiment_score=score,
                        published_at=dt,
                        processed_at=datetime.now(UTC),
                    )
                )
                records_added += 1

        if records_added > 0:
            await session.commit()

    logger.info(f"News sentiment update complete. Added {records_added} new records.")
    return {"status": "success", "records_added": records_added}
