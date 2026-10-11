"""add OTP + login-lockout auth security columns

Revision ID: c0698f36e21e
Revises: e05c01684d68
Create Date: 2026-09-29 00:00:00.000000

"""
from typing import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c0698f36e21e'
down_revision: str | None = 'e05c01684d68'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists (idempotent migration guard)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    if not _column_exists('users', 'password_hash'):
        op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=True))
    if not _column_exists('users', 'failed_login_attempts'):
        op.add_column(
            'users',
            sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'),
        )
    if not _column_exists('users', 'locked_until'):
        op.add_column('users', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))

    # `email_verified` has existed since the initial schema but was never
    # enforced anywhere - every row today is False purely because nothing
    # ever set it, not because these accounts are actually unverified.
    # Enforcing the new OTP-verified gate against that stale default would
    # lock every existing user out the moment this ships. Grandfather every
    # pre-existing account in; only accounts created by the new
    # /auth/register flow (which now explicitly sets False and requires an
    # OTP) start out unverified.
    op.execute("UPDATE users SET email_verified = true WHERE email_verified = false")

    # Check if email_otps already exists before creating
    conn = op.get_bind()
    table_check = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'email_otps'"
        )
    )
    if table_check.fetchone() is not None:
        return  # Table already exists, nothing more to do

    op.create_table(
        'email_otps',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('purpose', sa.String(length=30), nullable=False),
        sa.Column('otp_hash', sa.String(length=255), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_otps_email'), 'email_otps', ['email'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_email_otps_email'), table_name='email_otps')
    op.drop_table('email_otps')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'password_hash')
