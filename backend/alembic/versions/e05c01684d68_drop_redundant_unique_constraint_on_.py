"""drop redundant unique constraint on auto_trade_settings user_id

The previous migration (24189fff7837) created both a named
UniqueConstraint('user_id', name='uq_auto_trade_settings_user_id') AND a
separate unique index (ix_auto_trade_settings_user_id) on the same column -
two separate constraints redundantly enforcing the same uniqueness. The
AutoTradeSetting model (app/models/autotrade.py) only ever declared
`unique=True, index=True` on the column, which SQLAlchemy maps to the
unique index alone; it never declared the extra named constraint via
__table_args__. That mismatch is exactly what CI's migration/model drift
check caught (`alembic check` reported a stray remove_constraint op).

Revision ID: e05c01684d68
Revises: 5d881f9edd05
Create Date: 2026-09-27 20:19:21.680023

"""
from typing import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e05c01684d68'
down_revision: str | None = '5d881f9edd05'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        'uq_auto_trade_settings_user_id', 'auto_trade_settings', type_='unique'
    )


def downgrade() -> None:
    op.create_unique_constraint(
        'uq_auto_trade_settings_user_id', 'auto_trade_settings', ['user_id']
    )
