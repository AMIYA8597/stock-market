import asyncio
from datetime import datetime, timedelta

from sqlalchemy.future import select

from app.database.connection import async_session_factory
from app.ingestion.logger import IngestionLogger
from app.ingestion.provider_manager import ProviderManager
from app.models.market import OHLCV, Instrument, InstrumentAlias


async def ingest_historical(symbol: str, provider_name: str = "yfinance", days: int = 30):
    async with async_session_factory() as session:
        logger = IngestionLogger(session)
        run = await logger.start_run(engine_name="historical", target=symbol)

        try:
            # Resolve canonical symbol
            stmt = select(InstrumentAlias).join(Instrument).where(Instrument.canonical_symbol == symbol)
            res = await session.execute(stmt)
            alias = res.scalar_one_or_none()

            if not alias:
                raise ValueError(f"No alias found for canonical symbol {symbol}")

            provider = ProviderManager().get_provider(provider_name)
            end = datetime.now()
            start = end - timedelta(days=days)

            df = await provider.fetch_historical_ohlcv(alias.provider_symbol, start, end)
            df = df.dropna()

            rows_inserted = 0
            for index, row in df.iterrows():
                # Upsert logic simplified to simple insert, assuming clean DB or handling IntegrityError
                ohlcv = OHLCV(
                    instrument_id=alias.instrument_id,
                    timestamp=index.to_pydatetime(),
                    open=row['Open'],
                    high=row['High'],
                    low=row['Low'],
                    close=row['Close'],
                    interval='1d',
                    volume=row['Volume'],
                    provider=provider_name,
                    ingestion_run_id=run.id
                )
                session.add(ohlcv)
                rows_inserted += 1

            await session.commit()
            await logger.complete_run(run, rows_processed=rows_inserted)
            print(f"Historical ingestion complete: {rows_inserted} rows for {symbol}")

        except Exception as e:
            await logger.complete_run(run, rows_processed=0, error_message=str(e))
            print(f"Historical ingestion failed: {e}")

if __name__ == "__main__":
    asyncio.run(ingest_historical("AAPL"))
