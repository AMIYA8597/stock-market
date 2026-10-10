"""Short-lived, single-use email OTP codes for signup verification and
password reset. Codes are never stored in plaintext - only a bcrypt hash
of the code is persisted, mirroring how passwords themselves are handled."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class EmailOTP(Base):
    __tablename__ = "email_otps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)  # "signup" | "password_reset"
    otp_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # server_default mirrors migration c0698f36e21e; without it `alembic check`
    # (run in CI) reports drift and wants to drop the DB defaults.
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
