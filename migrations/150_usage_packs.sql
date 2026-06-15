-- Migration 150: tenant_usage_packs
-- Stores one-time AI usage pack purchases. Each row lifts the effective
-- monthly token hard-limit by `tokens` for the given billing `period`
-- (YYYY-MM format, matching current_period_month() in ai_usage_guard.py).
-- The Python policy layer reads these rows and adds them to the plan-derived
-- hard limit before passing it to the reserve_ai_token_budget RPC.

CREATE TABLE IF NOT EXISTS tenant_usage_packs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  tokens bigint NOT NULL CHECK (tokens > 0),
  period text NOT NULL,
  stripe_session_id text UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tenant_usage_packs_tenant_period
  ON tenant_usage_packs(tenant_id, period);

ALTER TABLE tenant_usage_packs ENABLE ROW LEVEL SECURITY;

-- No public policies: service-key only access (consistent with
-- billing_refunds, billing_dunning_events, tenant_ai_usage_monthly).
