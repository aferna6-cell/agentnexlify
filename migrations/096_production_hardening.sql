-- Migration 096: Production hardening
-- Fix fresh-schema client_id drift and add DB-backed coordination primitives.

-- Canonical tenant FK for app code: leads.client_id and conversations.client_id.
ALTER TABLE leads ADD COLUMN IF NOT EXISTS client_id UUID;
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'leads' AND column_name = 'tenant_id'
  ) THEN
    EXECUTE 'UPDATE leads SET client_id = tenant_id WHERE client_id IS NULL AND tenant_id IS NOT NULL';
  END IF;
END $$;

-- Existing production/staging data can contain orphaned client_id values.
-- Add the FK as NOT VALID first so new writes are protected without deleting
-- historical rows; validate only after the existing data is clean.
DO $$
DECLARE
  orphan_count INTEGER;
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'leads_client_id_fkey'
  ) THEN
    ALTER TABLE leads
      ADD CONSTRAINT leads_client_id_fkey
      FOREIGN KEY (client_id) REFERENCES tenants(id) ON DELETE CASCADE
      NOT VALID;
  END IF;

  SELECT COUNT(*) INTO orphan_count
    FROM leads l
   WHERE l.client_id IS NOT NULL
     AND NOT EXISTS (
       SELECT 1 FROM tenants t WHERE t.id = l.client_id
     );

  IF orphan_count = 0 THEN
    ALTER TABLE leads VALIDATE CONSTRAINT leads_client_id_fkey;
  ELSE
    RAISE NOTICE 'leads_client_id_fkey left NOT VALID: % existing leads.client_id values do not reference tenants.id', orphan_count;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM leads WHERE client_id IS NULL) AND orphan_count = 0 THEN
    ALTER TABLE leads ALTER COLUMN client_id SET NOT NULL;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_leads_client_id ON leads(client_id);

ALTER TABLE conversations ADD COLUMN IF NOT EXISTS client_id UUID;
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'conversations' AND column_name = 'tenant_id'
  ) THEN
    EXECUTE 'UPDATE conversations SET client_id = tenant_id WHERE client_id IS NULL AND tenant_id IS NOT NULL';
  END IF;
END $$;

-- Same strategy for historical conversations that predate the client_id schema.
DO $$
DECLARE
  orphan_count INTEGER;
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'conversations_client_id_fkey'
  ) THEN
    ALTER TABLE conversations
      ADD CONSTRAINT conversations_client_id_fkey
      FOREIGN KEY (client_id) REFERENCES tenants(id) ON DELETE CASCADE
      NOT VALID;
  END IF;

  SELECT COUNT(*) INTO orphan_count
    FROM conversations c
   WHERE c.client_id IS NOT NULL
     AND NOT EXISTS (
       SELECT 1 FROM tenants t WHERE t.id = c.client_id
     );

  IF orphan_count = 0 THEN
    ALTER TABLE conversations VALIDATE CONSTRAINT conversations_client_id_fkey;
  ELSE
    RAISE NOTICE 'conversations_client_id_fkey left NOT VALID: % existing conversations.client_id values do not reference tenants.id', orphan_count;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM conversations WHERE client_id IS NULL) AND orphan_count = 0 THEN
    ALTER TABLE conversations ALTER COLUMN client_id SET NOT NULL;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_conversations_client_id ON conversations(client_id);

-- One scheduler lease table shared by all Uvicorn workers.
CREATE TABLE IF NOT EXISTS automation_locks (
  name TEXT PRIMARY KEY,
  owner TEXT NOT NULL,
  locked_until TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE automation_locks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS automation_locks_service_role_all ON automation_locks;
CREATE POLICY automation_locks_service_role_all ON automation_locks
  FOR ALL USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

CREATE OR REPLACE FUNCTION try_acquire_automation_lock(
  p_name TEXT,
  p_owner TEXT,
  p_ttl_seconds INTEGER
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  rows_affected INTEGER;
BEGIN
  INSERT INTO automation_locks (name, owner, locked_until, updated_at)
  VALUES (p_name, p_owner, NOW() + make_interval(secs => p_ttl_seconds), NOW())
  ON CONFLICT (name) DO UPDATE
    SET owner = EXCLUDED.owner,
        locked_until = EXCLUDED.locked_until,
        updated_at = NOW()
    WHERE automation_locks.locked_until < NOW()
       OR automation_locks.owner = EXCLUDED.owner;

  GET DIAGNOSTICS rows_affected = ROW_COUNT;
  RETURN rows_affected > 0;
END;
$$;

CREATE OR REPLACE FUNCTION release_automation_lock(p_name TEXT, p_owner TEXT)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  DELETE FROM automation_locks WHERE name = p_name AND owner = p_owner;
END;
$$;

-- Durable per-tenant email quotas. This replaces process-local counters.
CREATE TABLE IF NOT EXISTS tenant_email_daily_sends (
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  send_date DATE NOT NULL DEFAULT CURRENT_DATE,
  send_count INTEGER NOT NULL DEFAULT 0 CHECK (send_count >= 0),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (tenant_id, send_date)
);

ALTER TABLE tenant_email_daily_sends ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_email_daily_sends_service_role_all ON tenant_email_daily_sends;
CREATE POLICY tenant_email_daily_sends_service_role_all ON tenant_email_daily_sends
  FOR ALL USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

CREATE OR REPLACE FUNCTION reserve_email_send_quota(
  p_tenant_id UUID,
  p_daily_limit INTEGER
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  rows_affected INTEGER;
BEGIN
  INSERT INTO tenant_email_daily_sends (tenant_id, send_date, send_count, updated_at)
  VALUES (p_tenant_id, CURRENT_DATE, 0, NOW())
  ON CONFLICT (tenant_id, send_date) DO NOTHING;

  UPDATE tenant_email_daily_sends
     SET send_count = send_count + 1,
         updated_at = NOW()
   WHERE tenant_id = p_tenant_id
     AND send_date = CURRENT_DATE
     AND send_count < p_daily_limit;

  GET DIAGNOSTICS rows_affected = ROW_COUNT;
  RETURN rows_affected > 0;
END;
$$;

-- One-time OAuth state nonces to prevent replay/cross-session OAuth linking.
CREATE TABLE IF NOT EXISTS oauth_states (
  provider TEXT NOT NULL,
  nonce TEXT NOT NULL,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  expires_at TIMESTAMPTZ NOT NULL,
  consumed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (provider, nonce)
);

CREATE INDEX IF NOT EXISTS idx_oauth_states_tenant_provider
  ON oauth_states(tenant_id, provider);
CREATE INDEX IF NOT EXISTS idx_oauth_states_expiry
  ON oauth_states(expires_at)
  WHERE consumed_at IS NULL;

ALTER TABLE oauth_states ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS oauth_states_service_role_all ON oauth_states;
CREATE POLICY oauth_states_service_role_all ON oauth_states
  FOR ALL USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');
