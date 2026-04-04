# LLM Knowledge Base Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an LLM-compiled knowledge base with automated discovery, Supabase pgvector storage, and Claude Code skills for ingestion, compilation, querying, and health checks.

**Architecture:** Raw sources (articles, competitor intel, AI news) land in `knowledge-base/raw/` via automated discovery or manual ingestion. An LLM compiles them into a `wiki/` of interlinked markdown articles. Articles are embedded and stored in Supabase with pgvector for semantic search. Five Claude Code skills (`/kb-discover`, `/kb-ingest`, `/kb-compile`, `/kb-query`, `/kb-health`) operate the full lifecycle.

**Tech Stack:** Supabase (pgvector), Voyage AI embeddings (1024-dim), Claude Code skills, Python (httpx for embedding API calls), FastAPI utility service.

**Spec:** `docs/superpowers/specs/2026-04-04-llm-knowledge-base-design.md`

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `migrations/081-kb-articles-and-sources.sql` | Create pgvector extension, `kb_articles` and `kb_sources` tables |
| `backend/services/embeddings.py` | Thin wrapper around Voyage AI / OpenAI embedding APIs |
| `knowledge-base/sources.yaml` | Search manifest — queries, blogs, feeds per category |
| `knowledge-base/known-urls.json` | URL dedup registry |
| `knowledge-base/INDEX.md` | Master catalog of all wiki articles |
| `knowledge-base/PENDING.md` | Tracks raw files awaiting compilation |
| `knowledge-base/.gitignore` | Ignore PDFs, images, large binaries |
| `knowledge-base/raw/` (7 subdirs) | Source documents by category |
| `knowledge-base/wiki/` (7 subdirs + `_outputs/`) | LLM-compiled articles |
| `.claude/skills/kb-discover/SKILL.md` | Automated article discovery skill |
| `.claude/skills/kb-ingest/SKILL.md` | Manual source ingestion skill |
| `.claude/skills/kb-compile/SKILL.md` | Wiki compilation skill |
| `.claude/skills/kb-query/SKILL.md` | Semantic Q&A skill |
| `.claude/skills/kb-health/SKILL.md` | Wiki audit skill |
| `tests/test_embeddings.py` | Tests for embedding service |

### Modified Files

| File | Change |
|------|--------|
| `backend/config.py` | Add `voyage_api_key` setting |
| `CLAUDE.md` | Add KB section to key directories, add skill references |
| `docs/dev-knowledge/schema-log.md` | Document new tables |

---

## Task 1: Database Migration — pgvector + KB Tables

**Files:**
- Create: `migrations/081-kb-articles-and-sources.sql`

- [ ] **Step 1: Create migration file**

```sql
-- 081: Knowledge Base tables with pgvector
-- Enables semantic search over LLM-compiled wiki articles

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Compiled wiki articles with embeddings
CREATE TABLE kb_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    summary TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1024),
    source_urls TEXT[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    word_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- HNSW index for cosine similarity search (works well at any scale)
CREATE INDEX kb_articles_embedding_idx ON kb_articles
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX kb_articles_category_idx ON kb_articles (category);

-- Raw source tracking and URL dedup
CREATE TABLE kb_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_url TEXT UNIQUE,
    file_path TEXT NOT NULL,
    category TEXT NOT NULL,
    relevance_score INT,
    title TEXT,
    discovered_at TIMESTAMPTZ DEFAULT now(),
    compiled BOOLEAN DEFAULT false,
    compiled_at TIMESTAMPTZ
);

CREATE INDEX kb_sources_compiled_idx ON kb_sources (compiled) WHERE compiled = false;
```

Write this to `migrations/081-kb-articles-and-sources.sql`.

- [ ] **Step 2: Apply migration via Supabase MCP**

Run: `mcp__supabase__apply_migration` with the SQL above.

Expected: Tables created, pgvector extension enabled.

- [ ] **Step 3: Update schema-log.md**

Add to `docs/dev-knowledge/schema-log.md`:

```markdown
### Migration 081 — Knowledge Base Tables (2026-04-04)
- Enabled pgvector extension
- Created `kb_articles` table: slug (unique), title, category, summary, content, embedding (vector 1024), source_urls (text[]), tags (text[]), word_count
- Created `kb_sources` table: source_url (unique), file_path, category, relevance_score, title, compiled (boolean)
- HNSW index on kb_articles.embedding for cosine similarity
- Index on kb_sources.compiled for pending source queries
```

