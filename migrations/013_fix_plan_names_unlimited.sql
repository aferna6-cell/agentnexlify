-- Migration 013: Fix old plan names and remove conversation limits
-- All plans now have unlimited conversations.

-- Map old plan names to current names
UPDATE tenants SET plan = 'growth' WHERE plan = 'foundation';
UPDATE tenants SET plan = 'professional' WHERE plan = 'operations';

-- Clear conversation limits (all plans are unlimited now)
UPDATE tenants SET monthly_conversation_limit = NULL;

-- Update the CHECK constraint to only allow current plan names
ALTER TABLE tenants DROP CONSTRAINT IF EXISTS tenants_plan_check;
ALTER TABLE tenants ADD CONSTRAINT tenants_plan_check
  CHECK (plan IN ('free', 'growth', 'professional', 'enterprise'));
