---
name: kb-ingest
description: Manually add a source to the knowledge base by fetching a URL or reading a local file, converting to markdown, categorizing, and registering in kb_sources. Use when user says 'kb-ingest', 'ingest url', 'ingest article', 'add source', 'save article to kb', or asks about kb ingest.
version: 1.1.0
origin: claude
user-invocable: true
agent: true
model: sonnet
triggers:
- kb-ingest
- ingest url
- ingest article
- add source
- save article to kb
effort: medium
argument-hint: "[url-or-path]"
allowed-tools: [Read, Write, Bash, WebFetch]
---

# KB Ingest — Manual Source Addition

Add a single source to the knowledge base for later compilation.

## Usage

- `/kb-ingest https://some-article.com` — fetch URL, convert to .md, categorize
- `/kb-ingest ./path/to/file.md` — copy local file, categorize

## When to Use
- Adding a single known URL or local file to the knowledge base
- Saving an article you found manually for later compilation

## When NOT to Use
- Automated web discovery (use kb-discover instead)
- Compiling raw sources into wiki articles (use kb-compile instead)
- Querying the knowledge base (use kb-query instead)
- Fast-path directly to wiki (use wiki skill instead)

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
