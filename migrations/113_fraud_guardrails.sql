-- Migration 113: Fraud guardrails
-- Tracks signup attempts for velocity limiting and fraud analysis.

CREATE TABLE IF NOT EXISTS signup_attempts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ip_address text NOT NULL,
  email text NOT NULL,
  tenant_id uuid REFERENCES tenants(id) ON DELETE SET NULL,
  blocked_reason text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signup_attempts_ip_created
  ON signup_attempts(ip_address, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signup_attempts_email_created
  ON signup_attempts(email, created_at DESC);

ALTER TABLE signup_attempts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS signup_attempts_service_role_all ON signup_attempts;
CREATE POLICY signup_attempts_service_role_all ON signup_attempts
  FOR ALL USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');
