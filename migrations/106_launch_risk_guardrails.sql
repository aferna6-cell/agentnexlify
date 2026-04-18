-- Migration 106: Launch risk guardrails
-- Adds DB-backed AI usage caps, refund audit trail, cancel reasons, and dunning logs.

ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS ai_monthly_token_alert_threshold integer CHECK (ai_monthly_token_alert_threshold IS NULL OR ai_monthly_token_alert_threshold > 0),
  ADD COLUMN IF NOT EXISTS ai_monthly_token_hard_limit integer CHECK (ai_monthly_token_hard_limit IS NULL OR ai_monthly_token_hard_limit > 0),
  ADD COLUMN IF NOT EXISTS cancellation_requested_at timestamptz,
  ADD COLUMN IF NOT EXISTS cancellation_reason text,
  ADD COLUMN IF NOT EXISTS cancellation_reason_detail text,
  ADD COLUMN IF NOT EXISTS billing_dunning_last_sent_at timestamptz,
  ADD COLUMN IF NOT EXISTS billing_dunning_attempt_count integer NOT NULL DEFAULT 0 CHECK (billing_dunning_attempt_count >= 0);

COMMENT ON COLUMN tenants.ai_monthly_token_alert_threshold IS
  'Optional per-tenant monthly AI token alert threshold. If null, app derives threshold from plan baseline x3.';
COMMENT ON COLUMN tenants.ai_monthly_token_hard_limit IS
  'Optional per-tenant monthly AI token hard stop. If null, app derives limit from plan baseline x5.';
COMMENT ON COLUMN tenants.cancellation_requested_at IS
  'Latest timestamp when tenant requested subscription cancellation at period end.';
COMMENT ON COLUMN tenants.cancellation_reason IS
  'Latest customer-selected cancellation reason.';
COMMENT ON COLUMN tenants.cancellation_reason_detail IS
  'Optional latest free-text cancellation feedback.';
COMMENT ON COLUMN tenants.billing_dunning_last_sent_at IS
  'Latest time the app sent a failed-payment notice for this tenant.';
COMMENT ON COLUMN tenants.billing_dunning_attempt_count IS
  'Latest Stripe invoice payment attempt count seen during dunning.';

CREATE TABLE IF NOT EXISTS tenant_ai_usage_monthly (
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  period_month date NOT NULL,
  input_tokens integer NOT NULL DEFAULT 0 CHECK (input_tokens >= 0),
  output_tokens integer NOT NULL DEFAULT 0 CHECK (output_tokens >= 0),
  cache_creation_input_tokens integer NOT NULL DEFAULT 0 CHECK (cache_creation_input_tokens >= 0),
  cache_read_input_tokens integer NOT NULL DEFAULT 0 CHECK (cache_read_input_tokens >= 0),
  reserved_tokens integer NOT NULL DEFAULT 0 CHECK (reserved_tokens >= 0),
  call_count integer NOT NULL DEFAULT 0 CHECK (call_count >= 0),
  blocked_count integer NOT NULL DEFAULT 0 CHECK (blocked_count >= 0),
  alert_sent_at timestamptz,
  hard_blocked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, period_month)
);

CREATE INDEX IF NOT EXISTS idx_tenant_ai_usage_period
  ON tenant_ai_usage_monthly(period_month, updated_at DESC);

ALTER TABLE tenant_ai_usage_monthly ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_ai_usage_monthly_service_role_all ON tenant_ai_usage_monthly;
CREATE POLICY tenant_ai_usage_monthly_service_role_all ON tenant_ai_usage_monthly
  FOR ALL USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

