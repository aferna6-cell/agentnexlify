# KB Log — Chronological Record

Append-only log of all knowledge-base operations. Format per Karpathy pattern:

```
## [YYYY-MM-DD HH:MM] <op> | <subject> | <metadata>
```

Ops: `ingest`, `compile`, `discover`, `query`, `lint`, `migrate`

Tail with: `grep "^## \[" log.md | tail -20`

---

## [2026-04-25 22:10] discover | cron autopop | found=4 ingested=4 deduped=0 skipped=5 (no source)
- ai-llm: anthropic-writing-tools-for-agents, anthropic-multi-agent-research-system
- competitors: intercom-kaizen-ai-era, birdeye-ai-multi-location-marketing
- skipped (no usable source): small_biz_saas, verticals, technical, regulations, growth — search MCPs returned 401 (exa/tavily/firecrawl), agent-browser not installed, sources.yaml has no blog URLs for these categories

## [2026-04-18 12:00] compile | competitor-landscape-2026-04-18 | 1 source → 5 wiki articles

Source: `raw/competitors/competitor-landscape-2026-04-18.md` (direct scrape of GHL, Drillbit, Phonely, Birdeye, Podium pricing pages on 2026-04-18 via agent-browser).

Created 5 entity profiles under `wiki/competitors/`:
- `gohighlevel.md` (482w)
- `drillbit.md` (434w)
- `phonely.md` (466w)
- `birdeye.md` (403w)
- `podium.md` (483w)

Embeddings: 5 Voyage AI voyage-3-lite 512-dim vectors generated, upserted into Supabase `kb_articles` via REST (`on_conflict=slug`, 201 Created). Hit Voyage free-tier 3 RPM rate limit once; batched into single call with 30s retry backoff.

Updated: `INDEX.md` (+5 competitor links, total 39 articles), `PENDING.md` (added compiled entry).

Existing `wiki/competitors/gohighlevel-agency-platform.md` preserved and cross-linked from new `gohighlevel.md` via `[[gohighlevel-agency-platform]]` backlink.

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

## [2026-04-13 18:22] discover+compile | cron 18:00 | commits=3 raw=0 wiki=0

## [2026-04-14 06:00] discover | cron 06:00 | found=3 ingested=3 skipped=4cats

- **Search method**: Bing RSS (agent-browser unavailable, DDG blocked curl, Bing RSS worked)
- **Categories processed**: 7 searched, 3 yielded articles (verticals, technical, regulations)
- **Skipped**: competitors (all known URLs), ai_llm (JS-rendered), small_biz_saas (noise: P.LEAGUE, stackexchange), growth (noise: Microsoft answers)
- **Ingested**:
  - `raw/verticals/mit-ai-chatbot-vulnerable-users-2026.md` — MIT study: AI chatbots less accurate for vulnerable users (2026-02-19)
  - `raw/technical/encore-pgvector-guide-2026.md` — Encore blog: pgvector vs dedicated vector DBs (2026-03-09)
  - `raw/regulations/ftc-warns-auto-dealers-deceptive-pricing-2026.md` — FTC warns 97 auto dealers on pricing (2026-03)
- **Rejected (added to known-urls.json)**: ~20 new URLs (Anthropic JS pages, GHL homepages, Drillbit plagiarism checker, dental clinics, HIPAA Journal Cloudflare block)
- **known-urls.json**: updated (57 → 76 entries)
- **Note**: Anthropic news pages (acquires-vercept, the-anthropic-institute) have relevant content but are fully JS-rendered — need agent-browser or Playwright to extract

## [2026-04-14 06:14] compile | headless-cron-batch | compiled=4 embeddings=0 embedding_errors=4

Processed 4 of 11 pending entries (4-entry cap). Remaining: 7 entries (2 regulations, 2 growth, 1 verticals, 1 technical, 1 regulations).

