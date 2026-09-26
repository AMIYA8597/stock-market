-- RLS Helpers
CREATE OR REPLACE FUNCTION current_auth_id() RETURNS text AS $$
BEGIN
    RETURN current_setting('app.auth_id', true);
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION current_user_id() RETURNS uuid AS $$
BEGIN
    RETURN current_setting('app.user_id', true)::uuid;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION is_system() RETURNS boolean AS $$
BEGIN
    RETURN current_setting('app.is_system', true) = 'true';
EXCEPTION WHEN OTHERS THEN
    RETURN false;
END;
$$ LANGUAGE plpgsql STABLE;

-- RLS Enablement
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE org_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_counters ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE exchanges ENABLE ROW LEVEL SECURITY;
ALTER TABLE instruments ENABLE ROW LEVEL SECURITY;
ALTER TABLE instrument_aliases ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_calendar ENABLE ROW LEVEL SECURITY;
ALTER TABLE ohlcv ENABLE ROW LEVEL SECURITY;
ALTER TABLE quote_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingestion_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_quality_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE paper_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE paper_ledger_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE plan_entitlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_events ENABLE ROW LEVEL SECURITY;

-- Base grants for nq_api. The role is created here (if missing) rather than
-- assumed to pre-exist: nothing else in this repo ever creates it, so
-- running this against any fresh database (including a brand new Supabase
-- project) failed with `role "nq_api" does not exist` before this existed.
-- No LOGIN/password is set here -- add those with ALTER ROLE when you
-- actually want a connection to run as this least-privilege role instead
-- of the default postgres/pooler user.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nq_api') THEN
        CREATE ROLE nq_api;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO nq_api;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO nq_api;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO nq_api;

-- Policies

-- Users
CREATE POLICY users_system ON users FOR ALL USING (is_system());
CREATE POLICY users_self ON users FOR ALL USING (auth_id = current_auth_id());

-- Organizations
CREATE POLICY org_system ON organizations FOR ALL USING (is_system());
CREATE POLICY org_member ON organizations FOR SELECT USING (id IN (SELECT organization_id FROM org_members WHERE user_id = current_user_id()));

-- Org Members
CREATE POLICY org_members_system ON org_members FOR ALL USING (is_system());
CREATE POLICY org_members_self ON org_members FOR SELECT USING (user_id = current_user_id());

-- Market Data (Public/System)
CREATE POLICY market_system ON exchanges FOR ALL USING (is_system());
CREATE POLICY market_read_exchanges ON exchanges FOR SELECT USING (true);

CREATE POLICY inst_system ON instruments FOR ALL USING (is_system());
CREATE POLICY inst_read ON instruments FOR SELECT USING (true);

CREATE POLICY alias_system ON instrument_aliases FOR ALL USING (is_system());
CREATE POLICY alias_read ON instrument_aliases FOR SELECT USING (true);

CREATE POLICY cal_system ON market_calendar FOR ALL USING (is_system());
CREATE POLICY cal_read ON market_calendar FOR SELECT USING (true);

CREATE POLICY ohlcv_system ON ohlcv FOR ALL USING (is_system());
CREATE POLICY ohlcv_read ON ohlcv FOR SELECT USING (true);

CREATE POLICY quote_system ON quote_snapshots FOR ALL USING (is_system());
CREATE POLICY quote_read ON quote_snapshots FOR SELECT USING (true);

CREATE POLICY ingestion_system ON ingestion_runs FOR ALL USING (is_system());
CREATE POLICY ingestion_read ON ingestion_runs FOR SELECT USING (true);

CREATE POLICY datasets_system ON datasets FOR ALL USING (is_system());
CREATE POLICY datasets_read ON datasets FOR SELECT USING (true);

CREATE POLICY models_system ON model_registry FOR ALL USING (is_system());
CREATE POLICY models_read ON model_registry FOR SELECT USING (true);

CREATE POLICY predictions_system ON predictions FOR ALL USING (is_system());
CREATE POLICY predictions_read ON predictions FOR SELECT USING (true);

-- Ledger
CREATE POLICY ledger_system ON paper_ledger_entries FOR ALL USING (is_system());
CREATE POLICY ledger_read ON paper_ledger_entries FOR SELECT USING (account_id IN (SELECT id FROM paper_accounts WHERE user_id = current_user_id()));

CREATE POLICY accounts_system ON paper_accounts FOR ALL USING (is_system());
CREATE POLICY accounts_self ON paper_accounts FOR ALL USING (user_id = current_user_id());
