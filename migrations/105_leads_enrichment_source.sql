-- Migration 105: Add enrichment_source to leads table
-- Tracks how lead fields were populated:
--   'regex'  — basic regex parser in widget chat
--   'ai'     — structured_extractor managed agent
--   NULL     — legacy / manual / unknown
ALTER TABLE leads ADD COLUMN IF NOT EXISTS enrichment_source TEXT;
