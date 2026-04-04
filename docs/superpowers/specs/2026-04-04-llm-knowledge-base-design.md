# LLM Knowledge Base — Design Spec

**Date:** 2026-04-04
**Status:** Approved
**Author:** Aidan + Claude

---

## Overview

An LLM-compiled knowledge base inside the AgentNexLiFy repo. Raw sources (articles, papers, competitor intel) are ingested into `raw/`, compiled by an LLM into a `.md` wiki, stored with vector embeddings in Supabase for semantic search, and queried via Claude Code skills.

The wiki is the LLM's domain — humans rarely edit it directly. The LLM writes articles, maintains cross-links, and keeps the index current.

### Topic Categories

1. **Competitors** — GoHighLevel, Drillbit, Phonely, Toma, Birdeye, Podium, Oscar Chat, Tidio
2. **AI/LLM Developments** — New models, capabilities, pricing, context windows, tool use
3. **Small Business SaaS** — Trends, buying patterns, churn research, pricing strategies
4. **Vertical Industries** — Contractors, dental, salon, legal, restaurants, real estate
5. **Technical Patterns** — Prompt engineering, RAG, agent architectures, streaming, structured output
6. **Regulations & Compliance** — HIPAA, TCPA (SMS), data privacy, AI disclosure laws
7. **Growth & Distribution** — PLG tactics, widget virality, partnerships, SEO/GEO for AI

---

## Directory Structure

```
knowledge-base/
├── raw/                          # Source documents (auto-discovered or manually clipped)
│   ├── competitors/
│   ├── ai-llm/
│   ├── small-biz-saas/
│   ├── verticals/
│   ├── technical/
│   ├── regulations/
│   └── growth/
├── wiki/                         # LLM-compiled articles (never manually edited)
│   ├── competitors/
│   ├── ai-llm/
│   ├── small-biz-saas/
│   ├── verticals/
│   ├── technical/
│   ├── regulations/
│   ├── growth/
│   └── _outputs/                 # Query results filed back into the wiki
├── sources.yaml                  # Search queries, RSS feeds, competitor domains
├── known-urls.json               # URL dedup registry
├── INDEX.md                      # Master catalog with summaries + backlinks
├── PENDING.md                    # Auto-detected raw files not yet compiled
└── .gitignore                    # Ignore large binaries (PDFs, images)
```

`raw/` mirrors `wiki/` categories. `INDEX.md` is the fast-scan entry point. `PENDING.md` tracks new raw files detected but not yet compiled.

---

## Database Schema

### Prerequisites

Enable pgvector extension in Supabase:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Table: `kb_articles`

Stores compiled wiki articles with vector embeddings for semantic search.

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | uuid | PK, default gen_random_uuid() | |
| slug | text | unique, not null | File path relative to wiki/, e.g. `competitors/gohighlevel` |
| title | text | not null | Article title |
| category | text | not null | One of the 7 categories |
| summary | text | not null | 1-2 sentence summary |
| content | text | not null | Full markdown body |
| embedding | vector(1024) | | Embedding of title + summary + first 500 words |
| source_urls | text[] | default '{}' | Raw files this was compiled from |
| tags | text[] | default '{}' | Cross-cutting tags |
| word_count | int | | |
| created_at | timestamptz | default now() | |
| updated_at | timestamptz | default now() | |

Indexes:
- `kb_articles_embedding_idx` — HNSW index on embedding column for cosine similarity (works well at any scale, unlike IVFFlat which needs ~1000+ rows)
- `kb_articles_category_idx` — btree on category for filtered searches

### Table: `kb_sources`

Tracks raw ingested documents and provides URL dedup.

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | uuid | PK, default gen_random_uuid() | |
| source_url | text | unique | Original URL for dedup |
| file_path | text | not null | Path in raw/ |
| category | text | not null | |
| relevance_score | int | | LLM-assigned 0-10 |
| title | text | | |
| discovered_at | timestamptz | default now() | |
| compiled | boolean | default false | Whether processed into wiki |
| compiled_at | timestamptz | | |

