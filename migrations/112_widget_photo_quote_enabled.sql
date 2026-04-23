-- 112_widget_photo_quote_enabled.sql
-- Add photo_quote_enabled flag to widget_configs
-- Issue: #36 (photo-quote feature)

ALTER TABLE widget_configs ADD COLUMN IF NOT EXISTS photo_quote_enabled boolean NOT NULL DEFAULT false;
