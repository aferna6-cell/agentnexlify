-- 127_os_sync_state.sql
-- Agent OS Group C foundation: data sync state.
--
-- One row per (client_id, source) — tracks last incremental cursor, status,
-- and last error for each sync module (leads, appointments, kb,
-- conversations, google_calendar). Scheduled jobs read this row to decide
-- what to sync next; manual run-now writes to it the same way.
--
-- os_memory_entries.source_ref: free-form upstream id (e.g. "leads:<uuid>",
-- "appt:<uuid>") for dedup so re-syncs upsert into the same memory entry
-- instead of duplicating it. Partial unique allows existing memory entries
-- created by workers (source_ref=NULL) to coexist with synced entries.
--
-- RLS: deny-public (same pattern as 118+).

CREATE TABLE IF NOT EXISTS os_sync_state (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id          UUID NOT NULL,
    source             TEXT NOT NULL,                   -- leads|appointments|kb|conversations|google_calendar
    enabled            BOOLEAN NOT NULL DEFAULT true,
    status             TEXT NOT NULL DEFAULT 'idle',    -- idle|running|error
    last_run_at        TIMESTAMPTZ,
    last_success_at    TIMESTAMPTZ,
    last_seen_cursor   TEXT,                            -- updated_at ISO, or source-specific cursor
    last_error         TEXT,
    rows_seen_total    BIGINT NOT NULL DEFAULT 0,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (client_id, source)
);

COMMENT ON TABLE os_sync_state IS
    'Agent OS sync state (Group C). One row per (client_id, source). Cursor + status + last error.';

CREATE INDEX IF NOT EXISTS os_sync_state_status_run_idx
    ON os_sync_state (status, last_run_at);

ALTER TABLE os_sync_state ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "os_sync_state_deny_public" ON os_sync_state;
CREATE POLICY "os_sync_state_deny_public"
    ON os_sync_state
    FOR ALL
    TO public
    USING (false)
    WITH CHECK (false);

-- Dedup column for sync writes into semantic memory. Nullable so existing
-- worker-written entries (no source_ref) coexist with synced ones.
ALTER TABLE os_memory_entries
    ADD COLUMN IF NOT EXISTS source_ref TEXT NULL;

-- Partial unique: one memory entry per (client_id, source_ref) where set.
CREATE UNIQUE INDEX IF NOT EXISTS os_memory_entries_source_ref_unique_idx
    ON os_memory_entries (client_id, source_ref)
    WHERE source_ref IS NOT NULL;