No tenant scoping — this is an internal knowledge base, not customer-facing.

Migration: `migrations/065-kb-articles-and-sources.sql`

---

## Embedding Infrastructure

### Provider

Use Voyage AI embeddings (`voyage-3-lite`, 1024 dimensions) as primary. Falls back to OpenAI `text-embedding-3-small` if Voyage is unavailable. Both produce 1024-dim vectors.

### Implementation

New utility: `backend/services/embeddings.py`

```python
async def embed_text(text: str) -> list[float]:
    """Embed text using Voyage AI. Returns 1024-dim vector."""
    # Truncate to ~8000 tokens for embedding
    # Returns list[float] of length 1024

async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Batch embed for efficiency during compilation."""
```

Environment variable: `VOYAGE_API_KEY` (or `OPENAI_API_KEY` as fallback).

This utility is shared — future product features (semantic FAQ search, etc.) can reuse it.

---

## Skills

### `/kb-discover` — Automated Article Discovery

1. Reads `knowledge-base/sources.yaml` for:
   - Keyword search queries per category
   - Competitor blog URLs to check
   - RSS feed URLs
   - Subreddit/HN/ProductHunt targets
2. Runs WebSearch for each query
3. WebFetches promising results, converts to .md
4. Checks `kb_sources` table and `known-urls.json` for duplicates
5. LLM scores each result for relevance (0-10), keeps 7+
6. Saves to `raw/{category}/` with frontmatter:
   ```yaml
   ---
   title: "Article Title"
   source_url: https://...
   discovered: 2026-04-04
   category: competitors
   relevance_score: 9
   ---
   ```
7. Inserts into `kb_sources` table
8. Updates `PENDING.md`
9. Reports: "Found 8 new articles. Run `/kb-compile` to process."

### `/kb-ingest` — Manual Source Addition

- `/kb-ingest https://some-article.com` — fetches, converts to .md, LLM categorizes, saves to `raw/`
- `/kb-ingest ./local-file.md` — copies to correct `raw/` subfolder
- Registers in `kb_sources` table, updates `PENDING.md`

### `/kb-compile` — Wiki Compilation

1. Reads uncompiled sources from `PENDING.md` / `kb_sources` where `compiled = false`
2. For each source, LLM decides: create new wiki article OR update existing one
3. Compilation rules:
   - **Merge, don't duplicate.** Second GoHighLevel article updates `wiki/competitors/gohighlevel.md`
   - **Three article types:**
     - **Entity profiles** — One per competitor/vertical/regulation. Living documents. (`gohighlevel.md`, `dental-industry.md`)
     - **Concept articles** — Technical or strategic concepts. (`prompt-caching.md`, `widget-virality-patterns.md`)
     - **Trend snapshots** — Time-stamped analysis. (`2026-q1-llm-pricing-trends.md`)
   - **Standard frontmatter:**
     ```yaml
     ---
     title: "GoHighLevel — Competitor Profile"
     category: competitors
     tags: ["crm", "ai-employee", "white-label", "pricing"]
     sources: ["raw/competitors/ghl-ai-employee-v2.md", "raw/competitors/ghl-pricing-2026.md"]
     created: 2026-04-04
     updated: 2026-04-04
     ---
     ```
   - **Every article ends with `## Relevance to AgentNexLiFy`** — connecting the knowledge back to "so what does this mean for us?"
   - **Backlinks are inline** — `see [[prompt-caching]]` when referencing another article
   - **Staleness markers** — Articles sourced from content older than 60 days get `⚠️ May be outdated`
4. Generates embeddings via `embed_text()`, upserts into `kb_articles`
5. Rebuilds `INDEX.md` with current summaries and backlink map
6. Clears `PENDING.md`, marks sources as `compiled = true`
7. Reports: "Compiled 8 sources into 5 new articles, updated 3 existing."

