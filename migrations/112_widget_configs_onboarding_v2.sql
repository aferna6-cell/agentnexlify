-- 112_widget_configs_onboarding_v2.sql
-- Onboarding v2 — feature-flag column + readiness tracking on widget_configs.
-- Per spec/onboarding-v2_spec.md §6.1.1.
--
-- Backward compat: every existing tenant defaults to onboarding_version='v1' and
-- ready_to_launch=false. v2 wizard completion flips the column for new signups.
--
-- Note: spec reserved migration 115-117 for this work, but actual sequence
-- gap was 111→. Using 112 (next sequential per migration-workflow rule).

ALTER TABLE widget_configs
  ADD COLUMN IF NOT EXISTS onboarding_version TEXT
    NOT NULL
    DEFAULT 'v1'
    CHECK (onboarding_version IN ('v1', 'v2'));

ALTER TABLE widget_configs
  ADD COLUMN IF NOT EXISTS ready_to_launch BOOLEAN
    NOT NULL
    DEFAULT false;

ALTER TABLE widget_configs
  ADD COLUMN IF NOT EXISTS readiness_criteria JSONB
    NOT NULL
    DEFAULT '{"services_count": 0, "hours_filled": false, "faqs_count": 0, "logo_uploaded": false}'::jsonb;

-- Cohort queries: filter by onboarding_version for v2 funnel analysis.
CREATE INDEX IF NOT EXISTS idx_widget_configs_onboarding_version
  ON widget_configs (onboarding_version)
  WHERE onboarding_version = 'v2';

-- Comment for self-documenting schema (visible in supabase studio).
COMMENT ON COLUMN widget_configs.onboarding_version IS
  'v1=legacy 6-step wizard, v2=7-step wizard with auto-KB + vertical presets (mig 112+)';
COMMENT ON COLUMN widget_configs.ready_to_launch IS
  'Flipped true when readiness_criteria thresholds met. Drives "Ready to launch" badge.';
COMMENT ON COLUMN widget_configs.readiness_criteria IS
  'Per-tenant readiness checklist. Keys: services_count, hours_filled, faqs_count, logo_uploaded.';
