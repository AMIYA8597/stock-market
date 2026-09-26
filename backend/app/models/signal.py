import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class EnsembleSignal(Base):
    """Persisted output of the ensemble signal-fusion engine (see
    app.services.prediction_engine.build_ensemble_signal) for a symbol at a
    point in time. `inputs_used` is a JSON snapshot of the sub-scores that
    fed the fusion (technical/pattern/momentum/xgboost/sentiment) so a past
    signal's provenance can be audited later; `outcome` tracks whether the
    signal's direction was later realized (PENDING/WIN/LOSS)."""

    __tablename__ = "ensemble_signals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    signal: Mapped[float] = mapped_column(Numeric(8, 6), nullable=False)
    kelly_fraction: Mapped[float | None] = mapped_column(Numeric(8, 6))
    direction: Mapped[str | None] = mapped_column(String(20))
    confidence: Mapped[float | None] = mapped_column(Numeric(6, 4))
    regime_state: Mapped[int | None] = mapped_column(Integer)
    inputs_used: Mapped[dict | None] = mapped_column(JSON)
    outcome: Mapped[str] = mapped_column(String(20), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
