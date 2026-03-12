-- Migration 025: Add scheduled_for to content_items
-- Allows tenants to schedule content for future posting dates.
-- When scheduled_for is set and status is 'scheduled', the content
-- appears on the calendar view in Content Studio.

ALTER TABLE content_items ADD COLUMN IF NOT EXISTS scheduled_for DATE;

CREATE INDEX IF NOT EXISTS idx_content_items_scheduled ON content_items(tenant_id, scheduled_for)
    WHERE scheduled_for IS NOT NULL;
