"""Initial schema aligned with thesis Section 2.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if not is_sqlite:
        op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    id_server_default = None if is_sqlite else sa.text("gen_random_uuid()")
    bool_true_default = sa.text("1") if is_sqlite else sa.text("true")
    bool_false_default = sa.text("0") if is_sqlite else sa.text("false")
    datetime_now_default = sa.text("CURRENT_TIMESTAMP") if is_sqlite else sa.text("NOW()")

    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())
    array_type = sa.JSON() if is_sqlite else postgresql.ARRAY(sa.Numeric(precision=6, scale=4))
    uuid_type = sa.UUID(as_uuid=True) if is_sqlite else postgresql.UUID(as_uuid=True)

    op.create_table(
        "users",
        sa.Column("id", uuid_type, nullable=False, server_default=id_server_default),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=bool_true_default),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=datetime_now_default),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=datetime_now_default),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "symbols",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("sector", sa.String(length=64), nullable=True),
        sa.Column("industry", sa.String(length=64), nullable=True),
        sa.Column("market_cap_bucket", sa.String(length=16), nullable=True),
        sa.Column("asset_type", sa.String(length=16), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=True, server_default=sa.text("'USD'")),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=bool_true_default),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=datetime_now_default),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker"),
    )

    op.create_table(
        "ohlcv",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=False),
        sa.Column("open", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("high", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("low", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("close", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("volume", sa.Numeric(precision=24, scale=4), nullable=False),
        sa.Column("adjusted_close", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("interval", sa.String(length=8), nullable=False),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"]),
        sa.PrimaryKeyConstraint("time", "symbol_id", "interval"),
    )

    op.create_table(
        "feature_vectors",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=False),
        sa.Column("features", json_type, nullable=False),
        sa.Column("feature_version", sa.String(length=16), nullable=False, server_default=sa.text("'v1'")),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"]),
        sa.PrimaryKeyConstraint("time", "symbol_id"),
    )

    op.create_table(
        "regime_states",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("viterbi_state", sa.SmallInteger(), nullable=False),
        sa.Column("state_probs", array_type, nullable=False),
        sa.Column("conditional_vol", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("vol_forecast_5d", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("vol_forecast_21d", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.PrimaryKeyConstraint("time"),
    )

    op.create_table(
        "ml_predictions",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=32), nullable=False),
        sa.Column("horizon_days", sa.SmallInteger(), nullable=False),
        sa.Column("p10_return", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("p50_return", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("p90_return", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("raw_signal", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("shap_values", json_type, nullable=True),
        sa.Column("attention_weights", json_type, nullable=True),
        sa.Column("actual_return", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=datetime_now_default),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ensemble_signals",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=False),
        sa.Column("signal", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("direction", sa.String(length=12), nullable=False),
        sa.Column("model_weights", json_type, nullable=False),
        sa.Column("regime_state", sa.SmallInteger(), nullable=False),
        sa.Column("kelly_fraction", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"]),
        sa.PrimaryKeyConstraint("time", "symbol_id"),
    )

    op.create_table(
        "portfolio_holdings",
        sa.Column("id", uuid_type, nullable=False, server_default=id_server_default),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("avg_buy_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(precision=20, scale=4), nullable=True, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=datetime_now_default),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "symbol_id"),
    )

    op.create_table(
        "transactions",
        sa.Column("id", uuid_type, nullable=False, server_default=id_server_default),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("brokerage", sa.Numeric(precision=12, scale=4), nullable=True, server_default=sa.text("0")),
        sa.Column("stt", sa.Numeric(precision=12, scale=4), nullable=True, server_default=sa.text("0")),
        sa.Column("net_amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True, server_default=datetime_now_default),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "alerts",
        sa.Column("id", uuid_type, nullable=False, server_default=id_server_default),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=True),
        sa.Column("alert_type", sa.String(length=32), nullable=False),
        sa.Column("threshold", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("is_triggered", sa.Boolean(), nullable=True, server_default=bool_false_default),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=datetime_now_default),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "backtest_jobs",
        sa.Column("id", uuid_type, nullable=False, server_default=id_server_default),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("strategy_params", json_type, nullable=False),
        sa.Column("universe", json_type, nullable=False),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("initial_capital", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=True, server_default=sa.text("'PENDING'")),
        sa.Column("results", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=datetime_now_default),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "news_sentiment",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("symbol_id", sa.Integer(), nullable=True),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("sentiment_label", sa.String(length=16), nullable=False),
        sa.Column("sentiment_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True, server_default=datetime_now_default),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_ml_predictions_symbol_time_model", "ml_predictions", ["symbol_id", "time", "model_name"])
    op.create_index("ix_news_sentiment_symbol_published", "news_sentiment", ["symbol_id", "published_at"])


def downgrade() -> None:
    op.drop_index("ix_news_sentiment_symbol_published", table_name="news_sentiment")
    op.drop_index("ix_ml_predictions_symbol_time_model", table_name="ml_predictions")

    op.drop_table("news_sentiment")
    op.drop_table("backtest_jobs")
    op.drop_table("alerts")
    op.drop_table("transactions")
    op.drop_table("portfolio_holdings")
    op.drop_table("ensemble_signals")
    op.drop_table("ml_predictions")
    op.drop_table("regime_states")
    op.drop_table("feature_vectors")
    op.drop_table("ohlcv")
    op.drop_table("symbols")
    op.drop_table("users")