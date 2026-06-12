-- 144: demo tenant flag for the public live-demo sandbox.
-- Demo tenants get outbound no-ops (email/SMS), a restricted "demo" JWT
-- role, and a nightly data reset. Default false for every real tenant.

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS is_demo BOOLEAN NOT NULL DEFAULT false;

-- The demo-login endpoint looks up "the" demo tenant on every visitor click.
CREATE INDEX IF NOT EXISTS idx_tenants_is_demo ON tenants (is_demo) WHERE is_demo;
