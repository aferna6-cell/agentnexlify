-- 161_allow_new_plan_names_in_tenants_check.sql
--
-- RENUMBERED 2026-07-09 (was 158_, duplicating 158_wizard_events_fix_step_range;
-- see GH #373). No prod action needed: this migration is ALREADY APPLIED to prod
-- (2026-06-24, migration-history name "allow_new_plan_names_in_tenants_check")
-- and the live tenants_plan_check constraint was verified 2026-07-09 to include
-- chatbot + agent_os. Rename is repo hygiene only.
--
-- The 2026-06-15 reprice introduced two live plans — chatbot ($19.99) and
-- agent_os ($99.99, "AI Workforce") — but the tenants_plan_check constraint
-- still only permitted the retired plan names. Result: any Stripe checkout for
-- a new plan would fail to persist `plan` (constraint violation), and admins
-- couldn't set the new tiers via SQL. This is the DB-layer half of the
-- repricing migration (the code-layer gates were fixed in PREMIUM_PLANS /
-- plan_catalog; see docs/dev-knowledge/bug-patterns.md 2026-06-23).
--
-- Allow both new plan names; keep the legacy names for grandfathered tenants.

ALTER TABLE tenants DROP CONSTRAINT IF EXISTS tenants_plan_check;

ALTER TABLE tenants ADD CONSTRAINT tenants_plan_check
  CHECK (plan = ANY (ARRAY[
    'free',
    'chatbot',
    'agent_os',
    -- legacy / grandfathered (still honored on old contracts)
    'growth',
    'professional',
    'autopilot',
    'enterprise'
  ]));
