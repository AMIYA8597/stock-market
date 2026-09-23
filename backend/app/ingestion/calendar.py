import asyncio
import pandas_market_calendars as mcal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import date, timedelta
from app.database.connection import async_session_factory
from app.models.market import Exchange, MarketCalendar

async def ingest_calendar():
    async with async_session_factory() as session:
        stmt = select(Exchange).where(Exchange.code == "XNAS")
        result = await session.execute(stmt)
        exchange = result.scalar_one_or_none()
        
        if not exchange:
            print("Exchange XNAS not found.")
            return

        nyse = mcal.get_calendar('NYSE')
        start_date = date.today() - timedelta(days=30)
        end_date = date.today() + timedelta(days=30)
        
        schedule = nyse.schedule(start_date=start_date, end_date=end_date)
        
        count = 0
        for index, row in schedule.iterrows():
            session_date = index.date()
            stmt = select(MarketCalendar).where(
                MarketCalendar.exchange_id == exchange.id,
                MarketCalendar.session_date == session_date
            )
            res = await session.execute(stmt)
            if not res.scalar_one_or_none():
                mc = MarketCalendar(
                    exchange_id=exchange.id,
                    session_date=session_date,
                    is_open=True,
                    open_time=row['market_open'].to_pydatetime(),
                    close_time=row['market_close'].to_pydatetime(),
                    source="pandas_market_calendars"
                )
                session.add(mc)
                count += 1
        
        await session.commit()
        print(f"Ingested {count} calendar days for {exchange.code}")

if __name__ == "__main__":
    asyncio.run(ingest_calendar())
