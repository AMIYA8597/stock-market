from sqlalchemy import Float

content = """

class FeatureSet(Base):
    __tablename__ = "feature_sets"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    features_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class ModelRun(Base):
    __tablename__ = "model_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("experiments.id"), nullable=False)
    model_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("model_registry.id"))
    run_config: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class ModelMetric(Base):
    __tablename__ = "model_metrics"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_runs.id"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float | None] = mapped_column(Float)
    metric_metadata: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class PredictionOutcome(Base):
    __tablename__ = "prediction_outcomes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prediction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("predictions.id"), nullable=False, unique=True)
    realized_value: Mapped[str | None] = mapped_column(String)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class CalibrationReport(Base):
    __tablename__ = "calibration_reports"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_registry.id"), nullable=False)
    report_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class SignificanceReport(Base):
    __tablename__ = "significance_reports"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_registry.id"), nullable=False)
    report_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class EdgeReport(Base):
    __tablename__ = "edge_reports"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_registry.id"), nullable=False)
    report_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class LeakageAudit(Base):
    __tablename__ = "leakage_audits"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_registry.id"), nullable=False)
    report_data: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class DriftReport(Base):
    __tablename__ = "drift_reports"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_registry.id"), nullable=False)
    report_data: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class SignalDefinition(Base):
    __tablename__ = "signal_definitions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    definition_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class SignalEvent(Base):
    __tablename__ = "signal_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("signal_definitions.id"), nullable=False)
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id"), nullable=False, index=True)
    signal_value: Mapped[str | None] = mapped_column(String)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class NewsDocument(Base):
    __tablename__ = "news_documents"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url: Mapped[str | None] = mapped_column(String)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    content_hash: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)

class SentimentEvent(Base):
    __tablename__ = "sentiment_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("news_documents.id"), nullable=False)
    instrument_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("instruments.id"), index=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float)
    sentiment_metadata: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class ModelExplanation(Base):
    __tablename__ = "model_explanations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prediction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("predictions.id"), nullable=False)
    explanation_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class LLMEvidencePack(Base):
    __tablename__ = "llm_evidence_packs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pack_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class LLMEvaluation(Base):
    __tablename__ = "llm_evaluations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_pack_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("llm_evidence_packs.id"), nullable=False)
    evaluation_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
"""

import re
with open('d:/work/stock-market/backend/app/models/research.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Add Float to imports
text = text.replace('from sqlalchemy import Boolean, DateTime, String, ForeignKey, Integer', 'from sqlalchemy import Boolean, DateTime, String, ForeignKey, Integer, Float')

with open('d:/work/stock-market/backend/app/models/research.py', 'w', encoding='utf-8') as f:
    f.write(text + content)
