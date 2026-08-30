-- 198_tenant_kb_chunks.sql
-- Milestone 7: tenant-scoped chunks for approved business knowledge.
--
-- Source of truth remains tenant_kb_documents (165). This table is the
-- retrievable projection: one row per chunk, Voyage 512d when available,
-- lexical search always possible from content.
--
-- client_id (NOT tenant_id) — same family as tenant_kb_documents / leads.
-- RLS deny-public. Search RPC requires p_client_id.
--
-- Lifecycle / orphans:
--   document_id REFERENCES tenant_kb_documents(id) ON DELETE CASCADE so a
--   hard-deleted source document cannot leave indefinitely active chunks.
--   Soft-delete / supersede still goes through the existing compile path
--   (index_after_compile → replace_chunks_for_tenant), which deletes all
--   tenant chunks and reinserts only from status='active' documents.
--   RPC and request-time retrieval only read status='active' chunks.
--   embedding NULL is allowed (lexical path); dense match RPC skips nulls.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS tenant_kb_chunks (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       uuid NOT NULL,
    document_id     uuid NOT NULL REFERENCES tenant_kb_documents(id) ON DELETE CASCADE,
    chunk_index     integer NOT NULL,
    source_type     text NOT NULL,
    title           text NOT NULL,
    section         text,
    content         text NOT NULL,
    content_sha256  text NOT NULL,
    status          text NOT NULL DEFAULT 'active',
    version         integer NOT NULL DEFAULT 1,
    effective_date  date,
    citation_label  text,
    embedding       vector(512),
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (client_id, document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS tenant_kb_chunks_client_status_idx
    ON tenant_kb_chunks (client_id, status);

CREATE INDEX IF NOT EXISTS tenant_kb_chunks_document_idx
    ON tenant_kb_chunks (document_id);

CREATE INDEX IF NOT EXISTS tenant_kb_chunks_embedding_idx
    ON tenant_kb_chunks
    USING hnsw (embedding vector_cosine_ops);

ALTER TABLE tenant_kb_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_kb_chunks_deny_public"
    ON tenant_kb_chunks
    FOR ALL
    TO public
    USING (false)
    WITH CHECK (false);

CREATE POLICY "tenant_kb_chunks_service_role"
    ON tenant_kb_chunks
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE OR REPLACE FUNCTION match_tenant_kb_chunks (
    p_client_id        uuid,
    p_query_embedding  vector(512),
    p_match_count      int DEFAULT 5
)
RETURNS TABLE (
    id              uuid,
    document_id     uuid,
    chunk_index     integer,
    source_type     text,
    title           text,
    section         text,
    content         text,
    citation_label  text,
    similarity      float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        c.id,
        c.document_id,
        c.chunk_index,
        c.source_type,
        c.title,
        c.section,
        c.content,
        c.citation_label,
        1 - (c.embedding <=> p_query_embedding) AS similarity
    FROM tenant_kb_chunks c
    WHERE c.client_id = p_client_id
      AND c.status = 'active'
      AND c.embedding IS NOT NULL
    ORDER BY c.embedding <=> p_query_embedding
    LIMIT p_match_count;
$$;

COMMENT ON TABLE tenant_kb_chunks IS
    'M7 approved tenant knowledge chunks. client_id scoped. FK cascade on document delete. voyage-3-lite 512d optional.';