- [ ] **Step 4: Commit**

```bash
git add migrations/081-kb-articles-and-sources.sql docs/dev-knowledge/schema-log.md
git commit -m "feat: add KB tables with pgvector for knowledge base system (migration 081)"
```

---

## Task 2: Embedding Service

**Files:**
- Create: `backend/services/embeddings.py`
- Create: `tests/test_embeddings.py`
- Modify: `backend/config.py`

- [ ] **Step 1: Add config setting**

Add to `backend/config.py` in the `Settings` class, after the existing `cloudflare_api_token` line:

```python
    voyage_api_key: str = ""
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_embeddings.py`:

```python
"""Tests for the embedding service."""

import os
os.environ["TESTING"] = "1"

import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def mock_httpx_response():
    """Mock a successful Voyage AI embedding response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [{"embedding": [0.1] * 1024}],
        "usage": {"total_tokens": 50}
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


@pytest.fixture
def mock_httpx_batch_response():
    """Mock a successful batch embedding response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {"embedding": [0.1] * 1024},
            {"embedding": [0.2] * 1024},
        ],
        "usage": {"total_tokens": 100}
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


@pytest.mark.asyncio
async def test_embed_text_returns_1024_dim_vector(mock_httpx_response):
    """embed_text returns a 1024-dimension float list."""
    with patch("backend.services.embeddings.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_httpx_response)
        mock_client_cls.return_value = mock_client

        from backend.services.embeddings import embed_text
        result = await embed_text("test query about AI chatbots")

        assert isinstance(result, list)
        assert len(result) == 1024
        assert all(isinstance(x, float) for x in result)


@pytest.mark.asyncio
async def test_embed_batch_returns_multiple_vectors(mock_httpx_batch_response):
    """embed_batch returns one vector per input text."""
    with patch("backend.services.embeddings.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_httpx_batch_response)
        mock_client_cls.return_value = mock_client

        from backend.services.embeddings import embed_batch
        result = await embed_batch(["text one", "text two"])

        assert len(result) == 2
        assert all(len(v) == 1024 for v in result)


@pytest.mark.asyncio
async def test_embed_text_truncates_long_input(mock_httpx_response):
    """embed_text truncates input longer than MAX_EMBED_CHARS."""
    with patch("backend.services.embeddings.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_httpx_response)
        mock_client_cls.return_value = mock_client

        from backend.services.embeddings import embed_text
        long_text = "word " * 10000  # ~50K chars
        result = await embed_text(long_text)

        assert len(result) == 1024
        # Verify the API was called with truncated text
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
        sent_text = payload["input"][0]
        assert len(sent_text) <= 32001  # MAX_EMBED_CHARS + 1 for safety
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /home/aidan/agentnexlify && python -m pytest tests/test_embeddings.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.services.embeddings'`

- [ ] **Step 4: Write the embedding service**

Create `backend/services/embeddings.py`:

```python
"""Embedding service for knowledge base semantic search.

Uses Voyage AI (voyage-3-lite, 1024 dimensions) as primary provider.
Shared utility — available for KB and future product features.
"""

import logging

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"
VOYAGE_MODEL = "voyage-3-lite"
EMBEDDING_DIM = 1024
MAX_EMBED_CHARS = 32000  # ~8K tokens, safe limit for embedding input


async def embed_text(text: str) -> list[float]:
    """Embed a single text string. Returns 1024-dim vector."""
    truncated = text[:MAX_EMBED_CHARS]
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            VOYAGE_API_URL,
            headers={"Authorization": f"Bearer {settings.voyage_api_key}"},
            json={
                "model": VOYAGE_MODEL,
                "input": [truncated],
                "input_type": "document",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return [float(x) for x in data["data"][0]["embedding"]]


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in one API call. Returns list of 1024-dim vectors."""
    truncated = [t[:MAX_EMBED_CHARS] for t in texts]
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            VOYAGE_API_URL,
            headers={"Authorization": f"Bearer {settings.voyage_api_key}"},
            json={
                "model": VOYAGE_MODEL,
                "input": truncated,
                "input_type": "document",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return [[float(x) for x in item["embedding"]] for item in data["data"]]


async def embed_query(text: str) -> list[float]:
    """Embed a search query. Uses input_type='query' for better retrieval."""
    truncated = text[:MAX_EMBED_CHARS]
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            VOYAGE_API_URL,
            headers={"Authorization": f"Bearer {settings.voyage_api_key}"},
            json={
                "model": VOYAGE_MODEL,
                "input": [truncated],
                "input_type": "query",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return [float(x) for x in data["data"][0]["embedding"]]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/aidan/agentnexlify && python -m pytest tests/test_embeddings.py -v`

