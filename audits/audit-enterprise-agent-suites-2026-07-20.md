# Audit — Enterprise AI Agent Suites vs AgentNexlify

Date: 2026-07-20
Scope: Amazon Quick Suite, Microsoft Copilot Studio (+ Agent 365 / Entra Agent ID), Google Gemini Enterprise Agent Platform (formerly Vertex AI / Agentspace; AI Studio is its dev-facing front door), Salesforce Agentforce. Brief peers: ServiceNow AI Agents, OpenAI AgentKit.
Method: web research (July 2026 sources) cross-checked against the actual AgentNexlify surface (`backend/services/managed_agents_registry.py`, `backend/routers/widget_chat.py`, os_actions, integrations, loop-health). KB competitor wiki covers SMB rivals (GHL, Birdeye, Intercom Fin) but had no enterprise-suite coverage — this audit fills that gap.

---

## 1. Suite profiles (what each one is, and its standout capability)

### Amazon Quick Suite (replaced Amazon Q Business, GA late 2025)
- Unified "agentic workspace": Quick Sight (NL-query BI), Quick Research (hours-long deep research agent over enterprise + web data), Quick Flows (end-user automation), Quick Automate (multi-agent, multi-department process automation incl. UI/browser automation), Quick Index (pooled enterprise data index, 30+ connectors).
- Third-party agents invokable in-chat (Box, Canva, PagerDuty) as of Jan 2026.
- Pricing: Free / $20/user Plus / $20/user Pro / $40/user Enterprise, **plus** $250/account/mo infrastructure fee on Pro+, plus metered "agent hours" ($3/agentic hr, $6/research hr overage) and $5/GB index overage.
- Standout: deep research + BI agents over a pooled org index; metered agent-hours model.

### Microsoft Copilot Studio + Agent 365
- Low-code agent builder publishing into M365, Teams, web, and external channels; 1,500+ Power Platform connectors; computer-using agents (UI automation) and real-time voice (May 2026); multi-agent orchestration with A2A + MCP GA (April 2026) — their new orchestration layer claims ~20% eval-performance gain at 50% fewer tokens.
- Agent 365 / Entra Agent ID: every agent gets a first-class **identity** — conditional access, human "sponsor" accountability, lifecycle management, org-wide agent registry/inventory (incl. non-Microsoft agents).
- Pricing: $200/tenant/mo for 25k messages, $10 per extra 1k; included with M365 Copilot seats for internal agents.
- Standout: governance depth (agent identity, registry, RBAC, audit) and connector breadth.

### Google Gemini Enterprise Agent Platform (Cloud Next '26 rebrand of Vertex AI + Agentspace)
- Two build paths: Agent Studio (low-code visual) and ADK (code-first, Python/Go/Java/TS) with graph-based supervisor→sub-agent orchestration mixing generative and **deterministic** paths for compliance-critical flows.
- A2A protocol in production as the cross-vendor interop standard (Agentforce agent → Google agent → ServiceNow agent on one task).
- Agent Memory Bank: auto-generated, curated long-term memory with per-user memory profiles.
- Model Garden: 200+ models incl. Claude as first-class.
- Google AI Studio remains the free dev/prototyping console (Gemini API keys, prompt tuning) — it is a developer on-ramp, not the enterprise suite itself.
- Standout: engineering-grade orchestration + memory + model choice.

### Salesforce Agentforce
- Agents defined by Topics + Instructions + Actions over CRM data; Agentforce Studio with built-in governance/observability; **Testing Center** (AI-generated test cases, batch CSV test suites, cheaper sandbox runs); Command Center analytics (latency, errors, escalation drill-down feeding topic/instruction refinement).
- Pricing: Flex Credits — $0.10/action ($0.15 voice), $500 per 100k credits, or $2/conversation; free starter allocation on Enterprise Edition orgs.
- Standout: the test-and-tune loop (Testing Center → Command Center → refine) as a product, plus AgentExchange marketplace.

