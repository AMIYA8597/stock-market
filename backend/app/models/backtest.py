from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text, dialects
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database.connection import Base
import uuid
import datetime

class BacktestJob(Base):
    __tablename__ = "backtest_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    
    strategy_name: Mapped[str] = mapped_column(String(255))
    strategy_params: Mapped[dict] = mapped_column(JSON, default={})
    universe: Mapped[list[str]] = mapped_column(JSON, default=[])
    
    date_from: Mapped[datetime.date] = mapped_column(DateTime)
    date_to: Mapped[datetime.date] = mapped_column(DateTime)
    initial_capital: Mapped[float] = mapped_column(Float, default=10000.0)
    
    status: Mapped[str] = mapped_column(String(50), default="QUEUED")  # QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED
    progress: Mapped[int] = mapped_column(Integer, default=0)
    
    queued_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    worker_id: Mapped[str] = mapped_column(String(255), nullable=True)
    error_code: Mapped[str] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    
    result_reference: Mapped[str] = mapped_column(String(255), nullable=True)
    results: Mapped[dict] = mapped_column(JSON, nullable=True)
