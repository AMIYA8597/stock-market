import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class ModelMetric(Base):
    __tablename__ = "model_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("model_artifacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    accuracy: Mapped[float | None] = mapped_column(Numeric(6, 4))
    precision: Mapped[float | None] = mapped_column(Numeric(6, 4))
    recall: Mapped[float | None] = mapped_column(Numeric(6, 4))
    auc: Mapped[float | None] = mapped_column(Numeric(6, 4))
    sharpe: Mapped[float | None] = mapped_column(Numeric(8, 4))
    cost_adjusted_sharpe: Mapped[float | None] = mapped_column(Numeric(8, 4))
    regime_breakdown: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
