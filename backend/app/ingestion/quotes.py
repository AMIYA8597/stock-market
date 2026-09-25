import asyncio

from sqlalchemy.future import select

from app.database.connection import async_session_factory
from app.ingestion.logger import IngestionLogger
from app.ingestion.provider_manager import ProviderManager
from app.models.market import Instrument, InstrumentAlias, QuoteSnapshot


async def ingest_quotes(symbol: str, provider_name: str = "yfinance"):
    async with async_session_factory() as session:
        logger = IngestionLogger(session)
        run = await logger.start_run(engine_name="quotes", target=symbol)

        try:
            stmt = select(InstrumentAlias).join(Instrument).where(Instrument.canonical_symbol == symbol)
            res = await session.execute(stmt)
            alias = res.scalar_one_or_none()

            if not alias:
                raise ValueError(f"No alias found for canonical symbol {symbol}")

            provider = ProviderManager().get_provider(provider_name)

            quote = await provider.fetch_quote(alias.provider_symbol)

            snapshot = QuoteSnapshot(
                instrument_id=alias.instrument_id,
                price=quote["price"],
                bid=quote.get("bid"),
                ask=quote.get("ask"),
                volume=quote.get("volume"),
                provider=provider_name,
                freshness_status='valid',
                observed_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc),
                ingestion_run_id=run.id
            )
            session.add(snapshot)

            await session.commit()
            await logger.complete_run(run, rows_processed=1)
            print(f"Quote snapshot ingestion complete for {symbol}: {quote['price']}")

        except Exception as e:
            await logger.complete_run(run, rows_processed=0, error_message=str(e))
            print(f"Quote ingestion failed: {e}")

if __name__ == "__main__":
    asyncio.run(ingest_quotes("AAPL"))
