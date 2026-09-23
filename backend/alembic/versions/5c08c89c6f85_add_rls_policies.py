"""Add RLS policies

Revision ID: 5c08c89c6f85
Revises: d3f7c1169f51
Create Date: 2026-09-23 21:57:19.957733

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c08c89c6f85'
down_revision: Union[str, None] = 'd3f7c1169f51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
    op.execute("CREATE POLICY select_own_user ON users FOR SELECT USING (id = current_setting('request.jwt.claim.sub', true)::uuid);")
    op.execute("ALTER TABLE paper_accounts ENABLE ROW LEVEL SECURITY;")
    op.execute("CREATE POLICY select_own_accounts ON paper_accounts FOR SELECT USING (user_id = current_setting('request.jwt.claim.sub', true)::uuid);")
    op.execute("ALTER TABLE paper_ledger_entries ENABLE ROW LEVEL SECURITY;")
    op.execute("CREATE POLICY select_own_entries ON paper_ledger_entries FOR SELECT USING (account_id IN (SELECT id FROM paper_accounts WHERE user_id = current_setting('request.jwt.claim.sub', true)::uuid));")
    op.execute("ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;")
    op.execute("CREATE POLICY select_own_subscriptions ON subscriptions FOR SELECT USING (user_id = current_setting('request.jwt.claim.sub', true)::uuid);")
    # Make market data public
    for table in ["exchanges", "instruments", "instrument_aliases", "market_calendar", "ohlcv", "quote_snapshots"]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"CREATE POLICY select_public_{table} ON {table} FOR SELECT USING (true);")

def downgrade() -> None:
    pass