### `/kb-query` — Semantic Q&A

1. Takes natural language question as argument
2. Embeds the question via `embed_text()`
3. Cosine similarity search on `kb_articles` — top 10 matches
4. LLM reads matched articles, synthesizes answer
5. Saves answer to `wiki/_outputs/{date}-{slug}.md`
6. Optionally files output back into wiki if it adds lasting value
7. Example: `/kb-query "How does GoHighLevel's AI Employee compare to our chat widget?"`

### `/kb-health` — Wiki Audit

1. Finds stale articles (sources older than 60 days, no update)
2. Detects missing cross-links between related articles
3. Finds category gaps (e.g., "no articles about dental AI competitors")
4. Checks for contradictions across articles
5. Suggests new discovery queries based on gaps
6. Reports health score and action items

---

## Integration

### Morning Routine

Add to `scripts/daily/morning-auto.sh`:
- Run `/kb-discover` automatically
- Morning session displays: "KB: 5 new articles pending compilation"
- User decides whether to `/kb-compile`

### Agent Access

- Agents (backend-dev, frontend-dev, etc.) can query the KB during feature work
- Read-only — agents never write to the KB, only KB skills do
- Example: backend-dev building competitor feature checks "how does Birdeye handle review responses?"

### Seed Data Migration

One-time migration of existing research into `raw/`:
- `docs/dev-knowledge/research-2026-03.md` → `raw/competitors/`
- `docs/dev-knowledge/customer-gaps.md` → `raw/verticals/`
- `docs/research/post-launch-growth-features.md` → `raw/growth/`

Original files stay in place (don't break existing references).

---

## Sources Manifest (`sources.yaml`)

```yaml
competitors:
  search_queries:
    - "GoHighLevel AI update 2026"
    - "AI chatbot small business CRM"
    - "Drillbit AI contractor"
    - "Phonely AI receptionist"
    - "Toma AI receptionist"
    - "Birdeye AI reviews 2026"
    - "Podium AI reviews"
  blogs:
    - https://www.gohighlevel.com/blog
    - https://birdeye.com/blog
    - https://www.podium.com/resources

ai_llm:
  search_queries:
    - "Anthropic Claude new features 2026"
    - "OpenAI GPT update 2026"
    - "LLM context window improvements"
    - "AI agent frameworks 2026"
    - "structured output LLM"
  blogs:
    - https://www.anthropic.com/news
    - https://openai.com/blog

small_biz_saas:
  search_queries:
    - "small business SaaS churn 2026"
    - "PLG small business"
    - "vertical SaaS trends"
  feeds:
    - https://news.ycombinator.com/rss

verticals:
  search_queries:
    - "AI for contractors 2026"
    - "dental practice management AI"
    - "salon booking AI chatbot"
    - "restaurant AI ordering"
    - "legal intake AI"

technical:
  search_queries:
    - "prompt engineering best practices 2026"
    - "RAG vs long context"
    - "LLM streaming structured output"
    - "AI agent tool use patterns"

regulations:
  search_queries:
    - "HIPAA AI chatbot compliance"
    - "TCPA SMS marketing rules 2026"
    - "AI disclosure laws United States"
    - "FTC AI guidelines"

growth:
  search_queries:
    - "chat widget viral growth"
    - "embedded SaaS distribution"
    - "small business SEO AI"
    - "GEO generative engine optimization"
```

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `VOYAGE_API_KEY` | Voyage AI embeddings (primary) |
| `OPENAI_API_KEY` | Fallback embeddings (already exists for other uses) |

---

## Out of Scope (Future Enhancements)

- Obsidian vault integration (viewer)
- Web UI search interface
- Synthetic data generation / fine-tuning from KB
- Customer-facing knowledge base (separate feature)
- Automated scheduled compilation (currently manual trigger after discovery)
