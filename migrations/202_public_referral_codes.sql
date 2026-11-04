-- Migration 202: public referral codes must not be widget API keys.
--
-- tenants.referral_code (migration 135) is the non-secret share code.
-- The widget watermark and GET /api/v1/referral/my-stats were publishing
-- widget_configs.api_key (anx_...) as that code. This backfill mints a
-- code for any tenant missing one, and replaces a code that is itself a
-- widget key.
--
-- Old ?ref=anx_... links stay resolvable in the API (server-side lookup of
-- widget_configs.api_key → this public code). The key is not written into
-- new share links or referral_clicks rows.
--
-- NOT applied by this PR. Do not run this file against production from an
-- agent session.
--
-- Uniqueness already exists: prod constraint tenants_referral_code_key
-- (migration 135, referral_code TEXT UNIQUE). A second unique index is not
-- created here. Prod has rows on tenants: 0 duplicate referral_code values
-- and 3 NULLs. The read-only count in the pull request body matches that.

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS referral_code TEXT;

DO $$
DECLARE
  r RECORD;
  candidate TEXT;
BEGIN
  FOR r IN
    SELECT t.id
    FROM tenants t
    LEFT JOIN widget_configs w ON w.tenant_id = t.id
    WHERE t.referral_code IS NULL
       OR t.referral_code LIKE 'anx\_%'
       OR (w.api_key IS NOT NULL AND t.referral_code = w.api_key)
  LOOP
    LOOP
      candidate := substr(replace(gen_random_uuid()::text, '-', ''), 1, 12);
      EXIT WHEN NOT EXISTS (
        SELECT 1 FROM tenants WHERE referral_code = candidate
      );
    END LOOP;
    UPDATE tenants SET referral_code = candidate WHERE id = r.id;
  END LOOP;
END $$;

-- No new unique index. tenants_referral_code_key already enforces
-- uniqueness. Multiple NULLs remain allowed.

COMMENT ON COLUMN tenants.referral_code IS
  'Public referral code. Never a widget API key. Share links use this value.';
