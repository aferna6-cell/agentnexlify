-- Migration 135: Tenant Stripe Connect scaffolding (Item 5, launch-safe / inert)
--
-- Lets a business owner connect THEIR OWN Stripe account so invoice payments
-- land in their account instead of the platform account. Architecture decision:
-- Stripe Connect *Standard* (OAuth) — we store ONLY the connected account id
-- (acct_xxx), never a secret key, so there is no key-vault liability. Zero
-- application fee by default (pure pass-through; not a marketplace cut).
--
-- These columns are additive and nullable. They stay empty until the gated
-- Connect onboarding flow is built and the TENANT_PAYMENTS_BYOK feature flag is
-- turned on. With the flag OFF (prod default), nothing reads these as active and
-- invoice payment links continue to use the platform Stripe account exactly as
-- before. Safe to apply before or with the backend deploy.

ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS stripe_connect_account_id TEXT;

ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS stripe_connect_status TEXT;

-- Allowed statuses: NULL (never connected), 'pending' (onboarding started),
-- 'active' (charges_enabled), 'disconnected' (owner revoked / we cleared it).
-- Enforced in application code, not a DB enum, so future states don't need a
-- migration.
COMMENT ON COLUMN tenants.stripe_connect_account_id IS
    'Stripe Connect Standard account id (acct_xxx) for routing this tenant''s invoice payments. NULL = use platform account. No secret key stored.';
COMMENT ON COLUMN tenants.stripe_connect_status IS
    'Connect onboarding state: pending | active | disconnected. NULL = never connected.';
