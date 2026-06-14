-- Encrypt integrations secrets at rest (onboarding-v2, GH #129).
--
-- Additive ONLY: adds BYTEA ciphertext columns alongside the existing plaintext
-- access_token / refresh_token (migration 007). Plaintext columns are retained
-- until a separate, fully-planned sunset migration runs after backfill is
-- verified (user-rules Rule 8: no half-migrations).
--
-- Encryption is performed app-side via cryptography.fernet in
-- backend/services/integration_key_vault.py (onboarding-v2 spec §9 sanctions
-- app-side over in-DB pgcrypto so the vault can be unit-tested to 100% coverage
-- without a live DB). The Fernet token is stored as BYTEA. pgcrypto is still
-- ensured present for any future SQL-side use.
--
-- RLS: the existing service-role-only policy on integrations is left untouched.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE integrations ADD COLUMN IF NOT EXISTS access_token_enc BYTEA;
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS refresh_token_enc BYTEA;
