════════════════════════════════════════════════════════════════════════════════
PHASE 2 — AUTHENTICATION SERVICE & USER MANAGEMENT
════════════════════════════════════════════════════════════════════════════════

This phase implements a complete authentication system with:
- User registration with email verification
- JWT-based login (RS256 signature)
- Refresh token rotation with family tracking
- TOTP 2FA setup and verification
- Secure password hashing (Argon2id)
- Field-level encryption (AES-256 via Fernet)
- Token blacklisting for logout
- Password reset flow

════════════════════════════════════════════════════════════════════════════════
FILES TO CREATE
════════════════════════════════════════════════════════════════════════════════

### 1. Backend Core Configuration (services/gateway/app/core/config.py)
Purpose: Pydantic Settings configuration for entire application
Size: ~200 lines
Key Settings:
  - DATABASE_URL (async SQLAlchemy URL)
  - REDIS_URL (cache + Celery)
  - JWT config (RS256 keys, expiry times)
  - Password policy (minEntropy, zxcvbn scoring)
  - CORS origins whitelist
  - Environment-specific configs (dev/prod/test)

### 2. Security Module (services/gateway/app/core/security.py)
Purpose: JWT, encryption, password hashing utilities
Size: ~400 lines
Functions:
  - create_access_token(user_id: UUID) → JWT
  - verify_access_token(token: str) → UUID or raises
  - create_refresh_token(user_id: UUID) → JWT + family_id
  - verify_refresh_token(token: str) → Tuple[UUID, family_id]
  - hash_password(password: str) → Argon2id hash
  - verify_password(password: str, hash: str) → bool
  - encrypt_field(data: str, key: str) → encrypted
  - decrypt_field(encrypted: str, key: str) → plaintext
  - generate_totp_secret() → base32 secret
  - verify_totp(secret: str, code: str) → bool
  - create_backup_codes() → List[str] (16 codes)
  - hash_backup_code(code: str) → hash
  - verify_backup_code(code: str, hash: str) → bool

### 3. User Model (services/gateway/app/models/user.py)
Purpose: SQLAlchemy ORM models for users and auth tokens
Size: ~150 lines
Models:
  - User:
    * id: UUID (PK)
    * username: str (unique)
    * email_hash: str (hash for dedup checking)
    * email_encrypted: str (encrypted, AES-256)
    * password_hash: str (Argon2id)
    * is_active: bool
    * is_verified: bool
    * two_fa_enabled: bool
    * two_fa_secret: str (encrypted)
    * locked_until: Optional[datetime] (account lockout)
    * failed_login_attempts: int (counter)
    * created_at, updated_at: datetime
  
  - RefreshToken:
    * id: UUID (PK)
    * user_id: UUID (FK → User)
    * token_family_id: UUID (for rotation tracking)
    * token_hash: str
    * jti: str (JWT ID for blacklist)
    * is_revoked: bool
    * expires_at: datetime
    * issued_at: datetime
  
  - BackupCode:
    * id: UUID (PK)
    * user_id: UUID (FK → User)
    * code_hash: str
    * used_at: Optional[datetime]

### 4. Auth Schemas (services/gateway/app/schemas/auth.py)
Purpose: Pydantic request/response schemas for API
Size: ~150 lines
Schemas:
  - RegisterRequest:
    * username: str (3-50 chars)
    * email: str (valid email)
    * password: str (min 12 chars, entropy > 4.0)
  
  - RegisterResponse:
    * user_id: UUID
    * username: str
    * message: str ("Please verify your email")
  
  - LoginRequest:
    * username: str
    * password: str
  
  - LoginResponse:
    * access_token: str
    * refresh_token: str
    * user: UserOut
    * token_type: str = "Bearer"
  
  - User2FASetupRequest:
    * password: str (verify current user)
  
  - User2FASetupResponse:
    * secret: str (base32)
    * qr_code: str (PNG base64)
    * backup_codes: List[str]
  
  - User2FAVerifyRequest:
    * code: str (6-digit TOTP)
  
  - User2FAVerifyResponse:
    * success: bool
    * message: str
  
  - RefreshTokenRequest:
    * refresh_token: str
  
  - RefreshTokenResponse:
    * access_token: str
    * refresh_token: str (new, rotated)
  
  - PasswordResetRequest:
    * email: str
  
  - PasswordResetConfirmRequest:
    * token: str
    * password: str
  
  - UserOut:
    * id: UUID
    * username: str
    * email: str
    * is_active: bool
    * two_fa_enabled: bool
    * created_at: datetime

