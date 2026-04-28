-- 115_contextual_reindex_marker.sql
-- Add contextual_reindexed_at marker to embedding tables so the
-- reindex script can skip already-processed chunks.
-- Affected tables:
--   kb_articles  (migration 081 — system-wide wiki, vector(512))

ALTER TABLE kb_articles
    ADD COLUMN IF NOT EXISTS contextual_reindexed_at TIMESTAMPTZ;

COMMENT ON COLUMN kb_articles.contextual_reindexed_at IS
    'Set by scripts/reindex_contextual.py when chunk has been re-embedded '
    'with Anthropic contextual retrieval prefix. NULL = not yet reindexed.';