### Cross-cutting enterprise buyer expectations (2026)
Runtime guardrails (pre/post-LLM PII, prompt-injection, hallucination policy gates), continuous evals on production traffic, OpenTelemetry-native per-step tracing, agent inventory/discovery, RBAC + audit trails, EU AI Act / NIST AI RMF / ISO 42001 mapping. ~40% of agentic projects are predicted to stall on inadequate controls — governance is now the purchase gate, not the model.

---

## 2. What they do differently and better than AgentNexlify (ranked by relevance to our market)

| # | Capability gap | They have | We have | SMB relevance |
|---|---|---|---|---|
| 1 | **Per-conversation observability** | Command-Center-style drill-in: per-run traces, latency/error/escalation analytics, step-level reasoning visibility | `/admin/loop-health`, BotHealthPage, morning digest — aggregate signals only; no way to open one conversation/run and see why the agent did what it did | HIGH — owners ask "why did it say that?"; today the answer requires us reading logs |
| 2 | **Agent testing / evals** | Agentforce Testing Center (batch suites, AI-generated cases), Copilot prompt-iteration tooling, continuous evals on prod traffic | Code-level pytest only; no tenant-facing bot-quality harness; KB/widget regressions surface via owner complaints | HIGH — cheapest trust builder we lack |
| 3 | **Customer-defined agents** | All four: customer creates new agents (topics/instructions/tools) via low-code builder | Fixed department registry in `managed_agents_registry.py`; tenants cannot add an agent or edit its instructions | MEDIUM-HIGH — even SMB owners want "make it also do X" |
| 4 | **Multi-agent orchestration + open interop (A2A/MCP)** | Supervisor→sub-agent graphs; A2A GA cross-vendor; MCP tool ecosystems | Single-hop routing to a department; no agent→agent delegation, no MCP client | MEDIUM — interop matters as clients adopt other agents |
| 5 | **Connector/action breadth + marketplace** | 1,500+ connectors (Copilot), 30+ index connectors + 3p agents (Quick), AgentExchange | ~8 native (Google Calendar, Drive KB, M365 mail/cal, HubSpot, Twilio BYO, GBP, Stripe) + Zapier escape hatch | MEDIUM — Zapier covers long tail but adds friction + cost |
| 6 | **Runtime guardrail layer** | Policy gates pre+post LLM: PII, injection, hallucination scoring, self-correction | `widget_guard` (rate/turn caps), propose-only records, PII strip on KB ingest — no outbound-content policy layer or hallucination scoring | MEDIUM — one bad auto-sent draft costs a tenant |
| 7 | **Governance: RBAC, audit, agent identity** | Entra Agent ID (identity, conditional access, sponsors), org agent registry, audit exports, compliance mapping | Single-owner tenants; `activity_log` is a partial audit trail; no roles, no export | LOW-MEDIUM today; HIGH if we ever sell multi-seat/agency |
| 8 | **Deep research + NL-query BI** | Quick Research (multi-hour agent), Quick Sight NL BI over pooled index | Lightweight research worker; fixed dashboard pages (Attribution, BotHealth, etc.) | MEDIUM — "ask your business a question" is a compelling demo |
| 9 | **Long-term memory** | Gemini Memory Bank: curated memories + per-user profiles | Routing memory only; conversations don't compound into durable tenant/customer memory | MEDIUM |
| 10 | **Model choice** | Model Garden 200+; multi-model routing | Pinned Claude family (per-tenant override of widget model ID only) | LOW for SMB (our routing is a feature, not a gap) |
| 11 | **Computer-use / RPA automation** | Copilot computer-using agents; Quick Automate UI automation | None | LOW — our tenants' work lives in the integrations we already hit via API |
| 12 | **Usage metering + cost controls surfaced to buyer** | Credits/agent-hours with dashboards, budget alerts, true-ups | Flat plans + internal `ai_usage_guard` token baselines — owner never sees usage | LOW-MEDIUM — flat price is a selling point, but zero visibility invites "what am I paying for?" churn |