### 5. Auth Endpoints (services/gateway/app/api/v1/auth.py)
Purpose: FastAPI routes for authentication
Size: ~500 lines
Endpoints:
  - POST /auth/register
    * Validate inputs
    * Hash email + compare for duplicates
    * Hash password (Argon2id)
    * Create user in DB
    * Send verification email (stub)
    * Return 201 with user_id
  
  - POST /auth/login
    * Validate username + password
    * Check account lockout (5 failed = 15min block)
    * Verify password hash
    * Check if 2FA enabled → return {requires_2fa: true}
    * Create JWT access_token (15 min expiry)
    * Create refresh_token (7 day expiry)
    * Store refresh_token_family in DB
    * Return tokens + user object
  
  - POST /auth/refresh
    * Valid refresh_token required
    * Verify token signature
    * Check JTI not in blacklist
    * Check family_id still valid (detect theft)
    * If family broken: revoke all tokens in family
    * Create new access_token
    * Create new refresh_token with NEW family_id
    * Return new tokens
  
  - POST /auth/logout
    * Access token required (Authorization: Bearer xxx)
    * Blacklist current refresh_token (set revoked=true)
    * Blacklist JTI in Redis (key: "jti_blacklist:{jti}", TTL=expiry)
    * Return 200
  
  - POST /auth/2fa/setup
    * Access token required
    * Password required (user re-verification)
    * Generate TOTP secret → qr_code (pyotp)
    * Generate 16 backup codes
    * Return secret + QR code + backup codes
    * Don't enable yet (wait for verify)
  
  - POST /auth/2fa/verify
    * Access token required
    * 6-digit TOTP code required
    * Verify code against secret
    * If valid: set two_fa_enabled=true
    * Store encrypted secret in DB
    * Mark backup codes in DB
    * Return success
  
  - POST /auth/2fa/backup-code
    * Access token required
    * 8-digit backup code required
    * Verify code
    * Mark as used (used_at=now())
    * Continue login
  
  - POST /auth/password-reset
    * Email required
    * Check if user exists (don't leak info)
    * Generate reset token (JWT, 1 hour expiry)
    * Send email with link (stub)
    * Return "Check your email"
  
  - POST /auth/password-reset/confirm
    * Reset token required
    * New password required
    * Verify token signature + expiry
    * Hash password
    * Update user password_hash
    * Revoke all refresh tokens (force re-login)
    * Return success
  
  - GET /auth/verify-email/{token}
    * Verify token (contains user_id)
    * Set is_verified=true
    * Return success/redirect to login

### 6. Database Module (services/gateway/app/core/database.py)
Purpose: SQLAlchemy database configuration
Size: ~100 lines
Functions:
  - create_async_engine() → engine with pool (20, overflow 10)
  - get_async_session() → sessionmaker
  - get_db() → async dependency for FastAPI
  - init_db() → create all tables
  - drop_db() → drop all tables (testing)

### 7. Tests (services/gateway/tests/test_auth.py)
Purpose: Comprehensive auth tests
Size: ~300 lines
Tests:
  - test_register_success()
    * POST /auth/register with valid data
    * Assert 201, user created in DB
    * Assert email_encrypted not same as plaintext
  
  - test_register_duplicate_email()
    * POST /auth/register with existing email
    * Assert 409 conflict
  
  - test_register_weak_password()
    * POST /auth/register with password "abc123"
    * Assert 400, entropy too low
  
  - test_login_success()
    * Create user
    * POST /auth/login with correct password
    * Assert 200, tokens returned
    * Verify JWT signature and expiry
  
  - test_login_wrong_password()
    * Create user
    * POST /auth/login with wrong password
    * Assert 401 unauthorized
  
  - test_login_account_lockout()
    * Create user
    * POST /auth/login 5 times with wrong password
    * Assert account locked (locked_until timestamp set)
    * Try again before lockout expires
    * Assert 429 too many requests
  
  - test_refresh_token_success()
    * Login to get tokens
    * POST /auth/refresh with refresh_token
    * Assert 200, new access + refresh tokens
    * Verify old refresh_token family no longer works
  
  - test_refresh_token_stolen()
    * Login to get tokens (family_id = F1)
    * POST /auth/refresh → new tokens (family_id = F2)
    * POST /auth/refresh with OLD refresh_token
    * Assert attempt with old family detected
    * All tokens in F1 revoked (breach detected)
  
  - test_logout()
    * Login to get tokens
    * POST /auth/logout with access_token
    * Try to refresh with old refresh_token
    * Assert 401 (token revoked)
  
  - test_2fa_setup()
    * Login without 2FA
    * POST /auth/2fa/setup with password
    * Assert 200, secret + QR code + backup codes
  
  - test_2fa_verify()
    * Setup 2FA
    * Generate correct TOTP code
    * POST /auth/2fa/verify with code
    * Assert 200, 2FA enabled
  
  - test_2fa_verify_wrong_code()
    * Setup 2FA
    * POST /auth/2fa/verify with wrong code
    * Assert 400 invalid code
  
  - test_login_with_2fa()
    * Create user with 2FA enabled
    * POST /auth/login
    * Assert 202 requires 2FA (not 200)
    * POST /auth/2fa/backup-code with backup code
    * Assert 200, logged in
  
  - test_password_reset_flow()
    * POST /auth/password-reset with email
    * Extract reset token from email (simulated)
    * POST /auth/password-reset/confirm with new password
    * Try login with old password → fail
    * Try login with new password → success
    * Assert all previous tokens revoked
  
  - test_concurrent_logins()
    * Create user
    * Simulate 3 concurrent logins
    * Each gets different refresh_token family
    * Verify tokens independent (not family conflicts)

════════════════════════════════════════════════════════════════════════════════
SECURITY CONSIDERATIONS
════════════════════════════════════════════════════════════════════════════════

✅ Implemented:
- RS256 JWT signature (not HS256, asymmetric)
- Argon2id password hashing (memory=64MB, iterations=3)
- AES-256-GCM field encryption via Fernet
- Refresh token rotation with family tracking
- Account lockout after 5 failed attempts (15 min)
- JTI blacklist in Redis
- TOTP 2FA (RFC 6238)
- Backup codes for account recovery
- Time-constant string comparison (avoid timing attacks)
- No email/username confusion (hash both separately)
- Password reset token expiry (1 hour)
- HTTP-only cookies option (for SPA)

════════════════════════════════════════════════════════════════════════════════
EXECUTION ORDER
════════════════════════════════════════════════════════════════════════════════

1. Create services/gateway/app/core/config.py
2. Create services/gateway/app/core/security.py
3. Create services/gateway/app/models/user.py
4. Create services/gateway/app/schemas/auth.py
5. Create services/gateway/app/core/database.py (depends on models)
6. Create services/gateway/app/api/v1/auth.py (depends on all above)
7. Create services/gateway/tests/test_auth.py
8. Run tests: pytest services/gateway/tests/test_auth.py -v --cov=app
9. Manual testing via REST client or Swagger UI

════════════════════════════════════════════════════════════════════════════════
TESTING STRATEGY
════════════════════════════════════════════════════════════════════════════════

Unit Tests (Isolation):
  - Security module (hashing, encryption, JWT)
  - Schema validation
  
Integration Tests (Database):
  - User creation + retrieval
  - Token generation + verification
  - Refresh token rotation
  - Account lockout
  - 2FA flow
  
End-to-End Tests (Full API):
  - Register → Login → Refresh → Logout flow
  - 2FA setup → verify → login with 2FA
  - Concurrent logins
  - Stolen token detection
  - Password reset

Coverage Target: ≥ 90%

════════════════════════════════════════════════════════════════════════════════
EXPECTED OUTCOMES
════════════════════════════════════════════════════════════════════════════════

After PHASE 2, you will have:

✅ Complete user registration system
✅ Secure JWT-based authentication
✅ Refresh token rotation
✅ TOTP 2FA support
✅ Account lockout protection
✅ Password reset flow
✅ All tested (90%+ coverage)
✅ Fully documented API endpoints

Then proceed to PHASE 3: Data Pipeline (yfinance, NSE, market data ingestion)

════════════════════════════════════════════════════════════════════════════════