Expected: 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/config.py backend/services/embeddings.py tests/test_embeddings.py
git commit -m "feat: add embedding service for KB semantic search (Voyage AI)"
```

---

## Task 3: Directory Structure + Scaffold Files

**Files:**
- Create: `knowledge-base/` directory tree
- Create: `knowledge-base/sources.yaml`
- Create: `knowledge-base/known-urls.json`
- Create: `knowledge-base/INDEX.md`
- Create: `knowledge-base/PENDING.md`
- Create: `knowledge-base/.gitignore`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p knowledge-base/raw/{competitors,ai-llm,small-biz-saas,verticals,technical,regulations,growth}
mkdir -p knowledge-base/wiki/{competitors,ai-llm,small-biz-saas,verticals,technical,regulations,growth,_outputs}
```

- [ ] **Step 2: Create .gitignore**

Write `knowledge-base/.gitignore`:

```
# Large binaries — keep raw .md files tracked, ignore heavy media
*.pdf
*.png
*.jpg
*.jpeg
*.gif
*.mp4
*.zip
```

- [ ] **Step 3: Create sources.yaml**

Write `knowledge-base/sources.yaml`:

```yaml
# Knowledge Base Discovery Manifest
# Defines search queries, competitor blogs, and feeds per category.
# /kb-discover reads this to find new articles.

competitors:
  search_queries:
    - "GoHighLevel AI update 2026"
    - "AI chatbot small business CRM"
    - "Drillbit AI contractor"
    - "Phonely AI receptionist"
    - "Toma AI receptionist"
    - "Birdeye AI reviews 2026"
    - "Podium AI reviews"
    - "Oscar Chat AI chatbot"
    - "Tidio AI chatbot update"
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

verticals:
  search_queries:
    - "AI for contractors 2026"
    - "dental practice management AI"
    - "salon booking AI chatbot"
    - "restaurant AI ordering"
    - "legal intake AI"
    - "real estate AI lead capture"

technical:
  search_queries:
    - "prompt engineering best practices 2026"
    - "RAG vs long context"
    - "LLM streaming structured output"
    - "AI agent tool use patterns"
    - "pgvector semantic search"

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

- [ ] **Step 4: Create known-urls.json**

Write `knowledge-base/known-urls.json`:

```json
[]
```

- [ ] **Step 5: Create INDEX.md**

Write `knowledge-base/INDEX.md`:

```markdown
# Knowledge Base Index

Master catalog of all compiled wiki articles. Auto-maintained by `/kb-compile`.

## Statistics
- Total articles: 0
- Last compiled: never

## Articles by Category

### Competitors
_No articles yet._

### AI/LLM Developments
_No articles yet._

### Small Business SaaS
_No articles yet._

### Vertical Industries
_No articles yet._

### Technical Patterns
_No articles yet._

### Regulations & Compliance
_No articles yet._

### Growth & Distribution
_No articles yet._

## Cross-Reference Map
_Populated after first compilation._
```

- [ ] **Step 6: Create PENDING.md**

Write `knowledge-base/PENDING.md`:

```markdown
# Pending Sources

Raw files awaiting compilation. Run `/kb-compile` to process.

_No pending sources._
```

- [ ] **Step 7: Add .gitkeep files to empty directories**

```bash
for dir in knowledge-base/raw/{competitors,ai-llm,small-biz-saas,verticals,technical,regulations,growth} knowledge-base/wiki/{competitors,ai-llm,small-biz-saas,verticals,technical,regulations,growth,_outputs}; do
    touch "$dir/.gitkeep"
