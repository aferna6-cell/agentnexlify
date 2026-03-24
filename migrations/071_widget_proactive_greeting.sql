-- Migration 071: Widget Proactive Greeting
-- Auto-opens the chat widget after a configurable delay to engage visitors

ALTER TABLE widget_configs
ADD COLUMN IF NOT EXISTS proactive_enabled BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE widget_configs
ADD COLUMN IF NOT EXISTS proactive_delay_seconds INTEGER NOT NULL DEFAULT 30;

ALTER TABLE widget_configs
ADD COLUMN IF NOT EXISTS proactive_message TEXT DEFAULT 'Hi there! Is there anything I can help you with today?';