- **Compiled (new articles):**
  - `wiki/ai-llm/anthropic-managed-agents-architecture.md` (from raw/ai-llm/anthropic-managed-agents-engineering.md)
  - `wiki/ai-llm/anthropic-building-effective-agents.md` (from raw/ai-llm/anthropic-building-effective-agents.md)
  - `wiki/technical/anthropic-advanced-tool-use.md` (from raw/technical/anthropic-advanced-tool-use.md)
  - `wiki/technical/anthropic-contextual-retrieval.md` (from raw/technical/anthropic-contextual-retrieval.md)
- **INDEX.md**: updated — 22 total articles (was 18)
- **PENDING.md**: 4 entries marked compiled, 7 remaining
- **Embeddings**: 0/4 stored (Supabase MCP Unauthorized — SUPABASE_ACCESS_TOKEN not available in cron env)
- **Cross-references**: all 4 articles cite ≥1 existing wiki page via `[[slug]]`; managed-agents and advanced-tool-use cross-link each other

## [2026-04-14 06:20] discover+compile | cron 06:00 | commits=3 raw=3 wiki=4

## [2026-04-14 18:00] discover | cron autopop | raw=+10 categories=6/7 deduped=29 errors=0

Headless cron run. agent-browser unavailable, DDG blocked curl, Google News RSS (xml.etree) used for URL discovery. TheNewStack sitemap crawled for article URLs. Content extracted via JSON-LD articleBody (TheNewStack) and HTML paragraph extraction (others).

- **Search method**: Google News RSS for discovery → TheNewStack sitemap for URL resolution → curl + content extraction
- **Categories processed**: 7 searched, 6 yielded articles
- **Ingested** (10 articles):
  - `raw/ai-llm/tns-memory-ai-agents-context-engineering.md` — Memory for AI Agents: Context Engineering (1825 words)
  - `raw/ai-llm/tns-why-agentic-llm-systems-fail.md` — Why Agentic LLM Systems Fail (2610 words)
  - `raw/technical/tns-production-ai-agents-rag-fastapi.md` — Production AI Agents with RAG and FastAPI (2291 words)
  - `raw/technical/tns-pgvector-benchmarks-lie.md` — Why pgvector Benchmarks Lie (2828 words)
  - `raw/small-biz-saas/tns-dawn-saaspocalypse.md` — Dawn of a SaaSpocalypse (1853 words)
  - `raw/small-biz-saas/dataconomy-ai-models-subscription-cost.md` — AI Models Redefining Subscription Cost Efficiency (2532 words)
  - `raw/growth/pctechmag-2026-blueprint-search-visibility.md` — 2026 Blueprint for Search Visibility (536 words)
  - `raw/growth/proginsider-top-10-ai-chatbots-2026.md` — Top 10 AI Chatbots of 2026 (1505 words)
  - `raw/competitors/aimultiple-ai-agent-tools-2026.md` — Compare 50+ AI Agent Tools 2026 (3337 words)
  - `raw/verticals/bizneworleans-ai-assistant-contractors.md` — AI Assistant for Contractors (576 words)
- **Skipped**: regulations (all HIPAA/FTC/compliance sites returned 403 — Cloudflare bot protection)
- **Rejected** (19 URLs added to known-urls.json for dedup): drbicuspid, dentistrytoday, dataprotectionreport, letsdatascience, learn.g2.com, saastr, morganlewis, cyberscoop, transparencycoalition, hunton, jdsupra, pillsburylaw, dealershipguy, cybernews, bbntimes, augmentcode, mobihealthnews, solutionsreview
- **known-urls.json**: 76 → 104 total (+29)
- **Note**: TheNewStack is the most curl-friendly source — serves full HTML with content-column-post-body class. Regulations category consistently blocked across runs; needs agent-browser or Playwright for HIPAA Journal, Morgan Lewis, CyberScoop.

## [2026-04-14 18:20] compile | headless-cron-batch | compiled=4 embeddings=0 embedding_errors=4

