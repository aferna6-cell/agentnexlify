-- Add teaser_delay_seconds and teaser_enabled to widget_configs
-- teaser_message was already added in migration 071

ALTER TABLE widget_configs
  ADD COLUMN IF NOT EXISTS teaser_delay_seconds INTEGER NOT NULL DEFAULT 3,
  ADD COLUMN IF NOT EXISTS teaser_enabled BOOLEAN NOT NULL DEFAULT TRUE;

COMMENT ON COLUMN widget_configs.teaser_delay_seconds IS 'Seconds after page load before teaser bubble appears (0-60)';
COMMENT ON COLUMN widget_configs.teaser_enabled IS 'Whether the teaser bubble is shown at all';
