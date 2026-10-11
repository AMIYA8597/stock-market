from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.connection import get_db
from app.models.identity import ApiKey, Organization, OrgMember, User

logger = logging.getLogger(__name__)
settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def ensure_personal_organization(db: AsyncSession, user: User) -> None:
    """Give a user a personal Organization + membership if they have none.

    Most endpoints (alerts history, billing, etc.) are organization-scoped
    and 403/empty without one. A user created outside the onboarding flow -
    a direct /auth/register call, or JIT provisioning from a bare Supabase
    JWT - would otherwise never get one and be permanently locked out of
    those endpoints.
    """
    existing = await db.execute(select(OrgMember).where(OrgMember.user_id == user.id))
    membership = existing.scalars().first()
    if membership:
        # Heals accounts that got a membership row created with the
        # lowercase "owner" bug below before it was fixed - role_hierarchy
        # only recognizes uppercase role names, so those accounts would
        # otherwise stay 403'd forever even after this fix ships.
        if membership.role != membership.role.upper():
            membership.role = membership.role.upper()
            await db.commit()
        return
    org = Organization(
        name=user.full_name or user.email.split("@")[0],
        slug=f"user-{user.id.hex}",
        status="active",
    )
    db.add(org)
    await db.flush()
    # role_hierarchy in dependencies.py's require_role() looks role names up
    # case-sensitively against uppercase keys ("OWNER", "VIEWER", ...) - a
    # lowercase "owner" here silently matched nothing, defaulted to level 0,
    # and made every require_role() check 403 regardless of the org/
    # membership actually existing. Matches the convention already used in
    # organizations.py's own owner-membership creation.
    db.add(OrgMember(organization_id=org.id, user_id=user.id, role="OWNER", status="active"))
    await db.commit()


class RequestContext:
    def __init__(
        self,
        user_id: str | None = None,
        organization_id: str | None = None,
        membership_id: str | None = None,
        organization_role: str | None = None,
        platform_role: str | None = None,
        plan_id: str | None = None,
        plan_name: str | None = None,
        entitlements: dict | None = None,
        auth_method: str = "anonymous",
        request_id: str | None = None,
    ):
        self.user_id = user_id
        self.organization_id = organization_id
        self.membership_id = membership_id
        self.organization_role = organization_role
        self.platform_role = platform_role
        self.plan_id = plan_id
        self.plan_name = plan_name
        self.entitlements = entitlements or {}
        self.auth_method = auth_method
        self.request_id = request_id


_jwks_cache: dict[str, Any] = {}