Processed 4 of 17 pending entries (4-entry cap). Remaining: 13 entries (3 regulations, 3 technical, 2 ai-llm, 2 small-biz-saas, 2 growth, 1 competitors, 1 verticals — from 2026-04-14 morning + evening batches).

- **Compiled (new articles):**
  - `wiki/regulations/hipaa-ai-chatbot-compliance-2026.md` (from raw/regulations/hipaa-ai-chatbots-2026-edinsol.md) — BAA, encryption, audit logging, data minimization for healthcare chatbots
  - `wiki/regulations/hipaa-compliant-ai-tools-baa-guide.md` (from raw/regulations/hipaa-ai-tools-2026-justinhealthcare.md) — BAA availability matrix for AI tools; GHL has healthcare BAA
  - `wiki/growth/answer-engine-optimization-aeo-2026.md` (from raw/growth/birdeye-answer-engine-optimization.md) — AEO vs SEO vs GEO; 9x conversion for AEO-optimized brands
  - `wiki/growth/community-forums-ai-brand-discovery.md` (from raw/growth/birdeye-brand-discovery-community-ai.md) — Forums/Reddit as AI answer layer; community signals drive AI Overviews
- **INDEX.md**: updated — 26 total articles (was 22)
- **PENDING.md**: 4 entries marked compiled, 13 remaining
- **Embeddings**: 0/4 stored (Supabase MCP Unauthorized — SUPABASE_ACCESS_TOKEN not available in cron env)
- **Cross-references**: all 4 articles cite ≥1 existing wiki page; HIPAA articles cross-link each other + hipaa-overview-cdc + hipaa-titles; growth articles cross-link each other + post-launch-growth-strategy

## [2026-04-14 18:26] discover+compile | cron 18:00 | commits=16 raw=10 wiki=4

## [2026-04-17 18:04] discover | categories=5 | ingested=10 | rejected=2 (jdsupra empty body) | skipped=2 (verticals, regulations — no passing URLs)

## [2026-04-17 18:10] compile | 4 articles (cron headless) | pending=6 embeddings=0

Compiled from PENDING 2026-04-17 cron ingest batch (cap=4):
- `wiki/ai-llm/claude-opus-4-7-release.md` (1093 words)
- `wiki/ai-llm/claude-code-best-practices.md` (1527 words)
- `wiki/competitors/ghl-lead-recovery-system.md` (1228 words)
- `wiki/competitors/intercom-fin-monitors-observability.md` (1262 words)

INDEX.md total: 26 → 30. 6 entries remain in PENDING for next run.

Embeddings skipped: Supabase MCP returned Unauthorized (SUPABASE_ACCESS_TOKEN missing). Per spec fallback, markdown compile completed without embeddings. embedding_errors=4.

## [2026-04-17 18:12] discover+compile | cron 18:00 | commits=4 raw=10 wiki=4
## 2026-04-18T10:05Z discover | processed=2 | ingested=4 (2 competitors + 2 ai-llm) | rejected_filtered_pre_fetch | curl fallback (no agent-browser)

## [2026-04-18 06:13] discover+compile | cron 06:00 | commits=3 raw=4 wiki=4

