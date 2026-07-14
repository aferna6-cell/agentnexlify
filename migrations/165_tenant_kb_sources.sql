-- Migration 165: tenant KB sources — bulk upload, Drive sync, second brain
--
-- Implements the schema from specs/drive-kb-onboarding_spec.md (grilled
-- 2026-04-20) plus a per-document store that also serves dashboard bulk
-- upload and the local folder-sync client. All three tables use client_id
-- (NOT tenant_id) per schema discipline — they are customer-data tables in
-- the leads/conversations family.
--
-- Deviations from the spec, with reasons:
--   * OAuth tokens are encrypted APP-SIDE via the Fernet vault
--     (backend/services/integration_key_vault.py, GH #131/#266) rather than
--     in-DB pgcrypto — the vault is the established, 100%-covered encryption
--     path and the spec predates it. Columns stay BYTEA as specced.
--   * kb_section_hashes is replaced by content_sha256 on tenant_kb_documents:
--     the tenant KB is prompt-injected text (widget_configs.knowledge_base,
--     migration 077), not per-tenant embeddings, so diffing per DOCUMENT
--     achieves the spec's "recompile only what changed" goal with one table.

-- One integration per provider per tenant (drive v1; dropbox/onedrive/box later)
CREATE TABLE IF NOT EXISTS tenant_integrations (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id                uuid NOT NULL,
    provider                 text NOT NULL,      -- 'drive' | 'dropbox' | 'onedrive' | 'box'
    config                   jsonb NOT NULL DEFAULT '{}'::jsonb,  -- {folder_id, folder_name, email}
    oauth_token_enc          bytea,
    oauth_refresh_token_enc  bytea,
    oauth_expires_at         timestamptz,
    enabled                  boolean NOT NULL DEFAULT true,
    last_synced_at           timestamptz,
    last_sync_status         text,               -- 'ok' | 'error' | 'partial'
    created_at               timestamptz NOT NULL DEFAULT now(),
    updated_at               timestamptz NOT NULL DEFAULT now(),
    UNIQUE (client_id, provider)
);

CREATE INDEX IF NOT EXISTS tenant_integrations_client_idx
    ON tenant_integrations (client_id);

-- Per-sync audit trail (dashboard sync log)
CREATE TABLE IF NOT EXISTS integration_sync_log (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id           uuid NOT NULL,
    integration_id      uuid,
    provider            text NOT NULL,
    synced_at           timestamptz NOT NULL DEFAULT now(),
    files_added         integer NOT NULL DEFAULT 0,
    files_updated       integer NOT NULL DEFAULT 0,
    files_skipped       integer NOT NULL DEFAULT 0,
    files_pii_flagged   integer NOT NULL DEFAULT 0,
    error               text
);

CREATE INDEX IF NOT EXISTS integration_sync_log_client_idx
    ON integration_sync_log (client_id, synced_at DESC);

-- Per-document KB source store: powers dashboard bulk upload ('upload'),
-- Drive sync ('drive'), and the local folder-sync client ('local_sync').
-- content_sha256 drives skip-unchanged; the compile step assembles active
-- documents into widget_configs.knowledge_base with provenance headers.
CREATE TABLE IF NOT EXISTS tenant_kb_documents (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       uuid NOT NULL,
    source          text NOT NULL,              -- 'upload' | 'drive' | 'local_sync'
    external_id     text NOT NULL,              -- drive file id / relative path / filename
    filename        text NOT NULL,
    content_md      text NOT NULL,
    content_sha256  text NOT NULL,
    pii_flags       integer NOT NULL DEFAULT 0,
    status          text NOT NULL DEFAULT 'active',  -- 'active' | 'skipped' | 'deleted'
    error           text,
    synced_at       timestamptz NOT NULL DEFAULT now(),
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (client_id, source, external_id)
);

CREATE INDEX IF NOT EXISTS tenant_kb_documents_client_idx
    ON tenant_kb_documents (client_id, status);