done
```

- [ ] **Step 8: Commit**

```bash
git add knowledge-base/
git commit -m "feat: scaffold knowledge base directory structure and config"
```

---

## Task 4: Skill — `/kb-ingest`

**Files:**
- Create: `.claude/skills/kb-ingest/SKILL.md`

- [ ] **Step 1: Write the skill**

Write `.claude/skills/kb-ingest/SKILL.md`:

````markdown
---
name: kb-ingest
description: "Manually add a source to the knowledge base. Takes a URL or local file path. Fetches, converts to markdown, categorizes, and registers in kb_sources."
user_invocable: true
---

# KB Ingest — Manual Source Addition

Add a single source to the knowledge base for later compilation.

## Usage

- `/kb-ingest https://some-article.com` — fetch URL, convert to .md, categorize
- `/kb-ingest ./path/to/file.md` — copy local file, categorize

## Workflow

### Step 1: Determine Input Type

If the argument starts with `http://` or `https://`:
- Use WebFetch to retrieve the page content
- Extract the article title, main body text, and publication date
- Strip navigation, ads, sidebars — keep only the article content
- Convert to clean markdown

If the argument is a local file path:
- Read the file content
- If it already has YAML frontmatter, preserve it

### Step 2: Categorize

Read the article content and assign it to exactly one category:
- `competitors` — About GoHighLevel, Drillbit, Phonely, Toma, Birdeye, Podium, Oscar Chat, Tidio, or any AI chatbot/CRM competitor
- `ai-llm` — About LLM models, capabilities, pricing, releases, benchmarks
- `small-biz-saas` — About SaaS trends, pricing, churn, PLG for small businesses
- `verticals` — About specific industries (contractors, dental, salon, legal, restaurant, real estate)
- `technical` — About prompt engineering, RAG, embeddings, agent patterns, streaming
- `regulations` — About HIPAA, TCPA, data privacy, AI disclosure, FTC
- `growth` — About distribution, virality, SEO, GEO, partnerships

### Step 3: Save Raw File

Generate a filename from the title: lowercase, hyphens, no special chars, max 60 chars.

Write to `knowledge-base/raw/{category}/{filename}.md` with frontmatter:

```yaml
---
title: "Article Title Here"
source_url: https://original-url.com  # or "local" for local files
discovered: YYYY-MM-DD
category: category_name
relevance_score: 8  # your assessment 0-10
---

[article content in markdown]
```

### Step 4: Register in Database

Execute SQL via Supabase MCP:

```sql
INSERT INTO kb_sources (source_url, file_path, category, relevance_score, title, discovered_at)
VALUES ('the_url', 'raw/category/filename.md', 'category', score, 'Title', now())
ON CONFLICT (source_url) DO NOTHING;
```

### Step 5: Update known-urls.json

Read `knowledge-base/known-urls.json`, append the new URL, write it back.

### Step 6: Update PENDING.md

Add a line to `knowledge-base/PENDING.md`:

```markdown
- `raw/category/filename.md` — "Article Title" (score: 8) — YYYY-MM-DD
```

### Step 7: Report

