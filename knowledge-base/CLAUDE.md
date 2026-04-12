# knowledge-base/CLAUDE.md — LLM Wiki Schema

This file is read by Claude Code (or any LLM agent) whenever it operates on the knowledge base. It is the schema/protocol that turns the LLM into a disciplined wiki maintainer, not a generic chatbot. Pattern: Karpathy's LLM Wiki (see `wiki/ai-llm/llm-wiki-karpathy-pattern.md`).

## Three-layer architecture

```
knowledge-base/
├── raw/                    # source-of-truth. LLM reads, never modifies.
│   ├── ai-llm/             # AI/LLM sources
│   ├── competitors/        # GHL, Drillbit, Podium, etc.
│   ├── growth/
│   ├── regulations/
│   ├── small-biz-saas/
│   ├── technical/
│   └── verticals/          # salon, dental, contractor, legal, etc.
│
├── wiki/                   # LLM-generated markdown. LLM owns fully.
│   ├── INDEX.md            # content catalog (auto-updated on every ingest)
│   ├── _outputs/           # query results filed back as pages
│   └── <category>/<slug>.md
│
├── CLAUDE.md               # this file — schema, conventions, workflows
├── INDEX.md                # top-level content catalog (category → pages)
├── log.md                  # chronological append-only record of operations
├── PENDING.md              # raw files awaiting compile
├── known-urls.json         # dedup list for kb-discover
├── sources.yaml            # discovery manifest (search queries, blogs)
└── ARTICLE_TEMPLATE.md     # Karpathy template (see wiki/ai-llm/llm-wiki-karpathy-pattern.md)
```

## Core rule

The LLM **never** edits `raw/`. The LLM **owns** `wiki/`, `INDEX.md`, `log.md`, `PENDING.md`, `known-urls.json`.

## Operations

### Ingest (manual)
Trigger: `/kb-ingest <url-or-file>`
1. Fetch source → markdown
2. Detect category (auto or user-supplied)
3. Write raw file to `raw/<category>/<slug>.md`
4. Append to `PENDING.md`
5. Run compile on that raw file (single-source compile)
6. Log to `log.md`: `## [YYYY-MM-DD HH:MM] ingest | <title> | <category>`

### Compile
Trigger: `/kb-compile` (all pending) or `/kb-compile <file>`
1. Read raw file(s)
2. Generate wiki article using `ARTICLE_TEMPLATE.md` format
3. Cross-reference existing wiki pages via `[[slug]]` links
4. Update `INDEX.md` (add link + one-line summary)
5. Update affected entity/concept pages (10-15 touches typical)
6. Generate Voyage embedding, store in Supabase `kb_articles`
7. Remove from `PENDING.md`
8. Log to `log.md`: `## [YYYY-MM-DD HH:MM] compile | <title>`

### Discover (auto-populate)
Trigger: `/kb-discover` or scheduled cron (6am + 6pm daily)
1. Load `sources.yaml` — search queries + blogs per category
2. Web search (agent-browser via Bash) → candidate URLs
3. Dedup against `known-urls.json`
4. Score relevance (heuristic + LLM)
5. Auto-ingest top-N per category (N=3 default)
6. Append URLs to `known-urls.json`
7. Log to `log.md`: `## [YYYY-MM-DD HH:MM] discover | found <N> | ingested <M>`

### Query
Trigger: `/kb-query "<question>"`
1. Read `INDEX.md` to find candidate pages
2. Semantic search via pgvector (cosine similarity) on Supabase
3. Read top-K relevant wiki pages (K=5 default)
4. Synthesize answer with citations (file paths)
5. **File back:** if answer is substantive (comparison, analysis, new connection), save to `wiki/_outputs/YYYY-MM-DD-<slug>.md` and add to `INDEX.md`
6. Log to `log.md`: `## [YYYY-MM-DD HH:MM] query | <question> | filed=<yes/no>`

### Lint (health check)
Trigger: `/kb-health` or weekly cron
1. Read every wiki page
2. Check for: contradictions between pages, orphan pages (no inbound links), stale claims, missing concept pages, data gaps
3. Write report to `wiki/lint-report.md` with specific fixes
4. Log to `log.md`: `## [YYYY-MM-DD HH:MM] lint | <N> issues found`

## Page conventions

Every wiki page uses the Karpathy template (see `.claude/skills/wiki/references/template.md`):
- YAML frontmatter: `title`, `category`, `tags`, `sources`, `created`, `updated`, `summary`
- Opening paragraph = abstract (3-5 sentences, establishes context and thesis)
- Body = essay prose (3-7 paragraphs, not bullet lists)
- `## Key Concepts` (3-7 domain-specific definitions)
- `## Related Articles` (inline `[[slug]]` cross-refs + explicit list)
- `## Relevance to AgentNexLiFy` (mandatory; actionable insight)

## Categories (AgentNexLiFy core)

Scope is tightened to what matters for AgentNexLiFy + AI as a whole:
- `ai-llm` — Claude API, prompt caching, model releases, agent frameworks, structured output
- `competitors` — GHL, Drillbit, Phonely, Toma, Birdeye, Podium, Oscar Chat, Tidio
- `verticals` — industries we sell to: salon, dental, contractor, legal, real estate, restaurant, auto shop, medical office
- `small-biz-saas` — churn, PLG, pricing, vertical SaaS trends
- `technical` — pgvector, RAG patterns, streaming, embeddings, tool use
- `regulations` — HIPAA, TCPA, FTC AI rules, AI disclosure laws
- `growth` — chat widget distribution, embedded SaaS, SEO, GEO

Anything outside these categories goes to `raw/_misc/` and is NOT auto-ingested.

## Cross-reference rules

- Use `[[slug]]` syntax inline wherever another article covers a topic deeper
- Every article links to ≥1 other article
- Link text must explain relationship, not just name the target

## No-surprise rule

LLM output must be predictable:
- No silent deletions from `wiki/`
- No edits to `raw/` ever
- No new top-level categories without explicit user ask
- `log.md` records every mutation

## Pointers

- Karpathy pattern article: `wiki/ai-llm/llm-wiki-karpathy-pattern.md`
- Skills: `.claude/skills/kb-{discover,ingest,compile,query,health}/`
- Template: `.claude/skills/wiki/references/template.md`
- Cron: `scripts/daily/kb-autopopulate.sh` (6am + 6pm)
