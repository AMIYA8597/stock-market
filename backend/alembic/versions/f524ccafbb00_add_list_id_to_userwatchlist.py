"""Add list_id to UserWatchlist

Revision ID: f524ccafbb00
Revises: 6eaa417877f4
Create Date: 2026-07-31 00:40:46.608346

"""
from typing import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f524ccafbb00'
down_revision: str | None = '6eaa417877f4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('user_watchlist', sa.Column('list_id', sa.Integer(), server_default='0', nullable=False))

    with op.batch_alter_table('user_watchlist', schema=None) as batch_op:
        batch_op.drop_constraint('uq_user_watchlist_user_symbol', type_='unique')
        batch_op.create_index(batch_op.f('ix_user_watchlist_list_id'), ['list_id'], unique=False)
        batch_op.create_unique_constraint('uq_user_watchlist_user_symbol_list', ['user_id', 'symbol', 'list_id'])


def downgrade() -> None:
    with op.batch_alter_table('user_watchlist', schema=None) as batch_op:
        batch_op.drop_constraint('uq_user_watchlist_user_symbol_list', type_='unique')
        batch_op.drop_index(batch_op.f('ix_user_watchlist_list_id'))
        batch_op.create_unique_constraint('uq_user_watchlist_user_symbol', ['user_id', 'symbol'])
        batch_op.drop_column('list_id')
