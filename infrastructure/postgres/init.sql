-- ════════════════════════════════════════════════════════════════════════════════
-- PHASE 1: DATABASE SCHEMA & MIGRATIONS
-- NeuroQuant - PostgreSQL 16 + TimescaleDB 2.14
-- ════════════════════════════════════════════════════════════════════════════════

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS inet CASCADE;

-- ════════════════════════════════════════════════════════════════════════════════
-- SECTION 1: USERS & AUTHENTICATION
-- ════════════════════════════════════════════════════════════════════════════════

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  email_hash TEXT UNIQUE NOT NULL,
  phone TEXT,
  phone_hash TEXT UNIQUE,
  password_hash TEXT NOT NULL,
  totp_secret TEXT,
  is_2fa_enabled BOOLEAN DEFAULT false,
  role TEXT DEFAULT 'ANALYST' CHECK (role IN ('ADMIN', 'RESEARCHER', 'ANALYST', 'VIEWER', 'API_USER')),
  is_active BOOLEAN DEFAULT true,
  email_verified_at TIMESTAMPTZ,
  last_login_at TIMESTAMPTZ,
  failed_login_attempts INT DEFAULT 0,
  locked_until TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- Refresh token storage for rotation+family tracking
CREATE TABLE refresh_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash TEXT UNIQUE NOT NULL,
  family_id UUID NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user_family ON refresh_tokens(user_id, family_id);

-- 2FA backup codes (single-use)
CREATE TABLE backup_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  code_hash TEXT NOT NULL,
  used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ════════════════════════════════════════════════════════════════════════════════
-- SECTION 2: MARKET DATA (TimescaleDB hypertables)
-- ════════════════════════════════════════════════════════════════════════════════

-- OHLCV (1-minute bars minimum, stored efficiently)
CREATE TABLE ohlcv (
  time TIMESTAMPTZ NOT NULL,
  symbol TEXT NOT NULL,
  exchange TEXT NOT NULL,
  open NUMERIC(18,4) NOT NULL,
  high NUMERIC(18,4) NOT NULL,
  low NUMERIC(18,4) NOT NULL,
  close NUMERIC(18,4) NOT NULL,
  volume BIGINT NOT NULL,
  PRIMARY KEY (time, symbol, exchange)
);

SELECT create_hypertable('ohlcv', 'time', if_not_exists => TRUE);
CREATE INDEX idx_ohlcv_symbol_time ON ohlcv (symbol, time DESC);

-- Tick data (high-frequency, raw ticks)
CREATE TABLE tick_data (
  time TIMESTAMPTZ NOT NULL,
  symbol TEXT NOT NULL,
  price NUMERIC(18,4),
  volume INT,
  side TEXT CHECK (side IN ('BUY', 'SELL', NULL)),
  bid NUMERIC(18,4),
  ask NUMERIC(18,4)
);

SELECT create_hypertable('tick_data', 'time', if_not_exists => TRUE);

-- ════════════════════════════════════════════════════════════════════════════════
-- SECTION 3: ML PREDICTIONS & MODELS
-- ════════════════════════════════════════════════════════════════════════════════

CREATE TABLE model_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  version TEXT NOT NULL,
  model_type TEXT NOT NULL, -- 'AMSTAN', 'XGBOOST', 'FINBERT', etc.
  parameters JSONB NOT NULL,
  metrics JSONB,
  training_date TIMESTAMPTZ,
  artifact_path TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(name, version)
);

CREATE TABLE predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol TEXT NOT NULL,
  model_id UUID REFERENCES model_versions(id),
  prediction_time TIMESTAMPTZ NOT NULL,
  horizon_days INT NOT NULL,
  predicted_price NUMERIC(18,4),
  predicted_direction INT CHECK (predicted_direction IN (-1, 0, 1)),
  confidence NUMERIC(5,4) CHECK (confidence >= 0 AND confidence <= 1),
  lower_80 NUMERIC(18,4),
  upper_80 NUMERIC(18,4),
  lower_95 NUMERIC(18,4),
  upper_95 NUMERIC(18,4),
  feature_importances JSONB,
  actual_price NUMERIC(18,4),
  actual_direction INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_predictions_symbol_time ON predictions(symbol, prediction_time DESC);

-- ════════════════════════════════════════════════════════════════════════════════
-- SECTION 4: PORTFOLIO & HOLDINGS
-- ════════════════════════════════════════════════════════════════════════════════

CREATE TABLE portfolios (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  base_currency TEXT DEFAULT 'INR',
  base_amount NUMERIC(18,2),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE holdings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
  symbol TEXT NOT NULL,
  exchange TEXT NOT NULL,
  quantity NUMERIC(18,8) NOT NULL,
  avg_cost NUMERIC(18,4) NOT NULL,
  stop_loss NUMERIC(18,4),
  take_profit NUMERIC(18,4),
  opened_at TIMESTAMPTZ DEFAULT NOW(),
  closed_at TIMESTAMPTZ
);

