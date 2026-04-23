-- 116: Integrations — add encrypted token columns for app-level key vault
-- Applied: 2026-04-23
--
-- NOTE: Plaintext access_token and refresh_token columns are retained intentionally.
-- They will remain until a follow-up migration completes the backfill+swap.
-- This is a staged approach (no half-migrations). The key vault service
-- (backend/services/integration_key_vault.py) writes to _enc columns from this
-- point forward; the plaintext columns stay readable for the backfill window.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE integrations
    ADD COLUMN IF NOT EXISTS access_token_enc BYTEA,
    ADD COLUMN IF NOT EXISTS refresh_token_enc BYTEA;
