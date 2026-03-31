-- Add configurable teaser bubble message to widget config
ALTER TABLE widget_configs ADD COLUMN IF NOT EXISTS teaser_message TEXT;
COMMENT ON COLUMN widget_configs.teaser_message IS 'Text shown in teaser bubble when widget is minimized (shown after 3s delay)';
