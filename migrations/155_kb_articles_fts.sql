-- 155: Add Postgres full-text-search (FTS) support to kb_articles
-- Enables KB retrieval when VOYAGE_API_KEY is absent or embeddings are missing.
-- Semantic search (match_kb_articles RPC) remains the primary path; FTS is the fallback.
--
-- Idempotent: uses IF NOT EXISTS / CREATE OR REPLACE throughout.
-- Requires owner role to add the generated column — flag for schema-guardian before prod apply.

-- 1. Generated tsvector column maintained automatically by Postgres.
--    Combines title + summary + content for broad coverage.
ALTER TABLE kb_articles
    ADD COLUMN IF NOT EXISTS content_tsv tsvector
        GENERATED ALWAYS AS (
            to_tsvector(
                'english',
                coalesce(title, '') || ' ' ||
                coalesce(summary, '') || ' ' ||
                coalesce(content, '')
            )
        ) STORED;

-- 2. GIN index on the generated column for fast FTS.
CREATE INDEX IF NOT EXISTS kb_articles_content_tsv_idx
    ON kb_articles USING GIN (content_tsv);

-- 3. FTS retrieval function — same return shape as the semantic match_kb_articles RPC.
--    Returns columns: id, slug, title, summary, source_url, last_validated,
--                     citation_count, similarity (as float8 rank score).
--
--    match_kb_articles_fts(query_text text, match_count int)
--
--    Uses websearch_to_tsquery so callers can pass raw user queries safely
--    (handles quotes, minus-prefixes, OR without injection risk).
CREATE OR REPLACE FUNCTION match_kb_articles_fts(
    query_text text,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id              uuid,
    slug            text,
    title           text,
    summary         text,
    source_url      text,
    last_validated  timestamptz,
    citation_count  int,
    similarity      float8
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        a.id,
        a.slug,
        a.title,
        a.summary,
        -- kb_articles has no source_url column; return NULL to match the
        -- semantic RPC contract so callers need no conditional logic.
        NULL::text                        AS source_url,
        NULL::timestamptz                 AS last_validated,
        0::int                            AS citation_count,
        ts_rank_cd(
            a.content_tsv,
            websearch_to_tsquery('english', query_text)
        )::float8                         AS similarity
    FROM kb_articles a
    WHERE
        query_text <> ''
        AND a.content_tsv @@ websearch_to_tsquery('english', query_text)
    ORDER BY similarity DESC
    LIMIT match_count;
$$;
