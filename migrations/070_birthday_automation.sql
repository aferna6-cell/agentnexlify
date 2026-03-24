-- Migration 070: Birthday Automation Settings
-- Adds configurable birthday greeting feature to tenants

ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS birthday_enabled BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS birthday_message TEXT DEFAULT NULL;
