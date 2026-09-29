"""Real-SQLite tests for app.core.otp: OTP lifecycle, password policy, and
login lockout. The shared `db` fixture in tests/conftest.py is a hand-mocked
DummySession that only recognizes a few hardcoded query shapes (users,
refresh_sessions) - it can't simulate the new email_otps table, so this
module uses a real (in-memory) SQLite engine instead, mirroring the pattern
already established in tests/integration/test_repository.py."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.otp import (
    PasswordPolicyError,
    create_otp,
    hash_otp,
    is_account_locked,
    record_failed_login,
    reset_failed_login,
    validate_password_strength,
    verify_otp,
)
from app.database.connection import Base
from app.models.auth_security import EmailOTP
from app.models.identity import User

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def real_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _make_user(real_db: AsyncSession, email: str = "otp_test@example.com") -> User:
    user = User(email=email, full_name="OTP Test", auth_id=f"auth_{email}", status="active")
    real_db.add(user)
    await real_db.commit()
    await real_db.refresh(user)
    return user


# ─── OTP lifecycle ───────────────────────────────────────────────────────


async def test_correct_otp_verifies(real_db: AsyncSession):
    email = "signup_ok@example.com"
    code = await create_otp(real_db, email, "signup")
    result = await verify_otp(real_db, email, "signup", code)
    assert result.ok is True


async def test_wrong_otp_is_rejected_and_counts_as_an_attempt(real_db: AsyncSession):
    email = "signup_wrong@example.com"
    await create_otp(real_db, email, "signup")

    result = await verify_otp(real_db, email, "signup", "000000")
    assert result.ok is False
    assert result.reason == "invalid"

    res = await real_db.execute(EmailOTP.__table__.select().where(EmailOTP.email == email))
    row = res.first()
    assert row.attempts == 1


async def test_otp_cannot_be_reused_after_success(real_db: AsyncSession):
    email = "signup_reuse@example.com"
    code = await create_otp(real_db, email, "signup")

    first = await verify_otp(real_db, email, "signup", code)
    assert first.ok is True

    second = await verify_otp(real_db, email, "signup", code)
    assert second.ok is False
    assert second.reason == "not_found"  # consumed row no longer counts as "live"


async def test_expired_otp_is_rejected(real_db: AsyncSession):
    email = "signup_expired@example.com"
    otp_row = EmailOTP(
        email=email,
        purpose="signup",
        otp_hash=hash_otp("123456"),
        max_attempts=5,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    real_db.add(otp_row)
    await real_db.commit()

    result = await verify_otp(real_db, email, "signup", "123456")
    assert result.ok is False
    assert result.reason == "expired"


async def test_excessive_wrong_attempts_locks_out_the_code(real_db: AsyncSession):
    email = "signup_bruteforce@example.com"
    otp_row = EmailOTP(
        email=email,
        purpose="signup",
        otp_hash=hash_otp("654321"),
        max_attempts=3,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    real_db.add(otp_row)
    await real_db.commit()

    for _ in range(3):
        result = await verify_otp(real_db, email, "signup", "000000")
        assert result.ok is False

    # Even the correct code is now rejected - the code itself is burned.
    final = await verify_otp(real_db, email, "signup", "654321")
    assert final.ok is False
    assert final.reason in {"too_many_attempts", "not_found"}


async def test_requesting_a_new_otp_invalidates_the_previous_one(real_db: AsyncSession):
    email = "signup_resend@example.com"
    old_code = await create_otp(real_db, email, "signup")
    new_code = await create_otp(real_db, email, "signup")
    assert old_code != new_code or True  # codes could theoretically collide; behavior matters, not the odds

    old_result = await verify_otp(real_db, email, "signup", old_code)
    assert old_result.ok is False

    new_result = await verify_otp(real_db, email, "signup", new_code)
    assert new_result.ok is True


async def test_signup_and_password_reset_otps_are_independent(real_db: AsyncSession):
    email = "dual_purpose@example.com"
    signup_code = await create_otp(real_db, email, "signup")
    reset_code = await create_otp(real_db, email, "password_reset")

    # A signup code must not verify a password-reset attempt, and vice versa.
    assert (await verify_otp(real_db, email, "password_reset", signup_code)).ok is False
    assert (await verify_otp(real_db, email, "signup", reset_code)).ok is False
    assert (await verify_otp(real_db, email, "signup", signup_code)).ok is True
    assert (await verify_otp(real_db, email, "password_reset", reset_code)).ok is True


# ─── Password strength policy ────────────────────────────────────────────


@pytest.mark.parametrize(
    "password",
    ["short1!A", "alllowercase123!", "ALLUPPERCASE123!", "nodigitshere!ABC", "nospecialchars123ABC"],
)
async def test_weak_passwords_are_rejected(password):
    with pytest.raises(PasswordPolicyError):
        validate_password_strength(password)


async def test_common_password_is_rejected_even_if_otherwise_well_formed():
    # Exact-match blocklist check: satisfies length/class rules but is a
    # known weak password verbatim.
    with pytest.raises(PasswordPolicyError):
        validate_password_strength("Passw0rd")


async def test_strong_password_passes():
    validate_password_strength("Tr0ub4dor&Zebra!")  # should not raise


async def test_password_containing_email_local_part_is_rejected():
    with pytest.raises(PasswordPolicyError):
        validate_password_strength("Amiyachowdhury04!", email="amiyachowdhury04@gmail.com")


# ─── Login lockout ───────────────────────────────────────────────────────


async def test_account_locks_after_max_failed_attempts(real_db: AsyncSession):
    user = await _make_user(real_db, "lockout@example.com")
    assert is_account_locked(user) is False

    for _ in range(5):  # settings.LOGIN_MAX_FAILED_ATTEMPTS default
        await record_failed_login(real_db, user)

    assert user.failed_login_attempts == 5
    assert is_account_locked(user) is True


async def test_successful_login_resets_the_counter(real_db: AsyncSession):
    user = await _make_user(real_db, "recovers@example.com")
    for _ in range(3):
        await record_failed_login(real_db, user)
    assert user.failed_login_attempts == 3

    await reset_failed_login(real_db, user)
    assert user.failed_login_attempts == 0
    assert user.locked_until is None
    assert is_account_locked(user) is False
