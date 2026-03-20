CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  hashed_password VARCHAR(255) NOT NULL,
  full_name VARCHAR(255),
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE symbols (
  id SERIAL PRIMARY KEY,
  ticker VARCHAR(32) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  exchange VARCHAR(32) NOT NULL,
  sector VARCHAR(64),
  industry VARCHAR(64),
  market_cap_bucket VARCHAR(16),
  asset_type VARCHAR(16) NOT NULL,
  currency VARCHAR(8) DEFAULT 'USD',
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ohlcv (
  time TIMESTAMPTZ NOT NULL,
  symbol_id INTEGER NOT NULL REFERENCES symbols(id),
  open NUMERIC(20, 8) NOT NULL,
  high NUMERIC(20, 8) NOT NULL,
  low NUMERIC(20, 8) NOT NULL,
  close NUMERIC(20, 8) NOT NULL,
  volume NUMERIC(24, 4) NOT NULL,
  adjusted_close NUMERIC(20, 8),
  interval VARCHAR(8) NOT NULL,
  PRIMARY KEY (time, symbol_id, interval)
);
SELECT create_hypertable('ohlcv', 'time', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS ix_ohlcv_symbol_time_desc ON ohlcv (symbol_id, time DESC);

CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_1h WITH (timescaledb.continuous) AS
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
  GROUP BY bucket, symbol_id;

CREATE TABLE feature_vectors (
  time TIMESTAMPTZ NOT NULL,
  symbol_id INTEGER NOT NULL REFERENCES symbols(id),
  features JSONB NOT NULL,
  feature_version VARCHAR(16) NOT NULL DEFAULT 'v1',
  PRIMARY KEY (time, symbol_id)
);
SELECT create_hypertable('feature_vectors', 'time', chunk_time_interval => INTERVAL '30 days', if_not_exists => TRUE);

CREATE TABLE regime_states (
  time TIMESTAMPTZ NOT NULL PRIMARY KEY,
  viterbi_state SMALLINT NOT NULL,
  state_probs NUMERIC(6,4)[] NOT NULL,
  conditional_vol NUMERIC(10,6) NOT NULL,
  vol_forecast_5d NUMERIC(10,6),
  vol_forecast_21d NUMERIC(10,6)
);

CREATE TABLE ml_predictions (
  id BIGSERIAL PRIMARY KEY,
  time TIMESTAMPTZ NOT NULL,
  symbol_id INTEGER NOT NULL REFERENCES symbols(id),
  model_name VARCHAR(32) NOT NULL,
  horizon_days SMALLINT NOT NULL,
  p10_return NUMERIC(10,6),
  p50_return NUMERIC(10,6),
  p90_return NUMERIC(10,6),
  raw_signal NUMERIC(6,4),
  confidence NUMERIC(5,4),
  shap_values JSONB,
  attention_weights JSONB,
  actual_return NUMERIC(10,6),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ml_predictions_symbol_time_model ON ml_predictions (symbol_id, time DESC, model_name);

CREATE TABLE ensemble_signals (
  time TIMESTAMPTZ NOT NULL,
  symbol_id INTEGER NOT NULL REFERENCES symbols(id),
  signal NUMERIC(6,4) NOT NULL,
  confidence NUMERIC(5,4) NOT NULL,
  direction VARCHAR(12) NOT NULL,
  model_weights JSONB NOT NULL,
  regime_state SMALLINT NOT NULL,
  kelly_fraction NUMERIC(5,4),
  PRIMARY KEY (time, symbol_id)
);

CREATE TABLE portfolio_holdings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  symbol_id INTEGER NOT NULL REFERENCES symbols(id),
  quantity NUMERIC(20, 8) NOT NULL,
  avg_buy_price NUMERIC(20, 8) NOT NULL,
  realized_pnl NUMERIC(20, 4) DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, symbol_id)
);

CREATE TABLE transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  symbol_id INTEGER NOT NULL REFERENCES symbols(id),
  type VARCHAR(8) NOT NULL,
  quantity NUMERIC(20, 8) NOT NULL,
  price NUMERIC(20, 8) NOT NULL,
  brokerage NUMERIC(12, 4) DEFAULT 0,
  stt NUMERIC(12, 4) DEFAULT 0,
  net_amount NUMERIC(20, 4) NOT NULL,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  symbol_id INTEGER REFERENCES symbols(id),
  alert_type VARCHAR(32) NOT NULL,
  threshold NUMERIC(20, 8),
  is_triggered BOOLEAN DEFAULT false,
  triggered_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE backtest_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  strategy_name VARCHAR(64) NOT NULL,
  strategy_params JSONB NOT NULL,
  universe JSONB NOT NULL,
  date_from DATE NOT NULL,
  date_to DATE NOT NULL,
  initial_capital NUMERIC(16, 2) NOT NULL,
  status VARCHAR(16) DEFAULT 'PENDING',
  results JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE TABLE news_sentiment (
  id BIGSERIAL PRIMARY KEY,
  symbol_id INTEGER REFERENCES symbols(id),
  headline TEXT NOT NULL,
  source VARCHAR(128),
  url TEXT,
  sentiment_label VARCHAR(16) NOT NULL,
  sentiment_score NUMERIC(5,4) NOT NULL,
  published_at TIMESTAMPTZ NOT NULL,
  processed_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_news_sentiment_symbol_published ON news_sentiment (symbol_id, published_at DESC);
