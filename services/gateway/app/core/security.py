"""
Security utilities for authentication, encryption, and authorization.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union

import bcrypt
import pyotp
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.padding import PSS, PKCS1v15
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
    load_pem_public_key,
)
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Field encryption
fernet = Fernet(settings.FIELD_ENCRYPTION_KEY.encode())


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create JWT access token.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
        "jti": secrets.token_urlsafe(16),
    }

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_PRIVATE_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any],
    family_id: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT refresh token.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),
        "family_id": family_id,
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_PRIVATE_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Verify and decode JWT token.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY,
            algorithms=[settings.ALGORITHM],
        )

        # Check token type
        if payload.get("type") != token_type:
            return None

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            return None

        return payload
    except JWTError:
        return None


def hash_password(password: str) -> str:
    """
    Hash password using Argon2id.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash.
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_totp_secret() -> str:
    """
    Generate TOTP secret for 2FA.
    """
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str) -> str:
    """
    Get TOTP URI for QR code generation.
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=settings.TOTP_ISSUER)


def verify_totp_code(secret: str, code: str) -> bool:
    """
    Verify TOTP code.
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(code)


def encrypt_field(data: str) -> str:
    """
    Encrypt sensitive field data.
    """
    return fernet.encrypt(data.encode()).decode()


def decrypt_field(encrypted_data: str) -> str:
    """
    Decrypt sensitive field data.
    """
    return fernet.decrypt(encrypted_data.encode()).decode()


def hash_api_key(api_key: str) -> str:
    """
    Hash API key for storage (SHA-256).
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """
    Generate secure API key.
    """
    return f"nq_live_{secrets.token_urlsafe(32)}"


def generate_backup_codes(count: int = 10) -> list[str]:
    """
    Generate backup codes for 2FA.
    """
    codes = []
    for _ in range(count):
        code = secrets.token_hex(4).upper()
        hashed = bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode()
        codes.append(hashed)
    return codes


def verify_backup_code(hashed_code: str, provided_code: str) -> bool:
    """
    Verify backup code.
    """
    return bcrypt.checkpw(provided_code.encode(), hashed_code.encode())


def check_password_strength(password: str) -> Dict[str, Any]:
    """
    Check password strength using zxcvbn.
    """
    try:
        import zxcvbn

        result = zxcvbn.zxcvbn(password)
        return {
            "score": result["score"],  # 0-4
            "feedback": result["feedback"],
            "crack_time": result["crack_times_display"]["offline_slow_hashing_1e4_per_second"],
            "is_strong": result["score"] >= 3,
        }
    except ImportError:
        # Fallback if zxcvbn not available
        return {
            "score": 3 if len(password) >= 8 else 1,
            "feedback": {"warning": "", "suggestions": []},
            "crack_time": "unknown",
            "is_strong": len(password) >= 8,
        }


def check_pwned_password(password: str) -> bool:
    """
    Check if password has been pwned using k-anonymity.
    """
    try:
        import pwnedpasswords

        pwned_count = pwnedpasswords.check(password, anonymous=True)
        return pwned_count > 0
    except ImportError:
        # Skip check if library not available
        return False


def generate_rsa_keypair() -> tuple[str, str]:
    """
    Generate RSA key pair for JWT signing.
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return private_pem.decode(), public_pem.decode()


def load_rsa_keys(private_key_pem: str, public_key_pem: str) -> tuple[Any, Any]:
    """
    Load RSA keys from PEM strings.
    """
    private_key = load_pem_private_key(private_key_pem.encode(), password=None)
    public_key = load_pem_public_key(public_key_pem.encode())

    return private_key, public_key


def sign_data(data: str, private_key: Any) -> str:
    """
    Sign data with RSA private key.
    """
    signature = private_key.sign(
        data.encode(),
        PSS(mgf=hashes.MGF1(hashes.SHA256()), salt_length=32),
        hashes.SHA256(),
    )
    return signature.hex()


def verify_signature(data: str, signature: str, public_key: Any) -> bool:
    """
    Verify data signature with RSA public key.
    """
    try:
        public_key.verify(
            bytes.fromhex(signature),
            data.encode(),
            PSS(mgf=hashes.MGF1(hashes.SHA256()), salt_length=32),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False