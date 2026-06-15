-- Migration 151: audit_log
-- backend/services/integration_key_vault.py writes a best-effort audit row on
-- every integration-key save (action='integration_key_saved', metadata.provider).
-- The table never existed, so those writes silently no-op'd (the insert is
-- try/except-wrapped). Create it so integration-key audit logging actually
-- persists. Service-key-only access (RLS on, no policies), like other
-- platform/audit tables.

CREATE TABLE IF NOT EXISTS audit_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid,
  action text NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_tenant_created
  ON audit_log (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_log_action
  ON audit_log (action, created_at DESC);

ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
