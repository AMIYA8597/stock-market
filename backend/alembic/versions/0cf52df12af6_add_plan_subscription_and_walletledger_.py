"""Add Plan, Subscription, and WalletLedger models

Revision ID: 0cf52df12af6
Revises: 0005
Create Date: 2026-07-21 08:52:00.656050

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0cf52df12af6'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('plans',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.Column('price_inr', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('interval', sa.String(length=20), nullable=False),
    sa.Column('features_json', sa.Text(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_plans_name'), 'plans', ['name'], unique=False)
    
    op.create_table('subscriptions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('plan_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=24), nullable=False),
    sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=False),
    sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscriptions_plan_id'), 'subscriptions', ['plan_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_status'), 'subscriptions', ['status'], unique=False)
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)
    
    op.create_table('wallet_ledger',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('transaction_type', sa.String(length=20), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.Column('reference_id', sa.String(length=120), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_wallet_ledger_reference_id'), 'wallet_ledger', ['reference_id'], unique=False)
    op.create_index(op.f('ix_wallet_ledger_user_id'), 'wallet_ledger', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_wallet_ledger_user_id'), table_name='wallet_ledger')
    op.drop_index(op.f('ix_wallet_ledger_reference_id'), table_name='wallet_ledger')
    op.drop_table('wallet_ledger')
    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_status'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_plan_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
    op.drop_index(op.f('ix_plans_name'), table_name='plans')
    op.drop_table('plans')
