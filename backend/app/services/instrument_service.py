import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.market import Instrument, InstrumentAlias


class InstrumentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_canonical_instrument(self, symbol: str, name: str, currency: str, exchange_id: uuid.UUID) -> Instrument:
        """Get an existing canonical instrument or create a new one."""
        stmt = select(Instrument).where(Instrument.canonical_symbol == symbol)
        result = await self.session.execute(stmt)
        instrument = result.scalar_one_or_none()

        if instrument:
            return instrument

        instrument = Instrument(
            canonical_symbol=symbol,
            display_name=name,
            currency=currency,
            exchange_id=exchange_id,
            is_active=True
        )
        self.session.add(instrument)
        await self.session.commit()
        await self.session.refresh(instrument)
        return instrument

    async def resolve_symbol(self, provider: str, provider_symbol: str) -> uuid.UUID | None:
        """Resolve a provider-specific symbol to a canonical instrument UUID."""
        stmt = select(InstrumentAlias.instrument_id).where(
            InstrumentAlias.provider == provider,
            InstrumentAlias.provider_symbol == provider_symbol
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_alias(self, instrument_id: uuid.UUID, provider: str, provider_symbol: str) -> InstrumentAlias:
        """Add an alias for a canonical instrument."""
        alias = InstrumentAlias(
            instrument_id=instrument_id,
            provider=provider,
            provider_symbol=provider_symbol
        )
        self.session.add(alias)
        await self.session.commit()
        await self.session.refresh(alias)
        return alias