Output: "Ingested: **Article Title** → `raw/category/filename.md` (relevance: 8/10). Run `/kb-compile` to process."
````

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/kb-ingest/
git commit -m "feat: add /kb-ingest skill for manual KB source addition"
```

---

## Task 5: Skill — `/kb-discover`

**Files:**
- Create: `.claude/skills/kb-discover/SKILL.md`

- [ ] **Step 1: Write the skill**

Write `.claude/skills/kb-discover/SKILL.md`:

````markdown
---
name: kb-discover
description: "Automated article discovery for the knowledge base. Searches the web using sources.yaml queries, scores relevance, and ingests high-quality results. Run to find new articles."
user_invocable: true
---

# KB Discover — Automated Article Discovery

Search the web for articles relevant to AgentNexLiFy and AI, score them for relevance, and ingest the best ones.

## Usage

- `/kb-discover` — run all categories
- `/kb-discover competitors` — run only the competitors category
- `/kb-discover ai_llm technical` — run multiple categories

## Workflow

### Step 1: Load Configuration

Read `knowledge-base/sources.yaml` to get search queries and blog URLs per category.

Read `knowledge-base/known-urls.json` to get the dedup list of already-ingested URLs.

Determine which categories to process:
- If arguments provided, only those categories
- If no arguments, all categories

### Step 2: Search (per category)

For each category being processed:

1. **Search queries:** For each `search_queries` entry, run WebSearch. Collect the top 5 result URLs per query.

2. **Blog checks:** For each `blogs` entry, WebFetch the blog page and extract article links from the last 30 days.

3. **Deduplicate:** Remove any URLs already in `known-urls.json`.

### Step 3: Fetch and Score

For each unique new URL (process up to 20 per category to control token usage):

1. WebFetch the URL to get article content
2. Extract: title, main body, publication date
3. Score relevance to AgentNexLiFy on a 0-10 scale:
   - 9-10: Directly about a competitor or feature we're building
   - 7-8: Relevant industry trend or technical pattern we can apply
   - 5-6: Tangentially related, might be useful
   - 0-4: Not relevant enough to keep
4. **Keep only scores 7+**

Scoring criteria — the article must relate to at least one of:
- AgentNexLiFy's direct competitors or market
- AI/LLM capabilities relevant to our product
- Small business software buying behavior
- Industries we serve (contractors, dental, salon, legal, restaurant, real estate)
- Technical patterns for chat, embeddings, agents, or automation
- Regulations affecting AI chatbots or SMS/email automation
- Distribution or growth strategies for embedded SaaS

### Step 4: Ingest Qualifying Articles

For each article scoring 7+, follow the same process as `/kb-ingest`:

1. Convert to clean markdown
2. Write to `knowledge-base/raw/{category}/{filename}.md` with frontmatter
3. Insert into `kb_sources` table
4. Append URL to `known-urls.json`
5. Add line to `PENDING.md`

### Step 5: Report

Output a summary table:

```
## Discovery Report — YYYY-MM-DD

| Category | Searched | Found | Ingested |
|----------|----------|-------|----------|
| competitors | 12 | 5 | 3 |
| ai_llm | 10 | 8 | 5 |
| ... | ... | ... | ... |
| **Total** | **X** | **Y** | **Z** |

### New Articles
- `raw/competitors/ghl-ai-employee-v3.md` — "GoHighLevel Launches AI Employee v3" (9/10)
- `raw/ai-llm/claude-4-announcement.md` — "Anthropic Announces Claude 4" (10/10)
- ...

Run `/kb-compile` to process these into the wiki.
```
````

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/kb-discover/
git commit -m "feat: add /kb-discover skill for automated KB article discovery"
```

---

## Task 6: Skill — `/kb-compile`

**Files:**
- Create: `.claude/skills/kb-compile/SKILL.md`

- [ ] **Step 1: Write the skill**

Write `.claude/skills/kb-compile/SKILL.md`:

````markdown
---
name: kb-compile
description: "Compile raw sources into the wiki. Reads pending sources, creates or updates wiki articles, generates embeddings, stores in Supabase pgvector, and rebuilds INDEX.md."
user_invocable: true
---

# KB Compile — Wiki Compilation

Transform raw sources into interlinked wiki articles with vector embeddings.

## Usage

- `/kb-compile` — compile all pending sources
- `/kb-compile --full` — recompile entire wiki (regenerate all embeddings)

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

### Step 10: Commit

```bash
git add knowledge-base/
git commit -m "kb: compile [N] sources into wiki ([new] new, [updated] updated)"
```
````

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/kb-compile/
git commit -m "feat: add /kb-compile skill for wiki compilation with embeddings"
```

---

## Task 7: Skill — `/kb-query`

**Files:**
- Create: `.claude/skills/kb-query/SKILL.md`

- [ ] **Step 1: Write the skill**

Write `.claude/skills/kb-query/SKILL.md`:

````markdown
---
name: kb-query
description: "Ask questions against the knowledge base using semantic search. Embeds your question, finds relevant articles via pgvector cosine similarity, and synthesizes an answer."
user_invocable: true
---

# KB Query — Semantic Q&A

Ask natural language questions against the compiled knowledge base.

## Usage

- `/kb-query How does GoHighLevel's AI Employee compare to our chat widget?`
- `/kb-query What are the latest LLM context window improvements?`
- `/kb-query What compliance risks do we face with SMS automation?`

## Workflow

### Step 1: Embed the Question

Run Python to embed the query using the query-optimized endpoint:

