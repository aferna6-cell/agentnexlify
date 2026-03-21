-- Migration 064: Date of birth on leads for birthday automation
ALTER TABLE leads ADD COLUMN IF NOT EXISTS date_of_birth DATE;
