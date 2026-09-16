"""News and Sentiment endpoints router (GET /news/*)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.instrument import Instrument
from app.models.sentiment import NewsSentiment

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/{symbol}")
async def get_news_for_symbol(symbol: str, db: AsyncSession = Depends(get_db)):
    """Get scraped news and sentiment for a specific symbol."""
    clean_symbol = symbol.split(".")[0].upper()
    inst_res = await db.execute(
        select(Instrument).where(Instrument.symbol.startswith(clean_symbol))
    )
    instrument = inst_res.scalars().first()

    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol} not found")

    news_res = await db.execute(
        select(NewsSentiment)
        .where(NewsSentiment.symbol_id == instrument.id)
        .order_by(NewsSentiment.published_at.desc())
        .limit(50)
    )
    articles = news_res.scalars().all()

    result = []
    total_score = 0.0
    for a in articles:
        score = float(a.sentiment_score) if a.sentiment_score is not None else 0.0
        total_score += score
        result.append(
            {
                "id": a.id,
                "headline": a.headline,
                "source": a.source,
                "published_at": a.published_at.isoformat(),
                "sentiment_score": score,
                "sentiment_label": a.sentiment_label,
                "url": a.url,
            }
        )

    daily_mean = total_score / len(articles) if articles else 0.0

    return {"symbol": symbol, "daily_mean": daily_mean, "articles": result}
