from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import relationship

from app.database.connection import Base


class ModelMetric(Base):
    """Stores out-of-sample evaluation metrics for a model artifact."""
    __tablename__ = "model_metric"

    id = Column(Integer, primary_key=True, index=True)
    artifact_id = Column(Integer, ForeignKey("model_artifact.id", ondelete="CASCADE"), nullable=False, index=True)

    # Standard Metrics
    accuracy = Column(Float, nullable=False)
    precision = Column(Float, nullable=False)
    recall = Column(Float, nullable=False)
    auc = Column(Float, nullable=False)
    sharpe = Column(Float, nullable=False)

    # Trading Metrics
    cost_adjusted_sharpe = Column(Float, nullable=True)
    regime_breakdown = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    artifact = relationship("ModelArtifact")
