"""Auth, billing, blog, notifications, and email queue schema.

Revision ID: 003_auth_billing_content_notifications
Revises: 002_timescale_hypertables
Create Date: 2026-03-28 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "003_auth_billing_content_notifications"
down_revision = "002_timescale_hypertables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    datetime_now_default = sa.text("CURRENT_TIMESTAMP") if is_sqlite else sa.text("NOW()")
    bool_false_default = sa.text("0") if is_sqlite else sa.text("false")
    uuid_type = sa.UUID(as_uuid=True) if is_sqlite else postgresql.UUID(as_uuid=True)

    op.add_column("users", sa.Column("role", sa.String(length=24), nullable=False, server_default="USER"))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "refresh_sessions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("family_id", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=datetime_now_default),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_sessions_user", "refresh_sessions", ["user_id"])
    op.create_index("ix_refresh_sessions_family", "refresh_sessions", ["family_id"])

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=datetime_now_default),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )

    op.create_table(
        "blog_posts",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("excerpt", sa.String(length=400), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("author_id", uuid_type, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=datetime_now_default),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=datetime_now_default),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_blog_posts_status", "blog_posts", ["status"])

    op.create_table(
        "payment_transactions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=True),
        sa.Column("intent_id", sa.String(length=100), nullable=False),
        sa.Column("provider_ref", sa.String(length=120), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("provider_event_id", sa.String(length=120), nullable=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="INR"),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="requires_confirmation"),
        sa.Column("metadata_json", sa.String(length=1200), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=datetime_now_default),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("intent_id"),
        sa.UniqueConstraint("idempotency_key"),
        sa.UniqueConstraint("provider_event_id"),
    )
    op.create_index("ix_payment_transactions_user", "payment_transactions", ["user_id"])
    op.create_index("ix_payment_transactions_status", "payment_transactions", ["status"])

    op.create_table(
        "notifications",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("level", sa.String(length=24), nullable=False, server_default="info"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=bool_false_default),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=datetime_now_default),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user", "notifications", ["user_id"])
    op.create_index("ix_notifications_read", "notifications", ["is_read"])

    op.create_table(
        "email_jobs",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("to_email", sa.String(length=255), nullable=False),
        sa.Column("template", sa.String(length=80), nullable=False),
        sa.Column("payload_json", sa.String(length=4000), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=datetime_now_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=datetime_now_default),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_jobs_status", "email_jobs", ["status"])
    op.create_index("ix_email_jobs_template", "email_jobs", ["template"])


def downgrade() -> None:
    op.drop_index("ix_email_jobs_template", table_name="email_jobs")
    op.drop_index("ix_email_jobs_status", table_name="email_jobs")
    op.drop_table("email_jobs")

    op.drop_index("ix_notifications_read", table_name="notifications")
    op.drop_index("ix_notifications_user", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_payment_transactions_status", table_name="payment_transactions")
    op.drop_index("ix_payment_transactions_user", table_name="payment_transactions")
    op.drop_table("payment_transactions")

    op.drop_index("ix_blog_posts_status", table_name="blog_posts")
    op.drop_table("blog_posts")

    op.drop_table("password_reset_tokens")

    op.drop_index("ix_refresh_sessions_family", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_user", table_name="refresh_sessions")
    op.drop_table("refresh_sessions")

    op.drop_index("ix_users_role", table_name="users")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "role")
