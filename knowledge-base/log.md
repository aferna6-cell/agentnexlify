# KB Log — Chronological Record

Append-only log of all knowledge-base operations. Format per Karpathy pattern:

```
## [YYYY-MM-DD HH:MM] <op> | <subject> | <metadata>
```

Ops: `ingest`, `compile`, `discover`, `query`, `lint`, `migrate`

Tail with: `grep "^## \[" log.md | tail -20`

---

## [2026-04-12 14:30] migrate | added log.md + CLAUDE.md schema | aligned to Karpathy LLM Wiki pattern

Created `knowledge-base/CLAUDE.md` (schema file defining 3-layer architecture + ops + page conventions + categories).

Created `knowledge-base/log.md` (this file). All future KB operations append here.

Tightened `sources.yaml` to AgentNexLiFy core categories (competitors, ai-llm focused on Claude/agents, verticals we sell to, small-biz SaaS, technical infra we use, relevant regulations, widget/GEO growth).

Scheduled `scripts/daily/kb-autopopulate.sh` via cron for 6am + 6pm daily.

## [2026-04-12 18:30] discover+compile | first-cron-run | raw=+8 wiki=+2 errors=0

First real run of `scripts/daily/kb-autopopulate.sh`. Fired manually (cron next at 6am).

- **Discover** — fetched 14 raw articles across 7 categories via agent-browser
- **Relevance filter** — 6 off-topic rejected manually after run (P.LEAGUE sports, 340B drug pricing, MIT general AI news, Front Porch Forum). URLs stay in `known-urls.json` to prevent refetch. Discover prompt now has explicit relevance filter + list of bad patterns.
- **Compile** — 2/14 completed (both GoHighLevel articles). Context cap reached. Compile prompt now has 4-entry-per-run cap with remainder left in PENDING for next cron.
- **Embeddings** — Supabase kb_articles insert status unverified this run; compile prompt now accepts `embedding_errors=N` as non-fatal so compile continues even if MCP unreachable.
- **INDEX.md** — updated manually to reflect 2 new wiki entries (compile didn't auto-update this run).

**Remaining PENDING (8 entries):** 2 Anthropic pages, 2 pgvector refs, 2 HIPAA pages. Will process at next cron fires (6am + 6pm daily).

## [2026-04-12 19:00] compile | headless-cron-batch-2 | compiled=4 embeddings=0 errors=4

Processed 4 of 6 pending entries this run (4-entry cap). Remaining: 2 HIPAA pages + 4 entries ingested at 22:54:23Z (Claude Opus 4.6, Sonnet 4.6, GHL AI responder, GHL email report).

- **Compiled:**
  - `wiki/ai-llm/anthropic-mission-and-latest-releases.md` (from raw/ai-llm/home-anthropic.md)
  - `wiki/ai-llm/anthropic-careers-and-culture.md` (from raw/ai-llm/careers-anthropic.md)
  - `wiki/technical/pgvector-postgres-vector-search.md` (from raw/technical/github---pgvector-pgvector-*.md)
  - `wiki/technical/pgvector-implementation-guide.md` (from raw/technical/pgvector---geeksforgeeks.md)
- **INDEX.md** — updated with 4 new entries, total 10 articles; added Technical Patterns section population (was empty).
- **Embeddings** — Supabase MCP returned Unauthorized (no SUPABASE_ACCESS_TOKEN in cron env). All 4 embeddings skipped. `kb_articles` table NOT updated this run. Follow-up: populate embeddings once MCP auth wired into cron environment, or run `/kb-compile --embed-only` interactively.
- **Cross-references** — all 4 articles cite ≥1 existing wiki page via `[[slug]]` inline; two pgvector articles cross-link each other for strategic/tactical split.

## [2026-04-12 19:00] discover+compile | cron 18:00 | commits=3 raw=4 wiki=4

## [2026-04-13 06:00] discover | cron autopop | raw=+10 categories=5/7 deduped=13 errors=0

Headless cron run. DDG rate-limited after first query — fell back to direct blog index scraping (GHL blog, Anthropic engineering, Birdeye blog, Intercom blog). Searched blog index pages via curl, applied relevance filter, deduped against known-urls.json.

- **competitors** (2): GHL automate-billing, Intercom Fin Apex vertical models
- **ai-llm** (2): Anthropic managed-agents engineering, building-effective-agents
- **technical** (2): Anthropic advanced-tool-use, contextual-retrieval
- **regulations** (2): HIPAA AI chatbots 2026 (edinsol), HIPAA AI tools 2026 (justinhealthcareai)
- **growth** (2): Birdeye AEO guide, Birdeye community/AI brand discovery
- **small_biz_saas** — SKIPPED (no blog sources, DDG rate-limited)
- **verticals** — SKIPPED (no blog sources, DDG rate-limited)
- **known-urls.json** — 41 total (was 18, +10 fetched, +13 rejected/filtered)

## [2026-04-13 06:08] compile | batch (4 entries)

- **regulations** HIPAA — Privacy Rule, Security Rule, and Covered Entities → `wiki/regulations/hipaa-overview-cdc.md` (indexed; article pre-existed from prior partial compile)
- **regulations** HIPAA Five Titles and the 2024 Security Rule NPRM → `wiki/regulations/hipaa-titles-and-security-rule-2024-nprm.md` (indexed; article pre-existed from prior partial compile)
- **ai-llm** Claude Opus 4.6 — Frontier Agentic Intelligence and 1M Context → `wiki/ai-llm/claude-opus-4-6-capabilities.md` (new)
- **ai-llm** Claude Sonnet 4.6 — Opus-Class Performance at Sonnet Pricing → `wiki/ai-llm/claude-sonnet-4-6-capabilities.md` (new)
- **embeddings**: 0/4 stored (Supabase MCP unreachable — SUPABASE_ACCESS_TOKEN auth failure)
- **INDEX.md**: updated — 14 total articles
- **PENDING.md**: 4 entries removed, 12 remaining

## [2026-04-13 06:15] discover+compile | cron 06:00 | commits=2 raw=10 wiki=8

## [2026-04-13 18:12] discover | cron autopop | raw=+0 categories=7/7 urls_found=10 content_failed=10

Headless cron run. Sandbox blocked outbound curl — fell back to Google News RSS (xml.etree) + googlenewsdecoder for URL resolution. All 7 categories searched (top 3 queries each), relevance-filtered, deduped against known-urls.json.

**Discovery succeeded** — found 10 new relevant URLs across all 7 categories. **Content extraction failed** — all 10 sites are JS-rendered; curl fetched empty HTML shells. Raw files written then deleted after content quality check revealed zero usable text.

**Root cause:** `agent-browser` not installed on this machine. Curl cannot extract content from JS-rendered pages (Newswire, CNBC, GitHub Blog, Hostinger, TechTarget, etc.). Previous successful cron runs used agent-browser which handles JS.

**Action needed:** Install agent-browser, or re-fetch these 10 URLs interactively via `/kb-ingest`.

- URLs discovered and saved to known-urls.json (10 new + 4 rejected = 14 added)
- **Rejected** (3): Chandigarh TiECon (generic conference), Forbes small business loans (not SaaS), Digital Piloto openPR (low-value press release)
- **Failed** (1): hipaajournal.com 403 Forbidden
- **known-urls.json**: 41 → 55 total

## [2026-04-13 18:30] compile | headless-cron-batch | compiled=4 embeddings=0 embedding_errors=4

Processed 4 of 12 pending entries (4-entry cap). Remaining: 8 entries (2 ai-llm, 2 technical, 2 regulations, 2 growth).

- **Compiled (indexed from prior partial run — articles existed, INDEX.md/PENDING.md not updated):**
  - `wiki/competitors/ghl-15-minute-ai-responder.md` (from raw/competitors/ghl-15-minute-ai-responder.md)
  - `wiki/competitors/ghl-email-marketing-march-2026.md` (from raw/competitors/ghl-email-marketing-report-feb-2026.md)
- **Compiled (new articles):**
  - `wiki/competitors/ghl-subscription-billing-automation.md` (from raw/competitors/ghl-automate-billing.md)
  - `wiki/competitors/intercom-fin-apex-vertical-models.md` (from raw/competitors/intercom-fin-apex-vertical-models.md)
- **INDEX.md**: updated — 18 total articles (was 14)
- **PENDING.md**: 4 entries marked compiled, 8 remaining
- **Embeddings**: 0/4 stored (Supabase MCP Unauthorized — SUPABASE_ACCESS_TOKEN not available in cron env)
