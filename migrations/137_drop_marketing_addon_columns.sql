-- Migration 137: Drop retired marketing add-on columns
--
-- APPLIED 2026-06-10 via Supabase MCP AFTER the add-on-removal commit
-- (PR #228) rolled out on Railway — sequencing per
-- audits/audit-architecture-2026-06-10.md C1.

ALTER TABLE tenants DROP COLUMN IF EXISTS marketing_addon_active;
ALTER TABLE tenants DROP COLUMN IF EXISTS marketing_addon_grandfathered;
ALTER TABLE tenants DROP COLUMN IF EXISTS marketing_addon_started_at;
ALTER TABLE tenants DROP COLUMN IF EXISTS marketing_addon_stripe_sub_id;
