import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
import yfinance as yf
from app.database.connection import async_session_factory
from app.services.instrument_service import InstrumentService
from app.models.market import Exchange
from sqlalchemy.future import select

async def ingest_universe():
    async with async_session_factory() as session:
        # Create default exchange
        stmt = select(Exchange).where(Exchange.code == "XNAS")
        result = await session.execute(stmt)
        exchange = result.scalar_one_or_none()
        if not exchange:
            exchange = Exchange(
                code="XNAS",
                name="NASDAQ",
                country="US",
                timezone="America/New_York"
            )
            session.add(exchange)
            await session.commit()
            await session.refresh(exchange)

        instrument_service = InstrumentService(session)
        
        # Fetch AAPL
        ticker = yf.Ticker("AAPL")
        info = ticker.info
        name = info.get("shortName", "Apple Inc.")
        currency = info.get("currency", "USD")

        instrument = await instrument_service.get_or_create_canonical_instrument(
            symbol="AAPL",
            name=name,
            currency=currency,
            exchange_id=exchange.id
        )

        await instrument_service.add_alias(
            instrument_id=instrument.id,
            provider="yfinance",
            provider_symbol="AAPL"
        )
        print(f"Ingested universe instrument: {instrument.canonical_symbol} ({instrument.display_name})")

if __name__ == "__main__":
    asyncio.run(ingest_universe())