### What the suites do *differently* (not better) — and why we shouldn't copy it
- **Build-vs-buy posture.** All four sell a *toolkit* that assumes a maker/admin/IT function exists. Setup is days-to-months (Agentforce implementations routinely need SI partners). Our buyer has nobody to staff that. Done-for-you departments are the product.
- **Consumption pricing.** $0.10/action, agent-hours, $250/mo infra fees, message packs — powerful for enterprises, terrifying for a coffee shop. Flat $19.99/$99.99 with an internal usage guard is a moat, not a lag.
- **Horizontal generality.** Suites optimize for any workflow in any department; answers come from a generic index. Our per-tenant vertical KB + widget-first lead capture ties the agent to revenue outcomes (leads, bookings, invoices) instead of productivity vibes.
- **Employee-facing vs customer-facing.** Quick/Copilot/Gemini agents mostly serve the company's *employees*. Nexlify's primary agent faces the tenant's *customers* and feeds an owner-approval loop. Only Agentforce (Service) and Intercom Fin really compete on that axis — already covered in KB.

### Where AgentNexlify is ahead of the suites (keep and market these)
- Time-to-value: paste one script tag → capturing leads same day; no maker, no SI partner.
- Propose-only trust model on customer/financial records (`propose-only-records.md`) — enterprises are only now bolting on equivalent policy gates.
- Owner-alert + digest loop: the agent reports to the owner daily without being asked.
- All-in price certainty at 1/2 to 1/10 the effective cost for our workloads.
- Vertical KB pattern per tenant vs generic org index.

---

## 3. Recommendations (adopt-cheaply list, ranked)

1. **Per-run trace viewer** — surface existing `chat_messages` + OS run/action rows as an owner-visible timeline ("what the agent saw → decided → did"). Data already stored; UI-only work. Mirrors Command Center at ~0 marginal cost. Biggest gap-closer.
2. **Golden-question eval harness** — per-tenant list of Q→expected-grounding pairs, run deterministically after each KB compile + nightly; regression alert into the digest. Mirrors Testing Center; deterministic-first, no LLM judge needed for v1.
3. **Owner-facing usage meter** — expose `ai_usage_guard` consumption per department on the dashboard. Kills "what am I paying for?" churn and pre-empts plan-tier upsell conversations.
4. **Per-department custom instructions ("topics-lite")** — one text field per department merged into the system prompt, with guardrail invariants pinned. Smallest credible step toward customer-defined agents; no builder UI needed.
5. **MCP client support in Agent OS** — one implementation buys an entire connector ecosystem and future A2A positioning; replaces per-connector build cost for the long tail.
6. **Outbound guardrail pass** — PII/claims screen on drafts before auto-send (Haiku, deterministic rules first); injection screen on KB ingestion sources.
7. **Audit export** — CSV export of `activity_log` per tenant. Cheap checkbox that matters the day an agency/multi-location buyer shows up.

Not worth building now: computer-use RPA, model garden/BYO model, consumption billing, Entra-class agent identity (single-owner tenants), org-wide agent discovery.

---

## Sources
- AWS: aws.amazon.com/quick (+ /pricing), aboutamazon.com Quick Suite launch, AWS News Blog Quick Suite announcement, Jan-2026 3p-agents what's-new
- Microsoft: Copilot Studio blog (multi-agent April 2026, computer-use + voice May 2026), Copilot Studio pricing page, Learn docs (Entra Agent ID, Agent 365 registry convergence, ID Governance for agents), 2026 release-wave-1 plan
- Google: cloud.google.com Gemini Enterprise Agent Platform product page + launch blog, Cloud Next '26 coverage (TheNextWeb, Virtualization Review, AIwire)
- Salesforce: salesforce.com Agentforce pricing, Flex Credits guides (jitendrazaa, ekfrazo, magicfuse), Testing Center GA notes
- Buyer-expectation baseline: Arthur/Galileo/Superblocks/Vellum 2026 governance + guardrail platform guides
