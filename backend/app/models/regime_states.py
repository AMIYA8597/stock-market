import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class RegimeState(Base):
    __tablename__ = "regime_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    viterbi_state: Mapped[int] = mapped_column(Integer, nullable=False)
    state_probs: Mapped[list] = mapped_column(JSON, nullable=False)
    conditional_vol: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    vol_forecast_5d: Mapped[float | None] = mapped_column(Numeric(10, 6))
    vol_forecast_21d: Mapped[float | None] = mapped_column(Numeric(10, 6))
