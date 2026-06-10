-- Migration 137: Drop retired marketing add-on columns
--
-- *** DO NOT APPLY until the add-on-removal commit (2026-06-10) is DEPLOYED
-- *** on Railway. The previous backend still SELECTs marketing_addon_active
-- *** in /me — dropping early 500s every authenticated request.
-- Sequencing per audits/audit-architecture-2026-06-10.md C1.

ALTER TABLE tenants DROP COLUMN IF EXISTS marketing_addon_active;
ALTER TABLE tenants DROP COLUMN IF EXISTS marketing_addon_grandfathered;
ALTER TABLE tenants DROP COLUMN IF EXISTS marketing_addon_started_at;
ALTER TABLE tenants DROP COLUMN IF EXISTS marketing_addon_stripe_sub_id;
