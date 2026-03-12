-- Migration 015: Widget offline mode toggle
-- Allows businesses to switch their widget between online (live chat) and offline (contact form) modes.

ALTER TABLE widget_configs ADD COLUMN IF NOT EXISTS is_online BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE widget_configs ADD COLUMN IF NOT EXISTS offline_message TEXT DEFAULT 'We are currently offline. Leave your details and we will get back to you soon!';
