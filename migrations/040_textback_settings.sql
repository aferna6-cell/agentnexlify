-- Migration 040: Missed call text-back settings on tenants
-- Configurable auto text-back: enable/disable, custom message, quiet hours.

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS textback_enabled BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS textback_message TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS textback_quiet_start TEXT; -- e.g. "22:00"
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS textback_quiet_end TEXT;   -- e.g. "07:00"