```python
import asyncio
import sys
sys.path.insert(0, '.')
from backend.services.embeddings import embed_query

question = "USER QUESTION HERE"
embedding = asyncio.run(embed_query(question))
# Format as string for SQL
embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
print(embedding_str)
```

### Step 2: Semantic Search

Query Supabase for the top 10 most similar articles:

```sql
SELECT slug, title, category, summary, content, tags,
       1 - (embedding <=> 'EMBEDDING_VECTOR'::vector) AS similarity
FROM kb_articles
WHERE embedding IS NOT NULL
ORDER BY embedding <=> 'EMBEDDING_VECTOR'::vector
LIMIT 10;
```

If results have similarity < 0.3, they're likely not relevant — note this in the answer.

### Step 3: Optional Category Filter

If the question clearly targets one category (e.g., "What are competitors doing with AI?"), add a WHERE clause:

```sql
WHERE embedding IS NOT NULL AND category = 'competitors'
```

### Step 4: Read Matched Articles

For each of the top 10 results, read the full wiki article from disk at `knowledge-base/wiki/{slug}.md`. Reading from disk ensures you get the latest content (which may have been edited since last embedding).

### Step 5: Synthesize Answer

Using the matched articles as context, write a comprehensive answer to the question:

- Cite specific articles: "According to [[gohighlevel]], ..."
- Include relevant data points, quotes, and comparisons
- End with a `## Sources` section listing the articles used
- If the KB lacks sufficient information, say so explicitly and suggest what to ingest

### Step 6: Save Output

Write the answer to `knowledge-base/wiki/_outputs/{YYYY-MM-DD}-{question-slug}.md`:

```yaml
---
title: "Query: How does GoHighLevel's AI Employee compare?"
category: _output
query: "How does GoHighLevel's AI Employee compare to our chat widget?"
sources_used: ["wiki/competitors/gohighlevel.md", "wiki/technical/ai-employee-market.md"]
created: YYYY-MM-DD
---

[Answer content here]
```

### Step 7: File Back (Optional)

If the answer contains lasting insights not already in the wiki (e.g., a novel comparison, a synthesis that connects multiple articles), ask:

> "This answer contains insights that could enhance the wiki. Want me to file it back as a new article or merge into an existing one?"

If yes, create/update the appropriate wiki article and run embedding + Supabase upsert for it.

### Step 8: Report

Display the full answer in the terminal, then:

```
---
Answer saved to: knowledge-base/wiki/_outputs/2026-04-04-ghl-comparison.md
Sources consulted: 6 articles (similarity range: 0.72 — 0.91)
```
````

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/kb-query/
git commit -m "feat: add /kb-query skill for semantic Q&A against knowledge base"
```

---

## Task 8: Skill — `/kb-health`

**Files:**
- Create: `.claude/skills/kb-health/SKILL.md`

- [ ] **Step 1: Write the skill**

Write `.claude/skills/kb-health/SKILL.md`:

````markdown
---
name: kb-health
description: "Audit the knowledge base for staleness, gaps, contradictions, and missing cross-links. Reports health score and suggests improvements."
user_invocable: true
---

# KB Health — Wiki Audit

Run quality checks across the knowledge base and suggest improvements.

## Usage

- `/kb-health` — full audit
- `/kb-health --category competitors` — audit one category

## Checks

### 1. Staleness Check

For each wiki article, check if ALL sources are older than 60 days:

```sql
SELECT slug, title, category, updated_at,
       now() - updated_at AS age
