-- 181: KB article provenance (issue #70) — DRAFT / UNAPPLIED
--
-- Status: DRAFT for peer review. Validated locally by applying against a scratch
--   Postgres 16 (see PR proof). NOT yet applied to prod Supabase (no Supabase MCP
--   access this session). A peer applies via mcp__supabase__apply_migration and
--   flips the schema-log entry to APPLIED.
-- Author: fable5 (Agent Nexlify team contract) — lane team/70/fable5/kb-provenance
-- Issue: #70. Migration number 181 chosen to avoid colliding with the open
--   PR #517 (migration 180, issue #114). Supersedes the closed auto-PR #72,
--   which used a colliding number 111.
--
-- WHAT: give compiled wiki articles (kb_articles, migration 081) provenance so
--   widget answers can cite a source + surface a staleness warning, and so we can
--   see which articles actually get cited.
--
-- DESIGN NOTES:
--   * Reuses the EXISTING source_urls TEXT[] column (mig 081) for the source
--     footer — no redundant singular source_url column is added.
--   * Adds only last_validated + citation_count.
--   * Does NOT modify the semantic match_kb_articles RPC: it has no checked-in
--     migration (applied ad-hoc to Supabase) and this session has no live Supabase
--     access, so recreating it blind would risk the primary retrieval path.
--     Provenance is instead merged in Python by article id after retrieval, which
--     works uniformly for both the semantic and FTS paths.
--   * last_validated: existing rows are backfilled to their updated_at (their real
--     age, so staleness is honest); the column default is set to now() AFTERWARDS
--     so newly-compiled articles are marked fresh on insert.

-- ============================================================
-- 1. Provenance columns on kb_articles
-- ============================================================
ALTER TABLE kb_articles
    ADD COLUMN IF NOT EXISTS last_validated timestamptz;

-- Backfill existing rows to their last content update (honest age, not "now").
UPDATE kb_articles
SET last_validated = updated_at
WHERE last_validated IS NULL;

-- Future inserts (new compiled articles) are marked fresh automatically.
ALTER TABLE kb_articles
    ALTER COLUMN last_validated SET DEFAULT now();

ALTER TABLE kb_articles
    ADD COLUMN IF NOT EXISTS citation_count int NOT NULL DEFAULT 0;

-- ============================================================
-- 2. Atomic citation increment on widget retrieval
--    SECURITY DEFINER so the service-role widget path can bump counts without
--    a direct table grant (kb_articles is otherwise reached only via RPCs).
-- ============================================================
CREATE OR REPLACE FUNCTION increment_kb_citations(article_ids uuid[])
RETURNS void
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    UPDATE kb_articles
    SET citation_count = citation_count + 1
    WHERE id = ANY(article_ids);
$$;

REVOKE ALL ON FUNCTION increment_kb_citations(uuid[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION increment_kb_citations(uuid[]) TO service_role;
