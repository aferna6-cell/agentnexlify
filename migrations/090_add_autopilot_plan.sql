-- 090: Add autopilot to plan CHECK constraint
-- The code supports autopilot plan but the DB constraint only allows
-- free, growth, professional, enterprise. This causes constraint violations
-- when autopilot subscriptions are created.

ALTER TABLE tenants DROP CONSTRAINT IF EXISTS tenants_plan_check;
ALTER TABLE tenants ADD CONSTRAINT tenants_plan_check
  CHECK (plan IN ('free', 'growth', 'professional', 'autopilot', 'enterprise'));

-- Also allow autopilot in autopilot_enabled (already exists as column from 046)
-- Update PLAN_PRICES in code already has autopilot: 29900