## kb-autopopulate 2026-04-18T22:03:01.633150+00:00
categories_processed=7  urls_fetched=2  new_raw_files=2  deduped=1  errors=0
- [competitors] gohighlevel-its-time-to-take-your-agency-to-the-next-level.md ← https://duckduckgo.com/y.js?ad_domain=gohighlevel.com&ad_provider=bingv7aa&ad_type=txad&click_metadata=7UAy0tWnY7sQXZIpzrbGe6cL2Jm3LusD%2DQexyL85ykMdiXJ4%2DHkY3vLJDqbvQ8SbMSuBnbXyFRetcDz6gYSXLZw%2DzhWC8GL4UqrVqVChP5VxdSZC8YwsUZ0LMPpNfL9Owl%2DTAuVjwKZwDMsPWjcbeoFQHLv6IRu4oVSJc_aWELc.rGa_AsTFqbWvhe8QuRuFag&rut=0b39de54c5158090f4943d0b32fb0f1ba69289f1d66215bea4edff80d83a60b3&u3=https%3A%2F%2Fwww.bing.com%2Faclick%3Fld%3De8Nm_Kbou0xnNw88ukkeqaQDVUCUxh%2DForOX71LX4pDOePwY%2DgIMvv3tdxujZByz2tXQ9DRALrz4f_qhDn3cHRXz2c7hiC3mqhBUrjxMzg%2D06iJLAZ7PQ5K5uk40WzzFB21kGng8Y5iQhChr10c%2D%2DXn1QMN%2DTHv5eWm5L9nzQn1B5WIZ1er24COLLM0u_b2iwmEtTJgrFJQV72R3alVNGhz2RvTf8%26u%3DaHR0cHMlM2ElMmYlMmZnb2hpZ2hsZXZlbC5jb20lM2YlMmYlM2ZmcF9yZWYlM2RnZXQtdHJpYWwlMjZtc2Nsa2lkJTNkN2I1MWFlYzlmYTA0MTM4MWYwMTNjNzJhMDU3MjE4ZWY%26rlid%3D7b51aec9fa041381f013c72a057218ef&vqd=4-185777231272257785694152835621178639069&iurl=%7B1%7DIG%3D3202F98D8F7544D49555BE24BDFD83B8%26CID%3D28783CF19BB1618317152BCE9A3A600F%26ID%3DDevEx%2C5046.1
- [competitors] gohighlevel-updates-2026-gohighlevelai.md ← https://www.gohighlevel.ai/blog/gohighlevel-updates-2026
- removed DDG ad redirect URL file (gohighlevel-its-time-to-take-your-agency-to-the-next-level.md, homepage spam) → kept 1 valid article (gohighlevel-updates-2026-gohighlevelai.md)

## [2026-04-18 18:11] discover+compile | cron 18:00 | commits=10 raw=1 wiki=4

## [2026-04-19 22:06] discover | cron kb-autopopulate | categories=7 fetched=14 new_raw=12 deduped=0 errors=2

- Fallback: agent-browser unavailable → curl + DDG HTML POST search
- New raw files: 12 across 7 categories (competitors, ai-llm, small-biz-saas, verticals, technical, regulations, growth)
- Errors: thin_body on saaspricelab.com + captahq.com (SPA-rendered, curl got shell HTML)
- Dedup source: known-urls.json (139 → 153)

## [2026-04-19 18:14] discover+compile | cron 18:00 | commits=6 raw=12 wiki=4

## [2026-04-20 10:02] discover | cats=7 fetched=0 new=0 rejected=0 errors=23
- competitors: new=0 fetched=0 rejected=0 errors=5
- ai_llm: new=0 fetched=0 rejected=0 errors=3
- small_biz_saas: new=0 fetched=0 rejected=0 errors=3
- verticals: new=0 fetched=0 rejected=0 errors=3
- technical: new=0 fetched=0 rejected=0 errors=3
- regulations: new=0 fetched=0 rejected=0 errors=3
- growth: new=0 fetched=0 rejected=0 errors=3

## [2026-04-20 10:03] discover | cats=7 fetched=23 new=14 rejected=9 errors=6
- competitors: new=2 fetched=2 rejected=0 errors=0
- ai_llm: new=2 fetched=2 rejected=0 errors=0
- small_biz_saas: new=2 fetched=2 rejected=0 errors=1
- verticals: new=2 fetched=3 rejected=1 errors=4
- technical: new=2 fetched=9 rejected=7 errors=0
- regulations: new=2 fetched=2 rejected=0 errors=1
- growth: new=2 fetched=3 rejected=1 errors=0

