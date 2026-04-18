-- Migration 107: Admin refund request idempotency
-- Stores the operator-supplied refund request id so retries cannot create
-- duplicate Stripe refunds after transient API or audit-log failures.

ALTER TABLE billing_refunds
  ADD COLUMN IF NOT EXISTS refund_request_id text;

CREATE UNIQUE INDEX IF NOT EXISTS idx_billing_refunds_tenant_request
  ON billing_refunds(tenant_id, refund_request_id)
  WHERE refund_request_id IS NOT NULL;

COMMENT ON COLUMN billing_refunds.refund_request_id IS
  'Operator-supplied idempotency key for an admin refund request.';
