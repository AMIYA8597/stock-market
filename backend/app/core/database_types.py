"""SQLAlchemy custom types for database field encryption."""

from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import String, TypeDecorator

from app.core.security import decrypt_field, encrypt_field


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy type that encrypts/decrypts strings using Fernet on the fly.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        return encrypt_field(value)

    def process_result_value(self, value: str | None, dialect: Dialect) -> str | None:
        if value is None:
            return None
        try:
            return decrypt_field(value)
        except Exception:
            return (
                value  # Fallback to returning raw if decryption fails (e.g., plaintext migration)
            )