## [2026-04-20 10:05] post-run filter | removed 4 low-quality
- competitors: the-only-helpdesk-designed-for-the-ai-agent-era.md (vendor landing)
- technical: the-ai-gateway-for-developers.md (product page, no article)
- verticals: drug-dealer-s-new-teeth-brag-leads-to-jail.md (crime news, not vertical relevance)
- verticals: convicted-dentist-arrested-for-practicing-without-a-license.md (crime news)
URLs kept in known-urls.json to prevent retry.

## [2026-04-20 06:12] discover+compile | cron 06:00 | commits=3 raw=10 wiki=4

## [2026-04-20T22:03:18Z] discover | blogs-only fallback | ingested 4 / candidates 4
- [competitors] tidio-best-agentic-customer-service-software <- https://www.tidio.com/blog/best-agentic-customer-service-software/
- [competitors] intercom-fin-product-updates-feb-2026 <- https://www.intercom.com/blog/fin-product-updates-february-recap/
- [ai-llm] anthropic-harness-design-long-running-apps <- https://www.anthropic.com/engineering/harness-design-long-running-apps
- [ai-llm] anthropic-claude-code-sandboxing <- https://www.anthropic.com/engineering/claude-code-sandboxing
- skipped: small-biz-saas, verticals, technical, regulations, growth (no blog URLs in sources.yaml, no search tool available)

## [2026-04-20T22:03:57Z] discover-rejects | blacklisted 17 non-article/off-topic URLs

## [2026-04-20 18:11] discover+compile | cron 18:00 | commits=10 raw=4 wiki=4

## [2026-04-21T10:02:45+00:00] kb-autopopulate | categories=7 fetched=0 new_raw=0 deduped=0 rejected=0 errors=0

## [2026-04-21T10:06:38+00:00] kb-autopopulate-rss | categories=2 fetched=4 new_raw=4 deduped=39 rejected=65 errors=0

## [2026-04-21T10:08:45+00:00] kb-autopopulate-rss | categories=1 fetched=2 new_raw=2 deduped=0 rejected=0 errors=0

## [2026-04-21 06:17] discover+compile | cron 06:00 | commits=5 raw=3 wiki=4

## [2026-04-21T22:01:40+00:00] discover | cats=7 fetched=2 written=2 deduped=2 rejected=3 errors=0

## [2026-04-21T22:04:07+00:00] discover | cats=7 fetched=8 written=8 deduped=2 rejected=9 errors=0

## [2026-04-21T22:05:13+00:00] discover (retry) | cats=3 fetched=0 written=0 deduped=0 rejected=0 errors=0

## [2026-04-21 18:12] discover+compile | cron 18:00 | commits=5 raw=10 wiki=4

## [2026-04-23 18:03] discover | categories=7 fetched=4 new_files=4 deduped=4 errors=0 known_added=5

## [2026-04-23 18:05] discover-retry | new_files=0 added_known=0

## [2026-04-23 18:06] discover-startpage | new_files=10

## [2026-04-23 18:15] discover+compile | cron 18:00 | commits=1 raw=14 wiki=4

## [2026-04-24 10:06] discover | cron 06:00 | categories=6 urls_fetched=14 new_raw_files=11 deduped=0 errors=3

## [2026-04-24 06:10] compile | cron 06:00 headless | pending=16 compiled=4 wiki=4 index_touched=1 embeddings_skipped=4 errors=0

## [2026-04-24 06:16] discover+compile | cron 06:00 | commits=2 raw=11 wiki=4

## [2026-04-24 18:13] discover+compile | cron 18:00 | commits=2 raw=8 wiki=4

