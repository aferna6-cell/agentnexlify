---
name: kb-discover
description: Automated article discovery for the knowledge base that searches the web, scores relevance, and ingests high-quality results. Use when user says 'kb-discover', 'discover articles', 'find new articles', 'automated discovery', 'search for articles', or asks about kb discover.
version: 1.0.0
origin: claude
user-invocable: true
triggers:
- kb-discover
- discover articles
- find new articles
- automated discovery
- search for articles
effort: medium
---

# KB Discover — Automated Article Discovery

Search the web for articles relevant to AgentNexLiFy and AI, score them for relevance, and ingest the best ones.

## Usage

- `/kb-discover` — run all categories
- `/kb-discover competitors` — run only the competitors category
- `/kb-discover ai_llm technical` — run multiple categories

## When to Use
- Finding new articles to add to the knowledge base automatically
- Refreshing stale categories with fresh web content
- Running targeted discovery for specific topic areas

## When NOT to Use
- Adding a single known URL (use kb-ingest instead)
- Compiling existing raw sources (use kb-compile instead)
- Querying the knowledge base (use kb-query instead)

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
