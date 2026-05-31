"""Add CSRF token table and critical indexes - alembic migration.

Revision ID: 0004
Revises: 0003_auth_billing_content_notifications
Create Date: 2026-03-29 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = "0004"
down_revision = "003_auth_billing_content_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create CSRF token table and add missing indexes."""
    
    # ───  CREATE CSRF_TOKENS TABLE ───
    op.create_table(
        "csrf_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    
    # Indexes for CSRF token queries
    op.create_index("ix_csrf_tokens_user_id", "csrf_tokens", ["user_id"])
    op.create_index("ix_csrf_tokens_token", "csrf_tokens", ["token"])
    op.create_index("ix_csrf_tokens_expires_at", "csrf_tokens", ["expires_at"])
    
    # ─── ADD MISSING INDEXES FOR CRITICAL QUERIES ───
    
    # User email lookup (login, password reset)
    op.create_index("ix_users_email", "users", ["email"], if_not_exists=True)
    
    # Lookups by user ID
    op.create_index("ix_users_id", "users", ["id"], if_not_exists=True)
    
    # Payment lookups
    op.create_index(
        "ix_payment_transactions_intent_id",
        "payment_transactions",
        ["intent_id"],
        if_not_exists=True
    )
    op.create_index(
        "ix_payment_transactions_user_id",
        "payment_transactions",
        ["user_id"],
        if_not_exists=True
    )
    op.create_index(
        "ix_payment_transactions_provider_event_id",
        "payment_transactions",
        ["provider_event_id"],
        if_not_exists=True
    )
    op.create_index(
        "ix_payment_transactions_idempotency_key",
        "payment_transactions",
        ["idempotency_key"],
        if_not_exists=True
    )
    
    # Notification lookups
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], if_not_exists=True)
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"], if_not_exists=True)
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"], if_not_exists=True)
    
    # Refresh token lookups
    op.create_index("ix_refresh_sessions_user_id", "refresh_sessions", ["user_id"], if_not_exists=True)
    op.create_index("ix_refresh_sessions_family_id", "refresh_sessions", ["family_id"], if_not_exists=True)
    op.create_index("ix_refresh_sessions_expires_at", "refresh_sessions", ["expires_at"], if_not_exists=True)
    
    # Blog post queries
    op.create_index("ix_blog_posts_slug", "blog_posts", ["slug"], if_not_exists=True)
    op.create_index("ix_blog_posts_status", "blog_posts", ["status"], if_not_exists=True)
    op.create_index("ix_blog_posts_published_at", "blog_posts", ["published_at"], if_not_exists=True)
    
    # Alert queries
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"], if_not_exists=True)
    op.create_index("ix_alerts_symbol_id", "alerts", ["symbol_id"], if_not_exists=True)
    op.create_index("ix_alerts_alert_type", "alerts", ["alert_type"], if_not_exists=True)


def downgrade() -> None:
    """Drop CSRF token table and indexes."""
    
    # Drop indexes
    op.drop_index("ix_csrf_tokens_expires_at", table_name="csrf_tokens")
    op.drop_index("ix_csrf_tokens_token", table_name="csrf_tokens")
    op.drop_index("ix_csrf_tokens_user_id", table_name="csrf_tokens")
    
    # Drop table
    op.drop_table("csrf_tokens")
    
    # Drop other indexes (if_exists check)
    indexes_to_drop = [
        ("ix_users_email", "users"),
        ("ix_users_id", "users"),
        ("ix_payment_transactions_intent_id", "payment_transactions"),
        ("ix_payment_transactions_user_id", "payment_transactions"),
        ("ix_payment_transactions_provider_event_id", "payment_transactions"),
        ("ix_payment_transactions_idempotency_key", "payment_transactions"),
        ("ix_notifications_user_id", "notifications"),
        ("ix_notifications_is_read", "notifications"),
        ("ix_notifications_created_at", "notifications"),
        ("ix_refresh_sessions_user_id", "refresh_sessions"),
        ("ix_refresh_sessions_family_id", "refresh_sessions"),
        ("ix_refresh_sessions_expires_at", "refresh_sessions"),
        ("ix_blog_posts_slug", "blog_posts"),
        ("ix_blog_posts_status", "blog_posts"),
        ("ix_blog_posts_published_at", "blog_posts"),
        ("ix_alerts_user_id", "alerts"),
        ("ix_alerts_symbol_id", "alerts"),
        ("ix_alerts_alert_type", "alerts"),
    ]
    
    for index_name, table_name in indexes_to_drop:
        op.drop_index(index_name, table_name=table_name, if_exists=True)