CREATE OR REPLACE FUNCTION reserve_ai_token_budget(
  p_tenant_id uuid,
  p_period_month date,
  p_hard_limit_tokens integer,
  p_estimated_tokens integer
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  rows_affected integer;
  estimate integer := greatest(coalesce(p_estimated_tokens, 1), 1);
BEGIN
  INSERT INTO tenant_ai_usage_monthly (tenant_id, period_month, updated_at)
  VALUES (p_tenant_id, p_period_month, now())
  ON CONFLICT (tenant_id, period_month) DO NOTHING;

  UPDATE tenant_ai_usage_monthly
     SET reserved_tokens = reserved_tokens + estimate,
         updated_at = now()
   WHERE tenant_id = p_tenant_id
     AND period_month = p_period_month
     AND (
       input_tokens
       + output_tokens
       + cache_creation_input_tokens
       + cache_read_input_tokens
       + reserved_tokens
       + estimate
     ) <= p_hard_limit_tokens;

  GET DIAGNOSTICS rows_affected = ROW_COUNT;
  IF rows_affected > 0 THEN
    RETURN true;
  END IF;

  UPDATE tenant_ai_usage_monthly
     SET blocked_count = blocked_count + 1,
         hard_blocked_at = coalesce(hard_blocked_at, now()),
         updated_at = now()
   WHERE tenant_id = p_tenant_id
     AND period_month = p_period_month;

  RETURN false;
END;
$$;

CREATE OR REPLACE FUNCTION release_ai_token_reservation(
  p_tenant_id uuid,
  p_period_month date,
  p_reserved_tokens integer
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  UPDATE tenant_ai_usage_monthly
     SET reserved_tokens = greatest(reserved_tokens - greatest(coalesce(p_reserved_tokens, 0), 0), 0),
         updated_at = now()
   WHERE tenant_id = p_tenant_id
     AND period_month = p_period_month;
END;
$$;

CREATE OR REPLACE FUNCTION record_ai_token_usage(
  p_tenant_id uuid,
  p_period_month date,
  p_reserved_tokens integer,
  p_input_tokens integer,
  p_output_tokens integer,
  p_cache_creation_input_tokens integer,
  p_cache_read_input_tokens integer,
  p_alert_threshold_tokens integer,
  p_hard_limit_tokens integer
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  usage_row tenant_ai_usage_monthly%ROWTYPE;
  total_tokens integer;
  alert_now boolean := false;
  hard_now boolean := false;
BEGIN
  INSERT INTO tenant_ai_usage_monthly (tenant_id, period_month, updated_at)
  VALUES (p_tenant_id, p_period_month, now())
  ON CONFLICT (tenant_id, period_month) DO NOTHING;

  UPDATE tenant_ai_usage_monthly
     SET input_tokens = input_tokens + greatest(coalesce(p_input_tokens, 0), 0),
         output_tokens = output_tokens + greatest(coalesce(p_output_tokens, 0), 0),
         cache_creation_input_tokens = cache_creation_input_tokens + greatest(coalesce(p_cache_creation_input_tokens, 0), 0),
         cache_read_input_tokens = cache_read_input_tokens + greatest(coalesce(p_cache_read_input_tokens, 0), 0),
         reserved_tokens = greatest(reserved_tokens - greatest(coalesce(p_reserved_tokens, 0), 0), 0),
         call_count = call_count + 1,
         updated_at = now()
   WHERE tenant_id = p_tenant_id
     AND period_month = p_period_month
   RETURNING * INTO usage_row;

  total_tokens :=
    usage_row.input_tokens
    + usage_row.output_tokens
    + usage_row.cache_creation_input_tokens
    + usage_row.cache_read_input_tokens;

  IF usage_row.alert_sent_at IS NULL AND total_tokens >= p_alert_threshold_tokens THEN
    alert_now := true;
    UPDATE tenant_ai_usage_monthly
       SET alert_sent_at = now(),
           updated_at = now()
     WHERE tenant_id = p_tenant_id
       AND period_month = p_period_month
     RETURNING * INTO usage_row;
  END IF;

  IF usage_row.hard_blocked_at IS NULL AND total_tokens >= p_hard_limit_tokens THEN
    hard_now := true;
    UPDATE tenant_ai_usage_monthly
       SET hard_blocked_at = now(),
           updated_at = now()
     WHERE tenant_id = p_tenant_id
       AND period_month = p_period_month
     RETURNING * INTO usage_row;
  END IF;

  RETURN jsonb_build_object(
    'total_tokens', total_tokens,
    'alert_triggered', alert_now,
    'hard_limit_reached', hard_now,
    'alert_threshold_tokens', p_alert_threshold_tokens,
    'hard_limit_tokens', p_hard_limit_tokens
  );
END;
$$;

CREATE TABLE IF NOT EXISTS billing_refunds (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  stripe_refund_id text NOT NULL UNIQUE,
  stripe_payment_intent_id text,
  stripe_charge_id text,
  amount_cents integer CHECK (amount_cents IS NULL OR amount_cents > 0),
  currency text NOT NULL DEFAULT 'usd',
  stripe_reason text,
  internal_reason text NOT NULL,
  requested_by text NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  raw_refund jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_billing_refunds_tenant_created
  ON billing_refunds(tenant_id, created_at DESC);

ALTER TABLE billing_refunds ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS billing_refunds_service_role_all ON billing_refunds;
CREATE POLICY billing_refunds_service_role_all ON billing_refunds
  FOR ALL USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

CREATE TABLE IF NOT EXISTS tenant_cancellation_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  stripe_subscription_id text,
  plan text,
  reason text NOT NULL,
  reason_detail text,
  feedback text,
  current_period_end timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tenant_cancellation_events_tenant_created
  ON tenant_cancellation_events(tenant_id, created_at DESC);

ALTER TABLE tenant_cancellation_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_cancellation_events_service_role_all ON tenant_cancellation_events;
CREATE POLICY tenant_cancellation_events_service_role_all ON tenant_cancellation_events
  FOR ALL USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

CREATE TABLE IF NOT EXISTS billing_dunning_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  stripe_invoice_id text NOT NULL,
  stripe_subscription_id text,
  stripe_customer_id text,
  attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  next_payment_attempt timestamptz,
  amount_due_cents integer,
  currency text NOT NULL DEFAULT 'usd',
  hosted_invoice_url text,
  invoice_pdf text,
  email_sent boolean NOT NULL DEFAULT false,
  email_detail text,
  raw_invoice jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_billing_dunning_events_tenant_created
  ON billing_dunning_events(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_billing_dunning_events_invoice
  ON billing_dunning_events(stripe_invoice_id);

ALTER TABLE billing_dunning_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS billing_dunning_events_service_role_all ON billing_dunning_events;
CREATE POLICY billing_dunning_events_service_role_all ON billing_dunning_events
  FOR ALL USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');
