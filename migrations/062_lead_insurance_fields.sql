-- Migration 062: Insurance fields on leads
-- For dental/medical/healthcare businesses to track patient insurance

ALTER TABLE leads ADD COLUMN IF NOT EXISTS insurance_carrier TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS insurance_member_id TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS insurance_group TEXT;
