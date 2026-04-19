---
name: kb-compile
description: Compile raw sources into the wiki by reading pending sources, creating or updating wiki articles, generating embeddings, storing in Supabase pgvector, and rebuilding INDEX.md. Use when user says 'kb-compile', 'compile sources', 'compile wiki', 'compile pending', 'recompile wiki', 'compile embeddings', or asks about kb compile.
version: 1.0.0
origin: claude
user-invocable: true
triggers:
- kb-compile
- compile sources
- compile wiki
- compile pending
- recompile wiki
- compile embeddings
effort: medium
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# KB Compile — Wiki Compilation

Transform raw sources into interlinked wiki articles with vector embeddings.

## Usage

- `/kb-compile` — compile all pending sources
- `/kb-compile --full` — recompile entire wiki (regenerate all embeddings)

## When to Use
- Pending raw sources need to be compiled into wiki articles
- New embeddings need to be generated for existing articles
- INDEX.md needs to be rebuilt from wiki articles

## When NOT to Use
- Adding a single new source (use kb-ingest instead)
- Searching the knowledge base (use kb-query instead)
- Checking knowledge base health (use kb-health instead)

## Workflow

### Step 1: Identify Pending Sources

Read `knowledge-base/PENDING.md` to get the list of uncompiled raw files.

Also query Supabase for safety:

```sql
SELECT file_path, title, category FROM kb_sources WHERE compiled = false ORDER BY discovered_at;
```

Union both lists and deduplicate.

If no pending sources, report "Nothing to compile." and exit.

### Step 2: Read Existing Wiki State

Read `knowledge-base/INDEX.md` to understand what articles already exist.

For each pending source's category, list existing wiki articles in that category directory.

### Step 3: Compile Each Source

For each pending raw file:

1. **Read the raw source** from `knowledge-base/raw/{category}/{filename}.md`

2. **Decide: new article or merge into existing?**
   - If the source covers an entity (competitor, regulation, industry) that already has a wiki article → **merge** into the existing article
   - If the source covers a new entity or concept → **create** a new article
   - If the source is a broad update touching multiple topics → **update** multiple existing articles and/or create a trend snapshot

3. **Write/update the wiki article** at `knowledge-base/wiki/{category}/{slug}.md`:

   Article types:
   - **Entity profiles:** One per competitor, vertical, or regulation. Living documents that accumulate data. Slug = entity name (e.g., `gohighlevel.md`, `dental-industry.md`)
   - **Concept articles:** Technical or strategic concepts. Slug = concept name (e.g., `prompt-caching.md`, `widget-virality-patterns.md`)
   - **Trend snapshots:** Time-stamped analysis. Slug = date + topic (e.g., `2026-q1-llm-pricing-trends.md`)

   Required frontmatter:
   ```yaml
   ---
   title: "Article Title"
   category: competitors
   tags: ["crm", "ai-employee", "white-label"]
   sources: ["raw/competitors/source1.md", "raw/competitors/source2.md"]
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   ---
   ```

   Required sections:
   - Main content (well-structured, factual, comprehensive)
   - `## Relevance to AgentNexLiFy` — what this means for our product/strategy
   - Inline backlinks to related articles using `[[article-slug]]` syntax

4. **Staleness check:** If any source in the article's `sources` list is older than 60 days, add a note at the top: `> ⚠️ Some sources are over 60 days old. Run /kb-health to check for updates.`

### Step 4: Generate Embeddings

For each new or updated wiki article, create the embedding text:

```
{title}\n\n{summary}\n\n{first 500 words of content}
```

Call the embedding service. This step requires Python execution:

```python
import asyncio
import sys
sys.path.insert(0, '.')
from backend.services.embeddings import embed_text

text = "Title\n\nSummary\n\nFirst 500 words..."
embedding = asyncio.run(embed_text(text))
print(f"Embedding generated: {len(embedding)} dimensions")
```

### Step 5: Store in Supabase

For each new or updated article, upsert into `kb_articles`:

```sql
INSERT INTO kb_articles (slug, title, category, summary, content, embedding, source_urls, tags, word_count, updated_at)
VALUES (
    'competitors/gohighlevel',
    'GoHighLevel — Competitor Profile',
    'competitors',
    'One-line summary here',
    'Full markdown content...',
    '[0.1, 0.2, ...]'::vector,
    ARRAY['raw/competitors/ghl-source1.md'],
    ARRAY['crm', 'ai-employee'],
    1234,
    now()
)
ON CONFLICT (slug) DO UPDATE SET
    title = EXCLUDED.title,
    summary = EXCLUDED.summary,
    content = EXCLUDED.content,
    embedding = EXCLUDED.embedding,
    source_urls = EXCLUDED.source_urls,
    tags = EXCLUDED.tags,
    word_count = EXCLUDED.word_count,
    updated_at = now();
```

### Step 6: Mark Sources as Compiled

```sql
UPDATE kb_sources SET compiled = true, compiled_at = now()
WHERE file_path = 'raw/category/filename.md';
```

### Step 7: Rebuild INDEX.md

Regenerate `knowledge-base/INDEX.md` by reading all wiki articles:

```markdown
# Knowledge Base Index

Master catalog of all compiled wiki articles. Auto-maintained by `/kb-compile`.

## Statistics
- Total articles: 42
- Last compiled: 2026-04-04

## Articles by Category

### Competitors
- [GoHighLevel](wiki/competitors/gohighlevel.md) — AI-powered CRM, $97-497/mo, #1 direct competitor. Tags: crm, ai-employee, white-label
- [Drillbit](wiki/competitors/drillbit.md) — YC-backed AI receptionist for contractors. Tags: contractors, ai-receptionist

### AI/LLM Developments
- [Claude Sonnet 4.6](wiki/ai-llm/claude-sonnet-4-6.md) — Latest Anthropic model, 1M context. Tags: anthropic, context-window
...

## Cross-Reference Map
- [[gohighlevel]] ← referenced by: [[ai-employee-market]], [[pricing-comparison]]
- [[prompt-caching]] ← referenced by: [[claude-sonnet-4-6]], [[widget-performance]]
```

### Step 8: Clear PENDING.md

Reset `knowledge-base/PENDING.md` to:

```markdown
# Pending Sources

Raw files awaiting compilation. Run `/kb-compile` to process.

_No pending sources._
```

### Step 9: Report

```
## Compilation Report — YYYY-MM-DD

- Sources processed: 8
- New articles created: 5
- Existing articles updated: 3
- Embeddings generated: 8
- Total wiki articles: 42
- Total wiki words: ~85,000
```

## Bundled Script

`scripts/list_pending.py` — deterministic filesystem diff, no API calls.

```bash
python .claude/skills/kb-compile/scripts/list_pending.py
# → [{"path": "raw/competitors/foo.md", "title": "Foo", "size_bytes": 1234}, ...]
```

Run before Step 1 to get the pending list without touching Supabase.

### Step 10: Commit

```bash
git add knowledge-base/
git commit -m "kb: compile [N] sources into wiki ([new] new, [updated] updated)"
```
