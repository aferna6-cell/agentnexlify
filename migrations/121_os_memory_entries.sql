-- 121_os_memory_entries.sql
-- Agent OS P0: semantic memory. One row per durable fact/preference/decision
-- the orchestrator should recall across threads. Embedding-backed; the Karpathy
-- graph layer (os_memory_nodes/edges) is deferred past P0 — it costs an LLM
-- call per write. P0 is semantic-only.
--
-- voyage-3-lite → 512-dim embeddings. HNSW index for cosine ANN search.
-- match_os_memory() is the search entrypoint the os_memory service calls.
--
-- RLS: deny-public (see 118 rationale).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS os_memory_entries (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id    UUID NOT NULL,
    kind         TEXT NOT NULL,                   -- fact|preference|decision|conversation_summary
    content      TEXT NOT NULL,
    embedding    vector(512),
    source       TEXT,                            -- thread:<id> | manual | agent_run:<id>
    created_by   TEXT,
    is_pinned    BOOLEAN NOT NULL DEFAULT false,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE os_memory_entries IS
    'Agent OS semantic memory (P0). voyage-3-lite 512d. Graph layer deferred.';

CREATE INDEX IF NOT EXISTS os_memory_entries_client_idx
    ON os_memory_entries (client_id, created_at DESC);

CREATE INDEX IF NOT EXISTS os_memory_entries_embedding_idx
    ON os_memory_entries
    USING hnsw (embedding vector_cosine_ops);

ALTER TABLE os_memory_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "os_memory_entries_deny_public"
    ON os_memory_entries
    FOR ALL
    TO public
    USING (false)
    WITH CHECK (false);

-- Cosine-similarity search scoped to one client. Called by the os_memory
-- service via the service-role client (RLS bypassed).
CREATE OR REPLACE FUNCTION match_os_memory (
    p_client_id        UUID,
    p_query_embedding  vector(512),
    p_match_count      INT DEFAULT 8
)
RETURNS TABLE (
    id          UUID,
    kind        TEXT,
    content     TEXT,
    source      TEXT,
    is_pinned   BOOLEAN,
    similarity  FLOAT
)
LANGUAGE sql STABLE
AS $$
    SELECT
        m.id,
        m.kind,
        m.content,
        m.source,
        m.is_pinned,
        1 - (m.embedding <=> p_query_embedding) AS similarity
    FROM os_memory_entries m
    WHERE m.client_id = p_client_id
      AND m.embedding IS NOT NULL
    ORDER BY m.embedding <=> p_query_embedding
    LIMIT p_match_count;
$$;
