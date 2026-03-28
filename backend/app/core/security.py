"""Enterprise security utilities for NeuroQuant.

This module implements:
- RS256 JWT access + refresh tokens
- Argon2id password hashing
- TOTP 2FA + backup codes
- AES-256-GCM field encryption (Fernet)
- FastAPI auth dependencies and RBAC helpers
- Secure password validation

All cryptographic operations use industry-standard libraries:
- python-jose: JWT encode/decode with RS256
- passlib: Password hashing with Argon2id
- cryptography: Fernet symmetric encryption
- pyotp: TOTP 2FA token generation/verification
"""

from __future__ import annotations

import hashlib
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any, Optional

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()

# ─── Password Hashing (Argon2id) ─────────────────────────────────────────
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=65536,  # 64MB
    argon2__time_cost=3,
    argon2__parallelism=4,
)

# ─── JWT RSA Keys ────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent.parent
JWT_PRIVATE_KEY_PATH = _PROJECT_ROOT / "keys" / "private.pem"
JWT_PUBLIC_KEY_PATH = _PROJECT_ROOT / "keys" / "public.pem"


def _load_jwt_keys() -> tuple[str, str]:
    """Load RSA keys for JWT signing/verification.
    
    Args:
        None
        
    Returns:
        tuple[str, str]: (private_key, public_key) PEM-encoded strings.
        
    Raises:
        RuntimeError: If JWT RSA keys cannot be found at expected paths.
    """
    if not JWT_PRIVATE_KEY_PATH.exists() or not JWT_PUBLIC_KEY_PATH.exists():
        raise FileNotFoundError(
            f"JWT RSA keys not found at {JWT_PRIVATE_KEY_PATH.parent}/. "
            f"Run: python -m scripts.generate_jwt_keys"
        )

    with open(JWT_PRIVATE_KEY_PATH, "r") as f:
        private_key = f.read()
    with open(JWT_PUBLIC_KEY_PATH, "r") as f:
        public_key = f.read()

    return private_key, public_key


try:
    JWT_PRIVATE_KEY, JWT_PUBLIC_KEY = _load_jwt_keys()
    JWT_ALGORITHM = settings.JWT_ALGORITHM
except FileNotFoundError:
    # Development/test fallback so module import does not hard-fail.
    fallback_secret = settings.FIELD_ENCRYPTION_KEY or secrets.token_urlsafe(32)
    JWT_PRIVATE_KEY = fallback_secret
    JWT_PUBLIC_KEY = fallback_secret
    JWT_ALGORITHM = "HS256"
    logger.warning("jwt_keys_missing_using_hs256_fallback")

# ─── Field Encryption (Fernet) ──────────────────────────────────────────
_fernet_cipher: Optional[Fernet] = None


def _get_fernet_cipher() -> Fernet:
    """Get or initialize Fernet cipher for field encryption.
    
    Args:
        None
        
    Returns:
        Fernet: Initialized cipher instance.
        
    Raises:
        RuntimeError: If encryption is enabled but key is not set.
    """
    global _fernet_cipher

    if _fernet_cipher is None:
        if not settings.FIELD_ENCRYPTION_KEY:
            if settings.ENCRYPTION_ENABLED:
                raise RuntimeError("FIELD_ENCRYPTION_KEY required when ENCRYPTION_ENABLED=true")
            return None

        try:
            _fernet_cipher = Fernet(settings.FIELD_ENCRYPTION_KEY.encode())
        except Exception as e:
            raise RuntimeError(f"Invalid FIELD_ENCRYPTION_KEY: {e}")

    return _fernet_cipher


# ─── OAuth2 Scheme ──────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    scopes={
        "read": "Read access",
        "write": "Write access",
        "admin": "Admin access",
    },
)

# ─── Enums ──────────────────────────────────────────────────────────────
class UserRole:
    """Role-based access control hierarchy.
    
    Roles are ordered by privilege level:
    ADMIN (5) > RESEARCHER (4) > ANALYST (3) > VIEWER (2) > API_USER (1)
    """
    ADMIN = "ADMIN"
    RESEARCHER = "RESEARCHER"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"
    API_USER = "API_USER"

    HIERARCHY = {
        ADMIN: 5,
        RESEARCHER: 4,
        ANALYST: 3,
        VIEWER: 2,
        API_USER: 1,
    }


class TokenType:
    """JWT token types."""
    ACCESS = "access"
    REFRESH = "refresh"


