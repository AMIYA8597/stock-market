"""Stage 1 Models

Revision ID: 53aef4df1954
Revises: 53aef4df1953
Create Date: 2026-09-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '53aef4df1954'
down_revision = '53aef4df1953'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add columns to instruments
    op.add_column('instruments', sa.Column('exchange_segment', sa.String(length=50), nullable=True))
    op.add_column('instruments', sa.Column('figi', sa.String(length=12), nullable=True))
    op.add_column('instruments', sa.Column('broker_token', sa.String(length=100), nullable=True))
    op.add_column('instruments', sa.Column('tick_size', sa.Numeric(precision=18, scale=6), nullable=True))
    op.add_column('instruments', sa.Column('lot_size', sa.Numeric(precision=18, scale=6), nullable=True))
    op.add_column('instruments', sa.Column('multiplier', sa.Numeric(precision=18, scale=6), nullable=True))

    # Add columns to ohlcv
    op.add_column('ohlcv', sa.Column('oi', sa.Numeric(precision=24, scale=6), nullable=True))
    op.add_column('ohlcv', sa.Column('vwap', sa.Numeric(precision=18, scale=6), nullable=True))

    # Create tick_data table
    op.create_table('tick_data',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('instrument_id', sa.UUID(), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.Column('price', sa.Numeric(precision=18, scale=6), nullable=True),
    sa.Column('volume', sa.Numeric(precision=24, scale=6), nullable=True),
    sa.Column('is_buyer_maker', sa.Boolean(), nullable=True),
    sa.Column('provider', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tick_data_instrument_id'), 'tick_data', ['instrument_id'], unique=False)
    op.create_index(op.f('ix_tick_data_timestamp'), 'tick_data', ['timestamp'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_tick_data_timestamp'), table_name='tick_data')
    op.drop_index(op.f('ix_tick_data_instrument_id'), table_name='tick_data')
    op.drop_table('tick_data')
    op.drop_column('ohlcv', 'vwap')
    op.drop_column('ohlcv', 'oi')
    op.drop_column('instruments', 'multiplier')
    op.drop_column('instruments', 'lot_size')
    op.drop_column('instruments', 'tick_size')
    op.drop_column('instruments', 'broker_token')
    op.drop_column('instruments', 'figi')
    op.drop_column('instruments', 'exchange_segment')
