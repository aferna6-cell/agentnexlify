-- 129_chat_messages_os_mirror.sql
-- Group C bi-directional sync: tag chat_messages rows that were mirrored
-- from an OS assistant message so the mirror hop is replay-safe.
--
-- Without this column, the OS outbound mirror has no way to detect that
-- it already mirrored a given os_messages row and would insert duplicates
-- on retry (e.g. background_tasks rerun after a worker restart).

ALTER TABLE chat_messages
    ADD COLUMN IF NOT EXISTS os_message_id UUID NULL;

-- Partial unique index: only enforce uniqueness for mirrored rows; legacy
-- pre-mirror rows have NULL and are unconstrained. Scope is per-tenant so
-- the same os_message_id never collides across tenants (defensive — UUIDs
-- collide with vanishingly small probability, but the index also speeds
-- the idempotency lookup in mirror_assistant_message).
CREATE UNIQUE INDEX IF NOT EXISTS chat_messages_os_message_id_uniq
    ON chat_messages (tenant_id, os_message_id)
    WHERE os_message_id IS NOT NULL;

COMMENT ON COLUMN chat_messages.os_message_id IS
    'OS messages.id this chat_messages row was mirrored from. NULL for rows '
    'originated by the legacy widget Claude path. Used by '
    'backend.services.os_outbound_mirror.mirror_assistant_message for '
    'replay-safe bi-directional sync.';