## [2026-04-25 10:35] compile | GoHighLevel AI Changelog 2024-2026 | competitors → wiki/competitors/ghl-ai-changelog-2024-2026.md (embedded)
## [2026-04-25 10:35] compile | GHL API V2 + AI Employee Funnel Stack | competitors → wiki/competitors/ghl-ai-employee-api-v2-funnels-2026.md (embedded)
## [2026-04-25 10:35] compile | Claude Release Notes Feb-Apr 2026 | ai-llm → wiki/ai-llm/anthropic-claude-release-notes-feb-apr-2026.md (embedded)
## [2026-04-25 10:35] compile | Claude Code v2.1.118 + v2.1.119 | ai-llm → wiki/ai-llm/claude-code-v2-1-118-119-release-notes.md (embedded after 429 retry)

## [2026-04-25 06:15] discover+compile | cron 06:00 | commits=3 raw=4 wiki=4

## [2026-04-25 18:20] discover+compile | cron 18:00 | commits=2 raw=4 wiki=4
## [2026-04-26T22:03:39Z] discover | cats=1 fetched=2 new_raw=2 dedup=5 errors=1
## [2026-04-26T22:06:34Z] discover-pass2 | cats=1 fetched=2 new_raw=2 dedup=7 errors=0

## [2026-04-26 22:10] compile (cron) | 4 articles compiled, 4 embedding skipped (Supabase MCP unauthorized)
- ghl-manus-ai-monday-google-forms-integrations-2026 (competitors)
- ghl-pricing-2026-true-monthly-cost-with-addons (competitors)
- anthropic-election-safeguards-2026 (ai-llm)
- anthropic-nec-japan-partnership-2026 (ai-llm)
- INDEX.md updated: 83 → 87 articles
- embedding_errors=4 (Supabase MCP returned Unauthorized; markdown compile completed)

## [2026-04-26 18:15] discover+compile | cron 18:00 | commits=1 raw=4 wiki=0

## [2026-04-27 22:17] discover | found 16 candidates | ingested 10 | skipped 2 categories (small-biz-saas, growth — DDG anomaly captcha)

## [2026-04-27 18:25] discover+compile | cron 18:00 | commits=2 raw=10 wiki=4

## [2026-04-28 23:30] compile (cron) | 4 articles compiled, 4 embedding skipped (Supabase MCP unauthorized)
- ghl-voice-ai-review-2026 (competitors)
- claude-prompt-caching-cost-optimization-kissapi (ai-llm)
- ai-receptionist-general-contractors-2026 (verticals)
- tcpa-sms-compliance-2026 (regulations)
- INDEX.md updated: 92 → 95 articles
- embedding_errors=4 (Supabase MCP returned Unauthorized; markdown compile completed)

## [2026-04-29 08:18] discover+compile | cron 18:00 | commits=3 raw=0 wiki=4

## [2026-04-29 cron] compile | 3 articles compiled, embeddings skipped (no VOYAGE_API_KEY in cron env), 1 raw skipped
- anthropic-managed-agents-pricing-finout-2026 (ai-llm)
- churnfree-b2b-saas-churn-benchmarks-2026 (small-biz-saas)
- vantainsights-saas-churn-federal-baseline-2026 (small-biz-saas)
- INDEX.md updated: 96 → 98 articles
- skipped: thenewstack-io-ai-agent-harness-pricing-split (raw is empty/JS-rendered, no extractable content)
- embedding_errors=3 (no Voyage key in cron env); kb_articles upsert NOT attempted

## [2026-04-29 18:19] discover+compile | cron 18:00 | commits=2 raw=0 wiki=3

## [2026-04-30 18:37] discover+compile | cron 18:00 | commits=2 raw=11 wiki=4

## [2026-05-01T22:05:21Z] discover | BLOCKED: network sandbox denies outbound + agent-browser not installed | found 0 | ingested 0

## [2026-05-01 18:19] discover+compile | cron 18:00 | commits=2 raw=0 wiki=4

## [2026-05-02 18:22] discover+compile | cron 18:00 | commits=6 raw=0 wiki=4

## [2026-05-05 11:16] discover+compile | cron 18:00 | commits=4 raw=0 wiki=0
