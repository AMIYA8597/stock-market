"""Add target_direction_1d to feature_vectors

Revision ID: 19d7b2aabd9f
Revises: f524ccafbb00
Create Date: 2026-08-07 23:56:59.683656

"""
from typing import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '19d7b2aabd9f'
down_revision: str | None = 'f524ccafbb00'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('feature_vectors', sa.Column('target_direction_1d', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('feature_vectors', 'target_direction_1d')
