-- Migration 056: Add google_place_id to tenants table
-- Enables direct Google write-review links in review request emails/SMS.
-- Format: https://search.google.com/local/writereview?placeid={place_id}

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS google_place_id TEXT;
