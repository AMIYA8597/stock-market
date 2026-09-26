"""add auto_trade_settings table

Revision ID: 24189fff7837
Revises: f3b91af9217c
Create Date: 2026-09-26 10:57:21.218175

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '24189fff7837'
down_revision: Union[str, None] = 'f3b91af9217c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'auto_trade_settings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('watchlist_id', sa.Integer(), nullable=False),
        sa.Column('max_open_positions', sa.Integer(), nullable=False),
        sa.Column('risk_per_trade_pct', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('min_confidence', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('last_scan_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_scan_result', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_auto_trade_settings_user_id'),
    )
    op.create_index(
        op.f('ix_auto_trade_settings_user_id'), 'auto_trade_settings', ['user_id'], unique=True
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_auto_trade_settings_user_id'), table_name='auto_trade_settings')
    op.drop_table('auto_trade_settings')