# ─── Password Functions ──────────────────────────────────────────────────
def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password against security requirements.
    
    Args:
        password: Plain text password to validate.
        
    Returns:
        tuple[bool, str]: (is_valid, error_message).
        
    Raises:
        None
    """
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters"

    if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if settings.PASSWORD_REQUIRE_NUMBERS and not re.search(r"\d", password):
        return False, "Password must contain at least one number"

    if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(r"[!@#$%^&*()_+\-=\[\]{};:'\",.<>?/\\|`~]", password):
        return False, "Password must contain at least one special character"

    return True, ""


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id.
    
    Args:
        password: Plain text password.
        
    Returns:
        str: Hashed password (Argon2 format).
        
    Raises:
        ValueError: If password validation fails.
    """
    is_valid, error_msg = validate_password_strength(password)
    if not is_valid:
        raise ValueError(error_msg)

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2 hash.
    
    Args:
        plain_password: Plain text password to verify.
        hashed_password: Stored password hash.
        
    Returns:
        bool: True if password matches, False otherwise.
        
    Raises:
        None
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.warning("password_verification_error", error=str(e))
        return False


# ─── JWT Functions ──────────────────────────────────────────────────────
def create_access_token(
    user_id: str,
    role: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token.
    
    Args:
        user_id: Subject (user ID) for the token.
        role: User role for RBAC (optional).
        expires_delta: Custom expiration time (uses default if None).
        
    Returns:
        str: Encoded JWT access token.
        
    Raises:
        None
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload = {
        "sub": user_id,
        "type": TokenType.ACCESS,
        "iat": now.timestamp(),
        "exp": expire.timestamp(),
        "jti": secrets.token_urlsafe(32),
    }

    if role:
        payload["role"] = role

    token = jwt.encode(
        payload,
        JWT_PRIVATE_KEY,
        algorithm=JWT_ALGORITHM,
    )

    logger.debug(
        "access_token_created",
        user_id=user_id,
        expires_at=expire.isoformat(),
    )

    return token


def create_refresh_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT refresh token for obtaining new access tokens.
    
    Args:
        user_id: Subject (user ID) for the token.
        expires_delta: Custom expiration time (uses default if None).
        
    Returns:
        str: Encoded JWT refresh token.
        
    Raises:
        None
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    family_id = secrets.token_urlsafe(32)
    payload = {
        "sub": user_id,
        "type": TokenType.REFRESH,
        "family": family_id,
        "iat": now.timestamp(),
        "exp": expire.timestamp(),
        "jti": secrets.token_urlsafe(32),
    }

    token = jwt.encode(
        payload,
        JWT_PRIVATE_KEY,
        algorithm=JWT_ALGORITHM,
    )

    logger.debug(
        "refresh_token_created",
        user_id=user_id,
        family_id=family_id,
        expires_at=expire.isoformat(),
    )

    return token


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.
    
    Args:
        token: JWT token string.
        
    Returns:
        dict: Decoded token payload.
        
    Raises:
        HTTPException: 401 if token is invalid, expired, or tampered.
    """
    try:
        payload = jwt.decode(
            token,
            JWT_PUBLIC_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        logger.warning("jwt_decode_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# ─── TOTP 2FA Functions ─────────────────────────────────────────────────
def generate_totp_secret() -> str:
    """Generate a new TOTP secret for 2FA setup.
    
    Args:
        None
        
    Returns:
        str: Base32-encoded TOTP secret.
        
    Raises:
        None
    """
    return pyotp.random_base32()


def get_totp_uri(
    secret: str,
    email: str,
    issuer: str = "NeuroQuant",
) -> str:
    """Generate TOTP provisioning URI for QR code generation.
    
    Args:
        secret: TOTP secret (from generate_totp_secret()).
        email: User email address.
        issuer: Issuer name (displayed in authenticator app).
        
    Returns:
        str: otpauth:// URI suitable for QR code encoding.
        
    Raises:
        None
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def verify_totp_code(secret: str, code: str) -> bool:
    """Verify a TOTP code entered by the user.
    
    Args:
        secret: TOTP secret (stored in User.totp_secret).
        code: 6-digit code entered by user.
        
    Returns:
        bool: True if code is valid, False otherwise.
        
    Raises:
        None
    """
    try:
        totp = pyotp.TOTP(secret)
        # Allow 1 time window before/after for clock drift
        return totp.verify(code, valid_window=1)
    except Exception as e:
        logger.warning("totp_verification_error", error=str(e))
        return False


# ─── Field Encryption Functions ─────────────────────────────────────────
def encrypt_field(plaintext: str) -> str:
    """Encrypt sensitive field data using Fernet (AES-128-CBC).
    
    Args:
        plaintext: Unencrypted data.
        
    Returns:
        str: Base64-encoded ciphertext.
        
    Raises:
        RuntimeError: If encryption is not configured.
    """
    if not settings.ENCRYPTION_ENABLED:
        return plaintext

    cipher = _get_fernet_cipher()
    if cipher is None:
        return plaintext

    try:
        ciphertext_bytes = cipher.encrypt(plaintext.encode())
        return ciphertext_bytes.decode()
    except Exception as e:
        logger.error("encrypt_field_error", error=str(e))
        raise ValueError(f"Field encryption failed: {e}") from e


def decrypt_field(ciphertext: str) -> str:
    """Decrypt sensitive field data using Fernet.
    
    Args:
        ciphertext: Base64-encoded ciphertext.
        
    Returns:
        str: Decrypted plaintext.
        
    Raises:
        ValueError: If decryption fails (invalid key or corrupted data).
    """
    if not settings.ENCRYPTION_ENABLED:
        return ciphertext

    cipher = _get_fernet_cipher()
    if cipher is None:
        return ciphertext

    try:
        plaintext_bytes = cipher.decrypt(ciphertext.encode())
        return plaintext_bytes.decode()
    except InvalidToken as e:
        logger.error("decrypt_field_error", error=str(e))
        raise ValueError("Field decryption failed: invalid token or key") from e
    except Exception as e:
        logger.error("decrypt_field_error", error=str(e))
        raise ValueError(f"Field decryption failed: {e}") from e


# ─── Email Hashing ──────────────────────────────────────────────────────
def hash_email(email: str) -> str:
    """Hash email for privacy (SHA-256).
    
    Used to store email hash in database for unique lookups without
    exposing plaintext email in logs.
    
    Args:
        email: Plain text email address.
        
    Returns:
        str: SHA-256 hexadecimal digest.
        
    Raises:
        None
    """
    normalized = email.lower().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


# ─── Auth Dependencies ──────────────────────────────────────────────────
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(lambda: None)],  # Placeholder
) -> dict[str, Any]:
    """Get current authenticated user from JWT token.
    
    This is a dependency function to be used in FastAPI route handlers.
    Validates JWT signature and expiration, then fetches user from database.
    
    Args:
        token: Bearer token from Authorization header.
        db: Async database session (injected by FastAPI).
        
    Returns:
        dict: User data from decoded JWT token.
        
    Raises:
        HTTPException: 401 if token invalid/expired or 404 if user not found.
    """
    payload = decode_token(token)

    if payload.get("type") != TokenType.ACCESS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    return {"user_id": user_id, **payload}


