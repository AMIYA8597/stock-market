import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class MLPrediction(Base):
    """A single model prediction at a point in time, later back-filled with
    `actual_return` once the forecast horizon has elapsed, so realized
    accuracy (precision/recall/RMSE/drift) can be computed honestly from
    real outcomes rather than reported at inference time."""

    __tablename__ = "ml_predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("instruments.id", ondelete="SET NULL"), index=True
    )
    model_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    raw_signal: Mapped[float | None] = mapped_column(Numeric(8, 6))
    p50_return: Mapped[float | None] = mapped_column(Numeric(10, 6))
    actual_return: Mapped[float | None] = mapped_column(Numeric(10, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