def _fetch_jwks() -> dict[str, Any] | None:
    """Fetch and cache the Supabase project's JWKS document, if configured.

    Supabase projects created with asymmetric (ES256/RS256) signing keys expose a
    JWKS endpoint at {SUPABASE_URL}/auth/v1/.well-known/jwks.json. Legacy projects
    still on the shared HS256 secret have no such endpoint; callers must fall back
    to verify_supabase_token's HS256 path in that case.

    Uses a synchronous httpx call — safe because this is called from the sync
    verify_supabase_token(), and the result is cached after the first success so
    subsequent calls return instantly without blocking the async event loop.
    """
    if _jwks_cache.get("keys"):
        return _jwks_cache
    if not settings.SUPABASE_URL:
        return None
    import httpx

    jwks_url = settings.SUPABASE_URL.rstrip("/") + "/auth/v1/.well-known/jwks.json"
    try:
        resp = httpx.get(jwks_url, timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
        if data.get("keys"):
            _jwks_cache.update(data)
            return _jwks_cache
    except Exception as exc:  # noqa: BLE001 - network/JWKS fetch failure, fall back to HS256
        logger.warning(f"Supabase JWKS fetch failed, falling back to HS256 secret: {exc}")
    return None


def verify_supabase_token(token: str) -> dict[str, Any]:
    """Verify Supabase JWT token signature and return payload.

    Prefers JWKS/asymmetric verification when the Supabase project exposes a JWKS
    endpoint (current Supabase default for new projects). Falls back to the legacy
    shared HS256 secret for projects still on that signing mode. Audience is always
    verified against Supabase's standard "authenticated" audience.
    """
    from app.core.test_state import is_test_mode

    try:
        header = jwt.get_unverified_header(token)
        jwks = None if is_test_mode() else _fetch_jwks()
        if jwks and header.get("kid"):
            key = next((k for k in jwks["keys"] if k.get("kid") == header["kid"]), None)
            if key is not None:
                payload = jwt.decode(
                    token,
                    key,
                    algorithms=[key.get("alg", "ES256")],
                    audience="authenticated",
                )
                return payload

        # Legacy/dev fallback: shared HS256 secret.
        secret = settings.SUPABASE_JWT_SECRET
        if is_test_mode() and not secret:
            from app.core.test_state import TEST_JWT_SECRET
            secret = TEST_JWT_SECRET
        if not secret:
            # JWKS verification didn't match (no kid in token, or JWKS
            # unavailable) and no HS256 fallback is configured. Rather than a
            # 500 (server misconfiguration), return 401 — the token simply
            # could not be verified with the available methods.
            logger.warning(
                "JWT has no JWKS kid match and SUPABASE_JWT_SECRET is not configured — "
                "token cannot be verified. Set SUPABASE_JWT_SECRET for HS256 fallback."
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials could not be verified",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_context(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    api_key: Annotated[str | None, Depends(api_key_header)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> RequestContext:
    """Resolve current context from token or API key."""
    req_id = getattr(request.state, "request_id", None)

    # 1. API Key Auth
    if api_key:
        import hashlib

        presented_hash = hashlib.sha256(api_key.encode()).hexdigest()
        result = await db.execute(
            select(ApiKey).where(ApiKey.key_hash == presented_hash, ApiKey.status == "active")
        )
        api_key_record = result.scalars().first()
        if not api_key_record:
            raise HTTPException(status_code=401, detail="Invalid API Key")

        ctx = RequestContext(
            user_id=str(api_key_record.created_by_id) if api_key_record.created_by_id else None,
            organization_id=str(api_key_record.organization_id),
            auth_method="API_KEY",
            request_id=req_id
        )

        # Set RLS context for the transaction
        if ctx.user_id:
            await db.execute(
                text("SELECT set_config('request.jwt.claim.sub', :uid, true)"),
                {"uid": ctx.user_id}
            )

        return ctx

    # 2. Supabase JWT Auth
    if token:
        try:
            payload = verify_supabase_token(token)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("JWT verification crashed: %s", exc, exc_info=True)
            raise HTTPException(status_code=401, detail="Authentication failed") from exc
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        # In a real flow, we map `sub` (auth_id) to our internal User
        try:
            result = await db.execute(select(User).where(User.auth_id == sub))
        except Exception as exc:
            logger.error("DB query for user by auth_id failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail="Database error during authentication") from exc
        user = result.scalars().first()
        if not user:
            # A valid Supabase-signed token proves this account is real and
            # confirmed - so a missing local row means our own /auth/register
            # never ran for it (e.g. a client that called supabase-js
            # directly), not that the user is unauthorized. Provision it now
            # instead of hard-failing every authenticated request forever.
            email = payload.get("email")
            if not email:
                raise HTTPException(status_code=401, detail="Token missing email claim")
            user = User(
                email=email,
                full_name=payload.get("user_metadata", {}).get("full_name"),
                auth_id=sub,
                status="active",
            )
            db.add(user)
            try:
                await db.commit()
                await db.refresh(user)
            except Exception:
                await db.rollback()
                # Lost a race with a concurrent request provisioning the same
                # user; re-fetch rather than surface a spurious 500.
                result = await db.execute(select(User).where(User.auth_id == sub))
                user = result.scalars().first()
                if not user:
                    raise HTTPException(status_code=401, detail="User profile not found")

        if user.status != "active":
            raise HTTPException(status_code=403, detail="User account suspended")

        # Authoritative OTP-verification gate. /auth/login already checks
        # this before issuing tokens, but a Supabase JWT can also be
        # obtained by calling Supabase's own auth API directly with the
        # public anon key (bypassing our /auth/register + OTP flow
        # entirely) - so this must be enforced here too, since this is the
        # function every protected endpoint actually goes through. /auth/me
        # is exempted so the frontend can detect "authenticated but
        # unverified" and prompt for the OTP rather than getting a bare 403.
        if not user.email_verified and not request.url.path.rstrip("/").endswith("/auth/me"):
            raise HTTPException(
                status_code=403,
                detail="Please verify your email before continuing. Check your inbox for the verification code.",
            )

        # Self-healing: also covers accounts created before this org-
        # provisioning existed, not just ones JIT-provisioned just above.
        try:
            await ensure_personal_organization(db, user)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(
                "ensure_personal_organization failed for user %s: %s",
                user.id, exc, exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to provision user organization",
            ) from exc

        # Resolve organization
        org_id = request.headers.get("X-Organization-ID")

        membership = None
        if org_id:
            res = await db.execute(select(OrgMember).where(
                OrgMember.user_id == user.id,
                OrgMember.organization_id == org_id,
                OrgMember.status == "active"
            ))
            membership = res.scalars().first()
            if not membership:
                raise HTTPException(status_code=403, detail="Not a member of this organization")
        else:
            # Get default organization
            res = await db.execute(select(OrgMember).where(
                OrgMember.user_id == user.id,
                OrgMember.status == "active"
            ).limit(1))
            membership = res.scalars().first()
            if membership:
                org_id = str(membership.organization_id)

        ctx = RequestContext(
            user_id=str(user.id),
            organization_id=org_id,
            membership_id=str(membership.id) if membership else None,
            organization_role=membership.role if membership else None,
            auth_method="SUPABASE_JWT",
            request_id=req_id
        )

        # Set RLS context for the transaction
        if ctx.user_id:
            await db.execute(
                text("SELECT set_config('request.jwt.claim.sub', :uid, true)"),
                {"uid": ctx.user_id}
            )

        return ctx

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ── Field Encryption ──

_fernet_cipher = None


def _get_fernet_cipher():
    global _fernet_cipher
    if _fernet_cipher is not None:
        return _fernet_cipher
    settings = get_settings()
    if not settings.FIELD_ENCRYPTION_KEY:
        if settings.ENCRYPTION_ENABLED:
            raise RuntimeError("FIELD_ENCRYPTION_KEY required when ENCRYPTION_ENABLED=true")
        return None
    try:
        from cryptography.fernet import Fernet
        _fernet_cipher = Fernet(settings.FIELD_ENCRYPTION_KEY.encode())
    except ImportError:
        if settings.ENCRYPTION_ENABLED:
            raise RuntimeError("cryptography is required when ENCRYPTION_ENABLED=true")
        return None
    except Exception as e:
        raise RuntimeError(f"Invalid FIELD_ENCRYPTION_KEY: {e}")
    return _fernet_cipher


def encrypt_field(plaintext: str) -> str:
    settings = get_settings()
    if not settings.ENCRYPTION_ENABLED:
        return plaintext
    cipher = _get_fernet_cipher()
    if cipher is None:
        return plaintext
    try:
        return cipher.encrypt(plaintext.encode()).decode()
    except Exception as e:
        logger.error("encrypt_field_error error=%s", str(e))
        raise ValueError(f"Field encryption failed: {e}") from e


def decrypt_field(ciphertext: str) -> str:
    settings = get_settings()
    if not settings.ENCRYPTION_ENABLED:
        return ciphertext
    cipher = _get_fernet_cipher()
    if cipher is None:
        return ciphertext
    try:
        return cipher.decrypt(ciphertext.encode()).decode()
    except Exception as e:
        logger.error("decrypt_field_error error=%s", str(e))
        raise ValueError("Field decryption failed: invalid token or key") from e
