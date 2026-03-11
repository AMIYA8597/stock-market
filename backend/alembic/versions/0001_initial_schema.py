"""PHASE 1 - Initial database schema with all tables

Revision ID: 0001_initial
Revises: 
Create Date: 2026-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all initial tables for PHASE 1: Database"""
    
    # Enable extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE')
    op.execute('CREATE EXTENSION IF NOT EXISTS inet CASCADE')
    
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.Text(), nullable=False),
        sa.Column('email_hash', sa.Text(), nullable=False),
        sa.Column('phone', sa.Text(), nullable=True),
        sa.Column('phone_hash', sa.Text(), nullable=True),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('totp_secret', sa.Text(), nullable=True),
        sa.Column('is_2fa_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('role', sa.Text(), nullable=False, server_default=sa.text("'ANALYST'")),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('email_hash'),
        sa.UniqueConstraint('phone_hash'),
        sa.CheckConstraint("role IN ('ADMIN', 'RESEARCHER', 'ANALYST', 'VIEWER', 'API_USER')"),
    )
    
    # Refresh tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.Text(), nullable=False),
        sa.Column('family_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )
    
    # Backup codes table
    op.create_table(
        'backup_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code_hash', sa.Text(), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # OHLCV table (will be hypertable)
    op.create_table(
        'ohlcv',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('symbol', sa.Text(), nullable=False),
        sa.Column('exchange', sa.Text(), nullable=False),
        sa.Column('open', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('high', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('low', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('close', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('volume', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('time', 'symbol', 'exchange'),
    )
    op.execute('SELECT create_hypertable(\'ohlcv\', \'time\', if_not_exists => TRUE)')
    
    # Tick data table (will be hypertable)
    op.create_table(
        'tick_data',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('symbol', sa.Text(), nullable=False),
        sa.Column('price', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('volume', sa.Integer(), nullable=True),
        sa.Column('side', sa.Text(), nullable=True),
        sa.Column('bid', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('ask', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.CheckConstraint("side IN ('BUY', 'SELL', NULL)"),
    )
    op.execute('SELECT create_hypertable(\'tick_data\', \'time\', if_not_exists => TRUE)')
    
    # Model versions table
    op.create_table(
        'model_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('version', sa.Text(), nullable=False),
        sa.Column('model_type', sa.Text(), nullable=False),
        sa.Column('parameters', postgresql.JSONB(), nullable=False),
        sa.Column('metrics', postgresql.JSONB(), nullable=True),
        sa.Column('training_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('artifact_path', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'version'),
    )
    
    # Predictions table
    op.create_table(
        'predictions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('symbol', sa.Text(), nullable=False),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('prediction_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('horizon_days', sa.Integer(), nullable=False),
        sa.Column('predicted_price', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('predicted_direction', sa.Integer(), nullable=True),
        sa.Column('confidence', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('lower_80', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('upper_80', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('lower_95', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('upper_95', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('feature_importances', postgresql.JSONB(), nullable=True),
        sa.Column('actual_price', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('actual_direction', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint('predicted_direction IN (-1, 0, 1)'),
        sa.CheckConstraint('confidence >= 0 AND confidence <= 1'),
        sa.ForeignKeyConstraint(['model_id'], ['model_versions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Portfolios table
    op.create_table(
        'portfolios',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('base_currency', sa.Text(), nullable=False, server_default=sa.text("'INR'")),
        sa.Column('base_amount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Holdings table
    op.create_table(
        'holdings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('portfolio_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('symbol', sa.Text(), nullable=False),
        sa.Column('exchange', sa.Text(), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('avg_cost', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('stop_loss', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('take_profit', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Alert definitions table
    op.create_table(
        'alert_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('symbol', sa.Text(), nullable=True),
        sa.Column('alert_type', sa.Text(), nullable=False),
        sa.Column('conditions', postgresql.JSONB(), nullable=False),
        sa.Column('channels', postgresql.JSONB(), nullable=False),
        sa.Column('cooldown_minutes', sa.Integer(), nullable=False, server_default=sa.text('60')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("alert_type IN ('PRICE', 'TECHNICAL', 'ML_SIGNAL', 'SENTIMENT', 'ANOMALY', 'NEWS')"),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Alert events table
    op.create_table(
        'alert_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('alert_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('payload', postgresql.JSON(), nullable=True),
        sa.Column('notified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.ForeignKeyConstraint(['alert_id'], ['alert_definitions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Audit log table (hypertable)
    op.create_table(
        'audit_log',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('resource_type', sa.Text(), nullable=True),
        sa.Column('resource_id', sa.Text(), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('prev_hash', sa.Text(), nullable=True),
        sa.Column('row_hash', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.execute('SELECT create_hypertable(\'audit_log\', \'created_at\', if_not_exists => TRUE)')
    
    # Indices
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_role', 'users', ['role'])
    op.create_index('idx_refresh_tokens_user_family', 'refresh_tokens', ['user_id', 'family_id'])
    op.create_index('idx_ohlcv_symbol_time', 'ohlcv', ['symbol', sa.text('time DESC')])
    op.create_index('idx_alert_events_triggered', 'alert_events', [sa.text('triggered_at DESC')])
    op.create_index('idx_audit_log_user_time', 'audit_log', ['user_id', sa.text('created_at DESC')])


def downgrade() -> None:
    """Drop all tables"""
    op.drop_index('idx_audit_log_user_time')
    op.drop_index('idx_alert_events_triggered')
    op.drop_index('idx_ohlcv_symbol_time')
    op.drop_index('idx_refresh_tokens_user_family')
    op.drop_index('idx_users_role')
    op.drop_index('idx_users_email')
    
    op.drop_table('audit_log')
    op.drop_table('alert_events')
    op.drop_table('alert_definitions')
    op.drop_table('holdings')
    op.drop_table('portfolios')
    op.drop_table('predictions')
    op.drop_table('model_versions')
    op.drop_table('tick_data')
    op.drop_table('ohlcv')
    op.drop_table('backup_codes')
    op.drop_table('refresh_tokens')
    op.drop_table('users')
