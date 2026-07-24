import asyncio

from sqlalchemy import select

from app.database.connection import async_session_factory
from app.models.sentiment import NewsSentiment
from app.tasks.sentiment_tasks import _update_news_sentiment_async


async def main():
    print("Starting sentiment analysis job...")
    result = await _update_news_sentiment_async()
    print(f"Job Result: {result}")

    # Verify DB output
    async with async_session_factory() as session:
        res = await session.execute(
            select(NewsSentiment).order_by(NewsSentiment.published_at.desc()).limit(10)
        )
        news = res.scalars().all()
        print("\n--- Top 10 Recent Sentiments ---")
        for n in news:
            print(f"[{n.source}] (Score: {n.sentiment_score:.3f} | {n.sentiment_label}) {n.headline[:80]}...")

if __name__ == "__main__":
    asyncio.run(main())
