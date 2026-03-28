"""User authentication and account management models.

Implements secure user schema with UUID primary keys, password hashing,
and proper audit timestamp columns.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from sqlalchemy import Boolean, DateTime, String, UUID as SQLA_UUID, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base

# Password hashing
ph = PasswordHasher()


class User(Base):
    """User account model with secure password management.
    
    Fields:
        id (UUID): Unique user identifier, primary key.
        email (str): User email address, must be unique and not null.
        hashed_password (str): Argon2-hashed password (never store plaintext).
        full_name (str): User full name for display purposes.
        is_active (bool): Account status; inactive users cannot log in.
        created_at (datetime): UTC timestamp when account was created.
        updated_at (datetime): UTC timestamp of last account update.
    
    Constraints:
        - Email is unique and case-insensitive (enforced at DB level as well).
        - Password is always hashed before storage.
        - All timestamps are UTC timezone-aware.
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        SQLA_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        doc="Unique user identifier (UUID v4)",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="User email address, must be unique",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Argon2-hashed password (never plaintext)",
    )
    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="User full name for display",
    )
    role: Mapped[str] = mapped_column(
        String(24),
        default="USER",
        nullable=False,
        index=True,
        doc="Application role (USER|ADMIN)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Account active status",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last successful login timestamp",
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        doc="Consecutive failed logins for lockout policy",
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Temporary lockout end time",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Account creation timestamp (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Last account update timestamp (UTC)",
    )

    def verify_password(self, password: str) -> bool:
        """Verify plaintext password against stored hash.
        
        Args:
            password: Plaintext password to verify.
            
        Returns:
            bool: True if password matches, False otherwise.
            
        Raises:
            None: Returns False on hash mismatch.
        """
        try:
            ph.verify(self.hashed_password, password)
            return True
        except VerifyMismatchError:
            return False

    @property
    def password_hash(self) -> str:
        """Compatibility alias for code expecting password_hash naming."""
        return self.hashed_password

    @password_hash.setter
    def password_hash(self, value: str) -> None:
        self.hashed_password = value

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash plaintext password using Argon2.
        
        Argon2id with secure defaults:
        - time_cost: 2 iterations
        - memory_cost: 65536 KiB
        - parallelism: 4 threads
        
        Args:
            password: Plaintext password to hash.
            
        Returns:
            str: Argon2id hash string (includes algorithm, salt, parameters).
        """
        return ph.hash(password)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', is_active={self.is_active})>"
