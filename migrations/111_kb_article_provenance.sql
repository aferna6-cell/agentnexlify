-- 111: KB article provenance — source_url, last_validated, citation_count
-- Additive. Does not touch existing rows or embeddings.
-- Adds:
--   source_url        — canonical URL shown in widget citation footer
--   last_validated    — timestamp set by compile step; used for stale warnings (>60 days)
--   citation_count    — incremented atomically each time the article is retrieved in widget chat
-- Adds RPC helpers used by the FastAPI widget retrieval path.

ALTER TABLE kb_articles
    ADD COLUMN IF NOT EXISTS source_url TEXT,
    ADD COLUMN IF NOT EXISTS last_validated TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS citation_count INT DEFAULT 0;

-- Back-fill existing rows so last_validated reflects when they were compiled.
UPDATE kb_articles SET last_validated = updated_at WHERE last_validated IS NULL;

CREATE INDEX IF NOT EXISTS kb_articles_last_validated_idx
    ON kb_articles (last_validated);

-- ---------------------------------------------------------------------------
-- match_kb_articles — cosine similarity search (called by widget KB path)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION match_kb_articles(
    query_embedding vector(512),
    match_threshold float DEFAULT 0.70,
    match_count int DEFAULT 3
)
RETURNS TABLE (
    id UUID,
    slug TEXT,
    title TEXT,
    summary TEXT,
    source_url TEXT,
    last_validated TIMESTAMPTZ,
    citation_count INT,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id,
        a.slug,
        a.title,
        a.summary,
        a.source_url,
        a.last_validated,
        a.citation_count,
        (1 - (a.embedding <=> query_embedding))::float AS similarity
    FROM kb_articles a
    WHERE
        a.embedding IS NOT NULL
        AND (1 - (a.embedding <=> query_embedding)) > match_threshold
    ORDER BY a.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ---------------------------------------------------------------------------
-- increment_kb_citations — atomic citation_count increment
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION increment_kb_citations(article_ids UUID[])
RETURNS VOID
LANGUAGE sql
AS $$
    UPDATE kb_articles
    SET citation_count = citation_count + 1
    WHERE id = ANY(article_ids);
$$;