CREATE INDEX idx_holdings_portfolio ON holdings(portfolio_id);

-- ════════════════════════════════════════════════════════════════════════════════
-- SECTION 5: RISK METRICS (TimescaleDB)
-- ════════════════════════════════════════════════════════════════════════════════

CREATE TABLE portfolio_risk_snapshots (
  time TIMESTAMPTZ NOT NULL,
  portfolio_id UUID NOT NULL REFERENCES portfolios(id),
  var_95 NUMERIC(18,4),
  var_99 NUMERIC(18,4),
  cvar_95 NUMERIC(18,4),
  cvar_99 NUMERIC(18,4),
  sharpe_90d NUMERIC(8,4),
  max_drawdown NUMERIC(8,4),
  beta NUMERIC(8,4),
  correlation_matrix JSONB
);

SELECT create_hypertable('portfolio_risk_snapshots', 'time', if_not_exists => TRUE);

-- ════════════════════════════════════════════════════════════════════════════════
-- SECTION 6: ALERTS & NOTIFICATIONS
-- ════════════════════════════════════════════════════════════════════════════════

CREATE TABLE alert_definitions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  symbol TEXT,
  alert_type TEXT NOT NULL CHECK (alert_type IN ('PRICE', 'TECHNICAL', 'ML_SIGNAL', 'SENTIMENT', 'ANOMALY', 'NEWS')),
  conditions JSONB NOT NULL,
  channels JSONB NOT NULL, -- ['IN_APP', 'EMAIL', 'WEBHOOK']
  cooldown_minutes INT DEFAULT 60,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE alert_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_id UUID REFERENCES alert_definitions(id),
  triggered_at TIMESTAMPTZ DEFAULT NOW(),
  payload JSON,
  notified BOOLEAN DEFAULT false
);

CREATE INDEX idx_alert_events_triggered ON alert_events(triggered_at DESC);

-- ════════════════════════════════════════════════════════════════════════════════
-- SECTION 7: AUDIT LOG (Immutable, blockchain-style integrity)
-- ════════════════════════════════════════════════════════════════════════════════

CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID,
  action TEXT NOT NULL,
  resource_type TEXT,
  resource_id TEXT,
  ip_address INET,
  user_agent TEXT,
  request_id UUID,
  metadata JSONB,
  prev_hash TEXT,
  row_hash TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

SELECT create_hypertable('audit_log', 'created_at', if_not_exists => TRUE);
CREATE INDEX idx_audit_log_user_time ON audit_log(user_id, created_at DESC);

-- ════════════════════════════════════════════════════════════════════════════════
-- SECTION 8: BACKTESTING RESULTS
-- ════════════════════════════════════════════════════════════════════════════════

CREATE TABLE backtest_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  strategy_name TEXT NOT NULL,
  parameters JSONB NOT NULL,
  start_date DATE,
  end_date DATE,
  initial_capital NUMERIC(18,2),
  final_value NUMERIC(18,2),
  returns NUMERIC(8,4),
  sharpe_ratio NUMERIC(8,4),
  max_drawdown NUMERIC(8,4),
  win_rate NUMERIC(5,4),
  profit_factor NUMERIC(8,4),
  num_trades INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE backtest_trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  backtest_id UUID NOT NULL REFERENCES backtest_runs(id) ON DELETE CASCADE,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
  entry_date DATE,
  entry_price NUMERIC(18,4),
  exit_date DATE,
  exit_price NUMERIC(18,4),
  quantity NUMERIC(18,8),
  pnl NUMERIC(18,4),
  pnl_percent NUMERIC(8,4)
);

-- ════════════════════════════════════════════════════════════════════════════════
-- SECTION 9: WATCHLISTS
-- ════════════════════════════════════════════════════════════════════════════════

CREATE TABLE watchlists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE watchlist_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  watchlist_id UUID NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
  symbol TEXT NOT NULL,
  exchange TEXT NOT NULL,
  added_at TIMESTAMPTZ DEFAULT NOW()
);

-- ════════════════════════════════════════════════════════════════════════════════
-- DONE - TimescaleDB Compression
-- ════════════════════════════════════════════════════════════════════════════════

-- Enable compression for historical data (older than 30 days)
ALTER TABLE ohlcv SET (
  timescaledb.compress,
  timescaledb.compress_interval='1 day'
);

ALTER TABLE tick_data SET (
  timescaledb.compress,
  timescaledb.compress_interval='1 day'
);

CREATE OR REPLACE FUNCTION compress_old_data()
RETURNS void AS $$
BEGIN
  SELECT compress_chunk(chunk) FROM show_chunks('ohlcv') chunk WHERE chunk::text::regclass::pg_stat_user_tables.last_vacuum < NOW() - INTERVAL '1 day';
END
$$ LANGUAGE plpgsql;

-- ════════════════════════════════════════════════════════════════════════════════

COMMIT;