from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.database.connection import Base


class ModelArtifact(Base):
    """Stores metadata for trained ML models."""
    __tablename__ = "model_artifact"

    id = Column(Integer, primary_key=True, index=True)
    symbol_id = Column(Integer, ForeignKey("instrument.id", ondelete="CASCADE"), nullable=False, index=True)
    model_type = Column(String(50), nullable=False) # e.g. "XGBoost", "LightGBM"
    version_tag = Column(String(50), nullable=False, unique=True, index=True) # e.g. "v1_20231015"
    artifact_path = Column(String(255), nullable=False) # disk path
    hyperparameters = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    instrument = relationship("Instrument")
