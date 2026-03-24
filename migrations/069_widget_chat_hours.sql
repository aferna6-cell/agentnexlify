-- Migration 069: Add chat hours to widget_configs
-- Separate schedule for when the AI chat widget is active vs showing offline form.
-- Different from business_hours which controls appointment booking availability.
-- JSONB format matches business_hours.hours structure:
-- {"monday": {"start": "09:00", "end": "17:00", "enabled": true}, ...}

ALTER TABLE widget_configs
    ADD COLUMN IF NOT EXISTS chat_hours JSONB DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS chat_hours_enabled BOOLEAN NOT NULL DEFAULT false;

-- When chat_hours_enabled is false, the widget uses is_online toggle only.
-- When chat_hours_enabled is true, the widget auto-switches between online/offline
-- based on the chat_hours schedule + business timezone from business_hours table.
