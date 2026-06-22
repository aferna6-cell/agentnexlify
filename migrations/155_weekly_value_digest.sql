-- Migration 155: Weekly Value Digest (spec: specs/weekly-value-digest_spec.md, gap G2)
-- Additive only. NOT auto-applied — apply via Supabase MCP after merge, then flag in schema-log.
--
-- Adds an opt-in flag so no tenant is emailed without explicit enablement, and an idempotency
-- ledger so a given (tenant, week) is sent at most once even if the job runs twice.

ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS weekly_digest_opt_in boolean NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS digest_sends (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  week_start  date NOT NULL,
  sent_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, week_start)
);

ALTER TABLE digest_sends ENABLE ROW LEVEL SECURITY;

COMMENT ON COLUMN tenants.weekly_digest_opt_in IS
  'When true, the weekly value digest job emails this tenant. Default false — no send without opt-in.';
COMMENT ON TABLE digest_sends IS
  'Idempotency ledger for the weekly value digest. One row per (tenant, week_start); UNIQUE prevents double-send.';
