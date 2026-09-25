import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select

from app.database.connection import async_session_factory
from app.models.instrument import Instrument
from app.models.research import Dataset as NewsSentiment
from tasks.news_tasks import _refresh_news_sentiment_async


async def run_news():
    print("Starting news ingestion...")
    await _refresh_news_sentiment_async()
    print("News ingestion complete.")

    async with async_session_factory() as session:
        # Let's print some sample headlines
        stmt = select(NewsSentiment, Instrument.symbol).outerjoin(Instrument).limit(10)
        result = await session.execute(stmt)
        rows = result.all()

        print("\n--- SAMPLE HEADLINES & SCORES ---")
        for news, symbol in rows:
            sym_str = symbol if symbol else "MARKET-WIDE"
            print(f"[{sym_str}] {news.headline} -> Score: {news.sentiment_score:.4f} ({news.sentiment_label})")

if __name__ == "__main__":
    asyncio.run(run_news())
