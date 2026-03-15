-- Migration 046: Local Business Autopilot — onboarding progress + monthly reports

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS autopilot_enabled BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS onboarding_completed_at TIMESTAMPTZ;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS last_monthly_report_at TIMESTAMPTZ;
