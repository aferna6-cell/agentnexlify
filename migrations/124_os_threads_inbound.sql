-- 124_os_threads_inbound.sql
-- Agent OS Connector Group A: Inbound channels bridge schema.
--
-- Adds source-channel metadata to os_threads + os_messages so messages
-- arriving from the widget, email, SMS, or Facebook can land in the same
-- thread structure as owner chat-shell prompts. The orchestrator then sees
-- every customer-facing message, not just owner-typed ones.
--
-- Source spec: specs/agent-os-connectors-inbound_spec.md
-- Build plan:  plans/agent-os-connectors-inbound_plan.md
--
-- Idempotency anchor: os_messages.source_ref. Bridges set this to
--   "<source>:<provider_message_id>" so retries from the upstream provider
--   never double-insert. Spec §Security calls for replay protection keyed
--   on (client_id, source, provider_message_id); this column + the unique
--   partial index below implements that key.
--
-- RLS posture: existing deny-public policies on os_threads + os_messages
-- still apply. New columns inherit RLS automatically.

-- ---------------------------------------------------------------------------
-- os_threads additions
-- ---------------------------------------------------------------------------

ALTER TABLE os_threads
    ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'chat';

ALTER TABLE os_threads
    ADD COLUMN IF NOT EXISTS source_thread_id TEXT NULL;

ALTER TABLE os_threads
    ADD COLUMN IF NOT EXISTS source_metadata JSONB NULL;

-- Enumerate valid source values. Adding a new source = adding to this CHECK.
ALTER TABLE os_threads
    DROP CONSTRAINT IF EXISTS os_threads_source_check;

ALTER TABLE os_threads
    ADD CONSTRAINT os_threads_source_check
    CHECK (source IN ('chat', 'widget', 'email', 'sms', 'facebook'));

-- Dedup key: one os_thread per (client, source, provider thread id) when
-- a provider thread id exists. Owner chat-shell threads have NULL
-- source_thread_id and are exempt from the uniqueness rule.
CREATE UNIQUE INDEX IF NOT EXISTS os_threads_source_thread_uniq
    ON os_threads (client_id, source, source_thread_id)
    WHERE source_thread_id IS NOT NULL;

-- Source-filtered lookup (e.g. "list all widget threads for this tenant")
CREATE INDEX IF NOT EXISTS os_threads_client_source_idx
    ON os_threads (client_id, source);

-- ---------------------------------------------------------------------------
-- os_messages additions
-- ---------------------------------------------------------------------------

ALTER TABLE os_messages
    ADD COLUMN IF NOT EXISTS inbound_kind TEXT NULL;

-- Enumerate valid inbound_kind values. NULL = owner-typed (not from bridge).
ALTER TABLE os_messages
    DROP CONSTRAINT IF EXISTS os_messages_inbound_kind_check;

ALTER TABLE os_messages
    ADD CONSTRAINT os_messages_inbound_kind_check
    CHECK (inbound_kind IS NULL
           OR inbound_kind IN ('auto_reply', 'normal', 'system_notice'));

-- Idempotency dedup anchor. Spec §Security requires that bridges reject
-- duplicate inbound messages from provider retries. Bridges set this to
-- "<source>:<provider_message_id>". NULL for owner-typed messages.
ALTER TABLE os_messages
    ADD COLUMN IF NOT EXISTS source_ref TEXT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS os_messages_source_ref_uniq
    ON os_messages (client_id, source_ref)
    WHERE source_ref IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Notes
-- ---------------------------------------------------------------------------
-- 1. Existing os_threads rows backfill `source='chat'` via the DEFAULT.
-- 2. Existing os_messages rows leave `inbound_kind` and `source_ref` NULL.
-- 3. No data migration needed. Rollback = drop the new columns + indexes.
-- 4. Group C (sync) will add a separate `source_ref` to os_memory_entries
--    in migration 126; same column name, different table, no conflict.
