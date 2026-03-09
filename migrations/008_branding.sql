-- 008: Add branding JSONB column to widget_configs for white-label support
ALTER TABLE widget_configs ADD COLUMN IF NOT EXISTS branding JSONB DEFAULT '{}'::jsonb;
