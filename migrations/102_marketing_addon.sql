-- Migration 102: Marketing Suite Add-on
-- Adds columns to tenants for the $49.99/mo Marketing Suite add-on subscription.
-- Gates: SEO Audit Hub, Social Media, Marketing Campaigns, Marketing Dashboard,
--        A/B Tests, Automation Rules, Trigger Logs.
--
-- Carve-out policy (answer #2 = strip-from-plans, force add-on):
--   - New column `marketing_addon_active` defaults FALSE for new tenants.
--   - Existing PAID tenants (growth/professional/autopilot/enterprise) are
--     GRANDFATHERED via one-time UPDATE below so today's live customers keep
--     access. Run `scripts/migrations/deactivate_grandfathered_marketing.sh`
--     separately when notice window expires to flip them off.
--   - Free-tier tenants default FALSE (they never had marketing).

ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS marketing_addon_active boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS marketing_addon_stripe_sub_id text,
  ADD COLUMN IF NOT EXISTS marketing_addon_started_at timestamptz,
  ADD COLUMN IF NOT EXISTS marketing_addon_grandfathered boolean NOT NULL DEFAULT false;

-- Grandfather existing paid customers (one-time). Flag `marketing_addon_grandfathered`
-- marks them so the deactivation script can target them distinctly from paid add-on
-- subscribers later.
UPDATE tenants
SET marketing_addon_active = true,
    marketing_addon_grandfathered = true
WHERE plan IN ('growth', 'professional', 'autopilot', 'enterprise')
  AND plan_status = 'active'
  AND marketing_addon_stripe_sub_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_tenants_marketing_addon_sub
  ON tenants (marketing_addon_stripe_sub_id)
  WHERE marketing_addon_stripe_sub_id IS NOT NULL;

COMMENT ON COLUMN tenants.marketing_addon_active IS
  'True when tenant has access to the Marketing Suite add-on (either via $49.99/mo subscription or grandfathered access).';
COMMENT ON COLUMN tenants.marketing_addon_stripe_sub_id IS
  'Stripe subscription ID for the Marketing Suite add-on. Separate from primary plan subscription.';
COMMENT ON COLUMN tenants.marketing_addon_started_at IS
  'Timestamp when add-on access began (subscription created or grandfather applied).';
COMMENT ON COLUMN tenants.marketing_addon_grandfathered IS
  'True if access came from one-time grandfather pass, not a paid add-on. Targeted by deactivation script.';
