"""
SQLAlchemy ORM models for the gateway service.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, UUID, Numeric, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    """
    User model with enterprise security features.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    email_hash = Column(String(64), unique=True, nullable=False)  # SHA-256 hash for lookups
    password_hash = Column(String(255), nullable=False)
    totp_secret = Column(Text)  # Encrypted TOTP secret
    is_2fa_enabled = Column(Boolean, default=False, nullable=False)
    role = Column(String(50), default="ANALYST", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified_at = Column(DateTime(timezone=True))
    last_login_at = Column(DateTime(timezone=True))
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    saved_screens = relationship("SavedScreen", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


class RefreshToken(Base):
    """
    Refresh token model for session management.
    """
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(Integer, nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False)  # SHA-256 hash
    family_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, family_id={self.family_id})>"


class BackupCode(Base):
    """
    Backup codes for 2FA recovery.
    """
    __tablename__ = "backup_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(Integer, nullable=False, index=True)
    code_hash = Column(String(255), nullable=False)  # bcrypt hash
    used_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<BackupCode(id={self.id}, user_id={self.user_id})>"


class AuditLog(Base):
    """
    Immutable audit log with hash chaining for integrity.
    """
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    user_id = Column(Integer, index=True)
    session_id = Column(String(255))
    ip_address = Column(String(45))  # IPv6 support
    user_agent = Column(Text)
    resource = Column(String(255))
    action = Column(String(100))
    details = Column(Text)  # JSON string
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text)
    prev_hash = Column(String(64))  # Previous entry hash
    row_hash = Column(String(64), unique=True, nullable=False)  # Current entry hash

    def __repr__(self):
        return f"<AuditLog(id={self.id}, event_type={self.event_type}, user_id={self.user_id})>"


class Alert(Base):
    """
    Alert configuration model.
    """
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    condition = Column(String(100), nullable=False)  # price_above, price_below, etc.
    threshold = Column(Integer, nullable=False)  # In paisa
    is_active = Column(Boolean, default=True, nullable=False)
    notification_channels = Column(String(255), default="in_app")  # comma-separated
    last_triggered_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Alert(id={self.id}, symbol={self.symbol}, condition={self.condition})>"