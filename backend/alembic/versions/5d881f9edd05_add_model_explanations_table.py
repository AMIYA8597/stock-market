"""add model_explanations table

Revision ID: 5d881f9edd05
Revises: 24189fff7837
Create Date: 2026-09-26 10:59:43.636761

"""
from typing import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5d881f9edd05'
down_revision: str | None = '24189fff7837'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'model_explanations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('prediction_id', sa.UUID(), nullable=False),
        sa.Column('explanation_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['prediction_id'], ['predictions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_model_explanations_prediction_id'),
        'model_explanations',
        ['prediction_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_model_explanations_prediction_id'), table_name='model_explanations')
    op.drop_table('model_explanations')
