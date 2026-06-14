-- Migration 135: Add referral columns to tenants + backfill codes (rubric 9.4)
--
-- URGENT prod fix: repo migration 001 lists these columns but the LIVE schema
-- never had them. The referral wiring shipped 2026-06-10 (PR #227) inserts
-- referral_code at signup — against the live schema that made every new
-- /register 500. Lesson re-learned: trust the live schema, not migration
-- files (schema-discipline.md).

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS referral_code TEXT UNIQUE;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS referred_by UUID REFERENCES tenants(id);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS referral_discount_pct INTEGER DEFAULT 0;

-- Backfill codes for tenants that predate signup-time minting
UPDATE tenants
SET referral_code = substr(md5(gen_random_uuid()::text || id::text), 1, 8)
WHERE referral_code IS NULL;
