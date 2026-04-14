# Knowledge Base Index

Master catalog of all compiled wiki articles. Auto-maintained by `/kb-compile`.

## Statistics
- Total articles: 22 (plus 1 in `_outputs/`)
- Last compiled: 2026-04-13
- Auto-populate: every 6 AM + 6 PM via `scripts/daily/kb-autopopulate.sh`

## Articles by Category

### Competitors
- [Competitive Landscape — March 2026](wiki/competitors/competitive-landscape-march-2026.md) — Analysis of 8 major competitors; AgentNexLiFy is feature-complete, gap is engagement/stickiness. Tags: intercom, drift, tidio, livechat, crisp, freshchat, hubspot, gohighlevel
- [GoHighLevel — Agency-Focused All-in-One Platform](wiki/competitors/gohighlevel-agency-platform.md) — 1M+ businesses, 7M+ AI voice calls, $97–497/mo white-label SaaS; #1 direct competitor. Tags: gohighlevel, crm, ai-employee, agency, white-label
- [GoHighLevel Scale Metrics (v3)](wiki/competitors/gohighlevel-scale-metrics-v3.md) — Scale benchmarks from GHL home page v3: leads, appointments, voice volume. Tags: gohighlevel, scale-metrics, benchmarks
- [GoHighLevel's 15-Minute AI Responder Positioning](wiki/competitors/ghl-15-minute-ai-responder.md) — Speed-to-lead pitch: HBR stats (7x conversations in 1hr, 80% drop after 5min), one-platform AI consolidation. Tags: gohighlevel, lead-response-time, ai-responder, voice-ai
- [GoHighLevel Email Infrastructure — March 2026 Performance Benchmarks](wiki/competitors/ghl-email-marketing-march-2026.md) — 1.37B emails in March 2026; 97.47% delivery, 40.80% open, 5.46% CTR on dedicated domains. Tags: gohighlevel, email-deliverability, open-rate, ctr
- [GoHighLevel Subscription Billing — Recurring Revenue Automation](wiki/competitors/ghl-subscription-billing-automation.md) — Native recurring billing extends GHL's all-in-one positioning into payments infrastructure. Tags: gohighlevel, subscription-billing, recurring-revenue, payments
- [Intercom Fin Apex — Custom Vertical Model for Customer Service](wiki/competitors/intercom-fin-apex-vertical-models.md) — Custom-trained model beats GPT-5.4 and Opus 4.5 at service; ~2M issues/week, ~$100M ARR, signals vertical AI companies building own models. Tags: intercom, fin-apex, vertical-models, customer-service-ai

### AI/LLM Developments
- [LLM Wiki — Karpathy's Compounding Knowledge Base Pattern](wiki/ai-llm/llm-wiki-karpathy-pattern.md) — LLM Wiki replaces RAG's ephemeral retrieval with a persistent, self-maintaining wiki where every source updates multiple entity pages simultaneously. Tags: knowledge-management, rag, llm-wiki, karpathy, compounding-knowledge
- [Anthropic — Mission, Safety Stance, and 2026 Release Cadence](wiki/ai-llm/anthropic-mission-and-latest-releases.md) — Opus 4.6 is the frontier model, "space to think" signals ad-free product stance, RSP gates downstream agentic capabilities. Tags: anthropic, claude, model-releases, ai-safety, responsible-scaling
- [Anthropic Careers — Operating Principles and Vendor Durability Signals](wiki/ai-llm/anthropic-careers-and-culture.md) — Seven operating principles and hiring bar as vendor-durability signals for the Claude dependency. Tags: anthropic, culture, operating-principles, vendor-risk, hiring
- [Claude Opus 4.6 — Frontier Agentic Intelligence and 1M Context](wiki/ai-llm/claude-opus-4-6-capabilities.md) — Opus 4.6 leads Terminal-Bench 2.0, HLE, and GDPval-AA by 144 Elo over GPT-5.2; 1M context, agent teams, adaptive thinking. Tags: claude, opus-4-6, agentic-coding, 1m-context, extended-thinking
- [Claude Sonnet 4.6 — Opus-Class Performance at Sonnet Pricing](wiki/ai-llm/claude-sonnet-4-6-capabilities.md) — Sonnet 4.6 approaches Opus at $3/$15; 70% preferred over Sonnet 4.5 in Claude Code, state-of-the-art computer use. Tags: claude, sonnet-4-6, computer-use, cost-efficiency, osworld
- [Managed Agents Architecture — Decoupling Brain from Hands](wiki/ai-llm/anthropic-managed-agents-architecture.md) — Anthropic's Managed Agents decouple harness, session, and sandbox into independent interfaces; p50 TTFT down 60%, credential isolation via vault proxy. Tags: managed-agents, anthropic, agent-architecture, session-durability, sandbox-isolation
- [Building Effective AI Agents — Anthropic's Pattern Catalog](wiki/ai-llm/anthropic-building-effective-agents.md) — Five composable workflow patterns (chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer) plus autonomous agents; simplicity over frameworks. Tags: agent-patterns, workflows, orchestration, tool-use, anthropic

### Small Business SaaS
_No articles yet._

### Vertical Industries
- [Customer Gaps by Industry](wiki/verticals/customer-gaps-by-industry.md) — Product-market fit across 7 industries; Salon 9/10, Plumber 8/10, Dental 8/10. Tags: salon, plumber, dental, restaurant, fitness, lawyer, real-estate

### Technical Patterns
- [pgvector — Native Vector Search in Postgres](wiki/technical/pgvector-postgres-vector-search.md) — Open-source Postgres extension powering AgentNexLiFy's KB search; six distance metrics, HNSW/IVFFlat indexes, hybrid queries. Tags: pgvector, postgres, embeddings, semantic-search, hnsw, ivfflat
- [pgvector Implementation Guide — Build, Enable, Query](wiki/technical/pgvector-implementation-guide.md) — Hands-on install, first query, and Python psycopg2 pattern for pgvector on self-managed Postgres. Tags: pgvector, postgres, installation, psycopg2, hybrid-search, tutorial
- [Advanced Tool Use — Search, Programmatic Calling, and Examples](wiki/technical/anthropic-advanced-tool-use.md) — Three Claude API features: Tool Search Tool (85% token reduction), Programmatic Tool Calling (37% savings), Tool Use Examples (72%→90% accuracy). Tags: tool-use, tool-search, programmatic-calling, tool-examples, claude-api
- [Contextual Retrieval — Reducing RAG Failure Rates by 67%](wiki/technical/anthropic-contextual-retrieval.md) — Prepend chunk-specific context before embedding/BM25 indexing; 49% fewer retrieval failures (67% with reranking) at $1.02/M tokens. Tags: contextual-retrieval, rag, embeddings, bm25, reranking, prompt-caching

### Regulations & Compliance
- [HIPAA — Privacy Rule, Security Rule, and Covered Entities](wiki/regulations/hipaa-overview-cdc.md) — HIPAA Privacy/Security Rules bind any business associate handling PHI; defines AgentNexLiFy's exposure for dental/medical tenants. Tags: hipaa, phi, ephi, privacy-rule, security-rule, healthcare-compliance
- [HIPAA Five Titles and the 2024 Security Rule NPRM](wiki/regulations/hipaa-titles-and-security-rule-2024-nprm.md) — Title II drives SaaS compliance; 2024 NPRM mandates encryption, MFA, annual audits, 72-hour recovery for ePHI platforms. Tags: hipaa, hitech, security-rule, nprm-2024, encryption, mfa

### Growth & Distribution
- [Post-Launch Growth Strategy](wiki/growth/post-launch-growth-strategy.md) — Top 10 features for activation, viral growth, daily engagement, and lock-in. Tags: activation, retention, viral-growth, onboarding, quickbooks, reviews

## Cross-Reference Map
- [[competitive-landscape-march-2026]] ← referenced by: [[customer-gaps-by-industry]], [[post-launch-growth-strategy]], [[llm-wiki-karpathy-pattern]]
- [[customer-gaps-by-industry]] ← referenced by: [[post-launch-growth-strategy]]
- [[post-launch-growth-strategy]] ← referenced by: [[customer-gaps-by-industry]], [[llm-wiki-karpathy-pattern]]
- [[llm-wiki-karpathy-pattern]] ← referenced by: (new — no backlinks yet)
