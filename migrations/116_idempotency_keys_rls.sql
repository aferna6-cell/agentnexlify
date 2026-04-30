-- Migration 116: Enable RLS on idempotency_keys
-- Why: response_body JSONB caches webhook payloads (Stripe customer email,
-- subscription IDs, Twilio phone numbers). Without RLS, anon/authenticated
-- callers using the project's public keys could enumerate cached webhook
-- responses across all tenants.
--
-- Service role bypasses RLS, so backend webhook handlers continue to work.
-- Anon and authenticated roles get nothing.

ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;

-- Deny all public access; service-role-only writes/reads.
CREATE POLICY "idempotency_keys_deny_public"
  ON idempotency_keys
  FOR ALL
  TO public
  USING (false)
  WITH CHECK (false);
