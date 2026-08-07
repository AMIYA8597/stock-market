"""Celery tasks for live news ingestion and sentiment analysis."""

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import Any

import redis
from celery import shared_task
from sqlalchemy import select

from app.database.connection import async_session_factory
from app.models.instrument import Instrument
from app.models.sentiment import NewsSentiment
from app.services.sentiment_analyzer import FinBERTSentimentAnalyzer

logger = logging.getLogger(__name__)

class DummyRedis:
    def __init__(self):
        self._cache = {}
    def get(self, key):
        return self._cache.get(key)
    def setex(self, key, time, value):
        self._cache[key] = value

def _get_redis_client():
    client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    try:
        client.ping()
        return client
    except redis.exceptions.ConnectionError:
        logger.warning("Redis is not running. Falling back to in-memory dict cache.")
        return DummyRedis()

def _hash_headline(headline: str) -> str:
    return hashlib.md5(headline.encode('utf-8')).hexdigest()

@shared_task(name="tasks.news_tasks.refresh_news_sentiment")
def refresh_news_sentiment() -> dict[str, Any]:
    """Ingest live news and score sentiment for active symbols."""
    return asyncio.run(_refresh_news_sentiment_async())

async def _refresh_news_sentiment_async() -> dict[str, Any]:
    # We will restrict to the 5 symbols we use for testing (or a specific universe)
    # to avoid Google News rate limits.
    # Alternatively we just get a few symbols for testing.

    async with async_session_factory() as session:
        # For our test DB, we might have weird symbols like 0ABCL31-N0
        # So we just get the first 5 symbols
        result = await session.execute(select(Instrument).limit(5))
        instruments = result.scalars().all()

    analyzer = FinBERTSentimentAnalyzer()
    analyzer.initialize()
    redis_client = _get_redis_client()


    # 1. Market-wide News
    logger.info("Scraping market-wide news...")
    market_headlines = analyzer.scrape_market_news()
    await _process_headlines(market_headlines, None, analyzer, redis_client)

    # 2. Per-symbol News
    for inst in instruments:
        logger.info(f"Scraping news for {inst.symbol}...")

        # Scrape
        symbol_query = f"{inst.symbol} stock"
        headlines = analyzer.scrape_google_news(symbol_query)

        await _process_headlines(headlines, inst.id, analyzer, redis_client)

        # Polite delay to avoid rate limiting
        await asyncio.sleep(1)

    return {"status": "ok"}

async def _process_headlines(
    headlines: list[dict[str, Any]],
    symbol_id: int | None,
    analyzer: FinBERTSentimentAnalyzer,
    redis_client: redis.Redis
) -> None:
    if not headlines:
        return

    to_score_texts = []
    to_score_indices = []

    # Check cache and deduplicate
    cached_results = []
    for i, hl in enumerate(headlines):
        h_hash = _hash_headline(hl['text'])
        cache_key = f"sentiment:{h_hash}"
        try:
            cached_score = redis_client.get(cache_key)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            cached_score = None

        if cached_score is not None:
            # We already scored this headline
            cached_results.append({
                'index': i,
                'score': float(cached_score)
            })
        else:
            to_score_texts.append(hl['text'])
            to_score_indices.append(i)

    # Score missing
    if to_score_texts:
        sentiment_results = analyzer.analyze_sentiment_batch(to_score_texts)
        for i, idx in enumerate(to_score_indices):
            res = sentiment_results[i]
            # Compound score in [-1, 1]
            compound_score = res.get("positive", 0.0) - res.get("negative", 0.0)

            # Cache it
            h_hash = _hash_headline(headlines[idx]['text'])
            try:
                redis_client.setex(f"sentiment:{h_hash}", 86400 * 30, str(compound_score))
            except Exception as e:
                logger.warning(f"Cache set error: {e}")

            cached_results.append({
                'index': idx,
                'score': compound_score
            })

    # Store in database
    from email.utils import parsedate_to_datetime

    async with async_session_factory() as session:
        for cr in cached_results:
            idx = cr['index']
            score = cr['score']
            hl = headlines[idx]

            # Parse date
            try:
                pub_date = parsedate_to_datetime(hl['date']) if hl['date'] else datetime.utcnow()
                # Ensure timezone-aware
                if pub_date.tzinfo is None:
                    import pytz
                    pub_date = pub_date.replace(tzinfo=pytz.UTC)
            except Exception:
                import pytz
                pub_date = datetime.utcnow().replace(tzinfo=pytz.UTC)

            label = "POSITIVE" if score > 0.05 else ("NEGATIVE" if score < -0.05 else "NEUTRAL")

            # Check if this specific headline for this symbol is already in the db
            stmt = select(NewsSentiment).where(
                NewsSentiment.headline == hl['text'],
                NewsSentiment.symbol_id == symbol_id
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()

            if not existing:
                news = NewsSentiment(
                    symbol_id=symbol_id,
                    headline=hl['text'],
                    source=hl['source'],
                    url=hl['url'],
                    sentiment_label=label,
                    sentiment_score=score,
                    published_at=pub_date
                )
                session.add(news)

        await session.commit()
