"""SQLAlchemy custom types for database field encryption."""

from typing import Any, Optional

from sqlalchemy.types import String, TypeDecorator
from sqlalchemy.engine.interfaces import Dialect

from app.core.security import encrypt_field, decrypt_field

class EncryptedString(TypeDecorator):
    """
    SQLAlchemy type that encrypts/decrypts strings using Fernet on the fly.
    """
    impl = String
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect: Dialect) -> Optional[str]:
        if value is None:
            return None
        return encrypt_field(value)

    def process_result_value(self, value: Optional[str], dialect: Dialect) -> Optional[str]:
        if value is None:
            return None
        try:
            return decrypt_field(value)
        except Exception:
            return value  # Fallback to returning raw if decryption fails (e.g., plaintext migration)
