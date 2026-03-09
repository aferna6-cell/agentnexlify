-- Add free trial tracking to tenants
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS free_trial_started_at TIMESTAMPTZ;

-- Backfill existing free users: set trial start to their created_at date
UPDATE tenants
SET free_trial_started_at = created_at
WHERE plan = 'free' AND free_trial_started_at IS NULL;