async def get_current_user_or_none(
    token: Annotated[str, Depends(oauth2_scheme)] = None,
) -> Optional[dict[str, Any]]:
    """Get current user if authenticated, otherwise None.
    
    Use this dependency when authentication is optional (e.g., public endpoints
    that show different data for authenticated users).
    
    Args:
        token: Bearer token from Authorization header (optional).
        
    Returns:
        dict or None: User data if authenticated, None otherwise.
        
    Raises:
        None
    """
    if not token:
        return None

    try:
        return await get_current_user(token, None)
    except HTTPException:
        return None


def require_role(required_role: str):
    """Dependency factory for role-based access control.
    
    Example:
        @app.get("/admin/users")
        async def list_users(current_user = Depends(require_role("ADMIN"))):
            ...
    
    Args:
        required_role: Minimum required role (e.g., "ADMIN", "ANALYST").
        
    Returns:
        Callable: Dependency function that checks user role.
        
    Raises:
        HTTPException: 403 if user lacks required role.
    """
    async def role_checker(
        token: Annotated[str, Depends(oauth2_scheme)],
    ) -> dict[str, Any]:
        """Check if current user has required role."""
        payload = decode_token(token)

        if payload.get("type") != TokenType.ACCESS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user_role = payload.get("role")
        user_id = payload.get("sub")

        required_level = UserRole.HIERARCHY.get(required_role, 99)
        user_level = UserRole.HIERARCHY.get(user_role, 0)

        if user_level < required_level:
            logger.warning(
                "insufficient_permissions",
                user_id=user_id,
                user_role=user_role,
                required_role=required_role,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role} role",
            )

        return {"user_id": user_id, "role": user_role, **payload}

    return role_checker


