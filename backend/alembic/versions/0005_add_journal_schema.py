"""Add trade journals table - alembic migration.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-03 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create trade_journals table."""
    op.create_table(
        "trade_journals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.String(length=1024), nullable=False, server_default=""),
        sa.Column("tags", sa.String(length=255), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("entry_price", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("exit_price", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("direction", sa.String(length=8), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create indexes for performance
    op.create_index("ix_trade_journals_user_id", "trade_journals", ["user_id"])
    op.create_index("ix_trade_journals_symbol", "trade_journals", ["symbol"])


def downgrade() -> None:
    """Drop trade_journals table."""
    op.drop_index("ix_trade_journals_symbol", table_name="trade_journals")
    op.drop_index("ix_trade_journals_user_id", table_name="trade_journals")
    op.drop_table("trade_journals")
