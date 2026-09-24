"""Update RLS for system actions

Revision ID: d7bf2b1f317b
Revises: 014b15080448
Create Date: 2026-09-24 10:51:45.698376

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7bf2b1f317b'
down_revision: Union[str, None] = '014b15080448'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # All tables in our schema
    tables = [
        "users", "organizations", "org_members", "usage_counters",
        "api_keys", "invitations",
        "exchanges", "instruments", "instrument_aliases", "market_calendar", "ohlcv", "quote_snapshots",
        "ingestion_runs", "data_quality_events",
        "datasets", "experiments", "model_registry", "predictions",
        "plans", "organization_subscriptions", "plan_entitlements", "payment_events",
        "paper_accounts", "paper_ledger_entries", "paper_positions", "paper_orders", "backtest_jobs",
        "audit_log"
    ]
    
    # 1. System bypass policy for all tables
    for table in tables:
        # Just in case they aren't enabled
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        # Drop if exists
        op.execute(f"DROP POLICY IF EXISTS system_all ON {table};")
        op.execute(
            f"CREATE POLICY system_all ON {table} FOR ALL "
            f"USING (current_setting('app.is_system', true) = 'true') "
            f"WITH CHECK (current_setting('app.is_system', true) = 'true');"
        )

    # 2. Public Read Policies
    public_read_tables = [
        "exchanges", "instruments", "instrument_aliases", 
        "market_calendar", "ohlcv", "quote_snapshots",
        "plans"
    ]
    for table in public_read_tables:
        op.execute(f"DROP POLICY IF EXISTS public_read ON {table};")
        op.execute(f"CREATE POLICY public_read ON {table} FOR SELECT USING (true);")

    # 3. User specific policies (already have some, let's recreate carefully)
    op.execute("DROP POLICY IF EXISTS select_own_user ON users;")
    op.execute("CREATE POLICY select_own_user ON users FOR SELECT USING (id = NULLIF(current_setting('request.jwt.claim.sub', true), '')::uuid);")
    
    op.execute("DROP POLICY IF EXISTS select_own_accounts ON paper_accounts;")
    op.execute("CREATE POLICY select_own_accounts ON paper_accounts FOR SELECT USING (user_id = NULLIF(current_setting('request.jwt.claim.sub', true), '')::uuid);")

    op.execute("DROP POLICY IF EXISTS select_own_entries ON paper_ledger_entries;")
    op.execute("CREATE POLICY select_own_entries ON paper_ledger_entries FOR SELECT USING (account_id IN (SELECT id FROM paper_accounts WHERE user_id = NULLIF(current_setting('request.jwt.claim.sub', true), '')::uuid));")

    # Org policies
    op.execute("DROP POLICY IF EXISTS select_own_org ON organizations;")
    op.execute("CREATE POLICY select_own_org ON organizations FOR SELECT USING (id IN (SELECT organization_id FROM org_members WHERE user_id = NULLIF(current_setting('request.jwt.claim.sub', true), '')::uuid));")


def downgrade() -> None:
    pass
