from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import UUID as SQLA_UUID
from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class EmailJob(Base):
    __tablename__ = "email_jobs"

    id: Mapped[UUID] = mapped_column(SQLA_UUID(as_uuid=True), primary_key=True, default=uuid4)
    to_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    template: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(String(4000), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="queued", nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
