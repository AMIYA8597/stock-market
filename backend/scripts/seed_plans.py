import asyncio
import json
from decimal import Decimal

from sqlalchemy import select

from app.database.connection import async_session_factory
from app.models.billing import Plan


async def seed_plans():
    async with async_session_factory() as db:
        # Check if already seeded
        result = await db.execute(select(Plan))
        if result.scalars().first():
            print("Plans already seeded.")
            return

        plans = [
            Plan(
                name="Free",
                description="Basic access to market data",
                price_inr=Decimal("0.00"),
                interval="monthly",
                features_json=json.dumps(["Basic Screening", "End-of-day Data", "1 Watchlist"]),
            ),
            Plan(
                name="Pro",
                description="Advanced tools and ML signals",
                price_inr=Decimal("499.00"),
                interval="monthly",
                features_json=json.dumps(
                    ["Real-time Data", "ML Predictions", "Unlimited Watchlists", "Backtesting"]
                ),
            ),
            Plan(
                name="Institutional",
                description="API access and raw data export",
                price_inr=Decimal("1999.00"),
                interval="monthly",
                features_json=json.dumps(
                    ["API Access", "Raw Data Export", "Custom Models", "Priority Support"]
                ),
            ),
        ]
        db.add_all(plans)
        await db.commit()
        print("Plans seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_plans())
