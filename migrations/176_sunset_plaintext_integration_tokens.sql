-- 176: Sunset plaintext OAuth token columns on integrations (GH #266 step 4).
--
-- PREREQUISITE — DO NOT APPLY until INTEGRATIONS_ENC_KEY is set in Railway
-- prod (and CI). Without the key the vault's encrypt_oauth_tokens() no-ops,
-- so new OAuth connects would have nowhere to store tokens after this drop.
--
-- Safe-to-apply evidence gathered 2026-07-20:
--   * prod `integrations` has 0 rows (verified via SQL) — nothing to backfill,
--     nothing to lose (step 3 of the staged plan is vacuous).
--   * every reader routes through integration_key_vault.decrypt_integration_row
--     (google_calendar, m365_calendar/mail, drive_kb_sync, hubspot_tenant,
--     integration_health_checker, twilio_tenant, os_actions/gbp — the last two
--     fixed in the same PR that adds this file).
--   * every writer goes through encrypt_oauth_tokens(), which dual-writes and
--     keeps working when the plaintext columns are gone only if the key is set.
--
-- Apply via mcp__supabase__apply_migration AFTER the key is provisioned.

ALTER TABLE integrations DROP COLUMN IF EXISTS access_token;
ALTER TABLE integrations DROP COLUMN IF EXISTS refresh_token;
