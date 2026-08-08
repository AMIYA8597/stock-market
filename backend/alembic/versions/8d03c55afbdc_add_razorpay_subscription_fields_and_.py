"""Add Razorpay Subscription fields and AuditLog

Revision ID: 8d03c55afbdc
Revises: 19d7b2aabd9f
Create Date: 2026-08-08 09:34:19.086447

"""
from typing import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8d03c55afbdc'
down_revision: str | None = '19d7b2aabd9f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('subscriptions', sa.Column('razorpay_subscription_id', sa.String(length=120), nullable=True))
    op.add_column('subscriptions', sa.Column('razorpay_customer_id', sa.String(length=120), nullable=True))
    op.create_index(op.f('ix_subscriptions_razorpay_subscription_id'), 'subscriptions', ['razorpay_subscription_id'], unique=True)
    op.create_index(op.f('ix_subscriptions_razorpay_customer_id'), 'subscriptions', ['razorpay_customer_id'], unique=False)

    op.create_table('billing_audit_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('payload_json', sa.String(length=4000), nullable=False),
        sa.Column('signature_verified', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('billing_audit_logs')
    op.drop_index(op.f('ix_subscriptions_razorpay_customer_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_razorpay_subscription_id'), table_name='subscriptions')
    op.drop_column('subscriptions', 'razorpay_customer_id')
    op.drop_column('subscriptions', 'razorpay_subscription_id')
