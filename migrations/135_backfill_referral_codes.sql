-- Migration 135: Backfill tenants.referral_code (launch rubric 9.4 follow-up)
-- New signups mint a code at provision time (auth.py, 2026-06-10); existing
-- tenants predate that and have NULL — they could never share a link.

UPDATE tenants
SET referral_code = substr(md5(gen_random_uuid()::text || id::text), 1, 8)
WHERE referral_code IS NULL;
