<<<<<<< HEAD
"""User model with enterprise security features."""
=======
"""User model with role-based access control."""
>>>>>>> 10e1aa79ae3f95f38345cbdf853c86957900630c

from __future__ import annotations

from datetime import datetime, timezone
<<<<<<< HEAD
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
=======

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
>>>>>>> 10e1aa79ae3f95f38345cbdf853c86957900630c

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

<<<<<<< HEAD
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(Text, nullable=False)  # AES-256-GCM encrypted
    email_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)  # SHA-256, for lookups
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)  # argon2id
    totp_secret: Mapped[str] = mapped_column(Text)  # encrypted
    is_2fa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="ANALYST")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
=======
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
>>>>>>> 10e1aa79ae3f95f38345cbdf853c86957900630c
    )

    # Relationships
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    backtest_results = relationship("BacktestResult", back_populates="user", cascade="all, delete-orphan")
<<<<<<< HEAD
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    backup_codes = relationship("BackupCode", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email_hash='{self.email_hash[:10]}...', role='{self.role}')>"


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)  # SHA-256 of token
    family_id: Mapped[str] = mapped_column(String(36), nullable=False)  # for reuse detection
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationship
    user = relationship("User", back_populates="refresh_tokens")


class BackupCode(Base):
    __tablename__ = "backup_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)  # bcrypt
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Relationship
    user = relationship("User", back_populates="backup_codes")
=======

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
>>>>>>> 10e1aa79ae3f95f38345cbdf853c86957900630c