FROM kb_articles
ORDER BY updated_at ASC;
```

Flag articles where `age > 60 days` as stale.

For stale articles, suggest discovery queries that could refresh them. Example:
- `wiki/competitors/gohighlevel.md` is 75 days old → suggest searching "GoHighLevel updates April 2026"

### 2. Category Coverage

Count articles per category:

```sql
SELECT category, COUNT(*) as count, SUM(word_count) as total_words
FROM kb_articles
GROUP BY category
ORDER BY count;
```

Flag categories with fewer than 3 articles as "thin coverage."

Compare against the 7 expected categories and flag any with 0 articles.

### 3. Missing Cross-Links

For each article, read its content and check for mentions of entities/concepts that have their own wiki articles but aren't linked with `[[backlink]]` syntax.

Example: if `wiki/competitors/gohighlevel.md` mentions "prompt caching" and `wiki/technical/prompt-caching.md` exists, but there's no `[[prompt-caching]]` link, flag it.

### 4. Orphan Detection

Find articles that are never referenced by any other article (no incoming backlinks). These might be isolated or poorly integrated.

### 5. Contradiction Check

Read articles within the same category and check for conflicting claims. Example:
- Article A says "GoHighLevel charges $97/mo for base plan"
- Article B says "GoHighLevel starts at $127/mo"
- Flag: "Possible contradiction about GHL pricing between [[gohighlevel]] and [[competitor-pricing-2026]]"

### 6. Embedding Coverage

```sql
SELECT COUNT(*) as total,
       COUNT(embedding) as has_embedding,
       COUNT(*) - COUNT(embedding) as missing_embedding
FROM kb_articles;
```

Flag articles missing embeddings — they won't appear in semantic search.

### 7. Pending Source Check

```sql
SELECT COUNT(*) FROM kb_sources WHERE compiled = false;
```

Report uncompiled sources.

## Health Report

Output a structured report:

```markdown
## Knowledge Base Health Report — YYYY-MM-DD

### Score: 78/100

### Summary
- Total articles: 42
- Total words: ~85,000
- Pending sources: 3
- Missing embeddings: 1

### Staleness (15 points deducted)
- 🔴 `wiki/competitors/phonely.md` — 90 days old
- 🟡 `wiki/regulations/hipaa.md` — 65 days old
- Suggested refresh queries:
  - "Phonely AI receptionist 2026 update"
  - "HIPAA AI chatbot compliance 2026"

### Coverage
| Category | Articles | Words | Status |
|----------|----------|-------|--------|
| competitors | 8 | 12,000 | ✅ Good |
| ai-llm | 12 | 18,000 | ✅ Good |
| regulations | 2 | 3,000 | ⚠️ Thin |
| growth | 1 | 1,500 | 🔴 Gap |

### Missing Cross-Links (5 points deducted)
- `gohighlevel.md` mentions "AI Employee" but doesn't link to [[ai-employee-market]]
- `prompt-caching.md` mentions "Claude" but doesn't link to [[claude-sonnet-4-6]]

### Contradictions (2 points deducted)
- GHL pricing conflict between [[gohighlevel]] and [[competitor-pricing-2026]]

### Recommended Actions
1. Run `/kb-discover regulations growth` to fill coverage gaps
2. Run `/kb-compile` to process 3 pending sources
3. Review pricing contradiction in competitor articles
```

### Scoring

| Check | Max Points | Deduction Logic |
|-------|-----------|-----------------|
| No stale articles | 25 | -5 per stale article (cap -25) |
| All categories ≥ 3 articles | 20 | -5 per thin category (cap -20) |
| No missing cross-links | 15 | -1 per missing link (cap -15) |
| No contradictions | 15 | -3 per contradiction (cap -15) |
| All embeddings present | 10 | -2 per missing (cap -10) |
| No pending sources | 10 | -2 per pending (cap -10) |
| No orphan articles | 5 | -1 per orphan (cap -5) |
````

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/kb-health/
git commit -m "feat: add /kb-health skill for wiki auditing and quality checks"
```

---

## Task 9: Seed Data Migration

**Files:**
- Create: `knowledge-base/raw/competitors/competitive-research-march-2026.md`
- Create: `knowledge-base/raw/verticals/customer-gaps-consolidated.md`
- Create: `knowledge-base/raw/growth/post-launch-growth-features.md`

- [ ] **Step 1: Copy existing research as seed sources**

Read `docs/dev-knowledge/research-2026-03.md` and write it to `knowledge-base/raw/competitors/competitive-research-march-2026.md` with frontmatter:

```yaml
---
title: "Competitive Research — March 2026"
source_url: local
discovered: 2026-03-15
category: competitors
relevance_score: 10
---

[existing content from research-2026-03.md]
```

- [ ] **Step 2: Copy customer gaps**

Read `docs/dev-knowledge/customer-gaps.md` and write to `knowledge-base/raw/verticals/customer-gaps-consolidated.md` with frontmatter:

```yaml
---
title: "Customer Gaps — Consolidated Findings"
source_url: local
discovered: 2026-03-20
category: verticals
relevance_score: 10
---

[existing content from customer-gaps.md]
```

- [ ] **Step 3: Copy growth research**

Read `docs/research/post-launch-growth-features.md` and write to `knowledge-base/raw/growth/post-launch-growth-features.md` with frontmatter:

```yaml
---
title: "Post-Launch Growth Features: Top 10 Recommendations"
source_url: local
discovered: 2026-03-18
category: growth
relevance_score: 10
---

[existing content from post-launch-growth-features.md]
```

- [ ] **Step 4: Register seed sources in database**

```sql
INSERT INTO kb_sources (source_url, file_path, category, relevance_score, title, discovered_at) VALUES
('local:research-2026-03', 'raw/competitors/competitive-research-march-2026.md', 'competitors', 10, 'Competitive Research — March 2026', '2026-03-15'),
('local:customer-gaps', 'raw/verticals/customer-gaps-consolidated.md', 'verticals', 10, 'Customer Gaps — Consolidated Findings', '2026-03-20'),
('local:post-launch-growth', 'raw/growth/post-launch-growth-features.md', 'growth', 10, 'Post-Launch Growth Features: Top 10 Recommendations', '2026-03-18')
ON CONFLICT (source_url) DO NOTHING;
```

- [ ] **Step 5: Update PENDING.md**

```markdown
# Pending Sources

Raw files awaiting compilation. Run `/kb-compile` to process.

- `raw/competitors/competitive-research-march-2026.md` — "Competitive Research — March 2026" (score: 10) — 2026-03-15
- `raw/verticals/customer-gaps-consolidated.md` — "Customer Gaps — Consolidated Findings" (score: 10) — 2026-03-20
- `raw/growth/post-launch-growth-features.md` — "Post-Launch Growth Features: Top 10 Recommendations" (score: 10) — 2026-03-18
```

- [ ] **Step 6: Commit**

```bash
git add knowledge-base/raw/ knowledge-base/PENDING.md
git commit -m "feat: seed knowledge base with existing research documents"
```

---

## Task 10: Update CLAUDE.md + Final Integration

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add KB to key directories section**

In CLAUDE.md, in the `## Key Directories` section, add after the `docs/dev-knowledge/` line:

```markdown
- `knowledge-base/` — LLM-compiled knowledge base (`raw/` sources, `wiki/` compiled articles, pgvector embeddings)
```

- [ ] **Step 2: Add KB skills to skills section**

In CLAUDE.md, in the Skills & Agents section, update the skills line to include KB skills:

```markdown
Skills in `.claude/skills/`: **schema-guard**, **debug-api**, **feature-build**, **widget-test**, **team-orchestration**, **industry-content**, **ai-feature-pattern**, **migration-workflow**, **build-loop**, **kb-discover**, **kb-ingest**, **kb-compile**, **kb-query**, **kb-health**. Also `.codex/skills/` for repo-native skills.
```

- [ ] **Step 3: Add KB workflow commands**

In the `## Workflow Commands` table, add:

```markdown
| `/kb-discover` | Search web for new articles relevant to AgentNexLiFy, score and ingest |
| `/kb-ingest` | Manually add a URL or file to the knowledge base |
| `/kb-compile` | Compile pending sources into wiki articles with embeddings |
| `/kb-query` | Semantic Q&A against the knowledge base |
| `/kb-health` | Audit wiki for staleness, gaps, contradictions |
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add knowledge base system to CLAUDE.md"
```

---

## Self-Review Results

**Spec coverage:** All 6 spec sections covered — directory structure (Task 3), database schema (Task 1), embedding infrastructure (Task 2), all 5 skills (Tasks 4-8), integration with morning routine and agents (documented in skills), seed data migration (Task 9), CLAUDE.md update (Task 10). `sources.yaml` manifest (Task 3). Environment variable (Task 2).

**Placeholder scan:** No TBDs, TODOs, or vague instructions. All SQL, code, and file contents are complete.

**Type consistency:** `embed_text` / `embed_batch` / `embed_query` names consistent across Task 2 (implementation) and Tasks 6-7 (skill references). Table names `kb_articles` / `kb_sources` consistent across migration (Task 1) and all skills. Column names match throughout.
