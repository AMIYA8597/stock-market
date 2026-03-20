"""Timescale hypertables and continuous aggregate setup.

Revision ID: 002_timescale_hypertables
Revises: 001_initial_schema
Create Date: 2026-01-01 00:10:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "002_timescale_hypertables"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SELECT create_hypertable('ohlcv', 'time', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ohlcv_symbol_time_desc ON ohlcv (symbol_id, time DESC)")

    op.execute("SELECT create_hypertable('feature_vectors', 'time', chunk_time_interval => INTERVAL '30 days', if_not_exists => TRUE)")

    op.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_1h
        WITH (timescaledb.continuous) AS
        SELECT
          time_bucket('1 hour', time) AS bucket,
          symbol_id,
          first(open, time) AS open,
          max(high) AS high,
          min(low) AS low,
          last(close, time) AS close,
          sum(volume) AS volume
        FROM ohlcv
        WHERE interval = '1m'
        GROUP BY bucket, symbol_id
        """
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS ohlcv_1h")
    op.execute("DROP INDEX IF EXISTS ix_ohlcv_symbol_time_desc")